"""Deterministic acceptance checks; never substitutes for finger testing."""
import math
import unittest
from unittest.mock import patch
import numpy as np
import main as app


def ppg(bpm=75, ratio=.6, noise=0):
    t = np.arange(200)/25
    rng = np.random.default_rng(43)
    wave = np.sin(2*np.pi*bpm/60*t) + .15*np.sin(4*np.pi*bpm/60*t)
    ir = 90000+1500*wave+rng.normal(0, noise, len(t))
    red = 80000+1500*(80000/90000)*ratio*wave+rng.normal(0, noise, len(t))
    return red, ir


class PulseTests(unittest.TestCase):
    def test_known_rates_and_oxygen_ratio(self):
        expected = -45.060*.6**2+30.354*.6+94.845
        for bpm in (40, 42, 50, 60, 75, 100, 120, 160, 200, 220):
            with self.subTest(bpm=bpm):
                r = app.estimate_pulse(*ppg(bpm))
                self.assertIsNotNone(r['heart_rate_bpm'], r)
                self.assertAlmostEqual(r['heart_rate_bpm'], bpm, delta=2)
                self.assertAlmostEqual(r['spo2_percent'], expected, delta=.5)

    def test_small_noise(self):
        r = app.estimate_pulse(*ppg(noise=30))
        self.assertAlmostEqual(r['heart_rate_bpm'], 75, delta=2)
        self.assertIsNotNone(r['spo2_percent'])

    def test_no_finger_and_no_pulse(self):
        for value in (450, 90000):
            r = app.estimate_pulse(np.full(200, value), np.full(200, value))
            self.assertIsNone(r['heart_rate_bpm'])
            self.assertIsNone(r['spo2_percent'])

    def test_saturation_and_invalid_samples(self):
        for value in (262143, math.nan, math.inf):
            r = app.estimate_pulse(np.full(200, value), np.full(200, value))
            self.assertIsNone(r['heart_rate_bpm'])

    def test_unrelated_noise(self):
        rng = np.random.default_rng(4)
        r = app.estimate_pulse(80000+rng.normal(0,1000,200), 90000+rng.normal(0,1000,200))
        self.assertIsNone(r['heart_rate_bpm'])

    def test_moving_baseline(self):
        red,ir=ppg()
        ir[100:]+=40000
        red[100:]+=30000
        self.assertIsNone(app.estimate_pulse(red,ir)['heart_rate_bpm'])

    def test_spo2_out_of_range_is_not_clipped(self):
        r=app.estimate_pulse(*ppg(ratio=1.6))
        self.assertIsNotNone(r['heart_rate_bpm'])
        self.assertIsNone(r['spo2_percent'])

    def test_detachment_clears_immediately(self):
        w=app.PulseWindow()
        w.add(list(zip(*ppg())),1)
        self.assertIsNotNone(w.result()['heart_rate_bpm'])
        w.add([(450,450)],1.02)
        self.assertEqual(len(w.ir),0)
        self.assertIsNone(w.result()['spo2_percent'])

    def test_gap_requires_new_window(self):
        w=app.PulseWindow()
        w.add(list(zip(*ppg())),1)
        w.add([(80000,90000)],2)
        self.assertEqual(len(w.ir),1)
        self.assertIsNone(w.result()['heart_rate_bpm'])


class FakeMAXBus:
    def __init__(self):
        self.regs={0xff:0x15,4:0,5:0,6:0}
    def read_byte_data(self,a,r):
        return self.regs.get(r,0)
    def write_byte_data(self,a,r,v):
        self.regs[r]=0 if r==9 and v==0x40 else v
    def i2c_rdwr(self,w,r):
        import ctypes
        pairs=[(80001,90001),(80002,90002),(80003,90003)]
        data=b''.join(x.to_bytes(3,'big') for pair in pairs for x in pair)
        self.read_size=len(r)
        ctypes.memmove(r.buf,data,len(data))


