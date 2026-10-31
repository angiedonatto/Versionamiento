"""Descarga verificable, auditoría y partición por grupos de entradas idénticas."""
import argparse
import hashlib
import time
import urllib.request
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from .common import EXCLUDED, RAW_NAMES, EXPECTED, MIRROR, sha, now, write_json, read_json

def download():
    Path('data/raw').mkdir(parents=True, exist_ok=True)
    records = {}
    for kind, name in RAW_NAMES.items():
        p = Path('data/raw') / name
        if not p.exists():
            urllib.request.urlretrieve(MIRROR + name, p)
        assert sha(p) == EXPECTED[kind], f'Hash incorrecto: {p}'
        records[kind] = {'source': MIRROR + name, 'sha256': sha(p), 'bytes': p.stat().st_size,
                         'verified_at_utc': now(), 'download_date_utc': '2026-10-31',
                         'official_attribution': 'https://research.unsw.edu.au/projects/unsw-nb15-dataset',
                         'provenance': 'Mirror inmutable enlazado en PDF; hash coincide con anexo. No autentica contra UNSW.'}
    write_json('evidencias/descarga.json', records)

def groups(df, features):
    # Hash SHA-256 por representación CSV canónica de cada fila; tipos iguales en ambas particiones.
    return df[features].apply(lambda row: hashlib.sha256(row.to_json(double_precision=15).encode()).hexdigest(), axis=1)

def main():
    start = time.perf_counter()
    download()
    config = read_json('configs/experiments.json')
    frames = {k: pd.read_csv(Path('data/raw') / n) for k, n in RAW_NAMES.items()}
    assert len(frames['training']) == 175341 and len(frames['testing']) == 82332
    assert list(frames['training'].columns) == list(frames['testing'].columns)
    features = [c for c in frames['training'].columns if c not in EXCLUDED]
    # El esquema es idéntico y se fuerza el mismo tipo numérico antes de agrupar.
    numeric = frames['training'][features].select_dtypes(include='number').columns.tolist()
    for df in frames.values():
        df[numeric] = df[numeric].astype(float)
    hashes = {k: groups(df, features) for k, df in frames.items()}
    audit = {'created_at_utc': now(), 'sources': read_json('evidencias/descarga.json'),
             'features': features, 'excluded': EXCLUDED, 'seed': config['seed'],
             'policy': 'Conservar todas las filas, incluso duplicados y contradicciones; agrupar entradas idénticas sin etiquetas mediante SHA256. No deduplicar test. No resolver contradicciones por mayoría. Peso natural por fila.',
             'group_encoding': 'pandas row.to_json(double_precision=15) tras uniformar números a float64; SHA256; comprobación adicional de duplicados con pandas',
             'test_label_policy': 'Sólo balance agregado/contradicciones para auditoría; nunca selección ni ajuste. Test predictivo reservado hasta congelación.'}
    for kind, df in frames.items():
        g = hashes[kind]
        label_counts = df.groupby(g)['label'].nunique()
        contradictions = label_counts[label_counts > 1].index
        audit[kind] = {'rows': len(df), 'columns': len(df.columns), 'column_names': list(df.columns),
                       'dtypes': {c: str(t) for c, t in pd.read_csv(Path('data/raw') / RAW_NAMES[kind], nrows=1000).dtypes.items()},
                       'missing': {c: int(v) for c, v in df.isna().sum().items()},
                       'class_balance': {str(k): int(v) for k, v in df.label.value_counts().items()},
                       'unique_feature_groups': int(g.nunique()), 'duplicate_extra_rows': int(g.duplicated().sum()),
                       'duplicate_rows_all_members': int(g.duplicated(keep=False).sum()),
                       'pandas_duplicate_extra_rows': int(df.duplicated(subset=features).sum()),
                       'contradictory_groups': len(contradictions), 'rows_in_contradictory_groups': int(g.isin(contradictions).sum())}
        assert audit[kind]['duplicate_extra_rows'] == audit[kind]['pandas_duplicate_extra_rows']
    train = frames['training']
    ti, vi = next(GroupShuffleSplit(n_splits=1, test_size=config['validation_fraction'], random_state=config['seed']).split(train, groups=hashes['training']))
    assert not set(hashes['training'].iloc[ti]) & set(hashes['training'].iloc[vi])
    Path('data/processed').mkdir(parents=True, exist_ok=True)
    manifest = pd.DataFrame({'row_id': [f'{RAW_NAMES["training"]}:row={i+1}' for i in range(len(train))],
                            'row_index': np.arange(len(train)), 'original_id': train.id,
                            'feature_group_sha256': hashes['training'], 'split': 'train'})
    manifest.loc[vi, 'split'] = 'validation'
    manifest.to_csv('data/processed/split_manifest.csv', index=False)
    for name, idx in [('train', ti), ('validation', vi)]:
        out = train.iloc[np.sort(idx)].copy()
        out.insert(0, 'row_id', manifest.iloc[np.sort(idx)].row_id.values)
        out.to_csv(f'data/processed/{name}.csv', index=False)
    audit['splits'] = {n: {'rows': len(idx), 'sha256': sha(f'data/processed/{n}.csv'),
                           'classes': {str(k): int(v) for k,v in train.iloc[idx].label.value_counts().items()}}
                       for n, idx in [('train', ti), ('validation', vi)]}
    audit['splits']['manifest_sha256'] = sha('data/processed/split_manifest.csv')
    testg = hashes['testing']
    audit['overlap'] = {'train_validation_groups': 0,
                        'test_rows_matching_train': int(testg.isin(set(hashes['training'].iloc[ti])).sum()),
                        'test_rows_matching_validation': int(testg.isin(set(hashes['training'].iloc[vi])).sum()),
                        'test_rows_matching_any_training_file': int(testg.isin(set(hashes['training'])).sum()),
                        'shared_unique_feature_groups': len(set(testg) & set(hashes['training']))}
    write_json('data/processed/features.json', {'features': features, 'numeric': numeric, 'categorical': [c for c in features if c not in numeric]})
    audit['prepared_hashes'] = {p.name: sha(p) for p in Path('data/processed').iterdir() if p.is_file()}
    audit['elapsed_seconds'] = time.perf_counter() - start
    write_json('evidencias/auditoria.json', audit)
    print('Auditoria y splits:', audit['splits'], 'solapamiento:', audit['overlap'], flush=True)

if __name__ == '__main__':
    main()
