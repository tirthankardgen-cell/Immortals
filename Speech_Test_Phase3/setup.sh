#!/usr/bin/env bash
# One-time online setup. Inference never downloads anything.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ $(uname -m) != aarch64 ]]; then
  echo 'This installer targets the 64-bit Raspberry Pi (aarch64).' >&2
  exit 1
fi
for tool in python3 curl tar arecord flock; do
  command -v "$tool" >/dev/null || { echo "Missing $tool. Install python3-venv curl alsa-utils." >&2; exit 1; }
done
mkdir -p models vendor results
python3 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
download() {
  local url="$1" target="$2"
  if [[ ! -s "$target" ]]; then
    curl --fail --location --retry 3 --connect-timeout 20 --max-time 1200 "$url" -o "$target.part"
    mv -- "$target.part" "$target"
  fi
}
.venv/bin/python install_indic_models.py

download 'https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2' models/segmentation.tar.bz2
if [[ ! -f models/sherpa-onnx-pyannote-segmentation-3-0/model.onnx ]]; then
  tar -xjf models/segmentation.tar.bz2 -C models
fi
download 'https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx' models/campplus.onnx
download 'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx' models/silero_vad.onnx
.venv/bin/python - <<'PY'
from pathlib import Path
import hashlib, json
from importlib.metadata import version
paths = [Path('models/campplus.onnx'), Path('models/silero_vad.onnx'),
         Path('models/sherpa-onnx-pyannote-segmentation-3-0/model.onnx')]
manifest = {'asr': 'IndicConformer only', 'languages': ['hi', 'bn'],
            'sherpa_onnx': version('sherpa-onnx'), 'uroman': version('uroman'),
            'onnxruntime': version('onnxruntime'),
            'sha256': {str(p): hashlib.file_digest(p.open('rb'), 'sha256').hexdigest() for p in paths}}
Path('models/installed.json').write_text(json.dumps(manifest, indent=2)+'\n')
PY
echo 'Setup complete. All recognition files are local. Run: ./run.sh'