class DriverTests(unittest.TestCase):
    def test_fifo_retains_all_pairs(self):
        b=FakeMAXBus()
        sensor=app.MAX30102(b)
        b.regs.update({4:2,6:31})
        self.assertEqual(sensor.read_samples(),[(80001,90001),(80002,90002),(80003,90003)])
        self.assertEqual(b.read_size,18)

    def test_overflow_resets_fifo(self):
        b=FakeMAXBus()
        sensor=app.MAX30102(b)
        b.regs[5]=1
        with self.assertRaises(BufferError): sensor.read_samples()
        self.assertEqual([b.regs[r] for r in (4,5,6)],[0,0,0])

    def test_bmp180_datasheet_compensation(self):
        sensor=app.BMP180.__new__(app.BMP180)
        params=dict(ac1=408,ac2=-72,ac3=-14383,ac4=32741,ac5=32757,ac6=23153,
                    b1=6190,b2=4,mc=-8711,md=2868,a=0x77,oss=0)
        sensor.__dict__.update(params)
        class Bus:
            def write_byte_data(self,*args): pass
            def read_i2c_block_data(self,a,r,n):
                value=27898 if n==2 else 23843<<8
                return list(value.to_bytes(n,'big'))
        sensor.b=Bus()
        with patch.object(app.time,'sleep'):
            temp,pressure=sensor.read()
        self.assertEqual(temp,15.)
        self.assertAlmostEqual(pressure,69964,delta=2)

    def test_stale_snapshot_removes_values(self):
        m=app.SensorMonitor()
        m.states['pulse']=dict(status='Pulse detected',values={'heart_rate_bpm':75},updated_mono=0)
        self.assertEqual(m.snapshot()['sensors']['pulse']['values'],{})

    def test_dht_retry_does_not_freshen_old_measurement(self):
        m=app.SensorMonitor()
        m.publish('dht','Live',temperature_c=28,humidity_percent=75)
        timestamp=m.states['dht']['updated_mono']
        m.retry_status('dht','DHT22 retrying')
        self.assertEqual(m.states['dht']['updated_mono'],timestamp)
        self.assertEqual(m.snapshot()['sensors']['dht']['values']['temperature_c'],28)
        m.states['dht']['updated_mono']-=8
        self.assertEqual(m.snapshot()['sensors']['dht']['values'],{})

    def test_ecg_rail_and_flat_input_are_not_called_active(self):
        self.assertIn('rail',app.ecg_signal_status([0.001]*250))
        self.assertIn('too weak',app.ecg_signal_status([1.65]*250))
        self.assertIn('active',app.ecg_signal_status(1.65+.1*np.sin(np.arange(250)/10)))


def ecg_fixture(bpm=75):
    t=np.arange(1250)/125
    signal=np.full(len(t),1.65)+.1*np.sin(2*np.pi*.15*t)+.08*np.sin(2*np.pi*50*t)
    for beat in np.arange(.5,10,60/bpm):
        for height,offset,width in [(1,0,.014),(-.2,-.025,.012),(-.3,.03,.016),(.15,.23,.06),(.07,-.18,.035)]:
            signal+=height*np.exp(-.5*((t-beat-offset)/width)**2)
    return list(zip(t,signal))


class ECGTests(unittest.TestCase):
    def test_qrs_rate_with_baseline_and_50hz_interference(self):
        for bpm in (40,50,60,75,100,150,200,220):
            with self.subTest(bpm=bpm):
                r=app.estimate_ecg(ecg_fixture(bpm))
                self.assertIsNotNone(r['heart_rate_bpm'],r)
                self.assertAlmostEqual(r['heart_rate_bpm'],bpm,delta=4)

    def test_flat_clipped_and_noise_are_unavailable(self):
        t=np.arange(1250)/125
        rng=np.random.default_rng(82)
        for v in (np.full(len(t),1.65),np.zeros(len(t)),1.65+.5*np.sin(2*np.pi*50*t),1.65+rng.normal(0,.25,len(t))):
            r=app.estimate_ecg(list(zip(t,v)))
            self.assertIsNone(r['heart_rate_bpm'],r)

    def test_missing_samples_cannot_produce_rate(self):
        trace=ecg_fixture()
        trace=trace[:600]+trace[640:]
        self.assertIsNone(app.estimate_ecg(trace)['heart_rate_bpm'])

    def test_filter_attenuates_50hz_without_inventing_beats(self):
        t=np.arange(1250)/125
        v=1.65+.3*np.sin(2*np.pi*50*t)
        _,filtered,_=app.filtered_ecg(list(zip(t,v)))
        self.assertLess(np.std(filtered[125:-125]),.005)

    def test_provisional_rate_never_becomes_a_qualified_clipped_reading(self):
        trace=ecg_fixture()
        trace=[(t,max(0,v-1.5)) for t,v in trace]
        r=app.estimate_ecg(trace)
        self.assertIsNone(r['heart_rate_bpm'])
        self.assertIn('clipping',r['status'])
        self.assertIsNotNone(r['candidate_bpm'])
        self.assertAlmostEqual(r['candidate_bpm'],75,delta=2)

    def test_flat_input_does_not_get_a_provisional_number(self):
        t=np.arange(1250)/125
        r=app.estimate_ecg(list(zip(t,np.full(len(t),1.65))))
        self.assertIsNone(r['candidate_bpm'])


if __name__=='__main__': unittest.main(verbosity=2)
