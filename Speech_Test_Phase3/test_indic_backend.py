"""Model-free checks for CTC time alignment, masks, and feature bounds."""
import unittest
import numpy as np

from indic_backend import ctc_words, choose_language, mel_features


class IndicTests(unittest.TestCase):
    def test_ctc_repeats_collapse_but_blank_separates_repeated_tokens(self):
        vocab = ['▁क', 'ा', '<blank>']
        ids = [0, 0, 1, 1, 2, 0, 1, 2]
        logits = np.full((len(ids), len(vocab)), -10.0)
        logits[np.arange(len(ids)), ids] = 5
        words = ctc_words(logits, vocab, 640)
        self.assertEqual([w['text'] for w in words], [' का', ' का'])
        self.assertEqual((words[0]['start_ms'], words[0]['end_ms']), (0, 320))
        self.assertEqual((words[1]['start_ms'], words[1]['end_ms']), (400, 560))

    def test_ctc_timestamps_clip_to_real_audio_and_ignore_blank(self):
        logits = np.array([[0., 1.], [4., 0.], [4., 0.]])
        self.assertEqual(ctc_words(logits, ['▁হ্যাঁ', '<blank>'], 190),
                         [{'text': ' হ্যাঁ', 'start_ms': 80, 'end_ms': 190}])
        self.assertEqual(ctc_words(np.array([[0., 5.]]), ['word', '<blank>'], 80), [])

    def test_language_choice_uses_global_evidence_not_blank_frequency(self):
        indices = {'hi': [0, 1, 4], 'bn': [2, 3, 4]}
        blank_frames = np.tile([-12., -12., -12., -12., 0.], (20, 1))
        hindi = np.vstack((blank_frames, [4., 3., -3., -4., 0.]))
        bengali = np.vstack((blank_frames, [-3., -4., 4., 3., 0.]))
        self.assertEqual(choose_language(hindi, indices)[0], 'hi')
        self.assertEqual(choose_language(bengali, indices)[0], 'bn')

    def test_feature_shape_and_padding_are_finite_for_silence(self):
        filters = np.ones((257, 80), dtype=np.float32)
        window = np.hanning(401)[:-1].astype(np.float32)
        features, length = mel_features(np.zeros(16000, dtype=np.float32), filters, window)
        self.assertEqual(length, 101)
        self.assertEqual(features.shape, (1, 80, 112))
        self.assertTrue(np.isfinite(features).all())
        self.assertTrue(np.all(features[:, :, length:] == 0))
        with self.assertRaises(ValueError):
            mel_features(np.array([np.nan] * 1024), filters, window)


if __name__ == '__main__':
    unittest.main()
