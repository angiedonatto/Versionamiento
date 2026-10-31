# Defiende el servidor — MLOps

Taller académico de clasificación normal/ataque UNSW-NB15. Fuente de requisitos:
PDF del profesor Julián Zuluaga (16 octubre 2026), transcripción en
`docs/requisitos-profesor.txt`. Evidencias ejecutadas en `evidencias/`;
`entrega.md` indexa versiones, métricas, accesos y limitaciones.

## Instalación

Python **3.12.14**, CPU, Linux x86_64; no necesita GPU ni servidor. Desde la raíz:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
export DVC_SITE_CACHE_DIR="$PWD/.runtime/dvc-site"
export HF_HUB_DISABLE_XET=1
export OPENBLAS_NUM_THREADS=2
export OMP_NUM_THREADS=2
```

Las dependencias directas y transitivas están fijadas en `requirements.txt`.
Se fija pathspec 0.12.1 porque 1.1.1 es incompatible con el DVC usado.
Las tareas de nube ya están aisladas: utiliza el checkout existente, sin crear
worktrees, salvo petición explícita del usuario. No hay procesos que reiniciar.

## Recuperar datos e historial

Descargar **por separado** `dvc-storage.zip` (ver enlaces/rutas en entrega.md).
Descomprimirlo al lado del proyecto: `../dvc-storage/`. No es la caché de DVC:
es una copia de almacenamiento que se entrega como archivo independiente.

```bash
python -m zipfile -e ../dvc-storage.zip ..
dvc pull
python -m src.recovery_check --output evidencias/recuperacion
git log --oneline --all
git show datos-originales:data/raw.dvc
git show datos-preparados:data/processed.dvc
```

El ZIP de proyecto incluye `historial.bundle` para conservar el historial aun
si falla GitHub. Para restaurarlo: `git clone historial.bundle proyecto-git`.
La comprobación del profesor requiere acceso de lectura al repositorio GitHub y
al repositorio privado HF mediante los mecanismos propios de cada plataforma.
Nunca se deben compartir tokens.

## Reproducir entrenamiento

Las cuatro configuraciones en `configs/experiments.json` comparten 139860 filas
de train y 35481 de validation. No hay muestreo de entrenamiento. Se conservaron
duplicados y contradicciones, agrupados por entradas idénticas para que ningún
grupo cruce entre train y validation. No se usan `id`, `attack_cat`, `label`.

Para reproducir en un checkout de código limpio, sin sobrescribir evidencias
de la entrega, usar la revisión que produjo los experimentos:

```bash
git clone https://github.com/angiedonatto/Versionamiento.git replica
cd replica
git checkout datos-preparados
# crear/activar venv e instalar requirements como arriba; descomprimir respaldo
export DVC_SITE_CACHE_DIR="$PWD/.runtime/dvc-site"
dvc pull
python -m src.train --ids lr_c01
```

`python -m src.train` ejecuta las cuatro configuraciones en una copia sin tabla
de experimentos previa; si existe una ejecución del mismo ID, falla para no
destruirla. El pipeline completo se registra con MLflow y se exporta en
`evidencias/mlflow/<run_id>/pipeline.joblib` y `run.json`.
`python -m src.lifecycle select` sólo usa validation y no sobrescribe una selección
existente. La tabla registra umbral 0.5 para las cuatro configuraciones; el
análisis de otros umbrales está en `umbrales-validation.json`.

## Descargar modelos por SHA y predecir

Ambas versiones están publicadas en el repositorio **privado**
https://huggingface.co/angiedonatto/defiende-el-servidor . Los SHA completos
inmutables se conservan en `evidencias/huggingface.json`; `v1`/`v2` son tags auxiliares.
Se requiere un `HF_TOKEN` propio con permiso de lectura. Configurarlo mediante
secretos seguros del entorno o el inicio de sesión interactivo de Hugging Face;
nunca incluirlo en comandos guardados, Git, ZIP o mensajes.

```bash
python -m src.download_model --version v1 --output descargado-v1
python -m src.download_model --version v2 --output descargado-v2
python -m src.lifecycle predict --model-dir descargado-v2 \
  --input evidencias/recuperacion/muestra-validation.csv --output predicciones.csv
```

El script exige SHA completo registrado, verifica SHA256 del pipeline y no
reemplaza una descarga fallida por un modelo local. Usar autenticación segura
HF con permisos de lectura al repo privado. Sólo cargar joblib de confianza.

## Recuperación independiente y test reservado

```bash
python -m src.recover --storage ../dvc-storage.zip \
  --git-source https://github.com/angiedonatto/Versionamiento.git \
  --revision "$(git rev-parse HEAD)"
python -m src.lifecycle recompute
python -m src.verify
```

`recover` crea carpeta, venv y cachés nuevos, instala todo sin caché pip, extrae
el remote entregado, hace `dvc pull`, verifica huellas y descarga ambas revisiones
HF por SHA. Compara exactamente 64 filas fijas y clases; tolerancia de scores
1e-12. Un bloqueo HF deja exit code 2 y `passed=false`, aunque DVC haya pasado.
La ejecución definitiva usa una revisión Git completa, un venv recién creado
y rutas de caché vacías, y obtiene los pipelines exclusivamente desde HF por SHA.
Los fallos iniciales sin credenciales permanecen en `recuperacion/historico/`.

La evaluación `python -m src.lifecycle test` sólo se permite una vez y después
del tag Git `v2` con selección congelada. **No repetirla en la entrega**: para
revisar métricas usar `recompute`, que lee las predicciones ya guardadas y no
vuelve a cargar el modelo ni calcular scores test. Ataque positivo=1; regla
`score_attack >= threshold`; denominadores cero producen 0. `row_id` identifica
archivo y número de registro (1-based, excluye cabecera).

## Artefactos y acceso

No hay datos masivos, venv ni cachés en el ZIP del proyecto. Modelos completos
de los cuatro experimentos están en la exportación MLflow, como evidencia;
el almacenamiento DVC se entrega aparte. `historial.bundle` contiene sólo
referencias recuperables de Git, sin datos crudos ni secretos. El informe PDF
se genera desde JSON/CSV reales con `python -m src.report` y tiene máximo cinco
páginas. Los pendientes de acceso, si los hay, figuran explícitamente en
`entrega.md`; no se consideran comprobaciones aprobadas.

## Finalización sin alterar los modelos

No se reentrenó ni se repitió la evaluación del test al publicar los modelos.
`evidencias/invariantes-finalizacion.json` conserva las huellas originales de la
selección, los dos pipelines, las referencias, la muestra y el test. La relación
HF con la evaluación ya realizada se añade en `trazabilidad-final.json`, sin
modificar `seleccion.json` ni `metricas-test.json`: la publicación HF ocurrió
después de la evaluación original y se verifica que el artefacto es el mismo.

La auditoría definitiva de los ocho requisitos y los 100 puntos se entrega en
`auditoria-cumplimiento.md` y `.json` junto al ZIP. La prueba de lectura del
profesor y los datos personales se distinguen de las comprobaciones técnicas.
Los archivos se distribuyen en un repositorio HF **de tipo dataset y privado**,
separado del repositorio de modelos:
https://huggingface.co/datasets/angiedonatto/defiende-el-servidor-entregables .
Los enlaces `resolve/<SHA>/...` y sus hashes figuran en la verificación final.
GitHub permitió publicar el código pero rechazó sus adjuntos binarios con HTTP
401 en uploads.github.com; no se extrajeron ni reemplazaron credenciales para
evitarlo. La distribución alternativa no modifica v1/v2 ni sus SHA.
