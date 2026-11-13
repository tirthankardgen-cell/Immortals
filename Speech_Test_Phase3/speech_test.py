#!/usr/bin/env python3
"""Streaming offline IndicConformer / Sherpa-ONNX terminal test."""
from __future__ import annotations

import argparse
import array
from datetime import datetime, timezone
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import queue
import selectors
import shutil
import signal
import subprocess
import sys
import threading
import textwrap
import traceback
import time
import uuid
import wave

from romanize_text import romanize
from indic_backend import IndicConformer, MODEL_ROOT, FILES as INDIC_FILES

ROOT = Path(__file__).resolve().parent
INDIC_MANIFEST = json.loads((ROOT / 'indic_model_manifest.json').read_text(encoding='utf-8'))
RATE = 16000
MAX_SECONDS = 120
MODELS = {
    'segmentation': ROOT / 'models/sherpa-onnx-pyannote-segmentation-3-0/model.onnx',
    'embedding': ROOT / 'models/campplus.onnx',
    'vad': ROOT / 'models/silero_vad.onnx',
}

LANGUAGES = {'auto': 'Auto (Hindi / Bengali)', 'hi': 'Hindi', 'bn': 'Bengali'}
ALL_MODELS = (*MODELS.values(), *(MODEL_ROOT / name for name in INDIC_FILES))


def language_code(value):
    value = value.strip().lower()
    value = {'hindi': 'hi', 'bengali': 'bn', 'bangla': 'bn'}.get(value, value)
    if value not in LANGUAGES:
        raise argparse.ArgumentTypeError('Choose auto, hi (Hindi), or bn (Bengali).')
    return value


class Terminal:
    """Serialize capture/recognition output; only the status line is redrawn."""
    def __init__(self, verbose=False, stream=None):
        self.stream = stream or sys.stdout
        self.interactive = self.stream.isatty() and os.environ.get('TERM') != 'dumb'
        self.verbose = verbose
        self.lock = threading.Lock()
        self.state = {'capture': '', 'processing': False, 'waiting': 0}
        self.last_draw = 0.0

    def _draw(self):
        if not self.interactive or not self.state['capture']:
            return
        parts = [self.state['capture']]
        if self.state['processing']:
            parts.append('Transcribing')
        if self.state['waiting']:
            parts.append(f"Waiting: {self.state['waiting']}")
        parts.append('Ctrl+C to stop')
        width = max(20, shutil.get_terminal_size((80, 24)).columns - 1)
        self.stream.write('\r\033[2K' + ' | '.join(parts)[:width])
        self.stream.flush()
        self.last_draw = time.monotonic()

    def status(self, **state):
        with self.lock:
            changed = any(self.state.get(k) != v for k, v in state.items())
            self.state.update(state)
            if changed or time.monotonic() - self.last_draw >= 0.25:
                self._draw()

    def line(self, text=''):
        with self.lock:
            if self.interactive:
                self.stream.write('\r\033[2K')
            self.stream.write(str(text) + '\n')
            self.stream.flush()
            self._draw()

    def detail(self, text):
        if self.verbose:
            self.line(text)

    def close(self):
        with self.lock:
            if self.interactive:
                self.stream.write('\r\033[2K')
                self.stream.flush()
            self.state['capture'] = ''


def show_transcript(report, terminal, offset_ms=0):
    language = report.get('language_detected') or report.get('language', 'auto')
    script = report.get('script', 'both')
    native_name = LANGUAGES.get(language, language)
    roman_name = {'hi': 'Hinglish', 'bn': 'Binglish'}.get(language, native_name)
    language_name = f'{native_name} / {roman_name}' if script == 'both' else roman_name if script == 'roman' else native_name
    width = max(40, shutil.get_terminal_size((100, 24)).columns)
    for row in report['segments']:
        seconds = (offset_ms + row['start_ms']) // 1000
        minutes, second = divmod(seconds, 60)
        speaker = {'Unknown': 'Unclear speaker', 'Ambiguous': 'Unclear / overlapping speakers'}.get(
            row['speaker_id'], row['speaker_id'])
        # Model text cannot insert terminal control sequences or extra status lines.
        heading = f'[{minutes:02d}:{second:02d}] {speaker} ({language_name})'
        terminal.line(heading + '\n' + format_transcript_text(row, language, script, width))


def format_transcript_text(row, language, script, width=100):
    """Render paired original/Roman text from one recognized segment."""
    native = row['text']
    roman = (row.get('display_text') or romanize(native, language)) if script != 'native' else ''
    if script == 'both':
        lines = [(LANGUAGES.get(language, language) + ': ', native),
                 ({'hi': 'Hinglish', 'bn': 'Binglish'}.get(language, language) + ': ', roman)]
    else:
        lines = [('', roman if script == 'roman' else native)]
    return '\n'.join(textwrap.fill(re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', text).strip(),
                     width=width, initial_indent='  ' + label, subsequent_indent='  ',
                     break_long_words=False) for label, text in lines)


