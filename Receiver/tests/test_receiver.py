import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import random
import struct
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import urlopen
from urllib.error import HTTPError
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main as app

SOURCE = '0013A200408DF0F0'
NOW = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)


def fixture(sequence=1, session=42, captured=NOW):
    return dict(schema_version=1, message_type='sensor_snapshot', sender_id=SOURCE,
                session_id=f'{session:08x}', sequence=sequence, timestamp=captured.isoformat(),
                ecg_enabled=True, units={'temperature_c': 'degC', 'heart_rate_bpm': 'bpm'},
                sensors={
                    'pulse': dict(status='Pulse detected', age_seconds=.1,
                                  values=dict(heart_rate_bpm=78.2, spo2_percent=98.1, quality_percent=91)),
                    'ecg': dict(status='Noisy', age_seconds=.2,
                                values=dict(heart_rate_bpm=None, candidate_bpm=83.4, voltage_v=1.65)),
                    'bmp': dict(status='Live', age_seconds=.5, values=dict(pressure_hpa=1013.4, temperature_c=30.1)),
                    'mlx': dict(status='Live', age_seconds=.6, values=dict(ambient_c=29.1, object_c=28.9)),
                    'dht': dict(status='Retrying', age_seconds=4.3, values=dict(temperature_c=27.2, humidity_percent=62.1))},
                waveforms={name: dict(unit='mV at ADC' if name == 'ecg' else 'relative IR counts',
                                     status='Noisy' if name == 'ecg' else 'Pulse detected',
                                     time_offset_ms=list(range(-8000, 0, 8 if name == 'ecg' else 40)),
                                     values=[round(random.Random(i).uniform(-100, 100), 2)
                                             for i in range(1000 if name == 'ecg' else 200)])
                           for name in ('pulse','ecg')})


def frames(message, size=200, raw=None):
    packed = zlib.compress(json.dumps(message, separators=(',', ':')).encode()) if raw is None else raw
    step = size-20
    count = (len(packed)+step-1)//step
    return [struct.pack('!2sBBIIHHI', b'IM', 1, 1, int(message['session_id'], 16),
                        message['sequence'], i, count, zlib.crc32(packed)) + packed[i*step:(i+1)*step]
            for i in range(count)]


def decode(assembler, payloads):
    result = None
    for payload in payloads:
        result = assembler.feed(SOURCE, payload, now=10) or result
    return result


