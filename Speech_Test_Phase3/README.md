# Immortals Phase 3 — offline Hindi/Bengali speech test

Updated 12 November 2026. This standalone sender-Pi terminal program listens to
the external USB microphone, transcribes locally, and distinguishes speakers with
Sherpa-ONNX. **Only Hindi and Bengali are supported.** Every speech segment shows
**both versions together**: **Hindi + Hinglish**, or **Bengali + Binglish**.
The original script and its Roman-letter version share the same timestamp and
speaker label. Recognition runs once; romanization renders that same text.

The previous chat installed **AI4Bharat IndicConformer 600M INT8 CTC** through
ONNX Runtime as the transcription backend. That installed backend is retained;
the tester no longer runs Whisper. The wider patient-to-cloud speech roadmap in
`PROJECT_UPGRADE_PLAN.md` is called Phase 2; this local testing stage is Phase 3.

## Start on the Pi

Open **Immortals Offline Speech Test** on the Pi desktop, or run:

```sh
cd /home/pi/Desktop/Immortals_Speech_Test_Phase3
./run.sh
```

The default `auto` setting chooses between **Hindi and Bengali only**, separately
for each finished speech section. To test one language consistently, select it:

```sh
./run.sh live --language bn   # Bengali + Binglish
./run.sh live --language hi   # Hindi + Hinglish
```

Example terminal layout (the wording depends on the speech):

```text
[00:04] Speaker 1 (Bengali / Binglish)
  Bengali: আমি বাংলা বলি
  Binglish: aami baanglaa bali
[00:09] Speaker 2 (Hindi / Hinglish)
  Hindi: नमस्ते दुनिया
  Hinglish: namaste duniyaa
```

The microphone stays open continuously while a separate process runs inference.
Text appears after a short pause (default 0.6 seconds) and processing, rather than
word by word. Speech longer than 15 seconds is split automatically. **Ctrl+C**
stops recording and model processing and preserves completed and pending results.
There is no automatic time limit and no boot autostart for this tester.

Other commands:

```sh
./run.sh devices
./run.sh doctor
./run.sh mic-test --seconds 5
./run.sh menu
./run.sh live --language bn --device plughw:CARD=UACDemoV10,DEV=0
./run.sh live --language hi --pause-seconds 0.8 --max-utterance-seconds 15
./run.sh record --seconds 30 --language bn --speakers 2
./run.sh analyze /path/to/audio.wav --language hi --speakers 2
./run.sh live --language bn --script roman   # Optional Binglish-only display
./run.sh live --language bn --script native  # Optional original-script display
```

`hi`, `Hindi`, `bn`, `Bengali`, and `Bangla` are accepted language selections,
along with the two-language `auto` setting. Other language codes are rejected.
Auto selection is a heuristic, not a detector that can reliably reject foreign
speech. Use Hindi/Bengali audio; other speech can produce incorrect text. Language
switches inside one uninterrupted section are not individually labelled.
WAV inputs must be mono 16 kHz signed 16-bit PCM and at most 120 seconds.

## Speaker testing

Use two or more people. Each person should speak for several seconds, pause, and
then let the first person speak again. Test turn-taking before overlap/noise.

- `--speakers 0` (default) estimates the count automatically, including more than two.
- Labels are `Speaker 1`, `Speaker 2`, etc. Within one live run, CAMPPlus embeddings
  match later sections to session references (cosine threshold 0.6, margin 0.08).
  The references reset when starting a new run.
- Labels are anonymous voices, not patient names or roles. Short/uncertain matches
  show `Unclear speaker`; detected overlaps/boundaries show
  `Unclear / overlapping speakers`.
- A known count such as `--speakers 2` helps compare a fixed recording. In live
  mode it applies to every section, so automatic count is usually preferable.
- `--threshold 0.5` controls clustering. Smaller values tend to find more clusters;
  larger values tend to find fewer. This does not change cross-section matching.
- Silence is suppressed with Silero VAD. Similar voices, short phrases, noise,
  and simultaneous speech can still produce errors. A single microphone cannot
  reliably separate simultaneous words.

Romanization changes spelling/display, not the recognized meaning. Hinglish and
Binglish spellings vary; inaccurate native recognition stays inaccurate after
romanization. Inspect `transcript_native.txt` when checking results.

## Measured timing on the sender Pi

Measured on 12 November 2026 on the actual ARM64 sender Pi with two CPU inference
threads. These are reference-WAV benchmarks, not a guaranteed live response time.

| Input/output | Audio length | ASR transcription | Speaker diarization | Total model processing | RTF |
|---|---:|---:|---:|---:|---:|
| Hindi + Hinglish | 22.68 s | 3.25 s | 5.37 s | 8.84 s | 0.390 |
| Bengali + Binglish | 7.62 s | 0.95 s | 0.69 s | 1.72 s | 0.226 |
| Silence | 5.00 s | 0.00 s | 0.00 s | 0.04 s | 0.009 |

- ASR model startup: **2.87 seconds** in the measured live run. It loads
  once per live run and is reused, rather than reloaded for each phrase.
- Live capture finalizes a phrase after **0.6 seconds of silence** by default;
  processing starts when the worker is available. Maximum uninterrupted speech is
  **15 seconds** before a forced split.