class StreamingVAD:
    """Feed exact PCM windows; keep source offsets through pauses and forced cuts."""
    def __init__(self, vad, window):
        self.vad, self.window = vad, window
        self.pending = b''
        self.samples = 0

    def feed(self, data):
        import numpy as np
        self.pending += data
        results = []
        size = self.window * 2
        while len(self.pending) >= size:
            block, self.pending = self.pending[:size], self.pending[size:]
            self.samples += self.window
            self.vad.accept_waveform(np.frombuffer(block, dtype='<i2').astype(np.float32) / 32768)
            results.extend(self.drain())
        return results

    def drain(self):
        results = []
        while not self.vad.empty():
            segment = self.vad.front
            start = max(0, segment.start)
            count = min(len(segment.samples), self.samples - start)
            if count > 0:
                # Own the buffer before pop releases Sherpa's storage.
                results.append((start, segment.samples[:count].copy()))
            self.vad.pop()
        return results

    def flush(self):
        import numpy as np
        count = len(self.pending) // 2
        if count:
            samples = np.frombuffer(self.pending[:count * 2], dtype='<i2').astype(np.float32) / 32768
            self.samples += count
            self.vad.accept_waveform(np.pad(samples, (0, self.window - count)))
        self.pending = b''
        self.vad.flush()
        return self.drain()


def save_json(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    tmp.replace(path)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def audio_info(path):
    with wave.open(str(path), 'rb') as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (1, 2, RATE, 'NONE'):
            raise ValueError('WAV must be mono 16000 Hz, signed 16-bit PCM. Convert it before analysis.')
        duration = wav.getnframes() / RATE
        if not 0 < duration <= MAX_SECONDS:
            raise ValueError(f'Audio must be between 0 and {MAX_SECONDS} seconds.')
        return {'seconds': duration, 'samples': wav.getnframes(), 'sample_rate': RATE}


def levels(data):
    samples = array.array('h', data)
    if sys.byteorder != 'little':
        samples.byteswap()
    if not samples:
        return -120.0, 0.0
    rms = math.sqrt(sum(float(x) ** 2 for x in samples) / len(samples)) / 32768
    return max(-120.0, 20 * math.log10(max(rms, 1e-6))), max(abs(x) for x in samples) / 32768


def devices():
    if not shutil.which('arecord'):
        raise RuntimeError('arecord is missing. Install alsa-utils on the Pi.')
    result = subprocess.run(['arecord', '-l'], capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'No ALSA capture devices found.')
    return result.stdout


def select_device(requested):
    if requested:
        return requested
    found = re.findall(r'^card \d+: (\S+) .*?device (\d+):', devices(), re.MULTILINE)
    if len(found) != 1:
        raise RuntimeError('No unique microphone. Run ./run.sh devices, then specify --device plughw:CARD=NAME,DEV=0.')
    return f'plughw:CARD={found[0][0]},DEV={found[0][1]}'


def capture_error(log_path):
    detail = log_path.read_text(errors='replace').lower() if log_path.exists() else ''
    if 'device or resource busy' in detail:
        return 'Microphone is in use. Close the other speech test or recording app, then retry.'
    return f'Microphone stopped or disconnected. Details: {log_path}'


def stop_process(proc):
    # Every child has its own session: never signal the monitor, shell, or SSH.
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            proc.wait()
            return
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=3)


def make_session(base):
    base.mkdir(parents=True, exist_ok=True)
    used = sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
    if used >= 512 * 1024 ** 2 or shutil.disk_usage(base).free < 128 * 1024 ** 2:
        raise RuntimeError('Results limit reached (512 MiB) or less than 128 MiB free. Archive old test sessions first.')
    session = base / (datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8])
    session.mkdir()
    return session


def capture(path, seconds, device):
    if not 1 <= seconds <= MAX_SECONDS:
        raise ValueError(f'Recording duration must be 1..{MAX_SECONDS} seconds.')
    print(f'RECORDING {seconds}s from {device}. Speak now. Ctrl+C cancels.', flush=True)
    remaining = seconds * RATE * 2
    started = time.monotonic()
    last_meter = 0.0
    max_peak = 0.0
    captured = 0
    log_path = path.parent / 'capture.log'
    with log_path.open('w') as log, wave.open(str(path), 'wb') as wav:
        wav.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
        proc = subprocess.Popen(['arecord', '-q', '-D', device, '-t', 'raw', '-f', 'S16_LE',
                                 '-r', str(RATE), '-c', '1', '-d', str(seconds)], stdout=subprocess.PIPE,
                                stderr=log, start_new_session=True)
        try:
            with selectors.DefaultSelector() as sel:
                sel.register(proc.stdout, selectors.EVENT_READ)
                pending = b''
                while remaining:
                    if time.monotonic() - started > seconds + 8:
                        raise RuntimeError('Microphone stalled or delivered audio too slowly.')
                    if not sel.select(timeout=0.25):
                        if proc.poll() is not None:
                            raise RuntimeError('Microphone stopped. Check capture.log and the USB connection.')
                        continue
                    block = os.read(proc.stdout.fileno(), min(3200, remaining))
                    if not block:
                        raise RuntimeError(capture_error(log_path))
                    pending += block
                    complete = len(pending) // 2 * 2
                    block, pending = pending[:complete], pending[complete:]
                    if not block:
                        continue
                    wav.writeframesraw(block)
                    remaining -= len(block)
                    captured += len(block)
                    db, peak = levels(block)
                    max_peak = max(max_peak, peak)
                    now = time.monotonic()
                    if now - last_meter >= (0.2 if sys.stdout.isatty() else 2):
                        meter = '#' * max(0, min(30, round((db + 60) / 2)))
                        print(f'  {captured / (RATE * 2):5.1f}s  [{meter:<30}] {db:6.1f} dBFS'
                              + (' CLIPPING' if peak > 0.99 else ''),
                              end='\r' if sys.stdout.isatty() else '\n', flush=True)
                        last_meter = now
                if proc.wait(timeout=3):
                    raise RuntimeError('Microphone capture failed. Check capture.log.')
        finally:
            stop_process(proc)
            proc.stdout.close()
            print()
    errors = log_path.read_text(errors='replace')
    if any(word in errors.lower() for word in ('overrun', 'read error', 'input/output error')):
        raise RuntimeError('Capture reported lost audio/errors; WAV retained for inspection. See capture.log.')
    if max_peak < 0.002:
        print('Very low input level. Check microphone gain, distance, and the selected device.')
    if max_peak > 0.99:
        print('Clipping detected. Reduce microphone gain or move farther away.')
    return {'peak': round(max_peak, 4), **audio_info(path)}


