"""Prueba SUPLEMENTARIA desde Git; NO reemplaza recuperación desde HF."""
from pathlib import Path
import argparse
import sys
import joblib
import numpy as np
import pandas as pd
from .common import read_json, write_json, sha, now, predict_frame, git_head

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    a = p.parse_args()
    out = Path(a.output)
    sample = pd.read_csv('evidencias/recuperacion/muestra-validation.csv')
    result = {'supplementary_local_git_only': True, 'hf_recovery_passed': False,
              'git_commit': git_head(), 'python_prefix': sys.prefix, 'rows': len(sample),
              'sample_sha256': sha('evidencias/recuperacion/muestra-validation.csv'),
              'verified_at_utc': now(), 'tolerance': 1e-12, 'versions': {}}
    for version in ['v1','v2']:
        cfg = read_json(f'evidencias/{version}.json')
        path = Path(f'evidencias/mlflow/{cfg["mlflow_run_id"]}/pipeline.joblib')
        assert sha(path) == cfg['model_sha256']
        pipe = joblib.load(path)
        after = predict_frame(pipe, sample, cfg['threshold'], sample.row_id)
        after.to_csv(out / f'{version}-local-despues.csv', index=False)
        before = pd.read_csv(f'evidencias/recuperacion/{version}-antes.csv', float_precision='round_trip')
        assert list(before.row_id) == list(after.row_id)
        difference = float(np.max(np.abs(before.score_attack.to_numpy() - after.score_attack.to_numpy())))
        assert np.array_equal(before.y_pred, after.y_pred) and difference <= 1e-12
        result['versions'][version] = {'classes_exact': True, 'max_score_difference': difference,
                                      'model_sha256': sha(path), 'output_sha256': sha(out / f'{version}-local-despues.csv')}
    write_json(out / 'comprobacion-local-suplementaria.json', result)
    print(result)

if __name__ == '__main__':
    main()
