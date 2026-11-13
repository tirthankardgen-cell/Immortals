"""Model-free regression checks for attribution, silence, and input bounds."""
import tempfile
import unittest
import io
import contextlib
from types import SimpleNamespace
from pathlib import Path
import wave

from speech_test import (align_transcript, audio_info, levels, speaker_for, parser,
                         StreamingVAD, Terminal, show_transcript)
from romanize_text import romanize


def turn(start, end, speaker):
    return {'start_ms': start, 'end_ms': end, 'speaker_id': speaker}


class SpeechTests(unittest.TestCase):
    def test_more_than_two_speakers_and_returning_voice(self):
        turns = [turn(0, 1000, 'Speaker 1'), turn(1000, 2000, 'Speaker 2'),
                 turn(2000, 3000, 'Speaker 3'), turn(3000, 4000, 'Speaker 1')]
        self.assertEqual([speaker_for(x, x + 500, turns)[0] for x in (0, 1000, 2000, 3000)],
                         ['Speaker 1', 'Speaker 2', 'Speaker 3', 'Speaker 1'])

    def test_overlapping_speech_is_ambiguous(self):
        self.assertEqual(speaker_for(100, 900, [turn(0, 1000, 'Speaker 1'), turn(800, 1200, 'Speaker 2')]),
                         ('Ambiguous', 'overlapping_speakers'))

    def test_word_crossing_speaker_boundary_is_ambiguous(self):
        self.assertEqual(speaker_for(800, 1200, [turn(0, 1000, 'Speaker 1'), turn(1000, 2000, 'Speaker 2')]),
                         ('Ambiguous', 'speaker_boundary'))

    def test_silence_or_short_coverage_is_unknown(self):
        self.assertEqual(speaker_for(0, 1000, [turn(500, 700, 'Speaker 1')])[0], 'Unknown')
        self.assertEqual(speaker_for(0, 1000, [])[0], 'Unknown')
        self.assertEqual(speaker_for(0, 0, [])[0], 'Unknown')

    def test_duplicate_turns_do_not_inflate_coverage(self):
        self.assertEqual(speaker_for(0, 1000, [turn(0, 300, 'Speaker 1')] * 3)[0], 'Unknown')

    def test_ctc_millisecond_offsets_and_silence_filter(self):
        raw = {'transcription': [
            {'offsets': {'from': 100, 'to': 500}, 'text': ' Hello'},
            {'offsets': {'from': 500, 'to': 800}, 'text': ' there'},
            {'offsets': {'from': 3000, 'to': 4000}, 'text': 'hallucination in silence'}]}
        result = align_transcript(raw, [turn(0, 1000, 'Speaker 1')], [[0, 1000]], 5000)
        self.assertEqual(result, [{'start_ms': 100, 'end_ms': 800, 'speaker_id': 'Speaker 1',
                                   'text': 'Hello there', 'quality': 'estimated'}])

    def test_no_vad_speech_means_no_text(self):
        raw = {'transcription': [{'offsets': {'from': 0, 'to': 1000}, 'text': 'fake text'}]}
        self.assertEqual(align_transcript(raw, [turn(0, 1000, 'Speaker 1')], [], 1000), [])

    def test_audio_format_and_duration_are_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.wav'
            for channels, rate, seconds, valid in [(1, 16000, 1, True), (2, 16000, 1, False),
                                                  (1, 48000, 1, False), (1, 16000, 121, False)]:
                with wave.open(str(path), 'wb') as wav:
                    wav.setparams((channels, 2, rate, 0, 'NONE', 'not compressed'))
                    wav.writeframes(b'\0\0' * channels * rate * seconds)
                if valid:
                    self.assertEqual(audio_info(path)['seconds'], 1)
                else:
                    with self.assertRaises(ValueError):
                        audio_info(path)

    def test_level_meter_silence_and_clipping(self):
        self.assertEqual(levels(b'\0\0' * 100), (-120.0, 0.0))
        self.assertGreater(levels(b'\xff\x7f' * 100)[1], 0.99)

    def test_multilingual_defaults_and_names(self):
        for command in ('live', 'record', 'analyze'):
            argv = [command] + (['test.wav'] if command == 'analyze' else [])
            self.assertEqual(parser().parse_args(argv).language, 'auto')
            self.assertEqual(parser().parse_args(argv).script, 'both')
        for value, code in [('Hindi', 'hi'), ('Bengali', 'bn'), ('Bangla', 'bn')]:
            self.assertEqual(parser().parse_args(['live', '--language', value]).language, code)

    def test_indic_subword_tokens_keep_vowel_signs_and_word_spaces(self):
        for tokens, expected in [([' नम', 'स्ते', ' दुनिया'], 'नमस्ते दुनिया'),
                                 ([' আম', 'ি', ' বাংলা', ' বলি'], 'আমি বাংলা বলি')]:
            raw = {'transcription': [{'offsets': {'from': i * 100, 'to': (i + 1) * 100}, 'text': token}
                                     for i, token in enumerate(tokens)]}
            result = align_transcript(raw, [turn(0, 1000, 'Speaker 1')], [[0, 1000]], 1000)
            self.assertEqual(result[0]['text'], expected)

    def test_clean_terminal_keeps_languages_and_uncertainty(self):
        out = io.StringIO()
        terminal = Terminal(stream=out)
        terminal.status(capture='Listening', processing=True)
        terminal.detail('RTF: hidden diagnostics')
        for language, words, speaker in [('hi', 'नमस्ते दुनिया', 'Speaker 1'),
                                          ('bn', 'আমি বাংলা বলি', 'Ambiguous')]:
            show_transcript({'language_detected': language, 'script': 'native', 'segments': [
                {'start_ms': 2000, 'speaker_id': speaker, 'text': words}]}, terminal, offset_ms=60000)
        result = out.getvalue()
        self.assertIn('[01:02] Speaker 1 (Hindi)', result)
        self.assertIn('नमस्ते दुनिया', result)
        self.assertIn('আমি বাংলা বলি', result)
        self.assertIn('Unclear / overlapping speakers (Bengali)', result)
        self.assertNotIn('RTF', result)
        self.assertNotIn('\x1b', result)
        self.assertNotIn('Listening', result)

    def test_only_hindi_bengali_can_be_selected(self):
        for command in ('live', 'record', 'analyze'):
            argv = [command] + (['test.wav'] if command == 'analyze' else [])
            for language in ('en', 'english', 'zh', 'es', 'ne', 'fr'):
                with self.subTest(command=command, language=language), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        parser().parse_args(argv + ['--language', language])

    def test_hinglish_binglish_default_keeps_original_text(self):
        for language, native, heading in [('hi', 'नमस्ते दुनिया', 'Hinglish'),
                                           ('bn', 'আমি বাংলা বলি', 'Binglish')]:
            out = io.StringIO()
            report = {'language_detected': language, 'script': 'roman', 'segments': [
                {'start_ms': 0, 'speaker_id': 'Speaker 1', 'text': native}]}
            show_transcript(report, Terminal(stream=out))
            self.assertIn(heading, out.getvalue())
            self.assertTrue(out.getvalue().isascii(), out.getvalue())
            self.assertEqual(report['segments'][0]['text'], native)
            self.assertTrue(romanize(native, language).strip())
        self.assertEqual(romanize('Please check my temperature.', 'en'), 'Please check my temperature.')

    def test_default_pairs_native_and_roman_for_the_same_speech(self):
        for language, native, native_name, roman_name in [
                ('hi', 'नमस्ते दुनिया', 'Hindi', 'Hinglish'),
                ('bn', 'আমি বাংলা বলি', 'Bengali', 'Binglish')]:
            with self.subTest(language=language):
                out = io.StringIO()
                report = {'language_detected': language, 'segments': [
                    {'start_ms': 2000, 'speaker_id': 'Speaker 2', 'text': native}]}
                show_transcript(report, Terminal(stream=out), offset_ms=60000)
                output = out.getvalue()
                self.assertIn(f'[01:02] Speaker 2 ({native_name} / {roman_name})', output)
                self.assertIn(f'{native_name}: {native}', output)
                self.assertIn(f'{roman_name}: {romanize(native, language)}', output)
                self.assertEqual(output.count('[01:02]'), 1)
                self.assertEqual(report['segments'][0]['text'], native)

    def test_terminal_model_text_cannot_clear_screen(self):
        out = io.StringIO()
        show_transcript({'language': 'en', 'segments': [
            {'start_ms': 0, 'speaker_id': 'Unknown', 'text': 'hello\x1b[2J\nworld'}]}, Terminal(stream=out))
        self.assertNotIn('\x1b', out.getvalue())

    def test_streaming_pcm_arbitrary_read_boundaries_and_flush(self):
        import numpy as np

        class FakeVad:
            def __init__(self):
                self.blocks, self.ready = [], []

            def accept_waveform(self, block):
                self.blocks.append(block.copy())
                # A phrase starts after initial silence and is emitted on flush.

            def flush(self):
                self.ready.append(SimpleNamespace(start=4, samples=np.concatenate(self.blocks)[4:]))

            def empty(self):
                return not self.ready

            @property
            def front(self):
                return self.ready[0]

            def pop(self):
                self.ready.pop(0)

        vad = FakeVad()
        stream = StreamingVAD(vad, 4)
        pcm = np.arange(11, dtype='<i2').tobytes()
        for block in (pcm[:1], pcm[1:7], pcm[7:18], pcm[18:]):
            self.assertEqual(stream.feed(block), [])
        result = stream.flush()
        self.assertEqual(stream.samples, 11)
        self.assertEqual(result[0][0], 4)
        self.assertEqual(len(result[0][1]), 7)  # No padding in the saved WAV.
        np.testing.assert_array_equal(result[0][1] * 32768, np.arange(4, 11))


if __name__ == '__main__':
    unittest.main()