def doctor():
    ok = True
    for name, path in {**MODELS, **{name: MODEL_ROOT / name for name in INDIC_FILES}}.items():
        expected = INDIC_MANIFEST['files'].get(name, {}).get('bytes')
        exists = path.is_file() and path.stat().st_size > 0 and (expected is None or path.stat().st_size == expected)
        ok &= exists
        print(f'{"OK" if exists else "MISSING":7} {name}: {path}')
    for name in ('numpy', 'sherpa_onnx', 'uroman', 'onnxruntime'):
        exists = importlib.util.find_spec(name) is not None
        ok &= exists
        print(f'{"OK" if exists else "MISSING":7} Python package {name}')
    try:
        print(devices())
    except RuntimeError as exc:
        print(exc)
        ok = False
    print('Recognition uses local files only. No API key, account, or network connection is used.')
    return ok


def union_duration(intervals):
    total, end = 0.0, -math.inf
    for start, stop in sorted(intervals):
        total += max(0.0, stop - max(start, end))
        end = max(end, stop)
    return total


def speaker_for(start, end, turns):
    """Conservative time alignment; scores are coverage, not identity probabilities."""
    if end <= start:
        return 'Unknown', 'invalid_timing'
    intersections = {}
    for turn in turns:
        left, right = max(start, turn['start_ms']), min(end, turn['end_ms'])
        if right > left:
            intersections.setdefault(turn['speaker_id'], []).append((left, right))
    ranked = sorted(((union_duration(v), k) for k, v in intersections.items()), reverse=True)
    if not ranked or ranked[0][0] / (end - start) < 0.5:
        return 'Unknown', 'insufficient_speaker_coverage'
    if len(ranked) > 1:
        # Concurrent voices cannot be transcribed separately from one mixed channel.
        for a in intersections[ranked[0][1]]:
            for b in (v for k, rows in intersections.items() if k != ranked[0][1] for v in rows):
                if min(a[1], b[1]) - max(a[0], b[0]) > 0:
                    return 'Ambiguous', 'overlapping_speakers'
        if ranked[1][0] >= (end - start) * 0.2:
            return 'Ambiguous', 'speaker_boundary'
    if ranked[0][1] == 'Unknown':
        return 'Unknown', 'uncertain_voice_match'
    return ranked[0][1], 'estimated'


def align_transcript(raw, turns, speech, duration_ms):
    output = []
    for row in raw.get('transcription', []):
        raw_text = row.get('text', '')
        text = raw_text.strip()
        offsets = row.get('offsets', {})
        start = max(0, int(offsets.get('from', 0)))
        end = min(duration_ms, int(offsets.get('to', 0)))
        if not text or end <= start or text.startswith('[_'):
            continue
        if not any(min(end, b) > max(start, a) for a, b in speech):
            continue  # Never accept text wholly outside VAD speech intervals.
        speaker, quality = speaker_for(start, end, turns)
        item = {'start_ms': start, 'end_ms': end, 'speaker_id': speaker, 'text': text, 'quality': quality}
        # Reassemble adjacent word-sized CTC segments for readable terminal output.
        if (output and output[-1]['speaker_id'] == speaker and output[-1]['quality'] == quality
                and 0 <= start - output[-1]['end_ms'] <= 350):
            # CTC can split an Indic word into several tokens. Preserve its
            # own whitespace so vowel signs and conjuncts stay attached.
            output[-1]['text'] += (' ' if raw_text[:1].isspace() else '') + text
            output[-1]['end_ms'] = end
        else:
            output.append(item)
    return output


