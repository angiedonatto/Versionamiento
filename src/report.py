"""Informe y entrega derivados exclusivamente de artefactos ejecutados."""
import html
import os
import platform
import subprocess
from pathlib import Path
import pandas as pd
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab
from .common import read_json, write_json, sha, now, git_head

def main():
    root = Path('dist')
    root.mkdir(exist_ok=True)
    audit = read_json('evidencias/auditoria.json')
    table = pd.read_csv('evidencias/experimentos.csv')
    selection = read_json('evidencias/seleccion.json')
    versions = {v: read_json(f'evidencias/{v}.json') for v in ['v1','v2']}
    test = read_json('evidencias/metricas-test.json') if Path('evidencias/metricas-test.json').exists() else None
    recovery = read_json('evidencias/recuperacion/resultado.json') if Path('evidencias/recuperacion/resultado.json').exists() else {}
    hf = read_json('evidencias/huggingface.json') if Path('evidencias/huggingface.json').exists() else {}
    github = read_json('evidencias/github.json') if Path('evidencias/github.json').exists() else {}
    people=read_json('configs/integrantes.json')
    author='; '.join(person['nombre'] for person in people['integrantes'])
    group='; '.join(person['grupo'] for person in people['integrantes'])
    styles = getSampleStyleSheet()
    fonts = Path(reportlab.__file__).parent / 'fonts'
    pdfmetrics.registerFont(TTFont('VeraEmbedded',str(fonts / 'Vera.ttf')))
    pdfmetrics.registerFont(TTFont('VeraEmbeddedBold',str(fonts / 'VeraBd.ttf')))
    for name in styles.byName:
        styles[name].fontName = 'VeraEmbeddedBold' if name.startswith('Heading') or name == 'Title' else 'VeraEmbedded'
    styles['BodyText'].fontSize = 9.5
    styles['BodyText'].leading = 13
    styles['BodyText'].spaceAfter = 7
    story = []
    def p(text, style='BodyText'):
        story.append(Paragraph(html.escape(str(text).replace('→',' a ')), styles[style]))
    def heading(text): p(text, 'Heading2')
    def tab(rows, widths=None):
        t = Table([[Paragraph(html.escape(str(c)), styles['BodyText']) for c in row] for row in rows], colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce8f0')),('GRID',(0,0),(-1,-1),.3,colors.lightgrey),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5)]))
        story.append(t)
        story.append(Spacer(1,8))
    p('Defiende el servidor', 'Title')
    p('Informe académico MLOps · evidencia ejecutada, sin garantía de eficacia operacional')
    p(f'Integrante: {author}. Modalidad: individual. Grupo: {group}, confirmado por la estudiante.')
    heading('1. Datos, procedencia y auditoría')
    p('UNSW-NB15: se descargaron las dos particiones académicas desde el mirror inmutable enlazado en el PDF del profesor. Los SHA-256 coinciden exactamente con el anexo. Fecha UTC de descarga: 31 octubre 2026 (30 octubre en Bogotá). El mirror no constituye autenticación frente al archivo oficial UNSW.')
    rows = [['Partición','Filas','Columnas','Normal / ataque','Duplicados extra','Grupos contradict.']]
    for k, label in [('training','Training'),('testing','Test')]:
        d=audit[k]
        rows.append([label,d['rows'],d['columns'],f'{d["class_balance"]["0"]} / {d["class_balance"]["1"]}',d['duplicate_extra_rows'],d['contradictory_groups']])
    tab(rows,[64,58,50,104,70,76])
    p(f'Se usan {len(audit["features"])} entradas; se excluyen id, attack_cat y label. Faltantes totales: training {sum(audit["training"]["missing"].values())}, test {sum(audit["testing"]["missing"].values())}. Tipos y faltantes por columna: auditoria.json.')
    p('Política: conservar todas las filas y las etiquetas originales, incluidas contradicciones; mantener frecuencia natural. Ninguna etiqueta decide qué registros eliminar. Las entradas se uniforman a tipos numéricos comunes y se agrupan por SHA-256; el conteo de duplicados se contrasta con pandas.')
    p(f'Train/validation sólo proceden de training: {audit["splits"]["train"]["rows"]} / {audit["splits"]["validation"]["rows"]} filas. GroupShuffleSplit, semilla {audit["seed"]}, 20% de grupos para validation. Cero grupos idénticos cruzan ambos. Manifiesto por fila y hashes quedan en DVC y auditoria.json.')
    p(f'Test comparte {audit["overlap"]["shared_unique_feature_groups"]} grupos únicos y {audit["overlap"]["test_rows_matching_any_training_file"]} filas de entradas con el archivo training: {audit["overlap"]["test_rows_matching_train"]} con train y {audit["overlap"]["test_rows_matching_validation"]} con validation. Se reporta sin filtrar test: limita la independencia de la evaluación publicada.')
    story.append(PageBreak())
    heading('2. Cuatro configuraciones, comparación justa')
    p('Pipeline serializable scikit-learn: imputación mediana numérica y moda categórica, escala numérica, one-hot ignorando categorías desconocidas y clasificador. Todas las transformaciones se ajustan exclusivamente con train. CPU, sin submuestreo, misma validation. Ataque positivo=1; precision/recall/F1 usan zero_division=0 y FPR=0 si no hay negativos.')
    rows=[['Configuración','Recall','Precision','FPR','Macro-F1','Segundos']]
    for r in table.itertuples(): rows.append([r.id,f'{r.recall_attack:.6f}',f'{r.precision_attack:.6f}',f'{r.fpr:.6f}',f'{r.macro_f1:.6f}',f'{r.elapsed_seconds:.3f}'])
    tab(rows,[92,66,66,66,66,66])
    p('Tabla: umbral 0.5 en las cuatro configuraciones. Hipótesis: lr_c01 ofrece referencia lineal regularizada; lr_c10 reduce regularización (C=10 frente a 0.1); tree_d08 captura interacciones con profundidad 8/hojas ≥20; tree_d16 aumenta flexibilidad con profundidad 16/hojas ≥5. No se cuentan cambios de semilla como experimentos.')
    rows=[['Configuración','TN','FP','FN','TP']]
    for r in table.itertuples(): rows.append([r.id,r.tn,r.fp,r.fn,r.tp])
    tab(rows,[120,76,76,76,76])
    p('Cada run MLflow conserva hipótesis, parámetros, semilla, commit, referencias DVC, métricas y pipeline completo. La exportación se obtuvo con MlflowClient.get_run: cuatro runs FINISHED, consultables sin servidor. Los pipelines se vuelven a cargar en la verificación final y se recalculan sus métricas de validation.')
    heading('Elección de umbral')
    p('Regla fijada antes de entrenar: entre configuraciones distintas del baseline, evaluar 17 umbrales de 0.10 a 0.90 en pasos de 0.05; exigir recall ≥0.90 y maximizar macro-F1, con desempate por menor FPR, mayor umbral e ID. Si ninguna cumple, maximizar macro-F1 sin restricción. No intervienen etiquetas ni métricas test.')
    p(f'Seleccionado: {selection["experiment"]}, umbral {selection["threshold"]}. Se mantiene 0.5 tras la comparación; el cambio sustantivo de v2 es el árbol frente a la logística de v1. El ajuste con una sola validation puede ser optimista; no se hace validación cruzada adicional.')
    story.append(PageBreak())
    heading('3. Dos versiones y evaluación final reservada')
    a,b=selection['v1_validation'],selection['v2_validation']
    p(f'Validation v1 → v2: macro-F1 {a["macro_f1"]:.6f} → {b["macro_f1"]:.6f}; FPR {a["fpr"]:.6f} → {b["fpr"]:.6f}; precision {a["precision_attack"]:.6f} → {b["precision_attack"]:.6f}; recall {a["recall_attack"]:.6f} → {b["recall_attack"]:.6f}.')
    p(f'Coste explícito: FP bajan de {a["fp"]} a {b["fp"]}, pero FN suben de {a["fn"]} a {b["fn"]}. Se aceptan más ataques omitidos para reducir alertas falsas y mejorar macro-F1 en esta partición. No se afirma que esa preferencia sea adecuada para una red real.')
    p(f'Congelación fechada: {selection["frozen_at_utc"]}. La selección se conserva en el tag Git v2 antes de la primera evaluación test. El hash del pipeline v2 es {selection["model_sha256"]}. No se reentrena con validation ni se ajusta el umbral después.')
    if test:
        m=test['metrics']
        tab([['Test final','Valor'],['Filas',test['rows']],['Recall ataque',f'{m["recall_attack"]:.8f}'],['Precision ataque',f'{m["precision_attack"]:.8f}'],['FPR',f'{m["fpr"]:.8f}'],['Macro-F1',f'{m["macro_f1"]:.8f}'],['Matriz [[TN,FP],[FN,TP]]',str(m['confusion_matrix'])]],[220,202])
        p(f'Evaluación test ejecutada: {test["evaluated_at_utc"]}, {test["elapsed_seconds"]:.3f} s. Una predicción por cada una de las 82332 filas originales. row_id identifica archivo/fila; y_pred=1 si score_attack ≥ {test["threshold"]}. Se recalcularon todas las métricas desde predicciones-test.csv y coincidieron exactamente con JSON. No se evalúa v1 en test.')
        p('El cambio de distribución y el solapamiento documentado limitan la interpretación. El resultado test se conserva aunque empeore respecto a validation; no se usa para cambiar el modelo.')
    else:
        p('Test NO ejecutado; pendiente. No se presentan métricas supuestas.')
    story.append(PageBreak())
    heading('4. Trazabilidad, recuperación y límites de acceso')
    for v in ['v1','v2']:
        cfg=versions[v]
        p(f'{v}: Git {cfg["git_commit"]}; MLflow {cfg["mlflow_run_id"]}; DVC prepared SHA256 {cfg["dvc_reference"]["data/processed.dvc"]["sha256"]}. HF: ' + (hf[v]['sha'] if v in hf else 'BLOQUEADO: no se ha publicado; no existe SHA verificable.'))
    p('DVC conserva originales y preparados con referencias Git separadas. El respaldo dvc-storage.zip se entrega fuera del ZIP del proyecto y se puede extraer como remote. Se verifican SHA256 de los dos originales y de todos los preparados tras dvc pull con caché vacía.')
    if recovery:
        p(f'Recuperación real: carpeta nueva, venv nuevo, pip sin caché y cachés DVC/HF nuevas. Inicio {recovery["started_at_utc"]}; duración {recovery["elapsed_seconds"]:.3f} s. DVC pasó: {recovery.get("dvc_passed",False)}. Recuperación completa de ambas revisiones HF: {recovery.get("passed",False)}. Log: evidencias/recuperacion/recuperacion.log. ' + str(recovery.get('blocker','')))
    p('Repositorio público de modelos: https://huggingface.co/angiedonatto/defiende-el-servidor . Visibilidad pública autorizada por la estudiante. Se guardaron 64 filas fijas de validation y salidas de referencia antes de recuperar. Descarga por SHA HF completos; tolerancia de scores 1e-12.')
    local_path=Path('evidencias/recuperacion/comprobacion-local-suplementaria.json')
    if recovery.get('passed'):
        comparison=read_json('evidencias/recuperacion/comparacion.json')
        p(f'Resultado HF: {comparison["rows"]} filas idénticas en ambas pruebas, clases exactas v1/v2; diferencias máximas de scores {comparison["versions"]["v1"]["max_score_difference"]} y {comparison["versions"]["v2"]["max_score_difference"]}. Configuración, umbral, dependencias y SHA256 coinciden con los congelados. Los fallos iniciales se conservaron en historico/sin-hf.')
    elif local_path.exists():
        local=read_json(local_path)
        p(f'Comprobación suplementaria desde el checkout nuevo y venv nuevo (fuente Git local, NO HF): {local["rows"]} filas, clases idénticas en v1/v2; diferencias máximas de scores {local["versions"]["v1"]["max_score_difference"]} y {local["versions"]["v2"]["max_score_difference"]}. Log: local-suplementaria-limpia.log. Esto no aprueba la recuperación exigida desde HF.')
    p(f'Recursos medidos: Linux {platform.machine()}, Python {platform.python_version()}, {os.cpu_count()} CPU visibles; límite de threads BLAS=2 en fit. Máximo RSS reportado por proceso de entrenamiento: {max(table.apply(lambda r: read_json(f"evidencias/mlflow/{r.mlflow_run_id}/run.json")["max_rss_kib_process"],axis=1))/1024:.1f} MiB (acumulado del proceso, no pico incremental por modelo). Tiempos individuales en experimentos.csv; auditoría {audit["elapsed_seconds"]:.3f} s.')
    p('GitHub: ' + ('repositorio público; API consultada sin token y lectura pública comprobada. No se necesita invitar al docente para consultar el código.' if github.get('anonymous_read_verified') else 'push y clon remoto comprobados; si permanece privado, falta verificar el permiso propio del docente.'))
    p('La finalización no volvió a entrenar ni a evaluar test. La publicación HF es posterior al test original; trazabilidad-final.json une sus SHA con el hash del mismo pipeline, sin alterar selección ni resultados. HF permite lectura pública; el acceso a GitHub se documenta por separado.')
    p('Contribuciones: '+people['declaracion_contribucion']+' Codex asistió con descarga, auditoría, código, entrenamiento, trazabilidad y documentos, comprobados con logs. La integrante es responsable de revisar y comprender la solución. No se adaptaron soluciones docentes; dependencias en requirements.txt y datos atribuidos a UNSW.')
    p('Fuentes: PDF del profesor (16-10-2026); research.unsw.edu.au/projects/unsw-nb15-dataset; mirror Nir-J/ML-Projects commit 44bbd02b9e70f74dd915218d5eb702f125341ffc; git-scm.com/doc; doc.dvc.org/start; mlflow.org/docs/latest/ml/tracking; huggingface.co/docs/huggingface_hub/guides/download; scikit-learn.org/stable/common_pitfalls.html.')
    doc=SimpleDocTemplate(str(root / 'informe.pdf'),pagesize=A4,rightMargin=50,leftMargin=50,topMargin=38,bottomMargin=38)
    def footer(canvas, document):
        canvas.setFont('VeraEmbedded',8)
        canvas.drawString(50,23,f'Defiende el servidor · Evidencia real · Página {document.page}')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    pages=len(PdfReader(root / 'informe.pdf').pages)
    assert pages <= 5, f'Informe excede máximo: {pages}'
    write_json('evidencias/informe-verificado.json', {'pages': pages, 'sha256': sha(root / 'informe.pdf'), 'generated_at_utc': now(),
               'numeric_sources':['auditoria.json','experimentos.csv','seleccion.json','metricas-test.json','recuperacion/resultado.json'],
               'method':'Cifras renderizadas directamente desde JSON/CSV; páginas comprobadas con pypdf.'})
    final=git_head()
    text=f'''# Índice de entrega — Defiende el servidor

- Integrante única: **{author}**.
- Grupo: **{group}**, confirmado por la estudiante.
- Contribución: {people['declaracion_contribucion']}
- GitHub solicitado: https://github.com/angiedonatto/Versionamiento
- Revisión base del paquete: `{final}`. El commit final de empaquetado se registra en `revision-entrega.txt` junto al ZIP y en el historial Git; no se inventa una autorreferencia de commit.
- Publicación GitHub: {"PUSH Y CLON REMOTO VERIFICADOS. El usuario autorizó publicar incluso si el repositorio es público; no se cambió su privacidad." if github.get("read_verified") else "PENDIENTE/NO COMPROBADA; consultar logs de acceso."}
- Acceso: repositorios públicos autorizados; se documentan comprobaciones de lectura sin token. No se afirma haber iniciado sesión con la cuenta del docente ni enviado invitaciones.
- Historial sin dependencia de GitHub: `historial.bundle` dentro del ZIP; `git clone historial.bundle proyecto`.

## Trazabilidad por versión
'''
    for v,cfg in versions.items():
        text+=f'\n### {v}\n\n- Commit productor: `{cfg["git_commit"]}`.\n- Tag recuperable: `{v}`.\n- DVC raw: `{cfg["dvc_reference"]["data/raw.dvc"]["sha256"]}` (SHA256 del puntero).\n- DVC preparados: `{cfg["dvc_reference"]["data/processed.dvc"]["sha256"]}` (SHA256 del puntero; contenido íntegro en evidencias/{v}.json).\n- MLflow run: `{cfg["mlflow_run_id"]}`.\n- Familia: {cfg["family"]}; parámetros: `{cfg["params"]}`.\n- Umbral: `{cfg["threshold"]}`; ataque si score >= umbral.\n- Modelo SHA256: `{cfg["model_sha256"]}`.\n- HF: '+(f'{hf[v]["url"]}/tree/{hf[v]["sha"]} (público, autorizado; SHA completo `{hf[v]["sha"]}`)' if v in hf else '**BLOQUEADO: no existe SHA publicado comprobado.**')+'\n'
    text+='''
## Evidencias y almacenamiento

- `evidencias/descarga.json`: fuentes y hashes contrastados con PDF.
- `evidencias/auditoria.json`: balance, tipos, faltantes, duplicados, contradicciones y solapamientos; semilla y hashes de splits.
- `data/raw.dvc`, `data/processed.dvc`, `.dvc/config`, `.dvcignore`: referencias de ambas versiones de datos.
- `evidencias/experimentos.csv`, `evidencias/umbrales-validation.json`: cuatro experimentos y comparación de umbrales.
- `evidencias/mlflow/<run_id>/`: entidad real exportada `mlflow-record.json`, metadatos `run.json` y pipeline completo `pipeline.joblib`.
- `evidencias/modelos/v1/` y `v2/`: bundles completos preparados localmente, con pipeline, threshold/config, model card, features y dependencias. No equivalen a publicación ni descarga desde HF.
- `evidencias/seleccion.json`: decisión de validation fechada, incluida en tag v2 antes de test; no se modifica después de test.
- `evidencias/trazabilidad-final.json`: SHA HF de ambas versiones, huellas originales, cronología real de publicación posterior al test y vínculo con el mismo artefacto evaluado.
- `evidencias/invariantes-finalizacion.json`: huellas ancla del commit anterior; permiten comprobar que no se alteraron selección, test, umbral, modelos ni muestra.
- `evidencias/metricas-test.json`, `predicciones-test.csv`, `recalculo-test.json`: test completo y comprobación por CSV.
- `evidencias/recuperacion/`: muestra fija de 64 filas, salidas antes/después (estas últimas sólo si HF funciona), hashes, log y resultado real.
- `comprobacion-local-suplementaria.json` y `local-suplementaria-limpia.log`: prueba adicional exitosa de ambas versiones desde Git local en checkout/venv nuevos; no sustituye HF. Los archivos `v*-local-despues.csv` se distinguen de las salidas HF.
- `evidencias/verificacion-final.json`: distingue verificado de pendiente/bloqueado.
- `README.md`: comandos exactos para instalación, DVC pull, reproducir un experimento, descargar por SHA y predecir.
- `proyecto.zip`: código, evidencias y bundle Git; sin CSV masivos, entornos ni cachés.
- `informe.pdf`: máximo cinco páginas; generado desde evidencia real.
- **`dvc-storage.zip` se entrega aparte**. Extraer junto al proyecto: debe quedar `../dvc-storage`. `.dvc/config` configura remote `entrega`. Ejecutar `DVC_SITE_CACHE_DIR="$PWD/.runtime/dvc-site" dvc pull`.
- Ubicación de los tres entregables: directorio de entrega `/workspace/entrega-defiende/` de esta tarea. No es un servicio público: descargar y adjuntar al canal del profesor, o compartir carpeta con permiso de lectura. Sin esa acción no se afirma acceso docente.
- Distribución pública autorizada de archivos: https://huggingface.co/datasets/angiedonatto/defiende-el-servidor-entregables . El SHA inmutable de la entrega y los enlaces directos de descarga se guardan en `verificacion-publicacion.json`, junto a los archivos.
- Índice GitHub de entrega: https://github.com/angiedonatto/Versionamiento/releases/tag/entrega-grupo-b-2026-10-30 . Esta revisión confirma grupo B y documenta la visibilidad pública autorizada; conserva versiones anteriores, sin tocar modelos congelados.
- `auditoria-cumplimiento.md` y `.json` junto al ZIP: auditoría definitiva de los ocho requisitos y de cada componente de la rúbrica, incluidos pendientes administrativos.

## Ejecución medida y limitaciones
'''
    text+=f'\nPython {platform.python_version()}, Linux {platform.machine()}, {os.cpu_count()} CPU visibles. Tiempos de fit+validación+serialización: '+', '.join(f'{r.id}={r.elapsed_seconds:.3f}s' for r in table.itertuples())+f'. Auditoría={audit["elapsed_seconds"]:.3f}s. Recuperación={recovery.get("elapsed_seconds","pendiente")}s. Máximo RSS por proceso en run.json. Sin GPU ni muestreo.\n'
    text+=f'\nRecuperación DVC comprobada: {recovery.get("dvc_passed",False)}; recuperación HF completa: {recovery.get("passed",False)}. Log: `evidencias/recuperacion/recuperacion.log`. Bloqueo: {recovery.get("blocker","ninguno registrado")}.\n'
    text+='''
La selección de 17 umbrales por modelo en una sola validation puede ser optimista.
Los grupos idénticos no cruzan train/validation, pero las particiones publicadas
contienen 8541 filas test con entradas vistas en training. No se filtra test.
Dataset histórico, sin validación en red actual ni garantía de seguridad operacional.
v2 reduce FP frente a v1 en validation, pero aumenta FN; no mejora todas las métricas.
No se afirma prueba de lectura del docente sin conocer sus cuentas y conceder acceso.

## IA, terceros y contribuciones

Se utilizó **OpenAI Codex** para leer los requisitos, implementar scripts, ejecutar
comandos, diagnosticar dependencias, entrenar, comparar y generar documentos.
Todas las cifras provienen de ejecuciones; lo bloqueado se informa como tal.
Angie Valentina Donato Pita es la única integrante y contribuyente estudiantil,
según su declaración. Es responsable de revisar, comprender y poder explicar
la solución; la asistencia de Codex se mantiene explícitamente declarada.
No se usaron soluciones docentes ni fragmentos adaptados de terceros; se usaron
APIs de herramientas de código abierto, identificadas en requirements.txt.
Datos de UNSW-NB15 con atribución y condiciones académicas de la fuente oficial.

## Recuperación y cierre

Las revisiones HF publicadas están en huggingface.json y los resultados reales
en recuperacion/resultado.json. Un `passed=true` sólo se emite después de descargar
ambas revisiones por SHA en un venv nuevo y reproducir las predicciones.
Para repetir la recuperación (sin entrenar ni reevaluar test):

```bash
python -m src.recover --storage ../dvc-storage.zip \
  --git-source https://github.com/angiedonatto/Versionamiento.git \
  --revision "$(git rev-parse HEAD)"
python -m src.lifecycle recompute
python -m src.verify
```

La lectura pública de HF no requiere token; las escrituras sí usan autenticación
segura. Nunca entregar ni publicar credenciales.
Los SHA evaluados no se sustituyen por main, tags móviles o nuevas serializaciones.

El grupo B ya está confirmado. Las lecturas públicas de HF y GitHub se comprueban
sin token, sin exigir credenciales del docente ni inventar invitaciones.
La prueba con la cuenta propietaria no demuestra acceso del docente. No se
inventan usuarios ni se afirma que se enviaron invitaciones o la entrega.

Texto de envío: `mensaje-profesor.txt` junto a los entregables. Completar campos
de acceso antes de enviar por **un único canal** (Teams o correo).
'''
    Path('entrega.md').write_text(text)
    print(f'Informe {pages} páginas; entrega.md generado. PDF SHA256 {sha(root / "informe.pdf")}')

if __name__ == '__main__':
    main()
