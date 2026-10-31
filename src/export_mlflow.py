"""Exporta las entidades reales de MLflow con MlflowClient, sin servidor requerido."""
from pathlib import Path
import pandas as pd
from mlflow import MlflowClient
from .common import write_json, now

def main():
    client = MlflowClient(tracking_uri=Path('mlruns').resolve().as_uri())
    table = pd.read_csv('evidencias/experimentos.csv')
    for row in table.itertuples():
        record = client.get_run(row.mlflow_run_id).to_dictionary()
        assert record['info']['status'] == 'FINISHED'
        record['info']['artifact_uri'] = f'./{row.mlflow_run_id}/'
        record['data']['tags'].pop('mlflow.user', None)
        record['data']['tags'].pop('mlflow.source.name', None)
        write_json(f'evidencias/mlflow/{row.mlflow_run_id}/mlflow-record.json', record)
    write_json('evidencias/mlflow/exportacion.json', {'exported_at_utc': now(), 'rows': len(table),
               'method': 'MlflowClient.get_run(run_id).to_dictionary(); artifact_uri reescrita a ruta portable; tags usuario y ruta local omitidos',
               'tracking_store_included': False, 'models': 'pipeline.joblib por run_id', 'query': 'JSON estándar; pandas.read_csv(../experimentos.csv)'})
    print(f'{len(table)} entidades MLflow FINISHED exportadas')

if __name__ == '__main__':
    main()