def stable_speakers(sherpa, samples, turns, registry_path, threads):
    """Session-only voice matching between live chunks, never real-name identification."""
    import numpy as np
    path = Path(registry_path)
    registry = json.loads(path.read_text()) if path.exists() else []
    extractor = sherpa.SpeakerEmbeddingExtractor(sherpa.SpeakerEmbeddingExtractorConfig(
        model=str(MODELS['embedding']), num_threads=threads, provider='cpu'))
    mapping, used = {}, set()
    for label in dict.fromkeys(t['speaker_id'] for t in turns):
        # Avoid embedding mixed speech where diarization reported an overlap.
        clean = [t for t in turns if t['speaker_id'] == label and not any(
            other['speaker_id'] != label and min(t['end_ms'], other['end_ms']) > max(t['start_ms'], other['start_ms'])
            for other in turns)]
        chunks = [samples[int(t['start_ms'] * RATE / 1000):int(t['end_ms'] * RATE / 1000)] for t in clean]
        voice = np.concatenate(chunks) if chunks else np.empty(0, dtype=np.float32)
        if len(voice) < RATE:  # Too little evidence to preserve an identity across chunks.
            mapping[label] = 'Unknown'
            continue
        stream = extractor.create_stream()
        stream.accept_waveform(sample_rate=RATE, waveform=voice[:RATE * 15])
        stream.input_finished()
        if not extractor.is_ready(stream):
            mapping[label] = 'Unknown'
            continue
        vector = np.array(extractor.compute(stream), dtype=np.float32)
        vector /= max(float(np.linalg.norm(vector)), 1e-9)
        matches = sorted([(float(np.dot(vector, r['embedding'])), i) for i, r in enumerate(registry)
                          if i not in used], reverse=True)
        if matches and matches[0][0] >= 0.6:
            if len(matches) > 1 and matches[0][0] - matches[1][0] < 0.08:
                mapping[label] = 'Unknown'
                continue
            index = matches[0][1]
            # Keep the original reference: do not let uncertain matches drift its identity.
        elif len(registry) < 20:
            index = len(registry)
            registry.append({'speaker_id': f'Speaker {index + 1}', 'embedding': vector.tolist()})
        else:
            mapping[label] = 'Unknown'
            continue
        used.add(index)
        mapping[label] = registry[index]['speaker_id']
    save_json(path, registry)
    return [{**t, 'speaker_id': mapping[t['speaker_id']]} for t in turns]


def process(config, backend=None):
    """Run local native models with a parent-enforced deadline."""
    import numpy as np
    import sherpa_onnx as sherpa
    from importlib.metadata import version

    session = Path(config['session'])
    info = audio_info(session / 'audio.wav')
    with wave.open(str(session / 'audio.wav'), 'rb') as wav:
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2').astype(np.float32) / 32768
    start_time = time.monotonic()
    print('Detecting speech locally...', flush=True)
    cfg = sherpa.VadModelConfig()
    cfg.silero_vad.model = str(MODELS['vad'])
    cfg.silero_vad.threshold = 0.5
    cfg.silero_vad.min_silence_duration = 0.3
    cfg.silero_vad.min_speech_duration = 0.25
    cfg.silero_vad.max_speech_duration = MAX_SECONDS
    cfg.sample_rate = RATE
    cfg.num_threads = config['threads']
    vad = sherpa.VoiceActivityDetector(cfg, buffer_size_in_seconds=MAX_SECONDS + 2)
    speech = []
    window = cfg.silero_vad.window_size

    def drain():
        while not vad.empty():
            segment = vad.front
            speech.append([round(segment.start / RATE * 1000),
                           min(round(info['seconds'] * 1000), round((segment.start + len(segment.samples)) / RATE * 1000))])
            vad.pop()

    for offset in range(0, len(samples), window):
        chunk = samples[offset:offset + window]
        if len(chunk) < window:
            chunk = np.pad(chunk, (0, window - len(chunk)))
        vad.accept_waveform(chunk)
        drain()
    vad.flush()
    drain()
    timings = {'vad_seconds': round(time.monotonic() - start_time, 3)}
    turns, segments = [], []
    detected_language = None
    if speech:
        print('Differentiating speakers locally (automatic clustering)...' if not config['speakers']
              else f"Differentiating speakers locally (requested count: {config['speakers']})...", flush=True)
        stage = time.monotonic()
        cfg = sherpa.OfflineSpeakerDiarizationConfig(
            segmentation=sherpa.OfflineSpeakerSegmentationModelConfig(
                pyannote=sherpa.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(MODELS['segmentation'])),
                num_threads=config['threads'], provider='cpu'),
            embedding=sherpa.SpeakerEmbeddingExtractorConfig(model=str(MODELS['embedding']),
                num_threads=config['threads'], provider='cpu'),
            clustering=sherpa.FastClusteringConfig(num_clusters=config['speakers'] or -1,
                threshold=config['threshold']), min_duration_on=0.3, min_duration_off=0.5)
        if not cfg.validate():
            raise RuntimeError('Sherpa-ONNX configuration/model validation failed.')
        diarizer = sherpa.OfflineSpeakerDiarization(cfg)
        if diarizer.sample_rate != RATE:
            raise RuntimeError('Diarization model requires an unexpected sample rate.')
        result = diarizer.process(samples).sort_by_start_time()
        names = {}
        for row in result:
            if row.speaker not in names:
                names[row.speaker] = f'Speaker {len(names) + 1}'
            turns.append({'start_ms': max(0, round(row.start * 1000)),
                          'end_ms': min(round(info['seconds'] * 1000), round(row.end * 1000)),
                          'speaker_id': names[row.speaker]})
        timings['diarization_seconds'] = round(time.monotonic() - stage, 3)
        del diarizer
        if config.get('speaker_registry'):
            turns = stable_speakers(sherpa, samples, turns, config['speaker_registry'], config['threads'])
        save_json(session / 'speaker_turns.json', turns)
        print(f'Found {len(names)} speaker cluster(s). Transcribing with IndicConformer...', flush=True)
        stage = time.monotonic()
        backend = backend or IndicConformer(threads=config['threads'])
        result = backend.transcribe(samples, config['language'])
        detected_language = result['language']
        save_json(session / 'recognition.json', result)
        raw = {'transcription': [{'text': w['text'], 'offsets': {'from': w['start_ms'], 'to': w['end_ms']}}
                                 for w in result['words']]}
        segments = align_transcript(raw, turns, speech, round(info['seconds'] * 1000))
        timings['asr_seconds'] = round(time.monotonic() - stage, 3)
    else:
        print('No speech detected. Transcription and speaker clustering skipped.', flush=True)
    elapsed = time.monotonic() - start_time
    timings.update(processing_seconds=round(elapsed, 3), real_time_factor=round(elapsed / info['seconds'], 3))
    document = {**config, 'status': ('complete' if segments else 'speech_unclear') if speech else 'no_speech', 'audio': info,
                'language_detected': detected_language, 'speech_intervals_ms': speech,
                'speaker_count': len({t['speaker_id'] for t in turns if t['speaker_id'] != 'Unknown'}), 'speaker_turns': turns,
                'segments': segments, 'timings': timings,
                'models': {'asr': 'AI4Bharat IndicConformer 600M INT8 CTC',
                           'export': INDIC_MANIFEST['repo'], 'revision': INDIC_MANIFEST['revision'],
                           'onnxruntime': version('onnxruntime'),
                           'sherpa_onnx': version('sherpa-onnx'), 'segmentation': 'pyannote segmentation 3.0',
                           'embedding': '3dspeaker CAMPPlus English VoxCeleb 16k', 'vad': 'Silero VAD'},
                'limitations': ['Speaker IDs apply only within this live session or recording; they are not names or roles.',
                                'Auto language is a Hindi/Bengali heuristic; English and other languages are unsupported.',
                                'Automatic speaker count and timestamps are estimates.',
                                'A single microphone cannot reliably separate simultaneous speech; some overlap may be missed.']}
    save_json(session / 'transcript.json', document)
    lines = [f"[{r['start_ms']/1000:6.2f}-{r['end_ms']/1000:6.2f}] {r['speaker_id']}: {r['text']}"
             + (f" [{r['quality']}]" if r['quality'] != 'estimated' else '') for r in segments]
    (session / 'transcript_native.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (session / 'transcript.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')


class ModelWorker:
    """One disposable process per live run; reuse its loaded ASR model."""
    def __init__(self, directory, threads):
        self.log_path = directory / 'inference.log'
        self.log = self.log_path.open('w', encoding='utf-8')
        try:
            self.proc = subprocess.Popen([sys.executable, '-u', str(Path(__file__).resolve()),
                                          '_serve', str(directory), str(threads)],
                                         stdin=subprocess.PIPE, stdout=self.log, stderr=subprocess.STDOUT,
                                         text=True, encoding='utf-8', start_new_session=True)
        except BaseException:
            self.log.close()
            raise

    def run(self, config_path, timeout, cancel_event):
        done = config_path.parent / 'processed.json'
        try:
            self.proc.stdin.write(json.dumps(str(config_path)) + '\n')
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError):
            raise RuntimeError(f'Model worker stopped. Details: {self.log_path}') from None
        started = time.monotonic()
        while not done.exists():
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError('Capture stopped; pending speech has been saved.')
            if self.proc.poll() is not None:
                raise RuntimeError(f'Model worker exited {self.proc.returncode}. Details: {self.log_path}')
            if time.monotonic() - started > timeout:
                raise RuntimeError(f'Recognition timed out; audio saved. Details: {self.log_path}')
            time.sleep(0.1)
        status = json.loads(done.read_text(encoding='utf-8'))
        if status['status'] != 'complete':
            raise RuntimeError(f"Recognition failed: {status['message']}. Details: {self.log_path}")

    def close(self):
        stop_process(self.proc)
        self.proc.stdin.close()
        self.log.close()


