"""Sender contract and concurrency checks; no radio or sensor hardware needed."""
import copy
import json
from pathlib import Path
import struct
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main as app
import numpy as np


def decode_fixture(frames):
    # Independent receiver-side contract check, not the future receiver app.
    header = struct.Struct('!2sBBIIHHI')
    pieces = {}
    identity = None
    for frame in frames:
        magic, version, flags, session, seq, index, total, crc = header.unpack(frame[:20])
        if magic != b'IM' or version not in (1, 2) or flags != 1 or not 0 <= index < total:
            raise ValueError('Invalid header')
        key = session, seq, total, crc
        if identity is not None and key != identity:
            raise ValueError('Mixed messages')
        identity = key
        if index in pieces and pieces[index] != frame[20:]:
            raise ValueError('Conflicting duplicate')
        pieces[index] = frame[20:]
    session, seq, total, crc = identity
    if len(pieces) != total:
        raise ValueError('Incomplete message')
    compressed = b''.join(pieces[i] for i in range(total))
    if zlib.crc32(compressed) != crc:
        raise ValueError('CRC mismatch')
    message = json.loads(zlib.decompress(compressed))
    if version == 2:
        captured, enabled, states, waves = message
        message = dict(timestamp=captured, ecg_enabled=enabled,
                       session_id=f'{session:08x}', sequence=seq,
                       sensors={name:dict(zip(('status','age_seconds','values'), state))
                                for name,state in zip(('pulse','ecg','bmp','mlx','dht'),states)},
                       waveforms={name:dict(zip(('status','clear','time_offset_ms','values'), wave))
                                  for name,wave in zip(('pulse','ecg'),waves)})
        for state in message['sensors'].values():
            state['values'] = {(app.ZIGBEE_FIELDS[int(k[1:])] if k.startswith('#') else k):v
                               for k,v in state['values'].items()}
    if message['session_id'] != f'{session:08x}' or message['sequence'] != seq:
        raise ValueError('Envelope mismatch')
    return message


def sensor_fixture():
    monitor = app.SensorMonitor()
    monitor.publish('pulse', 'Pulse detected', heart_rate_bpm=77.2, spo2_percent=98.4,
                    quality_percent=90, sample_rate_hz=25)
    monitor.publish('ecg', 'Noisy', heart_rate_bpm=None, candidate_bpm=91.4, voltage_v=1.6)
    monitor.publish('bmp', 'Live', pressure_hpa=1013.2, temperature_c=30.1)
    monitor.publish('mlx', 'Live', ambient_c=29.2, object_c=31.3)
    monitor.publish('dht', 'Live', temperature_c=28.4, humidity_percent=64.3)
    now = time.monotonic()
    monitor.ecg_enabled = True
    monitor.pulse_trace.extend((now-8+i/25, 90000+200*np.sin(i*.3)) for i in range(200))
    monitor.ecg_trace.extend((now-8+i/125, 1.65+.1*np.sin(i*.07)) for i in range(1000))
    return monitor


class PacketTests(unittest.TestCase):
    def test_live_batches_bound_history_preserve_fields_and_reset_unavailable(self):
        m = sensor_fixture()
        captured = time.monotonic()
        snapshot = m.snapshot(traces=True)
        message = app.zigbee_live_message(snapshot, 'test', 1, 2, captured, captured-.2)
        result = decode_fixture(app.zigbee_frames(message, 1, 2, 84))
        self.assertEqual(result['sensors'], snapshot['sensors'])
        for wave in result['waveforms'].values():
            self.assertFalse(wave['clear'])
            self.assertTrue(all(-200 <= t <= 0 for t in wave['time_offset_ms']))
            self.assertLessEqual(len(wave['values']), 26)
        m.states['pulse']['updated_mono'] = captured-10
        missing = app.zigbee_live_message(m.snapshot(traces=True), 'test', 1, 3, captured)
        self.assertTrue(missing['waveforms']['pulse']['clear'])
        self.assertFalse(missing['waveforms']['pulse']['values'])

    def test_all_measurements_and_graphs_roundtrip_with_small_radio(self):
        monitor = sensor_fixture()
        snapshot = monitor.snapshot(traces=True)
        original = copy.deepcopy(snapshot)
        message = app.zigbee_message(snapshot, '0013A200408DF0F0', 321, 9, time.monotonic())
        for size in (64, 84, 200, 255):
            frames = app.zigbee_frames(message, 321, 9, size)
            self.assertTrue(all(len(f) <= size for f in frames))
            result = decode_fixture(frames[::-1]+frames[:1])
            self.assertEqual(result['sensors'], original['sensors'])
            self.assertIsNone(result['sensors']['ecg']['values']['heart_rate_bpm'])
            self.assertEqual(result['sensors']['ecg']['values']['candidate_bpm'], 91.4)
            self.assertGreater(len(result['waveforms']['ecg']['values']), 950)
            self.assertGreater(len(result['waveforms']['pulse']['values']), 190)
        self.assertEqual(snapshot, original)

    def test_loss_corruption_and_mixed_sequences_are_rejected(self):
        m = sensor_fixture()
        message = app.zigbee_message(m.snapshot(traces=True), 'test', 1, 2, time.monotonic())
        frames = app.zigbee_frames(message, 1, 2, 84)
        with self.assertRaises(ValueError):
            decode_fixture(frames[:-1])
        damaged = frames[:]
        damaged[0] = damaged[0][:-1]+bytes([damaged[0][-1] ^ 1])
        with self.assertRaises(ValueError):
            decode_fixture(damaged)
        with self.assertRaises(ValueError):
            decode_fixture(frames+app.zigbee_frames(message, 1, 3, 84))

    def test_stale_data_and_disabled_ecg_do_not_leak_waveforms(self):
        m = sensor_fixture()
        m.ecg_enabled = False
        m.states['pulse']['updated_mono'] = time.monotonic()-10
        packet = app.zigbee_message(m.snapshot(traces=True), 'test', 1, 1, time.monotonic())
        self.assertEqual(packet['sensors']['pulse']['values'], {})
        self.assertEqual(packet['waveforms']['pulse']['values'], [])
        self.assertEqual(packet['waveforms']['ecg']['values'], [])

    def test_nonfinite_data_is_not_encoded(self):
        with self.assertRaises(ValueError):
            app.zigbee_frames({'bad': float('nan')}, 1, 1, 84)

    def test_bad_configuration_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(app, 'BASE', Path(directory)):
            for key, value in (('receiver_address', 'FFFF'), ('interval_seconds', float('nan')),
                               ('max_packet_bytes', 12), ('max_packet_bytes', 84.5),
                               ('receiver_address', '000000000000FFFF')):
                (Path(directory)/'zigbee_config.json').write_text(json.dumps({key: value}))
                with self.assertRaises(ValueError):
                    app.zigbee_config()


