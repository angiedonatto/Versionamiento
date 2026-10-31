"""Seleccionar y congelar con validation; publicar; evaluar test una sola vez."""
import argparse
import shutil
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from .common import read_json, write_json, sha, now, git_head, metrics, predict_frame

def bundle(version, experiment, threshold):
    source = Path('models') / experiment
    dest = Path('models') / version
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / 'pipeline.joblib', dest / 'pipeline.joblib')
    shutil.copy2('requirements.txt', dest / 'requirements.txt')
    shutil.copy2('data/processed/features.json', dest / 'features.json')
    config = read_json(source / 'metadata.json')
    val = pd.read_csv(source / 'validation_scores.csv')
    config.update({'version': version, 'threshold': float(threshold),
                   'validation': metrics(val.y_true, val.score_attack >= threshold),
                   'created_at_utc': now()})
    write_json(dest / 'config.json', config)
    m = config['validation']
    card = f'''---
library_name: scikit-learn
pipeline_tag: tabular-classification
tags:
- unsw-nb15
- academic
---
# Defiende el servidor — {version}

Clasificación binaria académica de conexiones: normal=0, ataque=1. NO usar para
bloqueo automático de tráfico real. Datos históricos UNSW-NB15, atribución:
https://research.unsw.edu.au/projects/unsw-nb15-dataset . Mirror inmutable del PDF
del docente, hashes y auditoría en el repositorio Git. Se excluyen id, label y attack_cat.
Pipeline completo sklearn: imputación mediana/moda, escala numérica, one-hot con
categorías desconocidas ignoradas y {config['family']}. Fit sólo en train, grupos
idénticos no cruzan validation. Se conserva frecuencia natural y contradicciones.

## Validation (ataque positivo; zero_division=0)
Threshold: {threshold}; regla: score_attack >= threshold.
Recall: {m['recall_attack']}; precision: {m['precision_attack']}; FPR: {m['fpr']};
macro-F1: {m['macro_f1']}; matriz [[TN,FP],[FN,TP]]: {m['confusion_matrix']}.
Selección sólo con validation. Estas NO son métricas test.

## Trazabilidad
Código: https://github.com/angiedonatto/Versionamiento/commit/{config['git_commit']}
DVC raw SHA256: {config['dvc_reference']['data/raw.dvc']['sha256']}
DVC processed SHA256: {config['dvc_reference']['data/processed.dvc']['sha256']}
Referencias DVC completas en config.json. MLflow run: {config['mlflow_run_id']}.
SHA256 pipeline.joblib: {config['model_sha256']}. Hipótesis: {config['hypothesis']}.

## Uso
Python 3.12.14, dependencias exactas en requirements.txt. Descargar esta revisión
por SHA completo, nunca confiar en main para reproducir.
```python
import json, joblib, pandas as pd
cfg = json.load(open('config.json'))
model = joblib.load('pipeline.joblib')  # sólo artefactos de confianza
frame = pd.read_csv('entradas.csv')
score = model.predict_proba(frame)[:, list(model.classes_).index(1)]
pred = (score >= cfg['threshold']).astype(int)
```

## Límites y costes
Una partición de validation y selección de hiperparámetros/umbral en ella implica
optimismo de selección. Test contiene cruces de entradas con training publicados;
ver auditoria.json. Dataset histórico, sin garantía para redes actuales. Falsos
negativos omiten ataques y falsos positivos consumen revisión humana. No hay
evaluación externa temporal ni calibración. El umbral no representa un coste real
validado. Licencia/condiciones de datos pertenecen a UNSW; no se redistribuyen CSV
en este repositorio de modelos. joblib puede ejecutar código: cargar sólo origen
confiable y verificar SHA256.
'''
    (dest / 'README.md').write_text(card)
    return config

