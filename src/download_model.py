import argparse
from pathlib import Path
from huggingface_hub import snapshot_download
from .common import read_json, sha

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--version', choices=['v1','v2'], required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    item = read_json('evidencias/huggingface.json')[a.version]
    assert len(item['sha']) == 40
    path = Path(snapshot_download(repo_id=item['repo_id'], revision=item['sha'], local_dir=a.output))
    assert sha(path / 'pipeline.joblib') == item['model_sha256']
    print(item['repo_id'], item['sha'], item['model_sha256'])

if __name__ == '__main__':
    main()