class FakeRadio:
    def __init__(self, blocked=False, fail=False):
        self.frames = []
        self.entered = threading.Event()
        self.release = threading.Event()
        self.closed = threading.Event()
        self.blocked, self.fail = blocked, fail

    def send_data(self, receiver, frame):
        self.frames.append(frame)
        self.entered.set()
        if self.blocked:
            if not self.release.wait(3):
                raise TimeoutError('Test radio timed out')
        if self.fail:
            raise OSError('Radio unplugged')

    def close(self):
        self.closed.set()


def until(predicate, seconds=2):
    end = time.monotonic()+seconds
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(.01)
    return bool(predicate())


class WorkerTests(unittest.TestCase):
    def start_sender(self, radio):
        m = sensor_fixture()
        sender = m.zigbee
        connector = patch.object(sender, '_connect', return_value=(radio, object(), 'test', 84))
        connector.start()
        thread = threading.Thread(target=sender.run)
        thread.start()
        def cleanup():
            m.stop.set()
            sender.set_enabled(False)
            radio.release.set()
            thread.join(3)
            connector.stop()
            self.assertFalse(thread.is_alive())
        self.addCleanup(cleanup)
        return m, sender

    def test_default_off_does_not_open_radio(self):
        radio = FakeRadio()
        m, s = self.start_sender(radio)
        time.sleep(.25)
        s._connect.assert_not_called()
        self.assertFalse(s.status()['enabled'])

    def test_off_during_slow_send_is_prompt_and_cancels_remainder(self):
        radio = FakeRadio(blocked=True)
        m, s = self.start_sender(radio)
        s.set_enabled(True)
        self.assertTrue(radio.entered.wait(2))
        start = time.monotonic()
        s.set_enabled(False)
        m.publish('dht', 'Live', temperature_c=31)
        self.assertEqual(m.snapshot()['sensors']['dht']['values']['temperature_c'], 31)
        self.assertLess(time.monotonic()-start, .15)
        radio.release.set()
        self.assertTrue(radio.closed.wait(2))
        self.assertEqual(len(radio.frames), 1)
        self.assertEqual(s.status()['snapshots_acked'], 0)

    def test_success_requires_every_fragment_ack(self):
        radio = FakeRadio()
        m, s = self.start_sender(radio)
        s.set_enabled(True)
        self.assertTrue(until(lambda: s.status()['snapshots_acked'] == 1))
        s.set_enabled(False)
        result = decode_fixture(radio.frames)
        self.assertEqual(result['sensors']['dht']['values']['humidity_percent'], 64.3)
        self.assertEqual(s.status()['frames_acked'], len(radio.frames))

    def test_disconnect_reports_error_without_stopping_acquisition(self):
        radio = FakeRadio(fail=True)
        m, s = self.start_sender(radio)
        s.set_enabled(True)
        self.assertTrue(until(lambda: s.status()['failures'] == 1))
        self.assertIn('unplugged', s.status()['last_error'])
        self.assertEqual(s.status()['snapshots_acked'], 0)
        self.assertTrue(radio.closed.wait(2))
        m.publish('bmp', 'Live', pressure_hpa=1010)
        self.assertEqual(m.snapshot()['sensors']['bmp']['values']['pressure_hpa'], 1010)
        s.set_enabled(False)

    def test_on_after_failure_reconnects_without_an_old_queue(self):
        radio = FakeRadio(fail=True)
        m, s = self.start_sender(radio)
        s.set_enabled(True)
        self.assertTrue(until(lambda: s.status()['failures'] == 1))
        self.assertTrue(radio.closed.wait(2))
        s.set_enabled(False)
        radio.fail = False
        radio.frames.clear()
        m.publish('dht', 'Live', temperature_c=35)
        s.set_enabled(True)
        self.assertTrue(until(lambda: s.status()['snapshots_acked'] == 1))
        s.set_enabled(False)
        self.assertEqual(decode_fixture(radio.frames)['sensors']['dht']['values']['temperature_c'], 35)
        self.assertGreaterEqual(s._connect.call_count, 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
