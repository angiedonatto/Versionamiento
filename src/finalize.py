"""Enlaza la publicación posterior con la evaluación original SIN modificarla."""
import subprocess
from pathlib import Path
from .common import read_json, write_json, sha, now

def main():
    anchors=read_json('evidencias/invariantes-finalizacion.json')
    comparisons=read_json('evidencias/recuperacion/comparacion.json')
    recovery=read_json('evidencias/recuperacion/resultado.json')
    publications=read_json('evidencias/huggingface.json')
    assert recovery['passed'] and recovery['dvc_passed'] and recovery['caches_absent_before_start']
    assert recovery['git_source']=='https://github.com/angiedonatto/Versionamiento.git'
    assert comparisons['rows']==64 and comparisons['passed']
    for p, expected in anchors['immutable_files'].items():
        assert sha(p)==expected, f'Se modificó el artefacto congelado: {p}'
        original=subprocess.check_output(['git','show',anchors['base_commit']+':'+p])
        assert original==Path(p).read_bytes(), p
    test=read_json('evidencias/metricas-test.json')
    assert test['evaluated_at_utc']==anchors['test_original_evaluated_at']
    versions={}
    for version in ['v1','v2']:
        cfg=read_json(f'evidencias/{version}.json')
        item=publications[version]
        downloaded=comparisons['versions'][version]
        assert cfg['model_sha256']==item['model_sha256']==downloaded['model_sha256']
        assert cfg['threshold']==downloaded['threshold']
        assert downloaded['sha']==item['sha'] and downloaded['classes_exact']
        versions[version]={'git_code_commit':cfg['git_commit'], 'git_tag':version,
                           'dvc_reference':cfg['dvc_reference'], 'mlflow_run_id':cfg['mlflow_run_id'],
                           'threshold':cfg['threshold'], 'model_sha256':cfg['model_sha256'],
                           'hf_repo':item['repo_id'],'hf_sha':item['sha'],
                           'hf_url':item['url']+'/tree/'+item['sha'],
                           'recovery_max_score_difference':downloaded['max_score_difference']}
    assert test['model_sha256']==versions['v2']['model_sha256']
    record={'recorded_at_utc':now(), 'base_commit':anchors['base_commit'], 'versions':versions,
            'immutable_files_verified':anchors['immutable_files'], 'models_retrained':False,
            'test_evaluation_repeated':False, 'selection_or_threshold_changed':False,
            'test_original_evaluated_at':test['evaluated_at_utc'],
            'test_metrics_file_sha256':sha('evidencias/metricas-test.json'),
            'test_predictions_file_sha256':sha('evidencias/predicciones-test.csv'),
            'hf_revision_containing_exact_evaluated_artifact':publications['v2']['sha'],
            'chronology':'Selección y test anteriores a publicación HF. Los SHA HF se añaden aquí porque los registros históricos originales tenían HF=null; el hash prueba identidad del mismo pipeline. No se retrofecha publicación ni se reevalúa test.',
            'recovery_git_commit':recovery['recovered_git_commit'],
            'recovery_log_sha256':sha('evidencias/recuperacion/recuperacion.log'),
            'dvc_storage_zip_sha256':recovery['storage_zip_sha256'],
            'all_immutable_files_unchanged':True}
    write_json('evidencias/trazabilidad-final.json',record)
    state=read_json('evidencias/modelos/estado.json')
    state.update({'status':'Publicados en HF con visibilidad autorizada y recuperados por SHA con coincidencia exacta en 64 filas.','hf_recovery_verified':True,'updated_at_utc':now()})
    write_json('evidencias/modelos/estado.json',state)
    print('Invariantes verificadas: selección, modelos y test intactos; dos descargas HF verificadas.')

if __name__=='__main__': main()
