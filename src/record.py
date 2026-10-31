"""Ejecuta un comando y preserva stdout/stderr, estado y tiempos reales."""
import argparse
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path
from .common import now

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--log', required=True)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    cmd = a.command[1:] if a.command[:1] == ['--'] else a.command
    path = Path(a.log)
    path.parent.mkdir(parents=True, exist_ok=True)
    started = now()
    tick = time.perf_counter()
    with path.open('a') as log:
        log.write(f'\n[{started}] cwd={Path.cwd()}\n$ {shlex.join(cmd)}\n')
        log.flush()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in proc.stdout:
            log.write(line)
            log.flush()
            print(line, end='', flush=True)
        status = proc.wait()
        result = {'command': cmd, 'started_at_utc': started, 'finished_at_utc': now(),
                  'elapsed_seconds': time.perf_counter() - tick, 'exit_code': status}
        log.write(json.dumps(result) + '\n')
    return status

if __name__ == '__main__':
    sys.exit(main())
