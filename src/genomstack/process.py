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
        return shlex.quote(os.path.expandvars(os.path.expanduser(path)))
    if path == '~' or path.startswith('~/'):
        path = '$HOME' + path[1:]
    if path == '$HOME' or path.startswith('$HOME/'):
        return '$HOME' + shlex.quote(path[5:])
    return shlex.quote(path)


def host_path(path, host: str) -> str:
    path = str(path)
    if not path:
        return path
    if is_localhost(host):
        return os.path.expandvars(os.path.expanduser(path))
    if path == '~' or path.startswith('~/') or path == '$HOME' or path.startswith('$HOME/'):
        return subprocess.check_output(['ssh', *SSH_OPTS, host, f'printf %s {shell_path(path)}'], text=True)
    return path


class LocalRunner:
    def __init__(self, workspace: str = '', setup: list[str] | None = None):
        self.ws = Path(os.path.expandvars(os.path.expanduser(str(workspace)))).resolve() if workspace else None
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
        self.host = host
        self.ws = workspace
        self.session = shlex.quote(session)
        self.setup_cmd = [f'source {shell_path(s)}' for s in (setup or [])]
        self.processes = {}

    def _ssh_run(self, cmd: str, timeout: float | None = None, check: bool = True, **kwargs):
        return subprocess.run(['ssh', *SSH_OPTS, self.host, f'bash -lc {shlex.quote(cmd)}'], timeout=timeout, check=check, **kwargs)

    def _wrap_cmds(self, cmds: list[str]) -> str:
        parts = []
        if self.ws:
            parts.append(f'cd {shell_path(self.ws)}')
        parts += self.setup_cmd + cmds
        return ' && '.join(parts)

    def run(self, cmd: str | list[str], timeout: float | None = None, check: bool = True, wait: float = 0.0):
        cmds = [cmd] if type(cmd) != list else cmd
        self._ssh_run(self._wrap_cmds(cmds), timeout=timeout, check=check)
        if wait:
            time.sleep(wait)

    def start(self, name: str, cmd: str | list[str], wait: float = 0.0) -> None:
        if name in self.processes:
            raise RuntimeError(f'Process "{name}" is already running')
        self._ssh_run(f'tmux has-session -t {self.session} 2>/dev/null || tmux new-session -d -s {self.session}')
        cmds = [cmd] if type(cmd) != list else cmd
        tmux_cmd = (
            f'tmux new-window -d -P -F {shlex.quote(r"#{pane_id}")} '
            f'-t {self.session} -n {shlex.quote(name)} '
            f'{shlex.quote("bash -lc " + shlex.quote(self._wrap_cmds(cmds)))}'
        )
        proc = self._ssh_run(tmux_cmd, stdout=subprocess.PIPE, text=True)
        self.processes[name] = proc.stdout.strip()
        if wait:
            time.sleep(wait)

    def stop(self, name: str, timeout: float = 1.0) -> None:
        with ignore_sigint():
            pane_id = self.processes.get(name, None)
            if pane_id is None:
                return
            try:
                self._ssh_run(f'tmux send-keys -t {shlex.quote(pane_id)} C-c', check=False)
                deadline = time.monotonic() + timeout
                while self._ssh_run(f'tmux has-session -t {shlex.quote(pane_id)}', stderr=subprocess.DEVNULL, check=False).returncode == 0:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        self._ssh_run(f'tmux kill-pane -t {shlex.quote(pane_id)}', stderr=subprocess.DEVNULL, check=False)
                        break
                    time.sleep(min(0.1, remaining))
            finally:
                self.processes.pop(name, None)

    def kill(self, name: str) -> None:
        with ignore_sigint():
            pane_id = self.processes.get(name, None)
            if pane_id is None:
                return
            try:
                self._ssh_run(f'tmux kill-pane -t {shlex.quote(pane_id)}', check=False)
            finally:
                self.processes.pop(name, None)

    def stop_all(self, timeout: float = 1.0) -> None:
        with ignore_sigint():
            for name in reversed(list(self.processes.keys())):
                self.stop(name, timeout=timeout)
            self._ssh_run(f'tmux kill-session -t {self.session}', check=False)

    def kill_all(self) -> None:
        with ignore_sigint():
            for name in reversed(list(self.processes.keys())):
                self.kill(name)
            self._ssh_run(f'tmux kill-session -t {self.session}', check=False)

    def hang(self, sleep_period=1.0) -> None:
        while True:
            time.sleep(sleep_period)
