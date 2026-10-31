# Índice de entrega — Defiende el servidor

- Integrante única: **Angie Valentina Donato Pita**.
- Grupo: **B**, confirmado por la estudiante.
- Contribución: Trabajo individual de Angie Valentina Donato Pita, única integrante y responsable de la entrega académica. La contribución estudiantil se atribuye íntegramente a ella. Se declara por separado la asistencia de OpenAI Codex en la implementación, ejecución y documentación; no se oculta dicha ayuda.
- GitHub solicitado: https://github.com/angiedonatto/Versionamiento
- Revisión base del paquete: `dfa6443fbc0993afa195fa1764f2b56463f1163d`. El commit final de empaquetado se registra en `revision-entrega.txt` junto al ZIP y en el historial Git; no se inventa una autorreferencia de commit.
- Publicación GitHub: PUSH Y CLON REMOTO VERIFICADOS. El usuario autorizó publicar incluso si el repositorio es público; no se cambió su privacidad.
- Acceso de la cuenta del docente: no comprobado; si el repositorio es privado, conceder lectura mediante invitación.
- Historial sin dependencia de GitHub: `historial.bundle` dentro del ZIP; `git clone historial.bundle proyecto`.

## Trazabilidad por versión

### v1

- Commit productor: `91b68ca202873d828a21f627473a61eee632d872`.
- Tag recuperable: `v1`.
- DVC raw: `aef69f0eb635b870b7d72e66e9ebdc27c29ad9f22df065bb6405aa6db29d6870` (SHA256 del puntero).
- DVC preparados: `8a3465fc54393b03148751c2c1db1422ca8c1ed48adb307fac757d16eade75a6` (SHA256 del puntero; contenido íntegro en evidencias/v1.json).
- MLflow run: `dbabc72d10584079894a1d4829fb4ddc`.
- Familia: LogisticRegression; parámetros: `{'C': 0.1, 'max_iter': 1000, 'solver': 'liblinear'}`.
- Umbral: `0.5`; ataque si score >= umbral.
- Modelo SHA256: `379b81212257ce54700242b7568e75ba5cc76d444cd25101dc589494bd9d6f40`.
- HF: https://huggingface.co/angiedonatto/defiende-el-servidor/tree/989ec48decb0f32dfc4ae448389e813bc0fc38c2 (privado; SHA completo `989ec48decb0f32dfc4ae448389e813bc0fc38c2`)

### v2

- Commit productor: `d7e3d35b724fc5828a79cdd68200fc560194a54d`.
- Tag recuperable: `v2`.
- DVC raw: `aef69f0eb635b870b7d72e66e9ebdc27c29ad9f22df065bb6405aa6db29d6870` (SHA256 del puntero).
- DVC preparados: `8a3465fc54393b03148751c2c1db1422ca8c1ed48adb307fac757d16eade75a6` (SHA256 del puntero; contenido íntegro en evidencias/v2.json).
- MLflow run: `d5002ef5f9544389ab3597c526771740`.
- Familia: DecisionTreeClassifier; parámetros: `{'max_depth': 16, 'min_samples_leaf': 5}`.
- Umbral: `0.5`; ataque si score >= umbral.
- Modelo SHA256: `a2d7aebf559a8393bb55a3ad80f698d1777bfe971eed850f463bbc6d96cdc95c`.
- HF: https://huggingface.co/angiedonatto/defiende-el-servidor/tree/9c8fd844aac0f3c04238a96dd7e43bd6b4fe7f27 (privado; SHA completo `9c8fd844aac0f3c04238a96dd7e43bd6b4fe7f27`)

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
- Distribución privada de archivos: https://huggingface.co/datasets/angiedonatto/defiende-el-servidor-entregables . El SHA inmutable de la entrega y los enlaces directos de descarga se guardan en `verificacion-publicacion.json`, junto a los archivos.
- Índice GitHub de entrega: https://github.com/angiedonatto/Versionamiento/releases/tag/entrega-grupo-b-2026-10-30 . Esta revisión corrige únicamente la identificación del grupo; conserva las publicaciones anteriores. Su publicación y los enlaces de archivos se comprueban en verificacion-publicacion.json. Se usa el destino HF privado autorizado, sin tocar los modelos congelados.
- `auditoria-cumplimiento.md` y `.json` junto al ZIP: auditoría definitiva de los ocho requisitos y de cada componente de la rúbrica, incluidos pendientes administrativos.

## Ejecución medida y limitaciones

Python 3.12.14, Linux x86_64, 5 CPU visibles. Tiempos de fit+validación+serialización: lr_c01=3.131s, lr_c10=15.703s, tree_d08=2.519s, tree_d16=5.054s. Auditoría=10.593s. Recuperación=57.112014585s. Máximo RSS por proceso en run.json. Sin GPU ni muestreo.

Recuperación DVC comprobada: True; recuperación HF completa: True. Log: `evidencias/recuperacion/recuperacion.log`. Bloqueo: ninguno registrado.

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
python -m src.recover --storage ../dvc-storage.zip   --git-source https://github.com/angiedonatto/Versionamiento.git   --revision "$(git rev-parse HEAD)"
python -m src.lifecycle recompute
python -m src.verify
```

HF_TOKEN debe ser propio o proporcionado por el entorno seguro y tener permiso
de lectura del repositorio privado. Nunca entregar ni publicar credenciales.
Los SHA evaluados no se sustituyen por main, tags móviles o nuevas serializaciones.

Pendiente de la entrega humana: comprobar el acceso de la cuenta del profesor
a GitHub, la release y ambos repositorios HF privados. El grupo B ya está confirmado.
La prueba con la cuenta propietaria no demuestra acceso del docente. No se
inventan usuarios ni se afirma que se enviaron invitaciones o la entrega.

Texto de envío: `mensaje-profesor.txt` junto a los entregables. Completar campos
de acceso antes de enviar por **un único canal** (Teams o correo).
