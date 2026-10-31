"""Auditoría de los ocho ítems de la guía y los 16 componentes / 100 puntos.

Se ejecuta después del empaquetado y de verificar la publicación remota.
No ajusta modelos ni evalúa test: usa sólo evidencia ya guardada.
"""
import argparse
import json
import re
from pathlib import Path
from zipfile import ZipFile
from pypdf import PdfReader
from .common import read_json, write_json, now, sha

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True,help='Directorio de entregables y auditoría definitiva')
    args=parser.parse_args()
    out=Path(args.output)
    trace=read_json('evidencias/trazabilidad-final.json')
    verification=read_json('evidencias/verificacion-final.json')
    recovery=read_json('evidencias/recuperacion/resultado.json')
    comparison=read_json('evidencias/recuperacion/comparacion.json')
    publications=read_json('evidencias/huggingface.json')
    original=read_json('evidencias/metricas-test.json')
    anchors=read_json('evidencias/invariantes-finalizacion.json')
    unchanged=all(sha(p)==h for p,h in anchors['immutable_files'].items())
    assert unchanged and verification['all_required_passed']
    rubric=[]
    def component(block,name,maximum,complete=True,evidence=''):
        rubric.append({'block':block,'component':name,'max_points':maximum,
                       'status':'verificado' if complete else 'parcial / pendiente administrativo',
                       'conditional_potential_points':maximum if complete else maximum*.5,
                       'evidence':evidence})
    component('Código Git', 'Historial y cambios explicados',5,evidence='GitHub, historial.bundle, log Git')
    component('Código Git', 'Revisiones recuperables v1/v2',5,evidence='Tags Git, clone GitHub del log de recuperación')
    component('Código Git', 'Configuración, dependencias y ausencia de secretos',5,evidence='requirements.txt, configs/, escaneo de ZIP')
    component('Datos DVC', 'Auditoría, splits y prevención de fuga',8,evidence='auditoria.json, manifiesto y verificación de grupos')
    component('Datos DVC', 'Originales y preparados con referencias',6,evidence='raw.dvc, processed.dvc, tags datos-originales/preparados')
    component('Datos DVC', 'Recuperación desde almacenamiento entregado y hashes',6,evidence='dvc-storage.zip, dvc pull y datos-verificados.json')
    component('MLflow', 'Cuatro configuraciones, dos familias y comparación justa',8,evidence='experimentos.csv; cuatro pipelines recargados')
    component('MLflow', 'Registros exportados y trazables',8,evidence='mlflow-record.json, run.json, pipeline.joblib por run_id')
    component('MLflow', 'Errores y umbral elegidos con validation',4,evidence='umbrales-validation.json, seleccion.json y comparación FP/FN del informe')
    component('Hugging Face', 'Dos versiones completas distintas por SHA',8,evidence='huggingface.json y comparacion.json con descargas reales')
    component('Hugging Face', 'Model cards, métricas, límites y uso',6,evidence='README.md descargados de cada revisión; hashes en comparacion.json')
    component('Hugging Face', 'Vínculo Git, DVC y MLflow',6,evidence='config.json en cada SHA; trazabilidad-final.json')
    component('Recuperación y evaluación', 'Entorno nuevo, descargas y predicciones coincidentes',8,evidence='recuperacion.log, resultado.json y comparación de 64 filas')
    component('Recuperación y evaluación', 'Test reservado, completo y recalculable',7,evidence='82332 predicciones, métricas originales intactas, recalculo-test.json')
    component('Explicación y entrega', 'Informe, decisiones y limitaciones',6,evidence='informe.pdf generado desde JSON/CSV, máximo 5 páginas')
    people=read_json('configs/integrantes.json') if Path('configs/integrantes.json').exists() else {}
    people_complete=bool(people.get('integrantes')) and all(p.get('nombre') and p.get('grupo') in ['A','B'] and p.get('contribucion') for p in people.get('integrantes',[]))
    component('Explicación y entrega', 'README, índice y contribuciones/ayudas',4,complete=people_complete,
              evidence='README.md, entrega.md y declaración IA; nombres, grupos y contribuciones humanas pendientes' if not people_complete else 'README.md, entrega.md, configs/integrantes.json y declaración IA')
    artifact_checks={}
    for name in ['proyecto.zip','informe.pdf','dvc-storage.zip']:
        artifact_checks[name]={'exists':(out/name).is_file()}
        if (out/name).is_file(): artifact_checks[name].update({'sha256':sha(out/name),'bytes':(out/name).stat().st_size})
    credential_scan=True
    zip_valid=False
    if (out/'proyecto.zip').exists():
        with ZipFile(out/'proyecto.zip') as z:
            zip_valid=z.testzip() is None
            names=z.namelist()
            required=['README.md','entrega.md','requirements.txt','.dvc/config','.dvcignore','data/raw.dvc','data/processed.dvc','historial.bundle','evidencias/huggingface.json','evidencias/trazabilidad-final.json','evidencias/recuperacion/comparacion.json','evidencias/recuperacion/recuperacion.log','evidencias/predicciones-test.csv']
            zip_valid=zip_valid and all('proyecto/'+p in names for p in required)
            zip_valid=zip_valid and not any(n.startswith(('proyecto/data/raw/','proyecto/data/processed/','proyecto/.venv/','proyecto/.dvc/cache/','proyecto/mlruns/')) for n in names)
            if 'proyecto/evidencias/huggingface.json' in names:
                zip_valid=zip_valid and json.loads(z.read('proyecto/evidencias/huggingface.json'))==publications
            for name in names:
                if Path(name).suffix in {'.py','.json','.md','.txt','.csv','.log','.dvc'}:
                    if re.search(rb'(?:hf_|ghp_)[A-Za-z0-9]{24,}|github_pat_[A-Za-z0-9_]{40,}',z.read(name)):
                        credential_scan=False
    pages=len(PdfReader(out/'informe.pdf').pages) if (out/'informe.pdf').exists() else None
    pdf_valid=pages is not None and pages<=5 and sha(out/'informe.pdf')==read_json('evidencias/informe-verificado.json')['sha256']
    artifact_checks.update({'zip_valid':zip_valid,'pdf_pages':pages,'pdf_valid':pdf_valid,'credential_pattern_scan_passed':credential_scan})
    publication=read_json(out/'verificacion-publicacion.json') if (out/'verificacion-publicacion.json').exists() else {}
    final_commit=(out/'revision-entrega.txt').read_text().strip() if (out/'revision-entrega.txt').exists() else None
    remote_verified=publication.get('passed',False) and publication.get('git_commit')==final_commit
    downloads=publication.get('assets_downloads_verified',{})
    assets_verified=all(downloads.get(n,{}).get('sha256')==artifact_checks[n].get('sha256') and downloads.get(n,{}).get('passed') for n in ['proyecto.zip','informe.pdf','dvc-storage.zip'])
    def item(number,text,passed,evidence,pending=None):
        return {'number':number,'requirement':text,'status':'verificado' if passed else 'pendiente / parcial','evidence':evidence,'pending':pending}
    items=[
        item(1,'Explicar cambios y recuperar código v1/v2',remote_verified,'GitHub main y tags v1/v2, bundle Git, comparación validation FP/FN'),
        item(2,'DVC conserva originales/preparados y recupera sin caché original',recovery['dvc_passed'] and recovery['caches_absent_before_start'],'ZIP DVC entregado, pull limpio, seis archivos y hashes comprobados'),
        item(3,'Cuatro configuraciones, misma partición, run ID consultable',verification['checks']['four_mlflow_runs_reloaded_and_validation_recomputed'],'Cuatro runs FINISHED exportados, dos familias, split fijo y pipelines completos'),
        item(4,'HF contiene dos soluciones completas por SHA y model card',comparison['passed'] and all(v['downloaded_from_hf'] for v in comparison['versions'].values()),'Dos SHA completos descargados, config/dependencias/cards y hashes verificados'),
        item(5,'Recuperación sobre mismas entradas reproduce ambas versiones',comparison['rows']==64 and all(v['classes_exact'] and v['max_score_difference']<=1e-12 for v in comparison['versions'].values()),'64 row_id fijos; clases exactas y diferencia máxima de scores 0 para v1/v2'),
        item(6,'Test no decide solución; predicciones y métricas coinciden',unchanged and original['rows']==82332 and verification['checks']['test_82332_and_recalculation'],'Selección pretest, invariantes contra commit original, CSV completo y recálculo sin reevaluar modelo'),
        item(7,'ZIP, informe, enlaces y README permiten reconstruir',zip_valid and pdf_valid and remote_verified and assets_verified,'ZIP íntegro, PDF <=5 páginas y descargas inmutables de entregables con huellas coincidentes','Resolver publicación/descarga de artefactos si aún no consta' if not assets_verified else None),
        item(8,'Acceso del docente y ausencia de credenciales/datos personales innecesarios',False,'Repositorios privados; token usado sólo mediante entorno seguro; escaneo del ZIP: '+str(credential_scan),'Falta comprobar acceso de la cuenta del profesor a GitHub/release y HF privado. No se dispone de sus usuarios; no se inventan invitaciones.')]
    blocks=[]
    for name in dict.fromkeys(r['block'] for r in rubric):
        rows=[r for r in rubric if r['block']==name]
        blocks.append({'block':name,'max_points':sum(r['max_points'] for r in rows),'conditional_potential_points':sum(r['conditional_potential_points'] for r in rows),'status':'verificado técnicamente' if all(r['status']=='verificado' for r in rows) else 'parcial / datos personales pendientes'})
    result={'audited_at_utc':now(),'final_git_commit':final_commit,'eight_guide_requirements':items,
            'rubric_components':rubric,'rubric_blocks':blocks,'rubric_total_max':100,
            'conditional_potential_points_not_grade':sum(r['conditional_potential_points'] for r in rubric),
            'score_caveat':'Estimación de cobertura, NO calificación. Supeditada a acceso efectivo del docente y su revisión. Sin datos personales/contribuciones humanas completas no se declara entrega administrativa cerrada.',
            'technical_checks_passed':verification['all_required_passed'] and zip_valid and pdf_valid and credential_scan and assets_verified and remote_verified,
            'teacher_access_verified':False,'human_identity_and_contribution_complete':people_complete,
            'artifacts':artifact_checks,'publication_evidence':'verificacion-publicacion.json',
            'preserved_test_evaluated_at':original['evaluated_at_utc'],'frozen_artifacts_unchanged':unchanged,
            'sources':['docs/requisitos-profesor.txt (lista final p.8, rúbrica p.7)','evidencias/verificacion-final.json','evidencias/trazabilidad-final.json','evidencias/recuperacion/resultado.json','verificacion-publicacion.json']}
    write_json(out/'auditoria-cumplimiento.json',result)
    text=f'# Auditoría final — Defiende el servidor\n\nCommit: `{final_commit}`. Fecha UTC: {result["audited_at_utc"]}.\n\n## Ocho requisitos de la guía\n\n| # | Requisito | Estado | Evidencia / pendiente |\n|---|---|---|---|\n'
    for x in items: text+=f'| {x["number"]} | {x["requirement"]} | {x["status"]} | {x["evidence"]}. {x["pending"] or ""} |\n'
    text+='\n## Rúbrica (100 puntos)\n\n| Bloque | Máximo | Cobertura potencial condicionada | Estado |\n|---|---:|---:|---|\n'
    for b in blocks: text+=f'| {b["block"]} | {b["max_points"]} | {b["conditional_potential_points"]:g} | {b["status"]} |\n'
    text+=f'\nPotencial condicionado estimado: **{result["conditional_potential_points_not_grade"]:g}/100**. {result["score_caveat"]}\n\n'
    text+='### Componentes individuales\n\n'
    for r in rubric: text+=f'- **{r["block"]} — {r["component"]} ({r["max_points"]} pts):** {r["status"]}. {r["evidence"]}.\n'
    distribution_note=('Se utilizó un repositorio HF privado separado para distribuirlos, con descargas verificadas por SHA.' if assets_verified else 'El destino HF privado está preparado, pero la carga de archivos fue bloqueada por revisión automática y requiere autorización explícita. No se afirma publicación ni descarga de esos archivos.')
    text+=f'\n## Integridad y cronología\n\nNo hubo reentrenamiento, cambio de umbral ni nueva evaluación test. Evaluación original conservada: {original["evaluated_at_utc"]}. La publicación HF fue posterior; trazabilidad-final.json vincula el mismo hash del artefacto con sus SHA HF, sin modificar registros históricos.\n\nPDF: {pages} páginas; ZIP sin datos masivos ni cachés; escaneo de patrones de credenciales aprobado: {credential_scan}. Las descargas inmutables de entregables coinciden con los tres archivos locales: {assets_verified}. GitHub rechazó adjuntos binarios con HTTP 401 en uploads.github.com. {distribution_note}\n\n'
    text+='## Pendientes humanos y de acceso\n\nCompletar nombres, grupo por integrante y contribución real. Comprobar lectura del profesor en GitHub/release y HF privado mediante mecanismos de las plataformas. No compartir tokens ni declarar invitaciones enviadas sin evidencia. No se afirma envío al docente.\n'
    (out/'auditoria-cumplimiento.md').write_text(text)
    print(json.dumps({'technical_checks_passed':result['technical_checks_passed'],'guide_verified':sum(x['status']=='verificado' for x in items),'guide_pending':sum(x['status']!='verificado' for x in items),'conditional_points_not_grade':result['conditional_potential_points_not_grade']},indent=2))

if __name__=='__main__': main()