class AssemblyTests(unittest.TestCase):
    def test_real_schema_small_packets_shuffled_and_duplicate(self):
        message = fixture()
        for size in (64,84,200,255):
            a=app.Reassembler(SOURCE)
            packets=frames(message,size)
            random.Random(8).shuffle(packets)
            self.assertEqual(decode(a, packets+packets), message)
            self.assertEqual(a.stats['completed_messages'],1)
            self.assertEqual(len(a.pending),0)

    def test_loss_and_expiry_never_publish_partial_values(self):
        a=app.Reassembler(SOURCE,timeout=20)
        self.assertIsNone(decode(a,frames(fixture())[:-1]))
        a.expire(31)
        self.assertEqual(len(a.pending),0)
        self.assertEqual(a.stats['expired_assemblies'],1)

    def test_corrupt_payload_crc_is_rejected(self):
        packets=frames(fixture())
        packets[-1]=packets[-1][:-1]+bytes([packets[-1][-1]^1])
        a=app.Reassembler(SOURCE)
        self.assertIsNone(decode(a,packets))
        self.assertEqual(a.stats['invalid_frames'],1)

    def test_conflicting_duplicate_abandons_assembly(self):
        a=app.Reassembler(SOURCE)
        first=frames(fixture())[0]
        a.feed(SOURCE,first)
        a.feed(SOURCE,first[:-1]+bytes([first[-1]^1]))
        self.assertEqual(len(a.pending),0)
        self.assertEqual(a.stats['invalid_frames'],1)

    def test_unexpected_source_and_header(self):
        for sender,payload in [('0013A20000000000',frames(fixture())[0]), (SOURCE,b'hello'),
                               (SOURCE,b'XX'+frames(fixture())[0][2:]),
                               (SOURCE,frames(fixture())[0][:2]+b'\x03'+frames(fixture())[0][3:])]:
            a=app.Reassembler(SOURCE)
            self.assertIsNone(a.feed(sender,payload))
            self.assertEqual(a.stats['invalid_frames'],1)

    def test_memory_bounded_with_many_incomplete_messages(self):
        a=app.Reassembler(SOURCE)
        for seq in range(20):
            a.feed(SOURCE,frames(fixture(seq))[0],now=10)
        self.assertEqual(len(a.pending),4)
        self.assertEqual(a.stats['expired_assemblies'],16)

    def test_decompression_bomb_truncation_and_trailing_data(self):
        message=fixture()
        packed=zlib.compress(json.dumps(message).encode())
        for raw in (zlib.compress(b' '*300000),packed[:-1],packed+b'junk'):
            a=app.Reassembler(SOURCE)
            self.assertIsNone(decode(a,frames(message,raw=raw)))
            self.assertEqual(a.stats['invalid_frames'],1)

    def test_semantic_errors_do_not_reach_display(self):
        for modify in (
            lambda m:m.update(sender_id='0013A20000000000'),
            lambda m:m.update(timestamp='2026-11-11T12:00:00'),
            lambda m:m['sensors']['pulse']['values'].update(heart_rate_bpm=float('nan')),
            lambda m:m['sensors']['ecg'].update(age_seconds=-1),
            lambda m:m['waveforms']['ecg']['values'].pop(),
            lambda m:m['waveforms']['ecg']['time_offset_ms'].__setitem__(1,-8001),
            lambda m:m.update(ecg_enabled=False),
        ):
            m=fixture();modify(m);a=app.Reassembler(SOURCE)
            self.assertIsNone(decode(a,frames(m)))
            self.assertEqual(a.stats['invalid_frames'],1)


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.receiver=app.Receiver(dict(app.DEFAULTS,stale_after_seconds=30),Path(self.temp.name))

    def test_values_null_provisional_rates_and_original_packet_preserved(self):
        m=fixture()
        self.assertTrue(self.receiver.accept(m,now=100,now_utc=NOW+timedelta(seconds=.12)))
        value=self.receiver.snapshot(now=100.1)
        ecg=value['snapshot']['sensors']['ecg']['values']
        self.assertIsNone(ecg['heart_rate_bpm'])
        self.assertEqual(ecg['candidate_bpm'],83.4)
        self.assertEqual(value['snapshot']['sensors']['dht']['age_seconds'],4.52)
        self.assertEqual(self.receiver.latest,m)
        self.assertEqual(m['sensors']['dht']['age_seconds'],4.3)

    def test_stale_transport_clears_numbers_and_graphs(self):
        self.receiver.accept(fixture(),now=100,now_utc=NOW+timedelta(seconds=12))
        stale=self.receiver.snapshot(now=119)
        self.assertEqual(stale['receiver']['state'],'stale')
        self.assertTrue(all(not s['values'] for s in stale['snapshot']['sensors'].values()))
        self.assertTrue(all(not w['values'] for w in stale['snapshot']['waveforms'].values()))

    def test_age_of_sensor_itself_is_used(self):
        self.receiver.accept(fixture(),now=100,now_utc=NOW)
        state=self.receiver.snapshot(now=102.8)['snapshot']['sensors']
        self.assertTrue(state['pulse']['values'])
        self.assertFalse(state['dht']['values'])

    def test_initial_state_ignores_old_disk_packet(self):
        (Path(self.temp.name)/'last_packet.json').write_text(json.dumps(fixture()))
        state=self.receiver.snapshot()
        self.assertEqual(state['receiver']['state'],'waiting')
        self.assertIsNone(state['snapshot'])

    def test_old_or_future_capture_is_rejected(self):
        for age in (-10,31):
            self.assertFalse(self.receiver.accept(fixture(),now=100,now_utc=NOW+timedelta(seconds=age)))
        self.assertIsNone(self.receiver.latest)

    def test_reordering_duplicate_and_sequence_wrap(self):
        self.assertTrue(self.receiver.accept(fixture(0xffffffff),now=100,now_utc=NOW))
        self.assertTrue(self.receiver.accept(fixture(0),now=101,now_utc=NOW))
        self.assertFalse(self.receiver.accept(fixture(0),now=102,now_utc=NOW))
        self.assertFalse(self.receiver.accept(fixture(0xffffffff),now=102,now_utc=NOW))

    def test_sender_restart_retires_old_session(self):
        self.receiver.accept(fixture(100),now=100,now_utc=NOW)
        self.assertTrue(self.receiver.accept(fixture(1,43),now=101,now_utc=NOW))
        self.assertFalse(self.receiver.accept(fixture(101,42),now=102,now_utc=NOW))

    def test_new_data_recovers_after_stale(self):
        self.receiver.accept(fixture(),now=100,now_utc=NOW)
        self.assertEqual(self.receiver.snapshot(now=135)['receiver']['state'],'stale')
        self.receiver.accept(fixture(2,captured=NOW+timedelta(seconds=35)),now=135,now_utc=NOW+timedelta(seconds=35))
        self.assertEqual(self.receiver.snapshot(now=136)['receiver']['state'],'receiving')

    def test_stop_clears_output(self):
        self.receiver.accept(fixture(),now=100,now_utc=NOW)
        self.receiver.stop.set()
        value=self.receiver.snapshot(now=101)
        self.assertEqual(value['receiver']['state'],'stopped')
        self.assertFalse(value['snapshot']['sensors']['pulse']['values'])

    def test_http_dashboard_api_and_no_arbitrary_file_serving(self):
        server=app.ThreadingHTTPServer(('127.0.0.1',0),app.handler_for(self.receiver))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(url+'/') as response:
                self.assertIn(b'WIRELESS RECEIVER',response.read())
                self.assertEqual(response.headers['Cache-Control'],'no-store')
            with urlopen(url+'/api/readings') as response:
                self.assertEqual(json.load(response)['receiver']['state'],'waiting')
            with self.assertRaises(HTTPError):urlopen(url+'/receiver_config.json')
        finally:
            server.shutdown();server.server_close();thread.join(2)


if __name__=='__main__':unittest.main(verbosity=2)