def serve(directory, threads):
    """Private worker protocol. Only local config file paths arrive on stdin."""
    started = time.monotonic()
    backend = IndicConformer(threads=threads)
    save_json(directory / 'model_ready.json', {'pid': os.getpid(), 'backend': 'IndicConformer',
                                              'load_seconds': round(time.monotonic() - started, 3)})
    for line in sys.stdin:
        config_path = Path(json.loads(line))
        try:
            process(json.loads(config_path.read_text(encoding='utf-8')), backend)
            result = {'status': 'complete', 'worker_pid': os.getpid()}
        except Exception as exc:
            traceback.print_exc()
            result = {'status': 'error', 'message': str(exc), 'worker_pid': os.getpid()}
        save_json(config_path.parent / 'processed.json', result)


def analyze(session, args, metadata, cancel_event=None, terminal=None, worker=None):
    terminal = terminal or Terminal(args.verbose)
    for path in ALL_MODELS:
        if not path.is_file():
            raise RuntimeError(f'Missing local model/runtime: {path}. Run bash setup.sh once online.')
    config = {**metadata, 'session': str(session), 'test_only': True,
              'speakers': args.speakers, 'threshold': args.threshold, 'language': args.language,
              'script': args.script, 'threads': args.threads}
    save_json(session / 'session.json', config)
    terminal.detail(f'Processing {session.name}; timeout {args.timeout}s.')
    terminal.status(processing=True)
    own_worker = worker is None
    try:
        worker = worker or ModelWorker(session, args.threads)
        worker.run(session / 'session.json', args.timeout, cancel_event)
    finally:
        if own_worker and worker is not None:
            worker.close()
        terminal.status(processing=False)
    report = json.loads((session / 'transcript.json').read_text(encoding='utf-8'))
    # Load the romanizer once in the live parent, not once per inference subprocess.
    for row in report['segments']:
        row['display_text'] = romanize(row['text'], report['language_detected'])
    save_json(session / 'transcript.json', report)
    lines = [f"[{r['start_ms']/1000:6.2f}-{r['end_ms']/1000:6.2f}] {r['speaker_id']}\n"
             + format_transcript_text(r, report['language_detected'], args.script)
             for r in report['segments']]
    (session / 'transcript.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    roman_lines = [f"[{r['start_ms']/1000:6.2f}-{r['end_ms']/1000:6.2f}] {r['speaker_id']}: {r['display_text']}"
                   for r in report['segments']]
    (session / 'transcript_roman.txt').write_text('\n'.join(roman_lines) + '\n', encoding='utf-8')
    show_transcript(report, terminal, metadata.get('offset_ms', 0))
    if report['status'] == 'speech_unclear':
        terminal.line('Speech unclear. Please repeat, or select --language hi / bn.')
    elif not report['segments'] and not metadata.get('speaker_registry'):
        terminal.line('No clear speech transcribed.')
    terminal.detail(f"Speakers: {report['speaker_count']} | Audio: {report['audio']['seconds']:.1f}s | "
                    f"Processing: {report['timings']['processing_seconds']:.1f}s | RTF: {report['timings']['real_time_factor']:.2f}")
    return report


