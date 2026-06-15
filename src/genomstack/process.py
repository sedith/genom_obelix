import os
import shlex
import signal
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path


SSH_OPTS = [
    '-o', 'ConnectTimeout=5',
    '-o', 'ServerAliveInterval=5',
    '-o', 'ServerAliveCountMax=3',
    '-o', 'BatchMode=yes',
    '-o', 'ConnectionAttempts=1',
]


@contextmanager
def ignore_sigint():
    old_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, old_handler)


## helpers
def is_localhost(host: str) -> bool:
    return host in ('localhost', '127.0.0.1', '::1', socket.gethostname())


def shell_path(path, expand: bool = False) -> str:
    path = str(path)
    if expand:
        path = os.path.expandvars(os.path.expanduser(path))
    return shlex.quote(path)


class LocalRunner:
    def __init__(self, workspace: str = '', setup: list[str] | None = None):
        self.ws = Path(workspace).expanduser().resolve() if workspace else None
        self.setup_cmd = [f'source {shell_path(s, True)}' for s in (setup or [])]
        self.processes = {}

    def _wrap_cmds(self, cmds: list[str]) -> str:
        return ' && '.join(self.setup_cmd + cmds)

    def run(self, cmd: str | list[str], timeout: float | None = None, check: bool = True, wait: float = 0.0):
        cmds = [cmd] if type(cmd) != list else cmd
        subprocess.run(['bash', '-lc', self._wrap_cmds(cmds)], cwd=self.ws, timeout=timeout, check=check)
        if wait:
            time.sleep(wait)

    def start(self, name: str, cmd: str | list[str], wait: float = 0.0) -> None:
        if name in self.processes:
            raise RuntimeError(f'Process "{name}" is already running')
        cmds = [cmd] if type(cmd) != list else cmd
        self.processes[name] = subprocess.Popen(['bash', '-lc', self._wrap_cmds(cmds)], cwd=self.ws, env=None, stdin=subprocess.DEVNULL, start_new_session=True)
        if wait:
            time.sleep(wait)

    def stop(self, name: str, timeout: float = 1.0) -> None:
        with ignore_sigint():
            proc = self.processes.get(name, None)
            if proc is None:
                return
            try:
                if proc.poll() is None:
                    try:
                        os.killpg(proc.pid, signal.SIGTERM)
                        proc.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
            finally:
                self.processes.pop(name, None)

    def kill(self, name: str) -> None:
        with ignore_sigint():
            proc = self.processes.get(name, None)
            if proc is None:
                return
            try:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
            finally:
                self.processes.pop(name, None)

    def stop_all(self, timeout: float = 1.0) -> None:
        with ignore_sigint():
            for name in reversed(list(self.processes.keys())):
                self.stop(name, timeout=timeout)

    def kill_all(self) -> None:
        with ignore_sigint():
            for name in reversed(list(self.processes.keys())):
                self.kill(name)

    def hang(self, sleep_period=1.0) -> None:
        while True:
            time.sleep(sleep_period)


class RemoteTmuxRunner:
    def __init__(self, host: str, workspace: str = '', setup: list[str] | None = None, session: str = 'genomstack'):
        raise(NotImplementedError)
#         self.host = host
#         self.ws = workspace
#         self.session = session
#         self.setup_cmd = [f'source {shell_path(s)}' for s in (setup or [])]
#         self.processes = {}

#     def _ssh_cmd(self, cmd: str) -> list[str]:
#         return ['ssh', *SSH_OPTS, self.host, f'bash -lc {shlex.quote(cmd)}']

#     def _ssh(self, cmd: str, timeout: float | None = None, check: bool = True):
#         return subprocess.run(self._ssh_cmd(cmd), timeout=timeout, check=check)

#     def _wrap_cmds(self, cmds: list[str]) -> str:
#         parts = []
#         if self.ws:
#             parts.append(f'cd {shell_path(self.ws)}')
#         parts += self.setup_cmd + cmds
#         return ' && '.join(parts)

#     def _target(self, name: str) -> str:
#         return shlex.quote(f'{self.session}:{name}')

#     def _ensure_session(self) -> None:
#         session = shlex.quote(self.session)
#         self._ssh(f'tmux has-session -t {session} 2>/dev/null || tmux new-session -d -s {session}')

#     def run(self, cmd: str | list[str], timeout: float | None = None, check: bool = True, wait: float = 0.0):
#         cmds = [cmd] if type(cmd) != list else cmd
#         self._ssh(self._wrap_cmds(cmds), timeout=timeout, check=check)
#         if wait:
#             time.sleep(wait)

#     def start(self, name: str, cmd: str | list[str], wait: float = 0.0) -> None:
#         if name in self.processes:
#             raise RuntimeError(f'Process "{name}" is already running')

#         self._ensure_session()
#         cmds = [cmd] if type(cmd) != list else cmd
#         shell_cmd = 'bash -lc ' + shlex.quote(self._wrap_cmds(cmds))
#         tmux_cmd = (
#             f'tmux new-window -d -t {shlex.quote(self.session)} '
#             f'-n {shlex.quote(name)} {shlex.quote(shell_cmd)}'
#         )
#         self._ssh(tmux_cmd)
#         self.processes[name] = True

#         if wait:
#             time.sleep(wait)

#     def stop(self, name: str, timeout: float = 1.0) -> None:
#         with ignore_sigint():
#             target = self._target(name)
#             self._ssh(f'tmux send-keys -t {target} C-c', check=False)
#             time.sleep(timeout)
#             self._ssh(f'tmux kill-window -t {target}', check=False)
#             self.processes.pop(name, None)

#     def kill(self, name: str) -> None:
#         with ignore_sigint():
#             self._ssh(f'tmux kill-window -t {self._target(name)}', check=False)
#             self.processes.pop(name, None)

#     def stop_all(self, timeout: float = 1.0) -> None:
#         with ignore_sigint():
#             for name in reversed(list(self.processes.keys())):
#                 self._ssh(f'tmux send-keys -t {self._target(name)} C-c', check=False)
#             if self.processes and timeout:
#                 time.sleep(timeout)
#             self._ssh(f'tmux kill-session -t {shlex.quote(self.session)}', check=False)
#             self.processes.clear()

#     def kill_all(self) -> None:
#         with ignore_sigint():
#             self._ssh(f'tmux kill-session -t {shlex.quote(self.session)}', check=False)
#             self.processes.clear()

#     def hang(self, sleep_period=1.0) -> None:
#         while True:
#             time.sleep(sleep_period)
