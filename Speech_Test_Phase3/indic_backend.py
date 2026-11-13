"""Local AI4Bharat IndicConformer 600M INT8 CTC inference (Hindi/Bengali).

The public ONNX export is pinned by the installer. No downloads or remote code
are used at runtime. NeMo features use the export's own mel/window tables.
"""
from pathlib import Path
import json
import math
import time

import numpy as np

RATE = 16000
FRAME_MS = 80  # 10 ms mel hop, 8x encoder subsampling
LANGUAGES = ('hi', 'bn')
MODEL_ROOT = Path(__file__).resolve().parent / 'models/indicconformer'
FILES = ('encoder_int8.onnx', 'ctc_decoder_int8.onnx', 'vocab.json',
         'language_indices.json', 'mel_filters.json', 'hanning_window.json')


def mel_features(samples, filters, window):
    """NeMo preemphasis, centered STFT, Slaney mel, log, per-bin normalization."""
    samples = np.asarray(samples, dtype=np.float32)
    if samples.ndim != 1 or len(samples) < 512 or not np.isfinite(samples).all():
        raise ValueError('IndicConformer needs finite mono audio of at least 32 ms.')
    emphasized = np.concatenate((samples[:1], samples[1:] - 0.97 * samples[:-1]))
    padded = np.pad(emphasized, (256, 256), mode='reflect')
    frames = np.lib.stride_tricks.sliding_window_view(padded, 512)[::160]
    fft_window = np.pad(window, (56, 56))
    fft = np.fft.rfft(frames * fft_window, axis=-1)
    power = (fft.real ** 2 + fft.imag ** 2).astype(np.float32)
    mel = (power @ filters).T
    log_mel = np.log(mel + 2 ** -24).astype(np.float32)
    mean = log_mel.mean(axis=1, keepdims=True)
    std = log_mel.std(axis=1, ddof=1, keepdims=True) + 1e-5
    result = (log_mel - mean) / std
    valid_frames = result.shape[1]
    result = np.pad(result, ((0, 0), (0, (-valid_frames) % 16)))
    return result[None].astype(np.float32), valid_frames


def ctc_words(logprobs, vocab, duration_ms):
    """Collapse repeats/blanks, then assemble BPE tokens into timestamped words."""
    blank = len(vocab) - 1
    ids = np.argmax(logprobs, axis=-1)
    tokens, previous, start = [], None, 0
    for frame, token in enumerate(np.append(ids, blank)):
        token = int(token)
        if token != previous:
            if previous is not None and previous != blank:
                tokens.append((vocab[previous], start * FRAME_MS, min(frame * FRAME_MS, duration_ms)))
            start, previous = frame, token
    words, current = [], None
    for text, start_ms, end_ms in tokens:
        if text.startswith('<') or end_ms <= start_ms:
            continue
        if '\u2581' in text:
            if current and current['text']:
                words.append(current)
            current = {'text': text.replace('\u2581', ' '), 'start_ms': start_ms, 'end_ms': end_ms}
        elif current is None:
            current = {'text': text, 'start_ms': start_ms, 'end_ms': end_ms}
        else:
            current['text'] += text
            current['end_ms'] = end_ms
    if current and current['text'].strip():
        words.append(current)
    return words


def choose_language(logprobs, indices):
    """Compare unnormalized vocabulary evidence on non-blank CTC frames.

    Both language heads share the same blank. These scores are a heuristic for
    session testing, not calibrated language probabilities.
    """
    scores = {}
    nonblank = np.maximum.reduce([logprobs[:, indices[lang][:-1]].max(axis=-1) for lang in LANGUAGES])
    blank = logprobs[:, indices['hi'][-1]]
    weights = np.exp(np.clip(nonblank - np.maximum(nonblank, blank), -30, 0))
    for lang in LANGUAGES:
        local = logprobs[:, indices[lang][:-1]]
        evidence = np.logaddexp.reduce(local, axis=-1)
        scores[lang] = float(np.sum(evidence * weights) / max(float(weights.sum()), 1e-8))
    return max(scores, key=scores.get), scores


class IndicConformer:
    def __init__(self, root=MODEL_ROOT, threads=2):
        import onnxruntime as ort
        self.root = Path(root)
        for name in FILES:
            if not (self.root / name).is_file():
                raise RuntimeError(f'Missing IndicConformer file: {name}. Run bash setup.sh.')
        self.vocab = json.loads((self.root / 'vocab.json').read_text(encoding='utf-8'))
        self.indices = json.loads((self.root / 'language_indices.json').read_text())
        self.filters = np.array(json.loads((self.root / 'mel_filters.json').read_text()), dtype=np.float32)
        self.window = np.array(json.loads((self.root / 'hanning_window.json').read_text()), dtype=np.float32)
        if self.filters.shape != (257, 80) or self.window.shape != (400,):
            raise RuntimeError('Unexpected IndicConformer feature tables.')
        for language in LANGUAGES:
            if len(self.vocab[language]) != 257 or len(self.indices[language]) != 257:
                raise RuntimeError('Unexpected IndicConformer vocabulary.')
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        options.add_session_config_entry('session.intra_op.allow_spinning', '0')
        options.add_session_config_entry('session.inter_op.allow_spinning', '0')
        options.log_severity_level = 3
        self.encoder = ort.InferenceSession(str(self.root / 'encoder_int8.onnx'), options,
                                           providers=['CPUExecutionProvider'])
        self.decoder = ort.InferenceSession(str(self.root / 'ctc_decoder_int8.onnx'), options,
                                           providers=['CPUExecutionProvider'])
        self.input_meta = self.encoder.get_inputs()
        self.decoder_meta = self.decoder.get_inputs()[0]

    def transcribe(self, samples, language='auto'):
        if language not in ('auto', *LANGUAGES):
            raise ValueError('IndicConformer test supports Hindi and Bengali only.')
        started = time.monotonic()
        features, length = mel_features(samples, self.filters, self.window)
        feeds = {}
        for meta in self.input_meta:
            if meta.type == 'tensor(float)':
                feeds[meta.name] = features
            elif meta.type == 'tensor(int64)':
                feeds[meta.name] = np.array([length], dtype=np.int64).reshape((1,) * len(meta.shape))
            else:
                raise RuntimeError('Unexpected encoder input: ' + str(meta))
        outputs = self.encoder.run(None, feeds)
        encoded = outputs[0]
        expected = self.decoder_meta.shape
        if len(expected) == 3 and expected[-1] == 1024 and encoded.shape[-1] != 1024:
            encoded = encoded.transpose(0, 2, 1)
        logprobs = self.decoder.run(None, {self.decoder_meta.name: encoded})[0][0]
        if len(outputs) > 1:
            valid = int(np.asarray(outputs[1]).reshape(-1)[0])
        else:
            valid = math.ceil(length / 8)
        logprobs = logprobs[:min(valid, len(logprobs))]
        if not len(logprobs) or not np.isfinite(logprobs).all():
            raise RuntimeError('IndicConformer returned invalid scores.')
        detected, scores = choose_language(logprobs, self.indices)
        language = detected if language == 'auto' else language
        words = ctc_words(logprobs[:, self.indices[language]], self.vocab[language], round(len(samples) / RATE * 1000))
        return {'language': language, 'language_scores': scores, 'words': words,
                'text': ''.join(word['text'] for word in words).strip(),
                'inference_seconds': round(time.monotonic() - started, 3)}