def live(args):
    """Continuous capture and streaming VAD, with independent queued recognition."""
    import numpy as np
    import sherpa_onnx as sherpa

    if not 5 <= args.chunk_seconds <= 60 or not 0.3 <= args.pause_seconds <= 2:
        raise ValueError('Use maximum speech length 5..60 seconds and pause 0.3..2 seconds.')
    device = select_device(args.device)
    cfg = sherpa.VadModelConfig()
    cfg.silero_vad.model = str(MODELS['vad'])
    cfg.silero_vad.min_silence_duration = args.pause_seconds
    cfg.silero_vad.min_speech_duration = 0.25
    cfg.silero_vad.max_speech_duration = args.chunk_seconds
    cfg.sample_rate = RATE
    cfg.num_threads = 1
    vad = sherpa.VoiceActivityDetector(cfg, buffer_size_in_seconds=args.chunk_seconds + 5)
    stream = StreamingVAD(vad, cfg.silero_vad.window_size)
    base = args.output.expanduser().resolve()
    session = make_session(base)
    terminal = Terminal(args.verbose)
    stopped = threading.Event()
    pending = queue.Queue(maxsize=8)
    failures = []
    stats = {'started_at': utc_now(), 'device': device, 'status': 'listening',
             'mode': 'streaming_vad', 'language': args.language, 'pause_seconds': args.pause_seconds,
             'max_utterance_seconds': args.chunk_seconds,
             'chunks_captured': 0, 'chunks_processed': 0, 'chunks_deferred': 0, 'samples': 0,
             'test_only': True, 'speaker_matching': 'session-only cosine threshold 0.6, margin 0.08'}
    save_json(session / 'live_session.json', stats)

    def record_speech():
        proc = None
        reserved_bytes = sum(p.stat().st_size for p in base.rglob('*') if p.is_file())

        def save_speech(offset, samples, partial=False):
            nonlocal reserved_bytes
            # Reserve space for audio, masked audio, JSON, and logs; never delete old tests.
            required = len(samples) * 6 + 65536
            if reserved_bytes + required >= 512 * 1024 ** 2 or shutil.disk_usage(session).free < 128 * 1024 ** 2 + required:
                raise RuntimeError('Test storage limit reached. Archive results before restarting.')
            reserved_bytes += required
            folder = session / f'speech-{stats["chunks_captured"] + 1:05d}'
            folder.mkdir()
            with wave.open(str(folder / 'audio.wav'), 'wb') as wav:
                wav.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
                wav.writeframes((np.asarray(samples) * 32768).clip(-32768, 32767).astype('<i2').tobytes())
            metadata = {'started_at': stats['started_at'], 'offset_ms': round(offset / RATE * 1000),
                        'device': device, 'capture_status': 'partial_stop' if partial else 'complete',
                        'speaker_registry': str(session / 'speaker_registry.json'), 'patient_id': None}
            save_json(folder / 'session.json', metadata)
            stats['chunks_captured'] += 1
            if stopped.is_set() or partial:
                stats['chunks_deferred'] += 1
                save_json(folder / 'pending.json', {'reason': 'stopped; audio available for manual analysis'})
            else:
                try:
                    pending.put_nowait((folder, metadata))
                except queue.Full:
                    stats['chunks_deferred'] += 1
                    save_json(folder / 'pending.json', {'reason': 'inference backlog full; audio retained'})
                    terminal.line(f'Recognition is behind. {folder.name} saved for later; listening continues.')
            terminal.status(waiting=pending.qsize())
            terminal.detail(f'Saved {folder.name}: {len(samples) / RATE:.1f}s')

        try:
            with (session / 'capture.log').open('w', encoding='utf-8') as log:
                stats['started_at'] = utc_now()
                proc = subprocess.Popen(['arecord', '-q', '-D', device, '-t', 'raw', '-f', 'S16_LE',
                                         '-r', str(RATE), '-c', '1'], stdout=subprocess.PIPE,
                                        stderr=log, start_new_session=True)
                with selectors.DefaultSelector() as sel:
                    sel.register(proc.stdout, selectors.EVENT_READ)
                    last_data = last_check = time.monotonic()
                    captured_bytes = 0
                    terminal.status(capture='Listening')
                    while not stopped.is_set():
                        if not sel.select(timeout=0.2):
                            if proc.poll() is not None or time.monotonic() - last_data > 8:
                                raise RuntimeError('Microphone stopped or disconnected. See capture.log.')
                            continue
                        data = os.read(proc.stdout.fileno(), 3200)
                        if not data:
                            raise RuntimeError(capture_error(session / 'capture.log'))
                        last_data = time.monotonic()
                        captured_bytes += len(data)
                        stats['samples'] = captured_bytes // 2
                        for offset, samples in stream.feed(data):
                            save_speech(offset, samples)
                        if last_data - last_check >= 1:
                            last_check = last_data
                            errors = (session / 'capture.log').read_text(errors='replace').lower()
                            if any(x in errors for x in ('overrun', 'read error', 'input/output error')):
                                raise RuntimeError('Microphone reported lost audio. See capture.log.')
                            if shutil.disk_usage(session).free < 128 * 1024 ** 2:
                                raise RuntimeError('Disk space is low. Archive results before restarting.')
                        terminal.status(capture='Listening - speech' if vad.is_speech_detected() else 'Listening',
                                        waiting=pending.qsize())
        except Exception as exc:
            failures.append(str(exc))
            stopped.set()
        finally:
            if proc:
                stop_process(proc)
                if proc.stdout:
                    proc.stdout.close()
            # Preserve an interrupted utterance, but do not make Ctrl+C wait for inference.
            try:
                for offset, samples in stream.flush():
                    save_speech(offset, samples, partial=True)
            except Exception as exc:
                failures.append(f'Could not save final speech: {exc}')
            stopped.set()

    terminal.line('IMMORTALS | Offline speech test | IndicConformer')
    terminal.line(f'Language: {LANGUAGES.get(args.language, args.language)} | Speakers: {args.speakers or "automatic"}')
    terminal.line({'both': 'Output: Hindi + Hinglish | Bengali + Binglish (same speech)',
                   'roman': 'Output: Hindi -> Hinglish | Bengali -> Binglish',
                   'native': 'Output: native Hindi / Bengali script'}[args.script])
    terminal.line(f'Speak naturally. Text appears after a short pause. Ctrl+C stops.\nSaved in: {session}')
    terminal.line('Speaker labels are estimates; unclear voices are marked.\n')
    terminal.status(capture='Opening microphone')
    collector = threading.Thread(target=record_speech, name='microphone-capture', daemon=True)
    worker = ModelWorker(session, args.threads)
    collector.start()
    interrupted = False
    try:
        while not stopped.is_set():
            if worker.proc.poll() is not None:
                raise RuntimeError(f'Model worker exited {worker.proc.returncode}. Details: {worker.log_path}')
            try:
                folder, metadata = pending.get(timeout=0.2)
            except queue.Empty:
                continue
            terminal.status(waiting=pending.qsize())
            try:
                analyze(folder, args, metadata, stopped, terminal, worker)
                stats['chunks_processed'] += 1
            except (Exception, KeyboardInterrupt) as exc:
                save_json(folder / 'pending.json', {'reason': str(exc) or 'interrupted; audio retained'})
                stats['chunks_deferred'] += 1
                raise
    except KeyboardInterrupt:
        interrupted = True
    except Exception as exc:
        failures.append(str(exc))
    finally:
        stopped.set()
        terminal.status(capture='Stopping', processing=False)
        worker.close()
        collector.join(timeout=8)
        if collector.is_alive():
            failures.append('Microphone worker did not stop within 8 seconds.')
        while not pending.empty():
            folder, _ = pending.get_nowait()
            save_json(folder / 'pending.json', {'reason': 'stopped before inference; audio retained'})
            stats['chunks_deferred'] += 1
        stats.update(status='error' if failures else 'stopped', ended_at=utc_now(), errors=failures)
        save_json(session / 'live_session.json', stats)
        terminal.close()
        terminal.line(f"Stopped. {stats['chunks_processed']} speech sections transcribed; "
                      f"{stats['chunks_deferred']} saved for later.")
        for error in failures:
            terminal.line(f'Error: {error}')
        terminal.line(f'Files: {session}')
    return 1 if failures else 130 if interrupted else 0