def select():
    if Path('evidencias/seleccion.json').exists():
        raise RuntimeError('Seleccion ya congelada; no sobrescribir.')
    comparison = pd.read_csv('evidencias/experimentos.csv')
    assert len(comparison) == 4 and comparison.family.nunique() >= 2
    grid = []
    for experiment in comparison.id:
        val = pd.read_csv(f'models/{experiment}/validation_scores.csv')
        for threshold in np.round(np.arange(.1, .901, .05), 2):
            grid.append({'id': experiment, 'threshold': float(threshold), **metrics(val.y_true, val.score_attack >= threshold)})
    write_json('evidencias/umbrales-validation.json', grid)
    candidates = [x for x in grid if x['id'] != 'lr_c01']
    feasible = [x for x in candidates if x['recall_attack'] >= .9]
    winner = sorted(feasible or candidates, key=lambda x: (-x['macro_f1'], x['fpr'], -x['threshold'], x['id']))[0]
    v1 = bundle('v1', 'lr_c01', .5)
    v2 = bundle('v2', winner['id'], winner['threshold'])
    sample = pd.read_csv('data/processed/validation.csv').iloc[:64].copy()
    sample.to_csv('evidencias/recuperacion/muestra-validation.csv', index=False)
    for version, cfg in [('v1', v1), ('v2', v2)]:
        pipe = joblib.load(f'models/{version}/pipeline.joblib')
        predict_frame(pipe, sample, cfg['threshold'], sample.row_id).to_csv(f'evidencias/recuperacion/{version}-antes.csv', index=False)
        write_json(f'evidencias/{version}.json', cfg)
    decision = {'frozen_at_utc': now(), 'code_commit_at_selection': git_head(), 'rule': read_json('configs/experiments.json')['selection_rule'],
                'feasible_recall_constraint': bool(feasible), 'version': 'v2', 'experiment': winner['id'],
                'threshold': winner['threshold'], 'threshold_rule': 'score_attack >= threshold',
                'model_sha256': v2['model_sha256'], 'mlflow_run_id': v2['mlflow_run_id'],
                'dvc_reference': v2['dvc_reference'], 'git_code_commit': v2['git_commit'],
                'hf_repo': None, 'hf_sha': None, 'test_evaluated_at_selection': False,
                'reason': 'Regla predeclarada: cuatro configuraciones con la misma validation; v2 cambia a arbol profundidad 16/hojas >=5. Se exploran 17 umbrales por configuracion y se conserva 0.5. Sin etiquetas ni metricas test.',
                'v1_validation': v1['validation'], 'v2_validation': v2['validation']}
    write_json('evidencias/seleccion.json', decision)
    print('Congelado:', winner, flush=True)

def publish(repo):
    from huggingface_hub import HfApi
    api = HfApi()
    if not repo:
        repo = api.whoami()['name'] + '/defiende-el-servidor'
    info = api.create_repo(repo_id=repo, repo_type='model', private=True, exist_ok=True)
    if not api.model_info(repo).private:
        raise RuntimeError('El repositorio HF existente es público; no subir sin autorización.')
    records = read_json('evidencias/huggingface.json') if Path('evidencias/huggingface.json').exists() else {}
    for version in ['v1', 'v2']:
        if version in records:
            continue
        cfg = read_json(f'models/{version}/config.json')
        assert sha(f'models/{version}/pipeline.joblib') == cfg['model_sha256']
        commit = api.upload_folder(repo_id=repo, folder_path=f'models/{version}', commit_message=f'Publicar {version}: pipeline congelado y trazabilidad')
        records[version] = {'repo_id': repo, 'url': f'https://huggingface.co/{repo}', 'sha': commit.oid,
                            'model_sha256': cfg['model_sha256'], 'published_at_utc': now(), 'private': True}
        write_json('evidencias/huggingface.json', records)
        api.create_tag(repo, tag=version, revision=commit.oid, exist_ok=True)
    # Referencia suplementaria: no mutar el registro de selección congelado.
    write_json('evidencias/publicacion-congelada.json', {'selection_sha256': sha('evidencias/seleccion.json'),
                'huggingface': records, 'recorded_at_utc': now(), 'git_commit': git_head()})
    print(records)

