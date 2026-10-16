"""Fake subprocess tests only; never launch a sandbox or target."""
import asyncio
from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from eu_compliance_guard.execution import ExecutionRequest, Limits, _namespace_exited, build_command, execute, probe_containment


class FakeProcess:
    def __init__(self, fd, *, out=b"", err=b"", running=False, status=True, stubborn=False, unkillable=False, code=0):
        self.fd, self.status = fd, status
        self.stubborn, self.unkillable = stubborn, unkillable
        self.returncode = None if running else code
        self.stdout, self.stderr = asyncio.StreamReader(), asyncio.StreamReader()
        self.stdout.feed_data(out)
        self.stderr.feed_data(err)
        self.stdout.feed_eof()
        self.stderr.feed_eof()
        self.done = asyncio.Event()
        if not running:
            self.done.set()
        self.terminated = self.killed = False

    async def wait(self):
        await self.done.wait()
        if self.status:
            os.write(self.fd, (json.dumps({"child-pid": 123}) + "\n" + json.dumps({"exit-code": self.returncode}) + "\n").encode())
        return self.returncode

    def terminate(self):
        self.terminated = True
        if not self.stubborn and not self.unkillable:
            self.returncode = -15
            self.done.set()

    def kill(self):
        self.killed = True
        if not self.unkillable:
            self.returncode = -9
            self.done.set()


class ExecutorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        snapshot, output = root / "input", root / "output"
        snapshot.mkdir(mode=0o700)
        output.mkdir(mode=0o700)
        self.request = ExecutionRequest("project", "run", "attempt", 3, Path("/usr/bin/true"), (), snapshot, output,
                                        Limits(seconds=.02, grace_seconds=.01, output_bytes=12))
        self.launcher = self.enterContext(patch("eu_compliance_guard.execution.asyncio.create_subprocess_exec", new_callable=AsyncMock))
        self.fake = None

    def process(self, **options):
        async def spawn(*args, **kwargs):
            self.fake = FakeProcess(kwargs["pass_fds"][0], **options)
            return self.fake
        self.launcher.side_effect = spawn

    def test_fixed_offline_command_minimal_environment(self):
        with patch.dict(os.environ, {"PRIVATE_TOKEN": "synthetic", "PYTHONPATH": "/untrusted"}):
            command, environment = build_command(self.request, 99)
        for flag in ("--unshare-user", "--unshare-pid", "--unshare-net", "--die-with-parent", "--disable-userns",
                     "--assert-userns-disabled", "--clearenv", "--new-session", "--core=0"):
            self.assertIn(flag, command)
        for flag in ("--as-pid-1", "--share-net", "--unshare-user-try"):
            self.assertNotIn(flag, command)
        self.assertEqual(set(environment), {"PATH", "HOME", "TMPDIR", "XDG_CACHE_HOME", "LC_ALL"})
        self.assertEqual(command[-2:], ["--", str(self.request.executable.resolve())])
        index = command.index(str(self.request.snapshot))
        self.assertEqual(command[index - 1:index + 2], ["--ro-bind", str(self.request.snapshot), "/input"])
        self.launcher.assert_not_called()

    async def test_invalid_roots_argv_and_limits_never_launch(self):
        link = Path(self.temp.name) / "link"
        link.symlink_to(self.request.snapshot, target_is_directory=True)
        for change in ({"snapshot": link}, {"output": self.request.snapshot}, {"snapshot": Path("/")},
                       {"snapshot": Path("relative")}, {"arguments": "echo shell"}, {"arguments": ("bad\0arg",)},
                       {"arguments": ("x" * 65537,)}, {"executable": Path("/usr/bin/sh")},
                       {"executable": Path("relative")}, {"generation": True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                await execute(replace(self.request, **change))
        self.request.output.chmod(0o755)
        with self.assertRaises(ValueError):
            await execute(self.request)
        for change in ({"seconds": float("nan")}, {"seconds": 0}, {"output_bytes": -1}, {"output_bytes": True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                Limits(**change)
        self.launcher.assert_not_called()

    async def test_private_capture_and_namespace_status(self):
        self.process(out=b"hello", err=b"private")
        result = await execute(self.request)
        self.assertEqual((result.reason, result.cleanup, result.generation), ("exited", "namespace_exited", 3))
        self.assertEqual((result.stdout, result.stderr), (b"hello", b"private"))
        self.assertNotIn("private", repr(result))
        self.assertEqual(self.launcher.call_args.kwargs["cwd"], "/")
        self.assertTrue(self.launcher.call_args.kwargs["close_fds"])
        self.assertNotIn("shell", self.launcher.call_args.kwargs)

    async def test_namespace_failure_never_falls_back(self):
        self.process(err=b"bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted", status=False, code=1)
        result = await execute(replace(self.request, limits=Limits(output_bytes=128)))
        self.assertEqual((result.reason, result.cleanup), ("blocked", "unverified"))
        self.assertNotIn("RTM_NEWADDR", repr(result))
        self.assertEqual(self.launcher.await_count, 1)

    async def test_missing_tools_and_spawn_failure_are_safe_blockers(self):
        with patch("eu_compliance_guard.execution.shutil.which", return_value=None):
            result = await execute(self.request)
        self.assertEqual((result.reason, result.cleanup), ("blocked", "not_started"))
        self.launcher.assert_not_called()
        self.launcher.side_effect = OSError("synthetic-private-diagnostic")
        result = await execute(self.request)
        self.assertEqual(result.blocker, "containment_launch_unavailable")
        self.assertNotIn("synthetic-private", repr(result))

    async def test_both_streams_share_one_cap(self):
        self.process(out=b"x" * 20, err=b"y" * 20, running=True)
        result = await execute(self.request)
        self.assertEqual(result.reason, "output_limit")
        self.assertEqual(len(result.stdout) + len(result.stderr), 12)
        self.assertTrue(self.fake.terminated)

    async def test_timeout_escalates_and_cleanup_stays_unverified(self):
        self.process(running=True, stubborn=True, status=False)
        result = await execute(self.request)
        self.assertEqual((result.reason, result.cleanup), ("timeout", "unverified"))
        self.assertTrue(self.fake.terminated and self.fake.killed)
        self.assertEqual(result.blocker, "containment_or_cleanup_unverified")

    async def test_unkillable_wait_is_bounded(self):
        self.process(running=True, unkillable=True, status=False)
        result = await asyncio.wait_for(execute(self.request), .5)
        self.assertEqual((result.reason, result.cleanup), ("timeout", "unverified"))
        self.assertTrue(self.fake.killed)

    async def test_cancel_before_and_during_execution(self):
        cancel = asyncio.Event()
        cancel.set()
        result = await execute(self.request, cancel=cancel)
        self.assertEqual((result.reason, result.cleanup), ("cancelled", "not_started"))
        self.launcher.assert_not_called()
        cancel.clear()
        self.process(running=True)
        task = asyncio.create_task(execute(replace(self.request, limits=Limits(seconds=1)), cancel=cancel))
        while self.fake is None:
            await asyncio.sleep(0)
        cancel.set()
        result = await task
        self.assertEqual(result.reason, "cancelled")
        self.assertTrue(self.fake.terminated)

    async def test_coroutine_cancel_during_spawn_acquires_and_stops_child(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def spawn(*args, **kwargs):
            entered.set()
            await release.wait()
            self.fake = FakeProcess(kwargs["pass_fds"][0], running=True)
            return self.fake
        self.launcher.side_effect = spawn
        task = asyncio.create_task(execute(self.request))
        await entered.wait()
        task.cancel()
        release.set()
        result = await task
        self.assertEqual(result.reason, "supervisor_cancelled")
        self.assertTrue(self.fake.terminated)

    async def test_twice_cancelled_delayed_spawn_stops_the_same_child(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def spawn(*args, **kwargs):
            entered.set()
            await release.wait()
            self.fake = FakeProcess(kwargs["pass_fds"][0], running=True, stubborn=True, status=False)
            return self.fake
        self.launcher.side_effect = spawn
        task = asyncio.create_task(execute(self.request))
        await entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        release.set()
        result = await asyncio.wait_for(task, .5)
        self.assertEqual(result.reason, "supervisor_cancelled")
        self.assertTrue(self.fake.terminated and self.fake.killed)
        self.assertEqual(self.launcher.await_count, 1)

    async def test_internally_cancelled_spawn_returns_cleanup_blocker(self):
        self.launcher.side_effect = asyncio.CancelledError()
        result = await asyncio.wait_for(execute(self.request), .5)
        self.assertEqual((result.reason, result.cleanup, result.blocker),
                         ("blocked", "unverified", "containment_spawn_cancelled"))
        self.assertEqual(self.launcher.await_count, 1)

    async def test_capture_error_cannot_be_a_success(self):
        self.process()
        original = self.launcher.side_effect
        async def spawn(*args, **kwargs):
            process = await original(*args, **kwargs)
            process.stdout.set_exception(OSError("synthetic-private-capture-error"))
            return process
        self.launcher.side_effect = spawn
        result = await execute(self.request)
        self.assertEqual((result.reason, result.blocker), ("blocked", "diagnostic_capture_failed"))
        self.assertNotIn("synthetic-private", repr(result))

    async def test_repeated_coroutine_cancellation_still_finishes_cleanup(self):
        self.process(running=True, stubborn=True, status=False)
        task = asyncio.create_task(execute(replace(self.request, limits=Limits(seconds=1, grace_seconds=.02))))
        while self.fake is None:
            await asyncio.sleep(0)
        task.cancel()
        while not self.fake.terminated:
            await asyncio.sleep(0)
        task.cancel()
        result = await task
        self.assertEqual(result.reason, "supervisor_cancelled")
        self.assertTrue(self.fake.killed)

    def test_status_needs_start_and_matching_exit(self):
        for status in (b"", b"{}", b"[]", b'{"exit-code":0}', b"broken", b" " * 8193,
                       b'{"child-pid":true}\n{"exit-code":0}', b'{"child-pid":1}\n{"exit-code":9}'):
            with self.subTest(status=status[:40]):
                self.assertFalse(_namespace_exited(status, 0))

    async def test_real_probe_requires_explicit_root_scope(self):
        with self.assertRaises(PermissionError):
            await probe_containment(Path(self.temp.name))
        self.launcher.assert_not_called()


if __name__ == "__main__":
    unittest.main()
