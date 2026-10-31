"""Cuatro configuraciones; sólo train ajusta el pipeline y validation lo compara."""
import argparse
import resource
import time
import warnings
from pathlib import Path
import joblib
import mlflow
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from threadpoolctl import threadpool_limits
from .common import read_json, write_json, now, sha, git_head, data_ref, metrics, scores

def pipeline(spec, schema, seed):
    numeric = Pipeline([('impute', SimpleImputer(strategy='median')), ('scale', StandardScaler())])
    categorical = Pipeline([('impute', SimpleImputer(strategy='most_frequent')),
                            ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=True))])
    prep = ColumnTransformer([('numeric', numeric, schema['numeric']), ('categorical', categorical, schema['categorical'])], sparse_threshold=1.0)
    cls = LogisticRegression if spec['family'] == 'LogisticRegression' else DecisionTreeClassifier
    return Pipeline([('preprocess', prep), ('classifier', cls(random_state=seed, **spec['params']))])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ids', nargs='+', default=None)
    args = parser.parse_args()
    cfg = read_json('configs/experiments.json')
    schema = read_json('data/processed/features.json')
    train = pd.read_csv('data/processed/train.csv')
    val = pd.read_csv('data/processed/validation.csv')
    mlflow.set_tracking_uri(Path('mlruns').resolve().as_uri())
    mlflow.set_experiment('defiende-el-servidor')
    Path('models').mkdir(exist_ok=True)
    export = Path('evidencias/mlflow')
    export.mkdir(parents=True, exist_ok=True)
    comparison = Path('evidencias/experimentos.csv')
    rows = pd.read_csv(comparison).to_dict('records') if comparison.exists() else []
    existing = {r['id'] for r in rows}
    for spec in cfg['experiments']:
        if args.ids and spec['id'] not in args.ids:
            continue
        if spec['id'] in existing:
            raise RuntimeError(f'{spec["id"]} ya ejecutado: no sobrescribir evidencia; use otra copia limpia.')
        start = time.perf_counter()
        pipe = pipeline(spec, schema, cfg['seed'])
        with mlflow.start_run(run_name=spec['id']) as run:
            git = git_head()
            ref = data_ref()
            mlflow.log_params({**spec['params'], 'seed': cfg['seed'], 'family': spec['family'], 'threshold': 0.5,
                               'train_rows': len(train), 'validation_rows': len(val),
                               'git_commit': git, 'dvc_raw_sha256': ref['data/raw.dvc']['sha256'],
                               'dvc_processed_sha256': ref['data/processed.dvc']['sha256']})
            mlflow.set_tags({'hypothesis': spec['hypothesis'], 'change': spec['change'], 'positive_class': 'attack=1'})
            with threadpool_limits(limits=2), warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                pipe.fit(train[schema['features']], train.label)
            converged = not any(issubclass(w.category, ConvergenceWarning) for w in caught)
            if not converged:
                raise RuntimeError(f'No convergio {spec["id"]}; no se considera experimento terminado.')
            s = scores(pipe, val[schema['features']])
            result = metrics(val.label, s >= 0.5)
            path = Path('models') / spec['id']
            path.mkdir(exist_ok=True)
            joblib.dump(pipe, path / 'pipeline.joblib', compress=3)
            pd.DataFrame({'row_id': val.row_id, 'y_true': val.label, 'score_attack': s}).to_csv(path / 'validation_scores.csv', index=False)
            elapsed = time.perf_counter() - start
            meta = {'id': spec['id'], 'hypothesis': spec['hypothesis'], 'change': spec['change'],
                    'family': spec['family'], 'params': spec['params'], 'seed': cfg['seed'], 'git_commit': git,
                    'dvc_reference': ref, 'mlflow_run_id': run.info.run_id, 'threshold': 0.5,
                    'threshold_rule': cfg['threshold_rule'], 'model_sha256': sha(path / 'pipeline.joblib'),
                    'validation': result, 'elapsed_seconds': elapsed, 'max_rss_kib_process': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    'warnings': [str(w.message) for w in caught], 'converged': converged, 'finished_at_utc': now()}
            write_json(path / 'metadata.json', meta)
            mlflow.log_metrics({k: v for k,v in result.items() if isinstance(v, (int,float))})
            mlflow.log_metric('elapsed_seconds', elapsed)
            mlflow.log_artifact(str(path / 'pipeline.joblib'), artifact_path='pipeline')
            mlflow.log_artifact(str(path / 'metadata.json'))
            mlflow.log_artifact('requirements.txt')
            # Exportación estructurada portable + pipeline completo, sin DB/URI locales.
            target = export / run.info.run_id
            target.mkdir(exist_ok=True)
            import shutil
            shutil.copy2(path / 'pipeline.joblib', target / 'pipeline.joblib')
            write_json(target / 'run.json', meta)
            row = {k: meta[k] for k in ['id','family','hypothesis','change','seed','git_commit','mlflow_run_id','threshold','model_sha256','elapsed_seconds']}
            row.update({k: v for k,v in result.items() if k != 'confusion_matrix'})
            row['params'] = __import__('json').dumps(spec['params'], sort_keys=True)
            row['dvc_reference'] = ref['data/processed.dvc']['sha256']
            row['conclusion'] = f'Validation: FN={result["fn"]}; FP={result["fp"]}; recall={result["recall_attack"]:.6f}; FPR={result["fpr"]:.6f}. Comparacion y umbral en seleccion.json.'
            rows.append(row)
            pd.DataFrame(rows).to_csv(comparison, index=False)
            print(spec['id'], run.info.run_id, result, 'seconds', elapsed, flush=True)
    write_json(export / 'index.json', {'tracking': 'MLflow local file store; exportacion portable en run_id/run.json + pipeline.joblib',
               'runs': [r['mlflow_run_id'] for r in rows], 'exported_at_utc': now()})

if __name__ == '__main__':
    main()