- Time from finishing speech to seeing text is approximately the pause delay,
  queue wait, speech/speaker/ASR processing, and Roman display work. The first
  output can also wait for model/romanizer startup. Romanizer startup and display,
  live cross-section voice matching, and queue waiting are not separately
  measured by this fixed-WAV table; timings can grow with noise, length, CPU load,
  and more speakers. There is no word-by-word output or fixed latency promise.
- RTF is model processing time divided by audio duration. Below 1 means those
  reference samples processed faster than their playback length. Eight sections
  may wait in the live queue; overflow is saved locally with a visible message.
- Ctrl+C stopped the measured live run in **0.164 seconds**, with exit 130
  and no leaked inference worker. The microphone captured nearly 10 seconds
  continuously; a separate 5-second mono 16 kHz capture also passed.
- Inference timeout: **900 seconds per section**, adjustable with `--timeout`.
  Use `--verbose` to see each run's timing and RTF. Raw stage timings are in
  `transcript.json`; model loading is in `model_ready.json`.

## Offline installation

All runtime models are local; there are no speech APIs, credentials, network
downloads, or remote code execution during recognition. One-time installation
on a fresh **64-bit ARM Raspberry Pi** needs internet:

```sh
# Already installed on the current sender Pi.
sudo apt install python3-venv curl alsa-utils bzip2 util-linux
bash setup.sh
./run.sh doctor
```

The installer creates a separate `.venv`. IndicConformer files are pinned to a
repository revision and verified against their sizes and SHA-256 hashes in
`indic_model_manifest.json`. Installation records are saved under `models/`.
Do not copy a Windows virtual environment to the Pi.

| Component | Installed choice |
|---|---|
| Transcription | AI4Bharat IndicConformer 600M INT8 CTC, CPU; Hindi/Bengali vocabulary selection |
| ONNX inference | onnxruntime 1.23.2 |
| Diarization | sherpa-onnx 2.0.1; Pyannote segmentation 3.0 ONNX |
| Voice embeddings | 3D-Speaker CAMPPlus English VoxCeleb 16 kHz ONNX |
| Speech detection | Silero VAD ONNX through Sherpa-ONNX |
| Roman-letter display | uroman 1.3.1.1 with Hindi/Bengali language tables |
| External USB microphone | `plughw:CARD=UACDemoV10,DEV=0`, mono 16 kHz PCM |

The embedding model's training name contains English; it is used to compare
voices and does not enable English transcription.

Sources: [AI4Bharat model](https://huggingface.co/ai4bharat/indic-conformer-600m-multilingual),
[pinned ONNX export](https://huggingface.co/akki244/indic-conformer-onnx-int8/tree/988451d62a11a7bc514630d75559d5f672c88690),
[Sherpa speaker models](https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-recongition-models),
[Sherpa segmentation models](https://github.com/k2-fsa/sherpa-onnx/releases/tag/speaker-segmentation-models).

## Results and recovery

`results/<run>/speech-00001/` contains `audio.wav`, `transcript.txt` (both versions
by default), `transcript_native.txt`, `transcript_roman.txt`, `transcript.json`, `recognition.json`,
`speaker_turns.json`, and processing metadata. JSON keeps `text` in the original
script and `display_text` in Roman letters. Section timestamps are relative to
its WAV; `offset_ms` relates it to the full run. Terminal timestamps include that
offset. `live_session.json` summarizes capture, processing, errors, and deferred
work. `speaker_registry.json` holds references only for this live run.

The ASR model is loaded once per run and reused. Eight speech sections can wait
behind the one being processed. If inference falls behind, further sections are
saved with `pending.json` and a visible message; recording continues. Ctrl+C
retains queued/interrupted speech for later analysis:

```sh
./run.sh analyze /path/to/speech-00001/audio.wav --language bn
```

Manual reanalysis creates a new result with fresh speaker labels. Native model
processing has a 900-second timeout, configurable with `--timeout`. Results are
bounded to approximately 512 MiB; capture stops near that limit or when free disk
space falls below 128 MiB. Archive old runs before restarting; no recordings are
automatically deleted. Two inference threads and lower scheduling priority leave
CPU capacity for other applications. `--verbose` shows timings and RTF: a value
above 1 means processing is slower than incoming audio.

This tester stores local test recordings without patient association. Patient
selection, vitals, Zigbee, Firebase, and website integration remain separate work.
See `VALIDATION.md` for actual Pi results and remaining live-person tests.

## Folder cleanup and laptop/Pi synchronization

Obsolete Whisper models, conversions, build folders, and old validation artifacts
were removed from the tester after verification in an archive outside it:
`/home/pi/.local/share/immortals-backups/speech-cleanup-20261112-161541/obsolete-files.tar`.
The archive contains 2,956 verified files (about 1.03 GB). Original laptop helper
files were moved to `.work/pi-backup/speech-laptop-cleanup-20261112-161544`.
Current models, `.venv`, and all `results/` recordings are preserved.

Laptop/Pi source files, launchers, tests, documentation, and current validation
evidence are synchronized. `source-sha256.json` records the source hashes. Linux
models and `.venv` stay on the Pi; user recordings in `results/` are not overwritten
by source synchronization. No background sync process is installed.
