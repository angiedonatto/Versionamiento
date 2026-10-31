"""Orquestación real: nuevo checkout, venv, cachés vacías y DVC storage entregado.

No sustituye descargas HF por archivos locales. Un fallo HF queda como bloqueado.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from .common import read_json, write_json, now, sha, git_head

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--storage', required=True)
    parser.add_argument('--git-source', default='.')
    parser.add_argument('--revision', default='HEAD')
    parser.add_argument('--work-root', default=None, help='Directorio temporal padre opcional; por defecto el temporal del sistema.')
    parser.add_argument('--skip-install', action='store_true', help='Sólo para diagnóstico; no se considera recuperación completa.')
    args = parser.parse_args()
    origin = Path.cwd()
    out = origin / 'evidencias/recuperacion'
    out.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='defiende-recuperacion-', dir=args.work_root))
    log_path = out / 'recuperacion.log'
    env = os.environ.copy()
    env.update({'DVC_SITE_CACHE_DIR': str(root / 'dvc-site-new'), 'HF_HOME': str(root / 'hf-home'), 'HF_HUB_CACHE': str(root / 'hf-cache'),
                'XDG_CACHE_HOME': str(root / 'xdg-cache'), 'PIP_NO_CACHE_DIR':'1',
                'HF_HUB_DISABLE_TELEMETRY':'1', 'HF_HUB_DISABLE_XET':'1',
                'DVC_NO_ANALYTICS':'1', 'MLFLOW_ENABLE_ASYNC_LOGGING':'false',
                'OPENBLAS_NUM_THREADS':'2', 'OMP_NUM_THREADS':'2'})
    result = {'started_at_utc': now(), 'root': str(root), 'git_source': args.git_source,
              'requested_revision': args.revision, 'steps': [], 'passed': False,
              'new_venv': True, 'original_caches_reused': False, 'score_tolerance': 1e-12,
              'storage_zip_sha256': sha(args.storage),
              'cache_paths': {k: env[k] for k in ['HF_HOME','HF_HUB_CACHE','XDG_CACHE_HOME','DVC_SITE_CACHE_DIR']},
              'caches_absent_before_start': all(not Path(env[k]).exists() for k in ['HF_HOME','HF_HUB_CACHE','XDG_CACHE_HOME','DVC_SITE_CACHE_DIR'])}
    assert result['caches_absent_before_start']
    start = time.perf_counter()
    with log_path.open('w') as log:
        def run(cmd, cwd=root, required=True):
            log.write(f'\n[{now()}] cwd={cwd}\n$ {__import__("shlex").join(map(str,cmd))}\n')
            log.flush()
            proc = subprocess.run(list(map(str,cmd)), cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
            step = {'command': list(map(str,cmd)), 'exit_code': proc.returncode, 'finished_at_utc': now()}
            result['steps'].append(step)
            log.write(f'EXIT_CODE={proc.returncode}\n')
            log.flush()
            if required and proc.returncode:
                raise RuntimeError(f'Paso fallido: {cmd[0:3]}, exit {proc.returncode}')
            return proc.returncode
        try:
            source = str(Path(args.git_source).resolve()) if Path(args.git_source).exists() else args.git_source
            run(['git','clone','--no-local', source, 'proyecto'])
            checkout = root / 'proyecto'
            run(['git','checkout','--detach', args.revision], cwd=checkout)
            result['recovered_git_commit'] = subprocess.check_output(['git','rev-parse','HEAD'], cwd=checkout, text=True).strip()
            run([sys.executable, '-m', 'venv', root / 'venv'])
            py = root / 'venv/bin/python'
            if not args.skip_install:
                run([py, '-m','pip','install','--no-cache-dir','-r','requirements.txt'], cwd=checkout)
                run([py, '-m','pip','check'], cwd=checkout)
            else:
                raise RuntimeError('skip-install no valida entorno limpio')
            with zipfile.ZipFile(args.storage) as archive:
                assert all(not p.startswith('/') and '..' not in Path(p).parts for p in archive.namelist())
                archive.extractall(root)
            assert (root / 'dvc-storage').is_dir()
            # Esta caché empieza vacía; el remote sólo contiene el respaldo entregado.
            run([root / 'venv/bin/dvc', 'config','--local','cache.dir', str(root / 'dvc-empty-cache')], cwd=checkout)
            run([root / 'venv/bin/dvc', 'remote','modify','--local','entrega','url', str(root / 'dvc-storage')], cwd=checkout)
            run([root / 'venv/bin/dvc','pull','--force'], cwd=checkout)
            run([py,'-m','src.recovery_check','--output',str(out)], cwd=checkout)
            result.update(read_json(out / 'datos-verificados.json'))
            if not (checkout / 'evidencias/huggingface.json').exists():
                raise RuntimeError('No hay SHAs de Hugging Face publicados: DVC verificado; recuperación HF bloqueada por acceso.')
            run([py,'-m','src.recovery_check','--output',str(out),'--hf'], cwd=checkout)
            result['huggingface'] = read_json(out / 'comparacion.json')
            result['passed'] = bool(result['huggingface']['passed'])
        except Exception as exc:
            result['blocker'] = str(exc)
            log.write(f'\nRESULTADO BLOQUEADO/FALLIDO: {exc}\n')
        result['finished_at_utc'] = now()
        result['elapsed_seconds'] = time.perf_counter() - start
    result['log_sha256'] = sha(log_path)
    write_json(out / 'resultado.json', result)
    print(result, flush=True)
    return 0 if result['passed'] else 2

if __name__ == '__main__':
    raise SystemExit(main())
