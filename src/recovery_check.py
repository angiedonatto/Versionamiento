"""Se ejecuta dentro del venv y checkout nuevos, nunca importa el entorno original."""
import argparse
import sys
import os
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from .common import EXPECTED, RAW_NAMES, sha, read_json, write_json, now, predict_frame

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--hf', action='store_true')
    args = parser.parse_args()
    out = Path(args.output)
    checks = {}
    for kind, name in RAW_NAMES.items():
        actual = sha(Path('data/raw') / name)
        assert actual == EXPECTED[kind]
        checks[f'raw/{name}'] = actual
    audit = read_json('evidencias/auditoria.json')
    for name, expected in audit['prepared_hashes'].items():
        actual = sha(Path('data/processed') / name)
        assert actual == expected
        checks[f'processed/{name}'] = actual
    write_json(out / 'datos-verificados.json', {'dvc_passed': True, 'verified_at_utc': now(), 'hashes': checks,
               'python': sys.version, 'venv_prefix': sys.prefix})
    if not args.hf:
        print('DVC: todos los hashes raw/prepared coinciden, venv=', sys.prefix)
        return
    from huggingface_hub import snapshot_download, HfApi
    publications = read_json('evidencias/huggingface.json')
    sample = pd.read_csv('evidencias/recuperacion/muestra-validation.csv')
    assert len(sample) >= 20
    manifest = pd.read_csv('data/processed/split_manifest.csv')
    assert set(sample.row_id) <= set(manifest.loc[manifest.split == 'validation','row_id'])
    result = {'passed': True, 'rows': len(sample), 'sample_sha256': sha('evidencias/recuperacion/muestra-validation.csv'),
              'score_tolerance': 1e-12, 'versions': {}, 'verified_at_utc': now()}
    for version in ['v1','v2']:
        item = publications[version]
        assert len(item['sha']) == 40 and all(c in '0123456789abcdef' for c in item['sha'])
        info = HfApi().model_info(item['repo_id'], revision=item['sha'])
        assert info.sha == item['sha'] and info.private
        # Caché HF vacía para este proceso, revisión SHA explícita. NO fallback local.
        path = Path(snapshot_download(repo_id=item['repo_id'], revision=item['sha']))
        assert sha(path / 'pipeline.joblib') == item['model_sha256']
        config = read_json(path / 'config.json')
        expected = read_json(f'evidencias/{version}.json')
        assert config == expected
        assert sha(path / 'requirements.txt') == sha('requirements.txt')
        required = ['pipeline.joblib','config.json','requirements.txt','README.md','features.json']
        assert all((path / name).is_file() for name in required)
        pipe = joblib.load(path / 'pipeline.joblib')
        after = predict_frame(pipe, sample, config['threshold'], sample.row_id)
        after.to_csv(out / f'{version}-despues.csv', index=False)
        before = pd.read_csv(f'evidencias/recuperacion/{version}-antes.csv', float_precision='round_trip')
        assert list(before.row_id) == list(after.row_id)
        equal = np.array_equal(before.y_pred.to_numpy(), after.y_pred.to_numpy())
        maxdiff = float(np.max(np.abs(before.score_attack.to_numpy() - after.score_attack.to_numpy())))
        assert equal and maxdiff <= 1e-12
        result['versions'][version] = {'sha': item['sha'], 'model_sha256': sha(path / 'pipeline.joblib'),
                                     'downloaded_from_hf': True, 'private': bool(info.private),
                                     'snapshot_path': str(path), 'threshold': config['threshold'],
                                     'mlflow_run_id': config['mlflow_run_id'], 'git_commit': config['git_commit'],
                                     'files_sha256': {name: sha(path / name) for name in required},
                                     'classes_exact': bool(equal), 'max_score_difference': maxdiff,
                                     'after_sha256': sha(out / f'{version}-despues.csv')}
    result['hf_cache_path'] = os.environ.get('HF_HUB_CACHE')
    write_json(out / 'comparacion.json', result)
    print(result)

if __name__ == '__main__':
    main()
