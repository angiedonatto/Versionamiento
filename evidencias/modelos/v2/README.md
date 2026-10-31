---
library_name: scikit-learn
pipeline_tag: tabular-classification
tags:
- unsw-nb15
- academic
---
# Defiende el servidor — v2

Clasificación binaria académica de conexiones: normal=0, ataque=1. NO usar para
bloqueo automático de tráfico real. Datos históricos UNSW-NB15, atribución:
https://research.unsw.edu.au/projects/unsw-nb15-dataset . Mirror inmutable del PDF
del docente, hashes y auditoría en el repositorio Git. Se excluyen id, label y attack_cat.
Pipeline completo sklearn: imputación mediana/moda, escala numérica, one-hot con
categorías desconocidas ignoradas y DecisionTreeClassifier. Fit sólo en train, grupos
idénticos no cruzan validation. Se conserva frecuencia natural y contradicciones.

## Validation (ataque positivo; zero_division=0)
Threshold: 0.5; regla: score_attack >= threshold.
Recall: 0.9599983453296931; precision: 0.9630659418184836; FPR: 0.07871230211373485;
macro-F1: 0.9398455412454236; matriz [[TN,FP],[FN,TP]]: [[10417, 890], [967, 23207]].
Selección sólo con validation. Estas NO son métricas test.

## Trazabilidad
Código: https://github.com/angiedonatto/Versionamiento/commit/d7e3d35b724fc5828a79cdd68200fc560194a54d
DVC raw SHA256: aef69f0eb635b870b7d72e66e9ebdc27c29ad9f22df065bb6405aa6db29d6870
DVC processed SHA256: 8a3465fc54393b03148751c2c1db1422ca8c1ed48adb307fac757d16eade75a6
Referencias DVC completas en config.json. MLflow run: d5002ef5f9544389ab3597c526771740.
SHA256 pipeline.joblib: a2d7aebf559a8393bb55a3ad80f698d1777bfe971eed850f463bbc6d96cdc95c. Hipótesis: Mayor profundidad captura patrones de ataque raros; puede elevar falsos positivos..

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