def evaluate_test():
    if Path('evidencias/metricas-test.json').exists() or Path('evidencias/test-iniciado.json').exists():
        raise RuntimeError('Test ya iniciado/evaluado: prohibido repetir evaluación de selección.')
    selection = read_json('evidencias/seleccion.json')
    # Un commit previo debe contener exactamente la selección congelada.
    import subprocess
    frozen_bytes = subprocess.check_output(['git', 'show', 'v2:evidencias/seleccion.json'])
    assert frozen_bytes == Path('evidencias/seleccion.json').read_bytes()
    frozen_commit = subprocess.check_output(['git','rev-parse','v2^{commit}'], text=True).strip()
    model = Path('models/v2/pipeline.joblib')
    assert sha(model) == selection['model_sha256']
    path = Path('data/raw/UNSW_NB15_testing-set.csv')
    from .common import EXPECTED
    assert sha(path) == EXPECTED['testing']
    write_json('evidencias/test-iniciado.json', {'started_at_utc': now(), 'selection_sha256': sha('evidencias/seleccion.json'), 'freeze_commit': frozen_commit})
    start = __import__('time').perf_counter()
    test = pd.read_csv(path)
    assert len(test) == 82332
    pipe = joblib.load(model)
    result = predict_frame(pipe, test, selection['threshold'], [f'{path.name}:row={i+1}' for i in range(len(test))], test.label)
    result = result[['row_id', 'y_true', 'score_attack', 'y_pred']]
    result.to_csv('evidencias/predicciones-test.csv', index=False)
    hf = read_json('evidencias/huggingface.json').get('v2') if Path('evidencias/huggingface.json').exists() else None
    report = {'evaluated_at_utc': now(), 'version': 'v2', 'freeze_commit': frozen_commit,
              'selection_sha256': sha('evidencias/seleccion.json'), 'model_sha256': sha(model),
              'huggingface': hf, 'test_sha256': sha(path), 'rows': len(test), 'threshold': selection['threshold'],
              'threshold_rule': selection['threshold_rule'], 'predictions_sha256': sha('evidencias/predicciones-test.csv'),
              'metrics': metrics(result.y_true, result.y_pred), 'elapsed_seconds': __import__('time').perf_counter() - start}
    write_json('evidencias/metricas-test.json', report)
    recompute()
    print('Test final:', report, flush=True)

def recompute():
    p = pd.read_csv('evidencias/predicciones-test.csv', float_precision='round_trip')
    cfg = read_json('evidencias/metricas-test.json')
    assert len(p) == cfg['rows'] == 82332 and p.row_id.nunique() == 82332
    assert np.array_equal((p.score_attack >= cfg['threshold']).astype(int), p.y_pred)
    actual = metrics(p.y_true, p.y_pred)
    assert actual == cfg['metrics'], (actual, cfg['metrics'])
    assert sha('evidencias/predicciones-test.csv') == cfg['predictions_sha256']
    write_json('evidencias/recalculo-test.json', {'passed': True, 'recomputed_at_utc': now(), 'source': 'predicciones-test.csv', 'metrics': actual})

def predict(model_dir, input_path, output):
    config = read_json(Path(model_dir) / 'config.json')
    assert sha(Path(model_dir) / 'pipeline.joblib') == config['model_sha256']
    pipe = joblib.load(Path(model_dir) / 'pipeline.joblib')
    x = pd.read_csv(input_path)
    ids = x.row_id if 'row_id' in x else [f'{Path(input_path).name}:row={i+1}' for i in range(len(x))]
    predict_frame(pipe, x, config['threshold'], ids).to_csv(output, index=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['select','publish','test','recompute','predict'])
    parser.add_argument('--repo')
    parser.add_argument('--model-dir')
    parser.add_argument('--input')
    parser.add_argument('--output')
    args = parser.parse_args()
    if args.action == 'select': select()
    elif args.action == 'publish': publish(args.repo)
    elif args.action == 'test': evaluate_test()
    elif args.action == 'recompute': recompute()
    else: predict(args.model_dir, args.input, args.output)
