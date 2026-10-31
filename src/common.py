"""Funciones compartidas; los artefactos sólo contienen clases estándar sklearn."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score, accuracy_score

EXCLUDED = ['label', 'attack_cat', 'id']
RAW_NAMES = {'training': 'UNSW_NB15_training-set.csv', 'testing': 'UNSW_NB15_testing-set.csv'}
EXPECTED = {'training': 'bec7dd5ec88dc2a0ccc7a07879d338395ed7421750f675fd0339e07dfe0648fa', 'testing': '734fe6642edf758f7c94d7d9149426b49d202fe8e7bf0bef47392489c3c0a559'}
MIRROR = 'https://raw.githubusercontent.com/Nir-J/ML-Projects/44bbd02b9e70f74dd915218d5eb702f125341ffc/UNSW-Network_Packet_Classification/'

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + '\n')

def read_json(path):
    return json.loads(Path(path).read_text())

def git_head():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()

def data_ref():
    return {p: {'sha256': sha(p), 'contents': Path(p).read_text()} for p in ['data/raw.dvc', 'data/processed.dvc']}

def metrics(y, pred):
    tn, fp, fn, tp = map(int, confusion_matrix(y, pred, labels=[0, 1]).ravel())
    return {'recall_attack': float(recall_score(y, pred, zero_division=0)),
            'precision_attack': float(precision_score(y, pred, zero_division=0)),
            'fpr': fp / (fp + tn) if fp + tn else 0.0,
            'macro_f1': float(f1_score(y, pred, average='macro', zero_division=0)),
            'accuracy': float(accuracy_score(y, pred)), 'tn': tn, 'fp': fp, 'fn': fn, 'tp': tp,
            'confusion_matrix': [[tn, fp], [fn, tp]],
            'positive_class': 1, 'zero_division': 0}

def scores(pipeline, x):
    index = list(pipeline.classes_).index(1)
    return pipeline.predict_proba(x)[:, index]

def predict_frame(pipeline, x, threshold, ids, y=None):
    import pandas as pd
    s = scores(pipeline, x)
    d = {'row_id': list(ids), 'score_attack': s, 'y_pred': (s >= threshold).astype(int)}
    if y is not None:
        d['y_true'] = np.asarray(y, dtype=int)
    return pd.DataFrame(d)
