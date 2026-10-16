"""Trusted, offline Linux executor. Returned bytes are PRIVATE diagnostics, not Evidence.

Callers own grant/input checks and root-owned observed admission. No shell, project
hooks, provider access or browser-network policy is accepted by this runner.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import shutil
import socket
import tempfile
from typing import Literal


@dataclass(frozen=True)
class Limits:
    seconds: float = 60
    grace_seconds: float = 5
    output_bytes: int = 10 * 1024 * 1024
    address_bytes: int = 1024 * 1024 * 1024
    file_bytes: int = 32 * 1024 * 1024
    open_files: int = 128
    user_processes: int = 256

    def __post_init__(self):
        if any(type(n) not in (int, float) or not math.isfinite(n) or not 0 < n <= 86400
               for n in (self.seconds, self.grace_seconds)):
            raise ValueError("invalid execution time limits")
        for n in (self.output_bytes, self.address_bytes, self.file_bytes,
                  self.open_files, self.user_processes):
            if type(n) is not int or not 0 < n <= 2**40:
                raise ValueError("invalid execution resource limits")


@dataclass(frozen=True)
class ExecutionRequest:
    project_id: str
    run_id: str
    attempt_id: str
    generation: int
    executable: Path
    arguments: tuple[str, ...]
    snapshot: Path
    output: Path
    limits: Limits = field(default_factory=Limits)


@dataclass(frozen=True)
class ExecutionResult:
    project_id: str
    run_id: str
    attempt_id: str
    generation: int
    reason: Literal["exited", "blocked", "timeout", "cancelled", "output_limit", "supervisor_cancelled"]
    returncode: int | None
    cleanup: Literal["not_started", "namespace_exited", "unverified"]
    stdout: bytes = field(default=b"", repr=False)
    stderr: bytes = field(default=b"", repr=False)
    blocker: str | None = None


def _root(path: Path) -> Path:
    if not isinstance(path, Path) or not path.is_absolute() or path.resolve() != path:
        raise ValueError("execution roots must be absolute and contain no symlinks")
    if not path.is_dir() or path == Path("/"):
        raise ValueError("execution root is not an included directory")
    return path


def _system_tool(name: str) -> str:
    found = shutil.which(name, path="/usr/bin:/bin")
    if not found or Path("/usr") not in Path(found).resolve().parents:
        raise FileNotFoundError("required containment tools unavailable")
    return str(Path(found).resolve())


def _validate(request: ExecutionRequest):
    for identity in (request.project_id, request.run_id, request.attempt_id):
        if not isinstance(identity, str) or not identity or len(identity) > 128:
            raise ValueError("invalid execution identity")
    if type(request.generation) is not int or request.generation < 0:
        raise ValueError("invalid execution generation")
    snapshot, output = _root(request.snapshot), _root(request.output)
    if snapshot == output or snapshot in output.parents or output in snapshot.parents:
        raise ValueError("input and output roots must be disjoint")
    if output.stat().st_uid != os.getuid() or output.stat().st_mode & 0o077:
        raise ValueError("output root must be owned and private")
    if not isinstance(request.arguments, tuple) or len(request.arguments) > 256:
        raise ValueError("expected bounded argv tuple, not a shell command")
    if any(not isinstance(arg, str) or "\0" in arg for arg in request.arguments):
        raise ValueError("invalid argument")
    if sum(len(arg.encode()) for arg in request.arguments) > 65536:
        raise ValueError("argument size exceeds limit")
    tool = request.executable
    if not isinstance(tool, Path) or not tool.is_absolute():
        raise ValueError("reviewed executable must be absolute")
    resolved = tool.resolve()
    if not resolved.is_file() or not os.access(resolved, os.X_OK) or Path("/usr") not in resolved.parents:
        raise ValueError("reviewed executable must be in the system runtime")
    if resolved.name in {"sh", "bash", "dash", "zsh", "fish", "env"}:
        raise ValueError("shell launchers are not supported")
    if snapshot == Path("/usr") or Path("/usr") in snapshot.parents or snapshot in Path("/usr").parents:
        raise ValueError("snapshot cannot be part of the system runtime")
    if output == Path("/usr") or Path("/usr") in output.parents or output in Path("/usr").parents:
        raise ValueError("output cannot be part of the system runtime")


def build_command(request: ExecutionRequest, status_fd: int) -> tuple[list[str], dict[str, str]]:
    """Build only engine-reviewed argv. System /usr must contain no private inputs."""
    _validate(request)
    bwrap, prlimit = _system_tool("bwrap"), _system_tool("prlimit")
    limit = request.limits
    # shortcut: per-process/user rlimits, aggregate job quotas require delegated cgroups.
    command = [str(Path(prlimit).resolve()), f"--as={limit.address_bytes}",
               f"--cpu={math.ceil(limit.seconds)}", f"--fsize={limit.file_bytes}",
               f"--nofile={limit.open_files}", f"--nproc={limit.user_processes}", "--core=0", "--",
               str(Path(bwrap).resolve()), "--unshare-user", "--unshare-pid", "--unshare-net",
               "--unshare-ipc", "--unshare-uts", "--disable-userns", "--assert-userns-disabled",
               "--die-with-parent", "--new-session", "--cap-drop", "ALL", "--clearenv",
               "--json-status-fd", str(status_fd), "--ro-bind", "/usr", "/usr"]
    for directory in ("/bin", "/lib", "/lib64"):
        if Path(directory).exists():
            command += ["--ro-bind", directory, directory]
    command += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                "--dir", "/home/audit", "--ro-bind", str(request.snapshot), "/input",
                "--bind", str(request.output), "/output", "--chdir", "/input"]
    environment = {"PATH": "/usr/bin:/bin", "HOME": "/home/audit", "TMPDIR": "/tmp",
                   "XDG_CACHE_HOME": "/tmp/cache", "LC_ALL": "C.UTF-8"}
    for key, value in environment.items():
        command += ["--setenv", key, value]
    command += ["--", str(request.executable.resolve()), *request.arguments]
    return command, environment


def _namespace_exited(status: bytes, returncode: int | None) -> bool:
    if len(status) > 8192:
        return False
    try:
        records = [json.loads(line) for line in status.splitlines() if line.strip()]
        return (any(type(r.get("child-pid")) is int and r["child-pid"] > 0 for r in records)
                and any(type(r.get("exit-code")) is int and r["exit-code"] == returncode for r in records))
    except (ValueError, AttributeError, TypeError):
        return False


async def execute(request: ExecutionRequest, *, cancel: asyncio.Event | None = None) -> ExecutionResult:
    """One owned execution; caller must not publish audit success from this result.

    Missing final Bubblewrap status leaves cleanup unverified even after wait().
    No alternate unsandboxed launch is attempted. Cancellation of this coroutine
    performs bounded cleanup and returns supervisor_cancelled rather than abandoning children.
    """
    _validate(request)
    identity = (request.project_id, request.run_id, request.attempt_id, request.generation)
    if cancel is not None and cancel.is_set():
        return ExecutionResult(*identity, "cancelled", None, "not_started")
    with tempfile.TemporaryFile() as status:
        try:
            command, environment = build_command(request, status.fileno())
            spawning = asyncio.create_task(asyncio.create_subprocess_exec(
                *command, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE, env=environment, cwd="/", close_fds=True,
                pass_fds=(status.fileno(),), start_new_session=True))
            cancelled_during_spawn = False
            while True:
                try:
                    process = await asyncio.shield(spawning)
                    break
                except asyncio.CancelledError:
                    if spawning.cancelled():
                        return ExecutionResult(*identity, "blocked", None, "unverified",
                                               blocker="containment_spawn_cancelled")
                    cancelled_during_spawn = True
        except OSError:
            return ExecutionResult(*identity, "blocked", None, "not_started", blocker="containment_launch_unavailable")
        buffers = [bytearray(), bytearray()]
        overflow = asyncio.Event()

        async def drain(stream, index):
            while chunk := await stream.read(65536):
                remaining = max(0, request.limits.output_bytes - sum(map(len, buffers)))
                buffers[index].extend(chunk[:remaining])
                if len(chunk) > remaining:
                    overflow.set()

        finished = asyncio.gather(process.wait(), drain(process.stdout, 0), drain(process.stderr, 1),
                                  return_exceptions=True)
        watchers = [asyncio.create_task(overflow.wait())]
        if cancel is not None:
            watchers.append(asyncio.create_task(cancel.wait()))
        reason = "exited"
        try:
            if cancelled_during_spawn:
                raise asyncio.CancelledError
            done, _ = await asyncio.wait([finished, *watchers], timeout=request.limits.seconds,
                                         return_when=asyncio.FIRST_COMPLETED)
            if overflow.is_set():
                reason = "output_limit"
            elif cancel is not None and cancel.is_set():
                reason = "cancelled"
            elif finished not in done:
                reason = "timeout"
        except asyncio.CancelledError:
            reason = "supervisor_cancelled"
        finally:
            for watcher in watchers:
                watcher.cancel()
        async def collect():
            await asyncio.gather(*watchers, return_exceptions=True)
            if reason != "exited":
                for stop in (process.terminate, process.kill):
                    try:
                        stop()
                    except OSError:
                        pass
                    try:
                        await asyncio.wait_for(asyncio.shield(finished), request.limits.grace_seconds)
                        break
                    except asyncio.TimeoutError:
                        continue
            if not finished.done():
                finished.cancel()
            return (await asyncio.gather(finished, return_exceptions=True))[0]

        collecting = asyncio.create_task(collect())
        while True:
            try:
                completion = await asyncio.shield(collecting)
                break
            except asyncio.CancelledError:
                reason = "supervisor_cancelled"
        stream_failed = (isinstance(completion, BaseException)
                         or any(isinstance(item, BaseException) for item in completion))
        status.seek(0)
        cleanup = "namespace_exited" if _namespace_exited(status.read(8193), process.returncode) else "unverified"
        blocker = None
        if stream_failed and reason == "exited":
            reason, blocker = "blocked", "diagnostic_capture_failed"
        if cleanup == "unverified":
            blocker = "containment_or_cleanup_unverified"
            if reason == "exited":
                reason = "blocked"
        return ExecutionResult(*identity, reason, process.returncode, cleanup,
                               bytes(buffers[0]), bytes(buffers[1]), blocker)


@dataclass(frozen=True)
class ProbeCase:
    state: Literal["passed", "failed", "blocked"]
    reason: str


async def probe_containment(work_root: Path, *, authorized: bool = False) -> dict[str, ProbeCase]:
    """ROOT COORDINATOR ONLY: real synthetic probes; never invoked by unit tests.

    Root must authorize execution and retain the returned facts before constructing
    observed CapabilityObservation passes. No real secret/auth input is read.
    Owner-death needs an external owner/observer harness and remains blocked here.
    """
    if not authorized:
        raise PermissionError("root-authorized synthetic probe scope required")
    _root(work_root)
    with tempfile.TemporaryDirectory(prefix="executor-probe-", dir=work_root) as folder:
        base = Path(folder)
        snapshot, output = base / "snapshot", base / "output"
        snapshot.mkdir(mode=0o700)
        output.mkdir(mode=0o700)
        marker = base / "private-marker"
        marker.write_text("synthetic-private-marker")
        (snapshot / "readonly").write_text("synthetic-input")
        host_net = os.readlink("/proc/self/ns/net")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            code = '''import json, os, socket
from pathlib import Path
facts = {}
try:
    Path('/input/readonly').write_text('changed'); facts['readonly'] = False
except OSError:
    facts['readonly'] = Path('/input/readonly').read_text() == 'synthetic-input'
try:
    Path(PRIVATE).read_text(); facts['private_read'] = False
except OSError:
    facts['private_read'] = True
facts['environment'] = set(os.environ) <= {'PATH','HOME','TMPDIR','XDG_CACHE_HOME','LC_ALL'}
s = socket.socket(); s.settimeout(0.2)
try:
    s.connect(('127.0.0.1', PORT)); denied = False
except OSError:
    denied = True
facts['egress'] = denied and os.readlink('/proc/self/ns/net') != HOST_NET
print(json.dumps(facts), flush=True)
'''.replace("PRIVATE", repr(str(marker))).replace("PORT", str(port)).replace("HOST_NET", repr(host_net))
            request = ExecutionRequest("probe", "probe", "denial", 0, Path("/usr/bin/python3"),
                                       ("-I", "-S", "-c", code), snapshot, output, Limits(seconds=5, grace_seconds=1))
            result = await execute(request)
        names = ("readonly", "private_read", "environment", "egress")
        cases = {}
        try:
            facts = json.loads(result.stdout)
            if not isinstance(facts, dict):
                facts = {}
        except (ValueError, UnicodeError):
            facts = {}
        for name in names:
            if result.reason != "exited" or result.returncode != 0 or result.cleanup != "namespace_exited":
                cases[name] = ProbeCase("blocked", result.blocker or result.reason)
            else:
                cases[name] = ProbeCase("passed" if facts.get(name) is True else "failed", "synthetic_denial_observation")
        # No claimed coverage for cases which require a separate external observer.
        for name in ("descendant_cleanup", "owner_death", "aggregate_resource_limits"):
            cases[name] = ProbeCase("blocked", "external_observer_or_delegated_cgroup_proof_required")
        return cases
