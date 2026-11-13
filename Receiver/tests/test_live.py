from datetime import timedelta
from pathlib import Path
import copy
import json
import struct
import tempfile
import unittest
import zlib
from test_receiver import app, fixture, SOURCE, NOW, decode


def live_frames(message, size=84):
    wire=[message['timestamp'],message['ecg_enabled'],
          [[message['sensors'][n]['status'],message['sensors'][n]['age_seconds'],
            {('#'+str(app.LIVE_FIELDS.index(k)) if k in app.LIVE_FIELDS else k):v
             for k,v in message['sensors'][n]['values'].items()}]
           for n in ('pulse','ecg','bmp','mlx','dht')],
          [[message['waveforms'][n][k] for k in ('status','clear','time_offset_ms','values')]
           for n in ('pulse','ecg')]]
    raw=zlib.compress(json.dumps(wire,separators=(',',':')).encode())
    chunks=[raw[i:i+size-20] for i in range(0,len(raw),size-20)]
    return [struct.pack('!2sBBIIHHI',b'IM',2,1,int(message['session_id'],16),message['sequence'],
                        i,len(chunks),zlib.crc32(raw))+chunk for i,chunk in enumerate(chunks)]


def live(sequence=1, at=NOW):
    m=fixture(sequence,captured=at)
    m['waveform_mode']='append'
    for wave in m['waveforms'].values():
        wave.update(clear=False,time_offset_ms=[-160,-120,-80,-40],values=[1,2,3,4])
    return m


class LiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.r=app.Receiver(dict(app.DEFAULTS),Path(self.temp.name))

    def accept(self,m,now=10):
        decoded=decode(app.Reassembler(SOURCE),live_frames(m))
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded['sensors'],m['sensors'])
        return self.r.accept(decoded,now=now,now_utc=app.timestamp(m['timestamp'])+timedelta(milliseconds=80))

    def test_v2_roundtrip_appends_history_without_repeating_eight_seconds(self):
        self.assertTrue(self.accept(live()))
        self.assertTrue(self.accept(live(2,NOW+timedelta(milliseconds=200)),10.2))
        wave=self.r.snapshot(10.2)['snapshot']['waveforms']['ecg']
        self.assertEqual(wave['values'],[1,2,3,4]*2)
        self.assertEqual(wave['time_offset_ms'],[-360,-320,-280,-240,-160,-120,-80,-40])
        self.assertEqual(self.r.snapshot(10.2)['receiver']['last_delivery_ms'],80)

    def test_clear_and_loss_do_not_draw_fabricated_continuous_trace(self):
        self.accept(live())
        m=live(2,NOW+timedelta(milliseconds=200))
        m['sensors']['pulse']['values']={}
        m['waveforms']['pulse'].update(clear=True,time_offset_ms=[],values=[])
        self.accept(m,10.2)
        self.assertFalse(self.r.snapshot(10.2)['snapshot']['waveforms']['pulse']['values'])
        self.accept(live(3,NOW+timedelta(seconds=2)),12)
        self.assertEqual(len(self.r.snapshot(12)['snapshot']['waveforms']['ecg']['values']),4)

    def test_stream_expires_quickly_then_recovers_and_retains_dht_sensor_age(self):
        self.accept(live())
        self.assertTrue(self.r.snapshot(10)['snapshot']['sensors']['dht']['values'])
        self.assertEqual(self.r.snapshot(13)['receiver']['state'],'stale')
        self.accept(live(2,NOW+timedelta(seconds=4)),14)
        self.assertEqual(self.r.snapshot(14)['receiver']['state'],'receiving')

    def test_restart_clears_old_history_and_corrupt_v2_never_publishes(self):
        self.accept(live())
        m=live(2,NOW+timedelta(milliseconds=200));m['session_id']='0000002b'
        self.accept(m,10.2)
        self.assertEqual(len(self.r.snapshot(10.2)['snapshot']['waveforms']['ecg']['values']),4)
        chunks=live_frames(live())
        chunks[-1]=chunks[-1][:-1]+bytes([chunks[-1][-1]^1])
        self.assertIsNone(decode(app.Reassembler(SOURCE),chunks))


if __name__=='__main__':unittest.main()