def execute(args):
    if args.command == 'menu':
        return menu(parser())
    if args.command == 'devices':
        print(devices())
        print('Use a stable name: --device plughw:CARD=UACDemoV10,DEV=0')
        return 0
    if args.command == 'doctor':
        return 0 if doctor() else 1
    # Validate before opening a microphone or creating a recording.
    if args.command != 'mic-test':
        if not 0 <= args.speakers <= 20 or not 0 < args.threshold <= 1 or not 1 <= args.threads <= 4 or not 10 <= args.timeout <= 3600:
            raise ValueError('Use speakers 0..20 (0=auto), threshold (0,1], threads 1..4, timeout 10..3600.')
        if args.language not in LANGUAGES:
            raise ValueError('Only auto, hi (Hindi), or bn (Bengali) is supported.')
        if any(not p.is_file() for p in ALL_MODELS):
            raise RuntimeError('Local models/runtime are missing. Run ./run.sh doctor or bash setup.sh.')
    if args.command == 'live':
        return live(args)
    if args.command != 'analyze' and not 1 <= args.seconds <= MAX_SECONDS:
        raise ValueError(f'Recording duration must be 1..{MAX_SECONDS} seconds.')
    device = select_device(args.device) if args.command != 'analyze' else None
    source = Path(args.wav).expanduser().resolve() if args.command == 'analyze' else None
    if source:
        audio_info(source)
    session = make_session(args.output.expanduser().resolve())
    print(f'Session files: {session}', flush=True)
    metadata = {'started_at': utc_now(), 'device': device, 'source_file': str(source) if source else None,
                'capture_status': 'not_started', 'patient_id': None}
    try:
        save_json(session / 'session.json', metadata)
        if source:
            shutil.copyfile(source, session / 'audio.wav')
        else:
            metadata['capture_status'] = 'recording'
            save_json(session / 'session.json', metadata)
            capture(session / 'audio.wav', args.seconds, device)
        metadata.update(capture_status='complete', capture_ended_at=utc_now())
        save_json(session / 'session.json', metadata)
        if args.command != 'mic-test':
            analyze(session, args, metadata)
        else:
            print(f"Microphone recording saved. Playback: aplay '{session / 'audio.wav'}'")
    except BaseException as exc:
        save_json(session / 'error.json', {'status': 'cancelled' if isinstance(exc, KeyboardInterrupt) else 'error',
                                         'message': str(exc), 'at': utc_now(), 'capture': metadata})
        raise
    print(f'Results saved in {session}')
    return 0


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command')
    sub.add_parser('devices', help='List ALSA capture devices')
    sub.add_parser('doctor', help='Check local installation and microphone')
    sub.add_parser('menu', help='Interactive test menu')
    for command in ('live', 'record', 'analyze', 'mic-test'):
        c = sub.add_parser(command)
        c.add_argument('--output', type=Path, default=ROOT / 'results')
        if command == 'analyze':
            c.add_argument('wav', help='Mono 16 kHz signed 16-bit PCM WAV, at most 120 seconds')
        else:
            c.add_argument('--device', default=None, help='ALSA name; auto-selects if exactly one microphone exists')
            if command == 'live':
                c.add_argument('--max-utterance-seconds', '--chunk-seconds', dest='chunk_seconds', type=int, default=15,
                               help='Maximum speech before a forced split (default 15); pauses finish speech earlier')
                c.add_argument('--pause-seconds', type=float, default=0.6,
                               help='Pause that finalizes a speech section (default 0.6 seconds)')
            else:
                c.add_argument('--seconds', type=int, default=5 if command == 'mic-test' else 30)
        if command != 'mic-test':
            c.add_argument('--speakers', type=int, default=0, help='0 = automatically detect count; 2 or more = known count')
            c.add_argument('--threshold', type=float, default=0.5, help='Auto-clustering threshold; smaller finds more speakers')
            c.add_argument('--language', type=language_code, default='auto',
                           help='auto (default), hi/Hindi or bn/Bengali; IndicConformer only')
            c.add_argument('--verbose', action='store_true', help='Show processing timing and diagnostics')
            c.add_argument('--script', choices=('both', 'roman', 'native'), default='both',
                           help='both (default): Hindi + Hinglish / Bengali + Binglish; roman or native for one version')
            c.add_argument('--threads', type=int, default=2)
            c.add_argument('--timeout', type=int, default=900, help='Bounded model-processing timeout, seconds')
    return p


