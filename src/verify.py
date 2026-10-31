"""Contratos de entrega. Reporta por separado lo comprobado y lo bloqueado."""
import json
import subprocess
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from .common import read_json, write_json, sha, metrics, scores, now, EXCLUDED

def main():
    results = {}
    audit = read_json('evidencias/auditoria.json')
    assert audit['training']['rows'] == 175341 and audit['testing']['rows'] == 82332
    manifest = pd.read_csv('data/processed/split_manifest.csv')
    assert manifest.groupby('feature_group_sha256').split.nunique().max() == 1
    assert manifest.row_id.nunique() == 175341
    assert set(audit['features']).isdisjoint(EXCLUDED)
    results['audit_group_split_no_leak'] = True
    val = pd.read_csv('data/processed/validation.csv')
    table = pd.read_csv('evidencias/experimentos.csv')
    assert len(table) == 4 and table.family.nunique() >= 2 and table.mlflow_run_id.nunique() == 4
    for row in table.itertuples():
        path = Path(f'evidencias/mlflow/{row.mlflow_run_id}')
        meta = read_json(path / 'run.json')
        record = read_json(path / 'mlflow-record.json')
        assert record['info']['status'] == 'FINISHED'
        assert sha(path / 'pipeline.joblib') == row.model_sha256 == meta['model_sha256']
        pipe = joblib.load(path / 'pipeline.joblib')
        used = set(sum([list(item[2]) for item in pipe.named_steps['preprocess'].transformers_ if item[0] != 'remainder'], []))
        assert used == set(audit['features']) and used.isdisjoint(EXCLUDED)
        s = scores(pipe, val)
        measured = metrics(val.label, s >= row.threshold)
        for key in ['recall_attack','precision_attack','fpr','macro_f1','tn','fp','fn','tp']:
            assert np.isclose(measured[key], getattr(row,key), atol=1e-14)
            assert measured[key] == meta['validation'][key]
            assert np.isclose(measured[key], record['data']['metrics'][key], atol=1e-14)
        assert meta['git_commit'] == row.git_commit
        subprocess.run(['git','cat-file','-e',row.git_commit + '^{commit}'], check=True)
    results['four_mlflow_runs_reloaded_and_validation_recomputed'] = True
    subprocess.run(['git','rev-parse','--verify','v1^{commit}'], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['git','rev-parse','--verify','v2^{commit}'], check=True, stdout=subprocess.DEVNULL)
    frozen = subprocess.check_output(['git','show','v2:evidencias/seleccion.json'])
    assert frozen == Path('evidencias/seleccion.json').read_bytes()
    results['git_v1_v2_and_frozen_selection'] = True
    if Path('evidencias/metricas-test.json').exists():
        from .lifecycle import recompute
        recompute()
        final = read_json('evidencias/metricas-test.json')
        assert read_json('evidencias/seleccion.json')['frozen_at_utc'] < final['evaluated_at_utc']
        results['test_82332_and_recalculation'] = True
    else:
        results['test_82332_and_recalculation'] = 'pendiente'
    recovery = read_json('evidencias/recuperacion/resultado.json') if Path('evidencias/recuperacion/resultado.json').exists() else {}
    results['clean_dvc_pull'] = recovery.get('dvc_passed', False)
    results['hf_download_both_sha_and_predictions'] = recovery.get('passed', False)
    results['huggingface_publication'] = Path('evidencias/huggingface.json').exists()
    if results['huggingface_publication']:
        pubs=read_json('evidencias/huggingface.json')
        comparison=read_json('evidencias/recuperacion/comparacion.json')
        assert pubs['v1']['sha'] != pubs['v2']['sha']
        assert pubs['v1']['model_sha256'] != pubs['v2']['model_sha256']
        for version in ['v1','v2']:
            assert comparison['versions'][version]['sha']==pubs[version]['sha']
            assert comparison['versions'][version]['downloaded_from_hf']
            assert comparison['versions'][version]['private'] == bool(pubs[version].get('private',True))
    anchors=read_json('evidencias/invariantes-finalizacion.json')
    for path, expected in anchors['immutable_files'].items():
        assert sha(path)==expected, path
    results['frozen_artifacts_and_original_test_unchanged']=True
    github = read_json('evidencias/github.json') if Path('evidencias/github.json').exists() else {}
    results['github_access'] = bool(github.get('push_verified') and github.get('read_verified'))
    write_json('evidencias/verificacion-final.json', {'verified_at_utc': now(), 'checks': results,
               'all_required_passed': all(value is True for value in results.values())})
    print(json.dumps(results, indent=2))

if __name__ == '__main__':
    main()
