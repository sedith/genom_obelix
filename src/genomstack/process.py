import os
import shlex
import signal
import socket
import subprocess
import time
from pathlib import Path


# SSH_OPTS = [
#     '-o', 'ConnectTimeout=5',
#     '-o', 'ServerAliveInterval=5',
#     '-o', 'ServerAliveCountMax=3',
# ]


## helpers
def is_localhost(host: str) -> bool:
    return host in ('localhost', '127.0.0.1', '::1', socket.gethostname())


# def shell_path(path) -> str:
#     path = str(path)
#     if path == '~' or path.startswith('~/'):
#         return path
#     return shlex.quote(path)


# def source_prefix(setup_files) -> str:
#     if not setup_files:
#         return ''

#     return ' && '.join(
#         f'source {shell_path(setup)}'
#         for setup in setup_files
#     )


class LocalRunner:
    def __init__(self, workspace: str ='', setup: list[str] = []):
        self.ws = Path(workspace).expanduser().resolve() if workspace else None
        self.setup_cmd = [f'source {shlex.quote(str(Path(os.path.expandvars(os.path.expanduser(s)))))}' for s in setup]
        self.processes = {}

    def _wrap_cmd(self, cmd: str) -> str:
        return ' && '.join(self.setup_cmd + [cmd])

    def run(self, cmd: str, timeout: float | None = None, check: bool = True, wait: float = 0.0):
        subprocess.run(['bash', '-lc', self._wrap_cmd(cmd)], cwd=self.ws, timeout=timeout, check=check)
        if wait:
            time.sleep(wait)

    def start(self, name: str, cmd: str, wait: float = 0.0) -> None:
        if name in self.processes:
            raise RuntimeError(f'Process "{name}" is already running')
            
        self.processes[name] = subprocess.Popen(['bash', '-lc', self._wrap_cmd(cmd)], cwd=self.ws, env=None, start_new_session=True)
        if wait:
            time.sleep(wait)

    def stop(self, name: str, timeout: float = 1.0) -> None:
        proc = self.processes.pop(name, None)
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()

    def kill(self, name: str) -> None:
        proc = self.processes.pop(name, None)
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()

    def stop_all(self, timeout: float = 1.0) -> None:
        for name in reversed(list(self.processes.keys())):
            self.stop(name, timeout=timeout)

    def kill_all(self) -> None:
        for name in reversed(list(self.processes.keys())):
            self.kill(name)

    def hang(self, sleep_period=1.0) -> None:
        while True:
            time.sleep(sleep_period)


## mockup by chatgpt
# class RemoteTmuxRunner:
#     """Launches remote processes inside a tmux session.

#     SSH is only used to send commands. The remote processes are owned by tmux,
#     so they do not immediately die if the SSH connection drops.

#     Requirements on the remote host:
#       - ssh access
#       - tmux installed
#       - bash
#     """
#     def __init__(
#         self,
#         host: str,
#         workspace: str,
#         session: str = 'genom_obelix',
#         setup=None,
#         log_dir: str = '/tmp/genom_obelix',
#         ssh_opts=None,
#     ):
#         self.host = host
#         self.workspace = workspace
#         self.session = session
#         self.setup = setup or []
#         self.log_dir = log_dir
#         self.ssh_opts = ssh_opts or SSH_OPTS
#         self._tail_process = None

#     def ssh(self, cmd: str, check: bool = True):
#         return subprocess.run(
#             [
#                 'ssh',
#                 *self.ssh_opts,
#                 self.host,
#                 f'bash -lc {shlex.quote(cmd)}',
#             ],
#             check=check,
#         )

#     def ssh_popen(self, cmd: str):
#         return subprocess.Popen([
#             'ssh',
#             *self.ssh_opts,
#             self.host,
#             f'bash -lc {shlex.quote(cmd)}',
#         ])

#     def start_session(self):
#         cmd = (
#             f'mkdir -p {shell_path(self.log_dir)} && '
#             f'tmux has-session -t {shlex.quote(self.session)} 2>/dev/null || '
#             f'tmux new-session -d -s {shlex.quote(self.session)} -n main'
#         )

#         self.ssh(cmd)

#     def wrap_cmd(self, name: str, cmd: str) -> str:
#         parts = [
#             f'mkdir -p {shell_path(self.log_dir)}',
#             f'cd {shell_path(self.workspace)}',
#         ]

#         prefix = source_prefix(self.setup)
#         if prefix:
#             parts.append(prefix)

#         process_log = f'{self.log_dir}/{name}.out'
#         stack_log = f'{self.log_dir}/stack.out'

#         parts.append(
#             "{ "
#             f"echo '[{name}] starting: {cmd}'; "
#             f"{cmd}; "
#             f"echo '[{name}] exited with code $?'; "
#             "} "
#             "2>&1 "
#             f"| sed -u {shlex.quote(f's/^/[{name}] /')} "
#             f"| tee -a {shell_path(process_log)} -a {shell_path(stack_log)}"
#         )

#         return ' && '.join(parts)

#     def start(self, name: str, cmd: str, wait: float = 0.0):
#         self.start_session()

#         wrapped = self.wrap_cmd(name, cmd)

#         tmux_cmd = (
#             f'tmux new-window '
#             f'-t {shlex.quote(self.session)} '
#             f'-n {shlex.quote(name)} '
#             f'{shlex.quote('bash -lc ' + shlex.quote(wrapped))}'
#         )

#         self.ssh(tmux_cmd)

#         if wait:
#             time.sleep(wait)

#     def stop(self, name: str):
#         self.ssh(
#             f'tmux kill-window '
#             f'-t {shlex.quote(self.session)}:{shlex.quote(name)}',
#             check=False,
#         )

#     def stop_all(self):
#         self.stop_tail()

#         self.ssh(
#             f'tmux kill-session -t {shlex.quote(self.session)}',
#             check=False,
#         )

#     def tail_logs(self):
#         if self._tail_process is not None and self._tail_process.poll() is None:
#             return self._tail_process

#         cmd = (
#             f'mkdir -p {shell_path(self.log_dir)} && '
#             f'touch {shell_path(self.log_dir)}/stack.out && '
#             f'tail -F {shell_path(self.log_dir)}/stack.out'
#         )

#         self._tail_process = self.ssh_popen(cmd)
#         return self._tail_process

#     def stop_tail(self):
#         if self._tail_process is None:
#             return

#         if self._tail_process.poll() is None:
#             self._tail_process.terminate()
#             try:
#                 self._tail_process.wait(timeout=2.0)
#             except subprocess.TimeoutExpired:
#                 self._tail_process.kill()
#                 self._tail_process.wait()

#         self._tail_process = None

#     def wait(self, follow_logs: bool = True):
#         if follow_logs:
#             self.tail_logs()

#         try:
#             while True:
#                 time.sleep(1.0)
#         except KeyboardInterrupt:
#             self.stop_all()
