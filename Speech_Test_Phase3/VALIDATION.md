# Pi validation — 12 November 2026

Current target: sender `raspberrypi`, ARM64 Debian 12, 8 GiB Raspberry Pi.
Runtime: `/home/pi/Desktop/Immortals_Speech_Test_Phase3`.
ASR: AI4Bharat IndicConformer 600M INT8 CTC, ONNX Runtime 1.23.2.
Speaker/VAD toolkit: Sherpa-ONNX 2.0.1 with Pyannote/CAMPPlus/Silero.

The final program defaults to **both versions of each speech segment**:
Hindi + Hinglish or Bengali + Binglish, under one timestamp and speaker label.
It recognizes only Hindi/Bengali; original `text` and Roman `display_text` are
stored together, with `transcript.txt`, `transcript_native.txt`, and
`transcript_roman.txt` exports.

## Verified on the actual Pi

- 21 regression tests pass, including paired native/Roman output, two-language
  restrictions, returning speakers, overlap/coverage, CTC timing, and streaming
  PCM boundaries.
- The final inference run was inside a Linux namespace without external network
  access. Connection to `1.1.1.1:443` failed with `[Errno 101] Network is unreachable`.
  Hindi, Bengali, and silence all completed using local models.
- Both original-script text and Hinglish/Binglish from the same segments were
  checked in terminal output and exports. All Roman exports contain Roman/ASCII
  characters. Native recognition remains unchanged.
- The same worker PID handled all three reference inputs, proving ASR model reuse.
- Anonymous speaker-only reference tests detected **two** and **four** speakers.
  Reversing two-speaker cluster/order retained the returning voices' labels.
  These reference WAVs include other languages only for testing voice clustering;
  they were not passed to ASR and do not enable other transcription languages.
- Physical USB microphone `plughw:CARD=UACDemoV10,DEV=0`: a continuous run captured
  157,600 samples without errors.
  Ctrl+C returned exit **130** in **0.164 seconds**; the inference worker was
  confirmed gone. This run was quiet and generated no speech sections.
- A separate **5-second** microphone-level capture saved exactly **80,000** mono
  16 kHz signed 16-bit PCM samples without errors.

| Input/output | Audio length | ASR transcription | Speaker diarization | Total model processing | RTF |
|---|---:|---:|---:|---:|---:|
| Hindi + Hinglish | 22.68 s | 3.25 s | 5.37 s | 8.84 s | 0.390 |
| Bengali + Binglish | 7.62 s | 0.95 s | 0.69 s | 1.72 s | 0.226 |
| Silence | 5.00 s | 0.00 s | 0.00 s | 0.04 s | 0.009 |

ASR model loading took 2.87 seconds in the live check. Fixed-WAV model
times exclude initial ASR load, parent romanization/display, live voice-registry
matching, and queue waits. See README for pause/timeout/backlog details.

## Evidence and cleanup

Final inference evidence: `/home/pi/Desktop/Immortals_Speech_Test_Phase3/validation_indic/20261112-161935/evidence.json`.
The `validation_indic` evidence tree is also synchronized to the laptop tester.
Local deployment records are in `.work/phase3-roman-verification.json`,
`.work/phase3-cleanup-verification.json`, and `.work/phase3-sync-verification.json`.

Obsolete Whisper/build/older-validation artifacts were archived with SHA-256
verification before removal. The 2,956-file archive is outside the test folder:
`/home/pi/.local/share/immortals-backups/speech-cleanup-20261112-161541/obsolete-files.tar`.
Current models, environment, and all user `results/` recordings remain intact.

Still requires field testing: two or more live people speaking Hindi/Bengali into
the USB microphone, short phrases, similar voices, overlap/noise, within-phrase
language switches, and sustained thermal/sensor/radio responsiveness. Reference
counts and timing do not establish accuracy in every room. This completes the
standalone terminal tester; patient-to-Zigbee/Firebase integration is separate.