def menu(p):
    device = None
    while True:
        print('\nIMMORTALS - PHASE 3 OFFLINE SPEECH TEST\n'
              '  1  Check microphone level (5 seconds)\n'
              '  2  Listen continuously until Ctrl+C\n'
              '  3  Analyze an existing WAV\n'
              '  4  Check installation\n'
              '  5  List/select microphone\n'
              '  q  Quit\n'
              'Local test recordings only. No patient, Zigbee, or cloud writes.')
        try:
            choice = input('Choose: ').strip().lower()
            if choice == 'q':
                return 0
            if choice == '5':
                print(devices())
                device = input('ALSA device name (Enter = auto): ').strip() or None
                continue
            if choice == '4':
                doctor()
                continue
            if choice == '1':
                argv = ['mic-test']
            elif choice in ('2', '3'):
                if choice == '2':
                    argv = ['live']
                else:
                    argv = ['analyze', input('WAV path: ').strip()]
                argv += ['--language', input('Language [auto / Hindi / Bengali]: ').strip() or 'auto']
                argv += ['--speakers', input('Speaker count [0 = auto, or known count e.g. 2/3]: ').strip() or '0']
                print('Take turns for several seconds each, pause, then have the first speaker speak again.')
            else:
                continue
            if device and choice != '3':
                argv += ['--device', device]
            execute(p.parse_args(argv))
        except EOFError:
            return 0
        except KeyboardInterrupt:
            print('\nCancelled. Microphone/model process stopped; any captured audio was retained.')
        except (OSError, RuntimeError, ValueError, wave.Error) as exc:
            print(f'ERROR: {exc}')
        except SystemExit:
            pass  # Bad menu input should not close the terminal program.


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    if len(sys.argv) == 3 and sys.argv[1] == '_process':
        process(json.loads(Path(sys.argv[2]).read_text(encoding='utf-8')))
        return 0
    if len(sys.argv) == 4 and sys.argv[1] == '_serve':
        serve(Path(sys.argv[2]), int(sys.argv[3]))
        return 0
    p = parser()
    args = p.parse_args(sys.argv[1:] or ['live'])
    if not args.command:
        if not sys.stdin.isatty():
            p.print_help()
            return 0
        return menu(p)
    try:
        return execute(args)
    except KeyboardInterrupt:
        print('\nCancelled. Child processes stopped; captured files retained.', file=sys.stderr)
        return 130
    except (OSError, RuntimeError, ValueError, wave.Error) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
