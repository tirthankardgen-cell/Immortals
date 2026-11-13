"""One-time online installation of pinned, hash-verified IndicConformer files."""
from pathlib import Path
import hashlib
import json
import time
import urllib.request

ROOT = Path(__file__).resolve().parent


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def install():
    manifest = json.loads((ROOT / 'indic_model_manifest.json').read_text())
    target = ROOT / 'models/indicconformer'
    target.mkdir(parents=True, exist_ok=True)
    for name, metadata in manifest['files'].items():
        path = target / name
        if path.is_file() and path.stat().st_size == metadata['bytes'] and digest(path) == metadata['sha256']:
            print('Verified:', name, flush=True)
            continue
        url = f"https://huggingface.co/{manifest['repo']}/resolve/{manifest['revision']}/{name}"
        partial = path.with_suffix(path.suffix + '.part')
        for attempt in range(3):
            try:
                started = last_status = time.monotonic()
                count = 0
                print('Downloading:', name, flush=True)
                with urllib.request.urlopen(url, timeout=45) as response, partial.open('wb') as output:
                    while block := response.read(1024 ** 2):
                        output.write(block)
                        count += len(block)
                        if count > metadata['bytes'] or time.monotonic() - started > 1800:
                            raise RuntimeError('Model download exceeded its size or time limit.')
                        if time.monotonic() - last_status > 20:
                            print(f'  {count / 1024**2:.0f} / {metadata["bytes"] / 1024**2:.0f} MiB', flush=True)
                            last_status = time.monotonic()
                if count != metadata['bytes'] or digest(partial) != metadata['sha256']:
                    raise RuntimeError('Downloaded model did not match the pinned SHA-256.')
                partial.replace(path)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
    (target / 'installed.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('IndicConformer is installed. Speech recognition now uses local files only.')


if __name__ == '__main__':
    install()
