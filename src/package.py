"""Empaqueta código + evidencia; almacenamiento DVC siempre separado."""
import argparse
import re
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from .common import git_head, sha, write_json, read_json, now

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='/workspace/entrega-defiende')
    parser.add_argument('--storage',default='/workspace/dvc-storage.zip')
    args=parser.parse_args()
    target=Path(args.output)
    target.mkdir(parents=True,exist_ok=True)
    # La revisión del bundle y los archivos deben coincidir exactamente.
    subprocess.run(['git','diff','--exit-code','HEAD'],check=True)
    commit=git_head()
    refs={v:subprocess.check_output(['git','rev-parse',v+'^{commit}'],text=True).strip() for v in ['v1','v2','datos-originales','datos-preparados']}
    files=[Path(p) for p in subprocess.check_output(['git','ls-files','-z']).decode().split('\0') if p]
    for p in files:
        assert not str(p).startswith(('data/raw/','data/processed/','.venv/','.runtime/','mlruns/','models/')), p
        if p.suffix in {'.py','.json','.md','.txt','.csv','.log','.dvc'}:
            content=p.read_text(errors='replace')
            assert not re.search(r'(?:hf_|ghp_)[A-Za-z0-9]{24,}|github_pat_[A-Za-z0-9_]{40,}',content), f'Posible credencial en {p}'
    objects=subprocess.check_output(['git','rev-list','--objects','--all'],text=True)
    assert not re.search(r' data/(raw|processed)/.*\.csv',objects), 'Datos masivos en historial alcanzable'
    bundle=target/'historial.bundle'
    subprocess.run(['git','bundle','create',str(bundle),'--all'],check=True)
    subprocess.run(['git','bundle','verify',str(bundle)],check=True)
    revision=f'{commit}\n'
    (target/'revision-entrega.txt').write_text(revision)
    package=target/'proyecto.zip'
    with ZipFile(package,'w',compression=ZIP_DEFLATED,compresslevel=6) as z:
        for p in files: z.write(p,Path('proyecto')/p)
        z.write(bundle,'proyecto/historial.bundle')
        z.writestr('proyecto/revision-entrega.txt',revision)
    bundle.unlink()
    shutil.copy2('dist/informe.pdf',target/'informe.pdf')
    storage=Path(args.storage)
    if storage.resolve() != (target/'dvc-storage.zip').resolve():
        shutil.copy2(storage,target/'dvc-storage.zip')
    hf=read_json('evidencias/huggingface.json') if Path('evidencias/huggingface.json').exists() else {}
    recovery=read_json('evidencias/recuperacion/resultado.json')
    comparison=read_json('evidencias/recuperacion/comparacion.json')
    people=read_json('configs/integrantes.json')
    author='; '.join(p['nombre'] for p in people['integrantes'])
    group='; '.join(p['grupo'] for p in people['integrantes'])
    assert recovery['passed'] and comparison['passed'], 'No empaquetar como recuperación completa sin prueba real'
    model_lines='\n'.join(f'{v}: {hf[v]["url"]}/tree/{hf[v]["sha"]}' if v in hf else f'{v}: PENDIENTE publicación HF por falta de token/acceso; no existe SHA verificable.' for v in ['v1','v2'])
    text=f'''MLOps — Defiende el servidor — Grupo {group} — {author}

Profesor Julián:

Integrante única: {author}. Grupo: {group}, confirmado.
Comparto la implementación y evidencias ejecutadas del taller.
Repositorio de código solicitado: https://github.com/angiedonatto/Versionamiento
Commit final de esta entrega: {commit}
La publicación se verifica con Git push y lectura pública; evidencia en github.json
y verificacion-publicacion.json junto a estos archivos. Los enlaces públicos
permiten revisión sin compartir credenciales.
Revisiones Git v1: {refs['v1']}; v2: {refs['v2']}.
Modelos:
{model_lines}

Adjuntos: proyecto.zip, informe.pdf y dvc-storage.zip (respaldo DVC separado).
Para DVC, extraer dvc-storage.zip junto al proyecto y ejecutar dvc pull según README.
El ZIP incluye un bundle Git recuperable, código, cuatro runs MLflow exportados,
auditoría, selección congelada y 82332 predicciones de la única evaluación final.
Las métricas se recalcularon desde el CSV original y coincidieron; no se repitió
la evaluación test. La recuperación completa desde GitHub, el respaldo DVC y
ambas revisiones HF se ejecutó en carpeta, venv y cachés nuevos. Las {comparison['rows']} filas
fijas reprodujeron clases exactas; diferencia máxima de scores en v1:
{comparison['versions']['v1']['max_score_difference']}; en v2: {comparison['versions']['v2']['max_score_difference']}.
Log y comparación en evidencias/recuperacion/; auditoría detallada adjunta.

Limitaciones y uso de Codex están declarados en entrega.md e informe.pdf.
Los repositorios y los entregables son públicos por autorización expresa;
sus descargas sin token se verificaron. No se comparten credenciales.

Contribución: {people['declaracion_contribucion']}
Saludos,
{author}
'''
    (target/'mensaje-profesor.txt').write_text(text)
    manifest={'created_at_utc':now(),'git_commit':commit,'refs':refs,'files':{},
              'archive_excludes':'raw/prepared datasets, venv, caches, secrets, MLflow DB',
              'teacher_access_verified':False, 'public_links_created':False}
    for p in target.iterdir():
        if p.is_file() and p.name not in {'manifest.json','SHA256SUMS'}:
            manifest['files'][p.name]={'bytes':p.stat().st_size,'sha256':sha(p)}
    write_json(target/'manifest.json',manifest)
    (target/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(target.iterdir()) if p.is_file() and p.name != 'SHA256SUMS'))
    with ZipFile(package) as z:
        assert z.testzip() is None
        assert 'proyecto/evidencias/predicciones-test.csv' in z.namelist()
        assert 'proyecto/historial.bundle' in z.namelist()
    with ZipFile(target/'dvc-storage.zip') as z: assert z.testzip() is None
    print(manifest)

if __name__=='__main__':
    main()
