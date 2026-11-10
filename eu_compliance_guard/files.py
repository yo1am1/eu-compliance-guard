"""Atomic writes of the tool's own project files: never through a link, never a half-written file."""
from __future__ import annotations

import os
from pathlib import Path
import stat

from . import revalidation as r


def _swap_in(parent_fd: int, name: str, content: bytes, mode: int, exact: bool) -> None:
    """Write `content` to a temporary name beside `name`, then rename it over `name`.

    `mode` is the creation mode, narrowed by the user's umask like any new file; with `exact`
    the file gets exactly `mode` (to keep the permission bits of the file it replaces)."""
    # Created exclusively without following links, so a planted temp symlink is replaced, never written through.
    temporary = "." + name + ".tmp"
    try:
        os.unlink(temporary, dir_fd=parent_fd)
    except FileNotFoundError:
        pass
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600 if exact else mode, dir_fd=parent_fd)
    with os.fdopen(fd, "wb") as handle:
        if exact:
            os.fchmod(fd, mode)
        handle.write(content)
        handle.flush()
        os.fsync(fd)
    os.replace(temporary, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
    os.fsync(parent_fd)


def write_bytes(path: str | os.PathLike, content: bytes, mode: int = 0o644) -> Path:
    """Atomically create or replace a project file, never through a link or over a folder."""
    path = Path(path)
    with r._parent(path) as (parent_fd, name):
        try:
            info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode):  # an existing link or folder is never replaced
                raise r.RevalidationError("unsafe-path")
        except FileNotFoundError:
            pass
        _swap_in(parent_fd, name, content, mode, exact=False)
    return path


def replace_existing(parent_fd: int, name: str, content: bytes) -> None:
    """Atomically replace a writable project file, keeping its permission bits.

    Like an editor, a read-only file is refused rather than replaced: os.access for the
    caller, and the owner's write bit, which root's access check ignores.
    """
    info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode):
        raise r.RevalidationError("unsafe-path")
    mode = stat.S_IMODE(info.st_mode) & 0o777
    if not mode & stat.S_IWUSR or not os.access(name, os.W_OK, dir_fd=parent_fd, follow_symlinks=False):
        raise r.RevalidationError("io-failed")
    _swap_in(parent_fd, name, content, mode, exact=True)
