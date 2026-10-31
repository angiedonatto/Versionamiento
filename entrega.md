# Índice de entrega — Defiende el servidor

- Integrantes: **[NOMBRES COMPLETOS POR COMPLETAR]**.
- Grupo de cada integrante: **[A/B POR COMPLETAR]**.
- Contribución humana: **[CADA INTEGRANTE DEBE DECLARAR Y COMPRENDER SU APORTE]**.
- GitHub solicitado: https://github.com/angiedonatto/Versionamiento
- Revisión base del paquete: `1e5a76f75ca2ff40301ececf37cdc021cefee860`. El commit final de empaquetado se registra en `revision-entrega.txt` junto al ZIP y en el historial Git; no se inventa una autorreferencia de commit.
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
- HF: **BLOQUEADO: HF_TOKEN no disponible o acceso sin resolver; no existe URL/SHA publicado comprobado.**

### v2

- Commit productor: `d7e3d35b724fc5828a79cdd68200fc560194a54d`.
- Tag recuperable: `v2`.
- DVC raw: `aef69f0eb635b870b7d72e66e9ebdc27c29ad9f22df065bb6405aa6db29d6870` (SHA256 del puntero).
- DVC preparados: `8a3465fc54393b03148751c2c1db1422ca8c1ed48adb307fac757d16eade75a6` (SHA256 del puntero; contenido íntegro en evidencias/v2.json).
- MLflow run: `d5002ef5f9544389ab3597c526771740`.
- Familia: DecisionTreeClassifier; parámetros: `{'max_depth': 16, 'min_samples_leaf': 5}`.
- Umbral: `0.5`; ataque si score >= umbral.
- Modelo SHA256: `a2d7aebf559a8393bb55a3ad80f698d1777bfe971eed850f463bbc6d96cdc95c`.
- HF: **BLOQUEADO: HF_TOKEN no disponible o acceso sin resolver; no existe URL/SHA publicado comprobado.**

## Evidencias y almacenamiento

- `evidencias/descarga.json`: fuentes y hashes contrastados con PDF.
- `evidencias/auditoria.json`: balance, tipos, faltantes, duplicados, contradicciones y solapamientos; semilla y hashes de splits.
- `data/raw.dvc`, `data/processed.dvc`, `.dvc/config`, `.dvcignore`: referencias de ambas versiones de datos.
- `evidencias/experimentos.csv`, `evidencias/umbrales-validation.json`: cuatro experimentos y comparación de umbrales.
- `evidencias/mlflow/<run_id>/`: entidad real exportada `mlflow-record.json`, metadatos `run.json` y pipeline completo `pipeline.joblib`.
- `evidencias/modelos/v1/` y `v2/`: bundles completos preparados localmente, con pipeline, threshold/config, model card, features y dependencias. No equivalen a publicación ni descarga desde HF.
- `evidencias/seleccion.json`: decisión de validation fechada, incluida en tag v2 antes de test; no se modifica después de test.
- `evidencias/metricas-test.json`, `predicciones-test.csv`, `recalculo-test.json`: test completo y comprobación por CSV.
- `evidencias/recuperacion/`: muestra fija de 64 filas, salidas antes/después (estas últimas sólo si HF funciona), hashes, log y resultado real.
- `comprobacion-local-suplementaria.json` y `local-suplementaria-limpia.log`: prueba adicional exitosa de ambas versiones desde Git local en checkout/venv nuevos; no sustituye HF. Los archivos `v*-local-despues.csv` se distinguen de las salidas HF.
- `evidencias/verificacion-final.json`: distingue verificado de pendiente/bloqueado.
- `README.md`: comandos exactos para instalación, DVC pull, reproducir un experimento, descargar por SHA y predecir.
- `proyecto.zip`: código, evidencias y bundle Git; sin CSV masivos, entornos ni cachés.
- `informe.pdf`: máximo cinco páginas; generado desde evidencia real.
- **`dvc-storage.zip` se entrega aparte**. Extraer junto al proyecto: debe quedar `../dvc-storage`. `.dvc/config` configura remote `entrega`. Ejecutar `DVC_SITE_CACHE_DIR="$PWD/.runtime/dvc-site" dvc pull`.
- Ubicación de los tres entregables: directorio de entrega `/workspace/entrega-defiende/` de esta tarea. No es un servicio público: descargar y adjuntar al canal del profesor, o compartir carpeta con permiso de lectura. Sin esa acción no se afirma acceso docente.

## Ejecución medida y limitaciones

Python 3.12.14, Linux x86_64, 5 CPU visibles. Tiempos de fit+validación+serialización: lr_c01=3.131s, lr_c10=15.703s, tree_d08=2.519s, tree_d16=5.054s. Auditoría=10.593s. Recuperación=68.029175087s. Máximo RSS por proceso en run.json. Sin GPU ni muestreo.

Recuperación DVC comprobada: True; recuperación HF completa: False. Log: `evidencias/recuperacion/recuperacion.log`. Bloqueo: No hay SHAs de Hugging Face publicados: DVC verificado; recuperación HF bloqueada por acceso..

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
El estudiante debe revisar, comprender y poder explicar el código y completar
su contribución real. No se inventa nombre, grupo ni participación humana.
No se usaron soluciones docentes ni fragmentos adaptados de terceros; se usaron
APIs de herramientas de código abierto, identificadas en requirements.txt.
Datos de UNSW-NB15 con atribución y condiciones académicas de la fuente oficial.

## Operaciones externas pendientes (si no hay evidencia de éxito)

1. En configuración del entorno: guardar HF_TOKEN con escritura a huggingface.co
   y aplicar dominios guardados. Nunca ponerlo en Git ni en el chat.
2. `python -m src.lifecycle publish` crea automáticamente repo HF privado en la
   cuenta del token. Sólo ejecutar si no existe ya publicación registrada; preserva SHA.
3. `git add evidencias/huggingface.json evidencias/publicacion-congelada.json && git commit -m 'publicar referencias HF verificables'`.
4. `python -m src.recover --storage ../dvc-storage.zip --git-source . --revision HEAD`.
5. GitHub: el usuario autorizó expresamente publicar incluso si el repositorio
   es público. No volver a pedir autorización ni cambiar su privacidad. Actualizar
   con `git push origin HEAD:main --tags` y comprobar el SHA con `git ls-remote`.
   Un Forbidden de la API no demuestra que Git push esté bloqueado: usar la
   operación Git requerida y el proxy suministrado.
6. Verificar lectura GitHub/HF; invitar al docente con su usuario en cada plataforma.
7. Regenerar informe, verificación y ZIP con las nuevas evidencias. No volver a
   evaluar test ni modificar pipeline, selección o umbral después del test.

Texto de envío: `mensaje-profesor.txt` junto a los entregables. Completar campos
personales y accesos antes de enviar por **un único canal** (Teams o correo).
