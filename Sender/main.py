#!/usr/bin/env python3
"""Immortals live sensor dashboard for Raspberry Pi 5.

Run: python main.py
One self-contained application with an independently controlled Zigbee sender.
"""
import argparse
import copy
import fcntl
import json
import logging
from logging.handlers import RotatingFileHandler
import math
import multiprocessing
import os
from pathlib import Path
import signal
import struct
import queue
import sys
import threading
import time
import zlib
from datetime import datetime, timezone
from collections import deque

BASE = Path(__file__).resolve().parent
# Prefer the project environment even when launched with system Python/Thonny.
ENV_PYTHON = BASE / '.venv/bin/python'
if __name__ == '__main__' and ENV_PYTHON.exists() and Path(sys.prefix) != BASE / '.venv':
    os.execv(str(ENV_PYTHON), [str(ENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])

import smbus2
import numpy as np
from scipy.signal import butter, sosfiltfilt, find_peaks, detrend, iirnotch, filtfilt

BUS_NO = 1
ADS_ADDR, MAX_ADDR, BMP_ADDR, MLX_ADDR = 0x48, 0x57, 0x77, 0x5A

def s16(bus, addr, reg):
    b = bus.read_i2c_block_data(addr, reg, 2)
    n = (b[0] << 8) | b[1]
    return n - 65536 if n > 32767 else n

def u16(bus, addr, reg):
    b = bus.read_i2c_block_data(addr, reg, 2)
    return (b[0] << 8) | b[1]

class BMP180:
    def __init__(self, bus, addr=0x77, oss=1):
        self.b, self.a, self.oss = bus, addr, oss
        self.ac1=s16(bus,addr,0xAA); self.ac2=s16(bus,addr,0xAC)
        self.ac3=s16(bus,addr,0xAE); self.ac4=u16(bus,addr,0xB0)
        self.ac5=u16(bus,addr,0xB2); self.ac6=u16(bus,addr,0xB4)
        self.b1=s16(bus,addr,0xB6); self.b2=s16(bus,addr,0xB8)
        self.mc=s16(bus,addr,0xBC); self.md=s16(bus,addr,0xBE)
    def read(self):
        b,a,o=self.b,self.a,self.oss
        b.write_byte_data(a,0xF4,0x2E); time.sleep(.005)
        d=b.read_i2c_block_data(a,0xF6,2); ut=(d[0]<<8)|d[1]
        x1=((ut-self.ac6)*self.ac5)>>15
        den=x1+self.md
        if den == 0: raise RuntimeError("BMP180 compensation error")
        x2=(self.mc<<11)//den; b5=x1+x2
        temp=((b5+8)>>4)/10.0
        b.write_byte_data(a,0xF4,0x34+(o<<6))
        time.sleep([.005,.008,.014,.026][o])
        d=b.read_i2c_block_data(a,0xF6,3)
        up=((d[0]<<16)|(d[1]<<8)|d[2])>>(8-o)
        b6=b5-4000
        x1=(self.b2*((b6*b6)>>12))>>11; x2=(self.ac2*b6)>>11
        x3=x1+x2; b3=(((self.ac1*4+x3)<<o)+2)>>2
        x1=(self.ac3*b6)>>13; x2=(self.b1*((b6*b6)>>12))>>16
        x3=(x1+x2+2)>>2; b4=(self.ac4*(x3+32768))>>15
        if not b4: raise RuntimeError("BMP180 pressure divisor is zero")
        b7=(up-b3)*(50000>>o)
        p=(b7*2)//b4 if b7 < 0x80000000 else (b7//b4)*2
        x1=(p>>8)*(p>>8); x1=(x1*3038)>>16; x2=(-7357*p)>>16
        p=p+((x1+x2+3791)>>4)
        return temp,p



def empty_result(status):
    return dict(heart_rate_bpm=None, spo2_percent=None, perfusion_percent=None,
                quality_percent=0, status=status, spo2_status=status)


def estimate_pulse(red, ir, sample_rate=25):
    red, ir = np.asarray(red, dtype=float), np.asarray(ir, dtype=float)
    if len(red) != len(ir) or len(ir) < sample_rate * 8:
        return empty_result("Hold still - collecting 8 seconds")
    if not np.isfinite(red).all() or not np.isfinite(ir).all():
        return empty_result("Invalid optical samples")
    if min(np.median(ir[-sample_rate:]), np.median(red[-sample_rate:])) < 10000:
        return empty_result("Place finger on pulse sensor")
    if max(np.max(red), np.max(ir)) >= 260000:
        return empty_result("Signal saturated - ease finger pressure")
    # A finger transition or large baseline wander must not become a pulse.
    if any(np.ptp(x) / np.mean(x) > .25 for x in (red, ir)):
        return empty_result("Movement detected - hold still")
    filt = butter(3, [.5, 4.0], btype="bandpass", fs=sample_rate, output="sos")
    ac_red = sosfiltfilt(filt, detrend(red))
    ac_ir = sosfiltfilt(filt, detrend(ir))
    # Ignore filter edge transients for amplitude and period measurements.
    margin = int(sample_rate * .5)
    r, x = ac_red[margin:-margin], ac_ir[margin:-margin]
    rms_ir = float(np.sqrt(np.mean(x*x)))
    rms_red = float(np.sqrt(np.mean(r*r)))
    dc_red, dc_ir = float(np.mean(red)), float(np.mean(ir))
    perfusion = 100 * rms_ir / dc_ir
    if perfusion < .03 or rms_red / dc_red < .00015:
        return empty_result("Weak pulse - adjust finger gently")
    corr = float(np.corrcoef(r, x)[0, 1])
    if not np.isfinite(corr) or corr < .80:
        return empty_result("Unstable optical signal - hold still")
    # Autocorrelation identifies a repeat period; choose the earliest strong
    # local maximum, avoiding half-rate readings at multiples of the period.
    lo, hi = int(sample_rate * 60 / 220), math.ceil(sample_rate * 60 / 40)+1
    lags = np.arange(lo, hi + 1)
    scores = np.array([np.dot(x[:-lag], x[lag:]) /
                       max(1e-12, np.linalg.norm(x[:-lag])*np.linalg.norm(x[lag:]))
                       for lag in lags])
    candidates = [i for i in range(1, len(scores)-1)
                  if scores[i] > scores[i-1] and scores[i] >= scores[i+1]]
    if not candidates:
        return empty_result("No consistent pulse - hold still")
    best = max(scores[i] for i in candidates)
    usable = [i for i in candidates if scores[i] >= max(.70, best*.9)]
    if not usable:
        return empty_result("No consistent pulse - hold still")
    k = usable[0]
    lag = float(lags[k])
    den = scores[k-1] - 2*scores[k] + scores[k+1]
    if abs(den) > 1e-9:
        lag += .5 * (scores[k-1] - scores[k+1]) / den
    periodicity = float(scores[k])
    # Require actual repeat peaks to agree with the autocorrelation estimate.
    peaks, _ = find_peaks(x, distance=max(1, int(.65*lag)),
                          prominence=max(10, rms_ir*.65))
    if len(peaks) < 4:
        return empty_result("Need more clear beats - hold still")
    intervals = np.diff(peaks)
    beat_period = float(np.median(intervals))
    if (abs(beat_period-lag)/lag > .15 or np.std(intervals)/np.mean(intervals) > .18
            or len(x)-peaks[-1] > lag*1.6):
        return empty_result("Irregular or moving signal - hold still")
    bpm = 60 * sample_rate / lag
    if not 40 <= round(bpm) <= 220:
        return empty_result("Pulse outside supported range")
    # Reject sudden loss of pulsation in the newest second, even if older
    # samples still contain a convincing rhythm.
    tail = detrend(ir[-2*sample_rate:])
    if np.std(tail) < rms_ir*.25:
        return empty_result("Pulse lost - reposition finger")
    ratio = (rms_red / dc_red) / (rms_ir / dc_ir)
    spo2 = -45.060 * ratio**2 + 30.354 * ratio + 94.845
    valid_spo2 = .4 <= ratio <= 1.4 and 70 <= spo2 <= 100
    return dict(heart_rate_bpm=round(bpm, 1),
                spo2_percent=round(spo2, 1) if valid_spo2 else None,
                perfusion_percent=round(perfusion, 2),
                quality_percent=round(100 * min(corr, periodicity)),
                status="Pulse detected", ratio=round(ratio, 4),
                spo2_status="Estimated blood oxygen" if valid_spo2
                else "SpO2 outside estimation range")


class PulseWindow:
    """A gap or loss of contact clears the entire calculation window."""
    def __init__(self, sample_rate=25):
        self.sample_rate = sample_rate
        self.red = deque(maxlen=sample_rate*8)
        self.ir = deque(maxlen=sample_rate*8)
        self.last_time = None

    def clear(self):
        self.red.clear()
        self.ir.clear()
        self.last_time = None

    def add(self, samples, now):
        if self.last_time is not None and now-self.last_time > .4:
            self.clear()
        if samples:
            self.last_time = now
        for red, ir in samples:
            if min(red, ir) < 10000 or max(red, ir) >= 260000:
                self.clear()
            else:
                self.red.append(red)
                self.ir.append(ir)

    def result(self):
        if not self.ir:
            return empty_result("Place finger on pulse sensor")
        return estimate_pulse(self.red, self.ir, self.sample_rate)


class MAX30102:
    """25 Hz FIFO output: 100 Hz conversions averaged in groups of four."""
    sample_rate = 25

    def __init__(self, bus, addr=MAX_ADDR):
        self.b, self.a = bus, addr
        if bus.read_byte_data(addr, 0xFF) != 0x15:
            raise RuntimeError("Unexpected MAX30102 identity")
        bus.write_byte_data(addr, 0x09, 0x40)
        deadline = time.monotonic() + .5
        while bus.read_byte_data(addr, 0x09) & 0x40:
            if time.monotonic() > deadline:
                raise RuntimeError("MAX30102 reset timed out")
            time.sleep(.01)
        for reg, value in [(0x02, 0), (0x03, 0), (0x08, 0x4F),
                           (0x0A, 0x27), (0x0C, 0x24), (0x0D, 0x24)]:
            bus.write_byte_data(addr, reg, value)
        self.clear_fifo()
        bus.write_byte_data(addr, 0x09, 0x03)

    def clear_fifo(self):
        for reg in (0x04, 0x05, 0x06):
            self.b.write_byte_data(self.a, reg, 0)

    def read_samples(self):
        # Read all pairs with a combined I2C transaction, retaining every sample.
        wr = self.b.read_byte_data(self.a, 0x04) & 31
        overflow = self.b.read_byte_data(self.a, 0x05) & 31
        rd = self.b.read_byte_data(self.a, 0x06) & 31
        if overflow:
            self.clear_fifo()
            raise BufferError("Pulse FIFO overflow - collecting again")
        count = (wr-rd) & 31
        if not count:
            return []
        request = smbus2.i2c_msg.write(self.a, [0x07])
        response = smbus2.i2c_msg.read(self.a, count*6)
        self.b.i2c_rdwr(request, response)
        data = list(response)
        return [(((data[i] << 16) | (data[i+1] << 8) | data[i+2]) & 0x3FFFF,
                 ((data[i+3] << 16) | (data[i+4] << 8) | data[i+5]) & 0x3FFFF)
                for i in range(0, len(data), 6)]

    def close(self):
        self.b.write_byte_data(self.a, 0x09, 0x80)


def ecg_signal_status(values):
    """Describe electrode input quality without inferring a cardiac diagnosis."""
    if len(values) < 50:
        return 'Checking ECG electrode signal'
    values = np.asarray(values)
    rails = float(np.mean((values < .03) | (values > 3.23)))
    if rails > .15:
        return 'Input at rail - check cable and electrodes'
    if np.std(values) < .002:
        return 'ECG signal too weak - check electrode contact'
    if np.std(values) > .65:
        return 'Movement or noise - check electrode contact'
    return 'ECG input active - verify electrode contact'


def filtered_ecg(trace):
    """Resample timestamps; remove 50 Hz pickup and baseline for a display ECG.

    Values remain volts at the AD8232 output, not calibrated skin ECG voltage.
    """
    data = np.asarray(trace, dtype=float)
    if len(data) < 80 or not np.isfinite(data).all():
        return None
    data = data[data[:, 0] >= data[-1, 0]-8]
    times, values = data[:, 0], data[:, 1]
    if np.any(np.diff(times) <= 0) or np.max(np.diff(times)) > .10:
        return None
    grid = np.arange(max(times[0], times[-1]-8), times[-1], 1/125)
    if len(grid) < 80:
        return None
    raw = np.interp(grid, times, values)
    b, a = iirnotch(50, 30, fs=125)
    clean = filtfilt(b, a, raw)
    clean = sosfiltfilt(butter(3, [.5, 35], fs=125, btype='bandpass', output='sos'), clean)
    return grid, clean, raw


def estimate_ecg(trace):
    """QRS-energy / RR-interval estimate with explicit invalid-signal handling."""
    candidate = None
    def unavailable(status):
        return dict(heart_rate_bpm=None, candidate_bpm=candidate, quality_percent=0, status=status)
    if len(trace) < 100 or trace[-1][0]-trace[0][0] < 7.5:
        return unavailable('Collecting 8 seconds of ECG')
    conditioned = filtered_ecg(trace)
    if conditioned is None:
        return unavailable('ECG sampling interrupted - collecting again')
    times, clean, raw = conditioned
    input_status = ecg_signal_status(raw)
    input_warning = input_status if 'active' not in input_status else None
    # A provisional peak rate may be displayed on request, but remains separate
    # from a qualified heart-rate value if clipping or noise invalidates it.
    if np.mean((raw < .03) | (raw > 3.23)) > .02:
        input_warning = 'ECG clipping - check electrode contact'
    qrs = sosfiltfilt(butter(3, [5, 20], fs=125, btype='bandpass', output='sos'), clean)
    slope = np.diff(qrs, prepend=qrs[0])
    energy = np.convolve(slope*slope, np.ones(13)/13, mode='same')
    # At a fast rate QRS complexes occupy too much of the window for its
    # median to represent background noise. Use the quieter lower percentile.
    floor = float(np.percentile(energy, 20))
    prominence = max(1e-8, float(np.percentile(energy, 95))*.25, floor*5)
    peaks, _ = find_peaks(energy, distance=34, prominence=prominence,
                          height=floor+prominence, width=(4, 32))
    # Discard filter edges and require a visible QRS, not residual filter noise.
    peaks = np.array([p for p in peaks if 32 < p < len(qrs)-32
                      and np.ptp(qrs[p-12:p+13]) >= .025], dtype=int)
    if len(peaks) < 4:
        return unavailable(input_warning or 'No clear ECG beats - check electrodes')
    rr = np.diff(peaks)/125
    median_rr = float(np.median(rr))
    bpm = 60/float(np.mean(rr))
    if 40 <= round(bpm) <= 220:
        candidate = round(bpm, 1)
    if input_warning:
        return unavailable(input_warning)
    if (not 40 <= round(bpm) <= 220 or np.std(rr)/np.mean(rr) > .18
            or np.mean(np.abs(rr-median_rr) <= median_rr*.2) < .8
            or (len(qrs)-peaks[-1])/125 > median_rr*1.8):
        return unavailable('Unstable ECG beats - rest still')
    # Repeated beat morphology must agree; random spikes are not heartbeats.
    segments = np.array([qrs[p-15:p+16] for p in peaks])
    template = np.median(segments, axis=0)
    similarities = [np.corrcoef(segment, template)[0, 1] for segment in segments]
    similarity = float(np.median(similarities))
    if not np.isfinite(similarity) or similarity < .75:
        return unavailable('Noisy ECG - check electrode contact')
    # Require most QRS-band energy to be concentrated around detected beats.
    mask = np.zeros(len(qrs), dtype=bool)
    for p in peaks:
        mask[p-16:p+17] = True
    concentration = float(np.sum(qrs[mask]**2)/max(1e-12, np.sum(qrs**2)))
    if concentration < .60:
        return unavailable('ECG noise exceeds beat signal')
    return dict(heart_rate_bpm=round(bpm, 1), candidate_bpm=round(bpm, 1),
                quality_percent=round(100*min(similarity, 1-np.std(rr)/np.mean(rr))),
                status='ECG beats detected')


def dht_process_reader(output, stop):
    """DHT bit-banging runs outside the ECG process and its Python GIL."""
    def send(kind, value):
        try:
            output.put_nowait((kind, value))
        except queue.Full:
            pass
    while not stop.is_set():
        sensor = None
        try:
            import board
            import adafruit_dht
            sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
            while not stop.is_set():
                try:
                    temperature, humidity = sensor.temperature, sensor.humidity
                    if temperature is None or humidity is None:
                        raise RuntimeError('No DHT22 reading')
                    if not (-40 <= temperature <= 80 and 0 <= humidity <= 100):
                        raise ValueError('DHT22 reading out of range')
                    send('reading', dict(temperature_c=temperature, humidity_percent=humidity))
                except RuntimeError as exc:
                    send('retry', f'DHT22 retrying: {exc}')
                    if 'busy' in str(exc).lower():
                        raise
                stop.wait(2.2)
        except Exception as exc:
            send('error', f'DHT22 unavailable: {exc}')
            stop.wait(3)
        finally:
            if sensor is not None:
                try:
                    sensor.exit()
                except Exception:
                    pass


ZIGBEE_HEADER = struct.Struct('!2sBBIIHHI')
ZIGBEE_FIELDS = ('heart_rate_bpm', 'spo2_percent', 'perfusion_percent', 'quality_percent',
                 'spo2_status', 'sample_count', 'fifo_overflows', 'sample_rate_hz',
                 'voltage_v', 'voltage_min_v', 'voltage_max_v', 'rail_percent',
                 'candidate_bpm', 'max_sample_gap_ms', 'temperature_c', 'pressure_hpa',
                 'ambient_c', 'object_c', 'humidity_percent')
ZIGBEE_DEFAULTS = dict(
    port='/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0',
    baud_rate=115200, receiver_address='0013A200408DF0CE',
    sender_address='0013A200408DF0F0', interval_seconds=.2,
    acknowledgement_timeout_seconds=2, max_packet_bytes=84,
    live_window_seconds=.5)


def zigbee_config():
    config = dict(ZIGBEE_DEFAULTS)
    path = BASE/'zigbee_config.json'
    if path.exists():
        config.update(json.loads(path.read_text()))
    for key in ('receiver_address', 'sender_address'):
        value = config[key]
        if not isinstance(value, str) or len(value) != 16:
            raise ValueError(f'{key} must be a 16-digit XBee address')
        int(value, 16)
        config[key] = value.upper()
    if config['receiver_address'] in ('000000000000FFFF', '0000000000000000', config['sender_address']):
        raise ValueError('Configure a distinct unicast receiver address')
    if not isinstance(config['port'], str) or not config['port'].startswith('/dev/'):
        raise ValueError('Zigbee port must be a /dev/ serial path')
    for key, low, high in (('interval_seconds', .05, 60),
                           ('live_window_seconds', .1, 1),
                           ('acknowledgement_timeout_seconds', 1, 3),
                           ('max_packet_bytes', 64, 255), ('baud_rate', 9600, 115200)):
        value = config[key]
        if not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'Invalid Zigbee {key}')
    if int(config['max_packet_bytes']) != config['max_packet_bytes'] or int(config['baud_rate']) != config['baud_rate']:
        raise ValueError('Packet size and baud rate must be integers')
    return config


def zigbee_message(snapshot, sender_id, session, sequence, captured_mono):
    """Values match the dashboard; graphs are bounded eight-second snapshots."""
    result = {k: copy.deepcopy(snapshot[k]) for k in ('timestamp', 'sensors', 'ecg_enabled')}
    result.update(schema_version=1, message_type='sensor_snapshot', sender_id=sender_id,
                  session_id=f'{session:08x}', sequence=sequence,
                  units=dict(heart_rate_bpm='bpm', candidate_bpm='bpm (unreliable)',
                             spo2_percent='%', perfusion_percent='%', quality_percent='%',
                             temperature_c='degC', ambient_c='degC', object_c='degC',
                             humidity_percent='%RH', pressure_hpa='hPa', voltage_v='V',
                             voltage_min_v='V', voltage_max_v='V', rail_percent='%',
                             max_sample_gap_ms='ms', age_seconds='s', sample_rate_hz='Hz',
                             sample_count='count', fifo_overflows='count'))
    waveforms = {}
    for name in ('pulse', 'ecg'):
        points = [(t, v) for t, v in snapshot.get(name+'_trace', [])
                  if captured_mono-8 <= t <= captured_mono]
        wave = dict(unit='mV at ADC' if name == 'ecg' else 'relative IR counts',
                    time_offset_ms=[], values=[], status='No fresh waveform')
        if (len(points) >= 4 and captured_mono-points[-1][0] < 1
                and snapshot['sensors'][name]['values']
                and (name != 'ecg' or snapshot['ecg_enabled'])):
            times = np.array([t for t, _ in points])
            values = np.array([v for _, v in points])
            if name == 'ecg':
                conditioned = filtered_ecg(points)
                if conditioned is None:
                    wave['status'] = 'Collecting ECG waveform'
                    waveforms[name] = wave
                    continue
                times, values, _ = conditioned
                values = values*1000
            else:
                values = detrend(values)
            wave.update(time_offset_ms=[round((float(t)-captured_mono)*1000) for t in times],
                        values=[round(float(v), 2) for v in values],
                        status=snapshot['sensors'][name]['status'])
        waveforms[name] = wave
    result['waveforms'] = waveforms
    return result


def zigbee_frames(message, session, sequence, max_packet_bytes):
    # v2 eliminates repeated envelope/unit labels, preserving all sensor fields.
    version = 2 if message.get('waveform_mode') == 'append' else 1
    content = message
    if version == 2:
        content = [message['timestamp'], message['ecg_enabled'],
                   [[message['sensors'][name]['status'], message['sensors'][name]['age_seconds'],
                     {('#'+str(ZIGBEE_FIELDS.index(key)) if key in ZIGBEE_FIELDS else key): value
                      for key, value in message['sensors'][name]['values'].items()}]
                    for name in ('pulse', 'ecg', 'bmp', 'mlx', 'dht')],
                   [[message['waveforms'][name][key] for key in
                     ('status', 'clear', 'time_offset_ms', 'values')]
                    for name in ('pulse', 'ecg')]]
    raw = json.dumps(content, separators=(',', ':'), allow_nan=False).encode('utf-8')
    compressed = zlib.compress(raw)
    if len(compressed) > 65536:
        raise ValueError('Zigbee snapshot exceeds 64 KiB limit')
    size = int(max_packet_bytes)-ZIGBEE_HEADER.size
    if size < 1:
        raise ValueError('XBee payload capacity is too small')
    count = math.ceil(len(compressed)/size)
    crc = zlib.crc32(compressed)
    return [ZIGBEE_HEADER.pack(b'IM', version, 1, session, sequence, i, count, crc)
            + compressed[i*size:(i+1)*size] for i in range(count)]


def zigbee_live_message(snapshot, sender_id, session, sequence, captured_mono,
                        since=None, window=.5):
    message = zigbee_message(snapshot, sender_id, session, sequence, captured_mono)
    message['waveform_mode'] = 'append'
    cutoff = max(captured_mono-window, since if since is not None else captured_mono-window)
    for wave in message['waveforms'].values():
        wave['clear'] = not wave['values']
        points = [(t, v) for t, v in zip(wave['time_offset_ms'], wave['values'])
                  if captured_mono+t/1000 > cutoff]
        wave['time_offset_ms'] = [t for t, _ in points]
        wave['values'] = [v for _, v in points]
    return message


class ZigbeeSender:
    """Only this worker owns the radio. No backlog, UI waits or sensor locks."""
    def __init__(self, monitor):
        self.monitor = monitor
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.enabled = False
        self.generation = 0
        self.session = int.from_bytes(os.urandom(4), 'big')
        self.sequence = 0
        self.state = dict(status='OFF - no data sent', frames_acked=0, snapshots_acked=0,
                          failures=0, last_ack_timestamp=None, last_error=None,
                          receiver_address=ZIGBEE_DEFAULTS['receiver_address'])

    def status(self):
        with self.lock:
            result = dict(self.state, enabled=self.enabled)
        if not result['enabled']:
            result['status'] = 'OFF - no new data sent'
        return result

    def set_enabled(self, enabled):
        with self.lock:
            enabled = bool(enabled)
            if enabled == self.enabled:
                return
            self.enabled = enabled
            self.generation += 1
            self.state['status'] = 'Connecting' if enabled else 'OFF - no new data sent'
            self.state['last_error'] = None
        self.wake.set()
        logging.info('Zigbee sending %s', 'enabled' if enabled else 'disabled')

    def _active(self, generation):
        with self.lock:
            return self.enabled and generation == self.generation and not self.monitor.stop.is_set()

    def _update(self, generation, **changes):
        with self.lock:
            if generation == self.generation:
                self.state.update(changes)

    def _wait(self, seconds, generation):
        deadline = time.monotonic()+seconds
        while self._active(generation) and time.monotonic() < deadline:
            self.wake.wait(min(.2, max(0, deadline-time.monotonic())))
            self.wake.clear()

    def _connect(self, config):
        from digi.xbee.devices import XBeeDevice, RemoteXBeeDevice
        from digi.xbee.models.address import XBee64BitAddress
        device = XBeeDevice(config['port'], int(config['baud_rate']))
        device.set_sync_ops_timeout(config['acknowledgement_timeout_seconds'])
        device.serial_port.write_timeout = config['acknowledgement_timeout_seconds']
        try:
            device.open()
            sender_id = str(device.get_64bit_addr())
            if sender_id != config['sender_address']:
                raise RuntimeError(f'Unexpected sender radio {sender_id}')
            if int.from_bytes(device.get_parameter('AI'), 'big') != 0:
                raise RuntimeError('Zigbee radio has not joined the network')
            capacity = int.from_bytes(device.get_parameter('NP'), 'big')
            packet_bytes = min(int(config['max_packet_bytes']), capacity)
            if packet_bytes <= ZIGBEE_HEADER.size:
                raise RuntimeError('Radio payload capacity too small')
            receiver = RemoteXBeeDevice(device, XBee64BitAddress.from_hex_string(config['receiver_address']))
            return device, receiver, sender_id, packet_bytes
        except Exception:
            device.close()
            raise

    def run(self):
        device = None
        try:
            while not self.monitor.stop.is_set():
                if not self.status()['enabled']:
                    self.wake.wait(.2)
                    self.wake.clear()
                    continue
                with self.lock:
                    generation = self.generation
                try:
                    config = zigbee_config()
                    self._update(generation, status='Connecting', receiver_address=config['receiver_address'])
                    device, receiver, sender_id, capacity = self._connect(config)
                    self._update(generation, sender_address=sender_id, packet_bytes=capacity)
                    since = None
                    while self._active(generation):
                        started = time.monotonic()
                        snapshot = self.monitor.snapshot(traces=True)
                        captured = time.monotonic()
                        self.sequence = (self.sequence+1) & 0xffffffff
                        message = zigbee_live_message(snapshot, sender_id, self.session, self.sequence,
                                                      captured, since, config['live_window_seconds'])
                        frames = zigbee_frames(message, self.session, self.sequence, capacity)
                        self._update(generation, status='Sending', sequence=self.sequence, fragments=len(frames))
                        for frame in frames:
                            if not self._active(generation):
                                break
                            # A bounded unicast send waits for the radio delivery status,
                            # never for receiver software. OFF cancels remaining frames.
                            device.send_data(receiver, frame)
                            with self.lock:
                                self.state['frames_acked'] += 1
                        else:
                            # Advance only after successful delivery. Cap the next batch's
                            # history even after a stall, so old samples never build up.
                            since = captured
                            with self.lock:
                                self.state['snapshots_acked'] += 1
                                self.state['last_ack_timestamp'] = datetime.now(timezone.utc).isoformat()
                            self._update(generation, status='Radio delivery OK', last_error=None,
                                         last_send_seconds=round(time.monotonic()-started, 3))
                        self._wait(max(.005, config['interval_seconds']-(time.monotonic()-started)), generation)
                except Exception as exc:
                    detail = str(getattr(exc, 'status', '') or exc)
                    logging.warning('Zigbee: %s: %s', type(exc).__name__, detail)
                    with self.lock:
                        self.state['failures'] += 1
                    # Digi TransmitException's text omits the useful delivery status.
                    self._update(generation, status='Link error - retrying',
                                 last_error=f'{type(exc).__name__}: {detail}')
                finally:
                    if device is not None:
                        try:
                            device.close()
                        except Exception:
                            logging.exception('Cannot close Zigbee radio')
                        device = None
                self._wait(5, generation)
        finally:
            if device is not None:
                device.close()


class SensorMonitor:
    def __init__(self):
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.threads = []
        self.states = {name: dict(status="Starting", values={}, updated_mono=0.)
                       for name in ("pulse", "ecg", "bmp", "mlx", "dht")}
        self.pulse_trace = deque(maxlen=250)
        self.ecg_trace = deque(maxlen=1200)
        self.started = time.monotonic()
        self.zigbee = ZigbeeSender(self)
        self.ecg_enabled = True
        try:
            self.ecg_enabled = bool(json.loads((BASE/'settings.json').read_text()).get('ecg_enabled', False))
        except (OSError, ValueError):
            pass

    def publish(self, name, status, **values):
        with self.lock:
            prior = self.states[name]['status']
            self.states[name] = dict(status=status, values=values,
                                     updated_mono=time.monotonic())
        if prior != status:
            logging.info('%s: %s', name, status)

    def retry_status(self, name, status):
        # Keep the previous good value with its ORIGINAL timestamp. Snapshot
        # age limits still remove it if retries continue; never freshen old data.
        with self.lock:
            prior = self.states[name]['status']
            self.states[name]['status'] = status
        if prior != status:
            logging.info('%s: %s', name, status)

    def start(self):
        for name, target in [('pulse', self.pulse_worker), ('ecg', self.ecg_worker),
                             ('bmp', self.bmp_worker), ('mlx', self.mlx_worker),
                             ('dht', self.dht_worker), ('snapshot', self.snapshot_worker),
                             ('zigbee', self.zigbee.run)]:
            thread = threading.Thread(target=target, name=name, daemon=True)
            self.threads.append(thread)
            thread.start()

    def snapshot(self, traces=False):
        with self.lock:
            result = copy.deepcopy(self.states)
            if traces:
                pulse, ecg = list(self.pulse_trace), list(self.ecg_trace)
        now = time.monotonic()
        for name, state in result.items():
            age = now-state.pop('updated_mono')
            state['age_seconds'] = round(age, 2)
            if age > (7 if name == 'dht' else 3):
                state['values'] = {}
                state['status'] = 'Waiting for sensor' if now-self.started < 7 else 'Sensor data unavailable'
        snapshot = dict(schema_version=1, timestamp=datetime.now(timezone.utc).isoformat(),
                        sensors=result, ecg_enabled=self.ecg_enabled, zigbee=self.zigbee.status())
        if traces:
            snapshot.update(pulse_trace=pulse, ecg_trace=ecg)
        return snapshot

    def pulse_worker(self):
        while not self.stop.is_set():
            device = None
            try:
                with smbus2.SMBus(BUS_NO) as bus:
                    device = MAX30102(bus)
                    window = PulseWindow(device.sample_rate)
                    last_sample = time.monotonic()
                    last_calc = 0.
                    count = 0
                    overflows = 0
                    try:
                        while not self.stop.is_set():
                            now = time.monotonic()
                            try:
                                samples = device.read_samples()
                            except BufferError:
                                window.clear()
                                overflows += 1
                                self.publish('pulse', 'Sampling interrupted - hold still')
                                with self.lock:
                                    self.pulse_trace.clear()
                                continue
                            if samples:
                                count += len(samples)
                                last_sample = now
                                window.add(samples, now)
                                with self.lock:
                                    if not window.ir:
                                        self.pulse_trace.clear()
                                    else:
                                        for index, (_, ir) in enumerate(samples):
                                            self.pulse_trace.append((now-(len(samples)-1-index)/25, ir))
                                if now-last_calc >= .5 or not window.ir:
                                    reading = window.result()
                                    status = reading.pop('status')
                                    reading.update(sample_count=count, fifo_overflows=overflows,
                                                   sample_rate_hz=25)
                                    self.publish('pulse', status, **reading)
                                    last_calc = now
                            elif now-last_sample > 1:
                                raise RuntimeError('No pulse samples - check wiring')
                            self.stop.wait(.02)
                    finally:
                        device.close()
            except Exception as exc:
                self.publish('pulse', f'Pulse sensor unavailable: {exc}')
                with self.lock:
                    self.pulse_trace.clear()
                self.stop.wait(3)

    def ecg_worker(self):
        # ADS1115 A0, gain=1 (+/-4.096 V), continuous conversion at 250 SPS.
        # Poll at 125 Hz using real timestamps; this is a display trace, not a
        # diagnostic ECG recorder or a substitute pulse-rate calculation.
        while not self.stop.is_set():
            try:
                with smbus2.SMBus(BUS_NO) as bus:
                    bus.write_i2c_block_data(ADS_ADDR, 1, [0xC2, 0xA3])
                    self.stop.wait(.02)
                    last_publish = 0
                    recent = deque(maxlen=250)
                    last_estimate = 0
                    estimate = dict(heart_rate_bpm=None, quality_percent=0)
                    while not self.stop.is_set():
                        start = time.monotonic()
                        raw = s16(bus, ADS_ADDR, 0)
                        volts = raw * 4.096 / 32768
                        if not -.05 <= volts <= 3.4:
                            raise ValueError('ADC voltage out of expected 3.3 V range')
                        recent.append(volts)
                        with self.lock:
                            if self.ecg_enabled:
                                self.ecg_trace.append((start, volts))
                            else:
                                self.ecg_trace.clear()
                        if start-last_publish >= .2:
                            status = 'ECG monitoring off'
                            if self.ecg_enabled:
                                status = ecg_signal_status(recent)
                                if start-last_estimate >= 1:
                                    with self.lock:
                                        trace = list(self.ecg_trace)
                                    estimate = estimate_ecg(trace)
                                    last_estimate = start
                                if 'active' in status or status.startswith('Checking'):
                                    status = estimate.get('status', status)
                                else:
                                    estimate = dict(heart_rate_bpm=None, quality_percent=0,
                                                    candidate_bpm=estimate.get('candidate_bpm'))
                            else:
                                estimate = dict(heart_rate_bpm=None, quality_percent=0)
                            rail_percent = 100*sum(v < .03 or v > 3.23 for v in recent)/len(recent)
                            with self.lock:
                                timing = [t for t, _ in self.ecg_trace if t >= start-8]
                            max_gap = max((b-a for a,b in zip(timing,timing[1:])), default=0)
                            self.publish('ecg', status, voltage_v=round(volts, 4),
                                         voltage_min_v=round(min(recent), 4),
                                         voltage_max_v=round(max(recent), 4),
                                         rail_percent=round(rail_percent, 1),
                                         heart_rate_bpm=estimate['heart_rate_bpm'],
                                         candidate_bpm=estimate.get('candidate_bpm'),
                                         quality_percent=estimate['quality_percent'],
                                         max_sample_gap_ms=round(max_gap*1000, 1))
                            last_publish = start
                        self.stop.wait(max(0, .008-(time.monotonic()-start)))
            except Exception as exc:
                self.publish('ecg', f'ECG ADC unavailable: {exc}')
                with self.lock:
                    self.ecg_trace.clear()
                self.stop.wait(3)

    def bmp_worker(self):
        while not self.stop.is_set():
            try:
                with smbus2.SMBus(BUS_NO) as bus:
                    if bus.read_byte_data(BMP_ADDR, 0xD0) != 0x55:
                        raise RuntimeError('Unexpected BMP180 identity')
                    sensor = BMP180(bus)
                    while not self.stop.is_set():
                        temperature, pressure = sensor.read()
                        if not (-40 <= temperature <= 85 and 30000 <= pressure <= 110000):
                            raise ValueError('BMP180 reading out of range')
                        self.publish('bmp', 'Live', temperature_c=temperature, pressure_hpa=round(pressure/100, 2))
                        self.stop.wait(1)
            except Exception as exc:
                self.publish('bmp', f'Pressure sensor unavailable: {exc}')
                self.stop.wait(3)

    def mlx_worker(self):
        while not self.stop.is_set():
            try:
                with smbus2.SMBus(BUS_NO) as bus:
                    while not self.stop.is_set():
                        words = [bus.read_word_data(MLX_ADDR, r) for r in (0x06, 0x07)]
                        if any(w & 0x8000 for w in words):
                            raise ValueError('MLX90614 reports an invalid temperature')
                        ambient, surface = [round(w*.02-273.15, 2) for w in words]
                        if not (-40 <= ambient <= 125 and -70 <= surface <= 380):
                            raise ValueError('MLX90614 temperature out of range')
                        self.publish('mlx', 'Live', ambient_c=ambient, object_c=surface)
                        self.stop.wait(.5)
            except Exception as exc:
                self.publish('mlx', f'IR temperature unavailable: {exc}')
                self.stop.wait(3)

    def dht_worker(self):
        context = multiprocessing.get_context('spawn')
        while not self.stop.is_set():
            output = context.Queue(maxsize=4)
            stop = context.Event()
            process = context.Process(target=dht_process_reader, args=(output, stop), daemon=True)
            try:
                process.start()
                while not self.stop.is_set():
                    try:
                        kind, value = output.get(timeout=.2)
                    except queue.Empty:
                        if not process.is_alive():
                            raise RuntimeError('DHT reader exited')
                        continue
                    if kind == 'reading':
                        self.publish('dht', 'Live', **value)
                    elif kind == 'retry':
                        self.retry_status('dht', value)
                    else:
                        self.publish('dht', value)
            except Exception as exc:
                self.publish('dht', f'DHT22 unavailable: {exc}')
                self.stop.wait(3)
            finally:
                stop.set()
                if process.pid is not None:
                    process.join(2)
                    if process.is_alive():
                        process.terminate()
                        process.join(1)
                    process.close()
                output.close()
                output.join_thread()

    def snapshot_worker(self):
        while not self.stop.is_set():
            try:
                temporary = BASE/'latest_readings.tmp'
                temporary.write_text(json.dumps(self.snapshot(), indent=2, allow_nan=False), encoding='utf-8')
                temporary.replace(BASE/'latest_readings.json')
            except Exception:
                logging.exception('Cannot write readings snapshot')
            self.stop.wait(1)

    def close(self):
        self.zigbee.set_enabled(False)
        self.stop.set()
        deadline = time.monotonic()+5
        for thread in self.threads:
            thread.join(max(0, deadline-time.monotonic()))
        # No old numbers remain valid after shutdown, including future Zigbee readers.
        stopped = self.snapshot()
        for state in stopped['sensors'].values():
            state.update(status='Monitor stopped', values={})
        (BASE/'latest_readings.json').write_text(json.dumps(stopped, indent=2), encoding='utf-8')


class Dashboard:
    """Canvas UI designed for the connected 1024 x 600 HDMI display."""
    BG = '#0b1321'
    PANEL = '#142136'
    TEXT = '#edf5ff'
    MUTED = '#9aadc8'
    GREEN = '#54e3b0'
    BLUE = '#61baff'
    GOLD = '#ffcb78'
    # Display placeholders until the patient registration flow is implemented.
    PATIENT_NAME = 'Demo Patient'
    PATIENT_ID = 'DEMO-001'

    def __init__(self, monitor, fullscreen=True):
        import tkinter as tk
        self.tk, self.monitor = tk, monitor
        self.root = tk.Tk()
        self.root.title('Immortals | Patient Monitor')
        self.root.geometry('960x520+32+30')
        self.root.minsize(800, 480)
        self.root.configure(bg=self.BG)
        self.is_fullscreen = False
        self.set_fullscreen(fullscreen)
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.bind('<Escape>', lambda e: self.set_fullscreen(False))
        self.root.bind('<F11>', lambda e: self.fullscreen())
        self.root.bind('<Control-q>', lambda e: self.close())
        self.canvas = tk.Canvas(self.root, bg=self.BG, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Button-1>', self.click)
        self.sx = self.sy = 1
        self.frame = 0
        # A persistent control is not recreated with the live graphs. Handle
        # release once for both mouse clicks and touch-generated pointer events.
        self.zigbee_button = tk.Button(self.canvas, command=self.toggle_zigbee,
                                      bg=self.BG, activebackground=self.BG,
                                      borderwidth=0, highlightthickness=0, relief='flat',
                                      padx=0, pady=0, compound='center', cursor='hand2', takefocus=True)
        self.zigbee_button.bind('<Return>', self.toggle_zigbee)
        self._zigbee_style = None
        self.root.after(100, self.render)

    def text(self, x, y, text, size=12, color=None, weight='normal', anchor='nw', width=None):
        kwargs = dict(text=text, fill=color or self.TEXT, anchor=anchor,
                      font=('DejaVu Sans', max(8, round(size*min(self.sx, self.sy))), weight))
        if width:
            kwargs['width'] = width*self.sx
        return self.canvas.create_text(x*self.sx, y*self.sy, **kwargs)

    @staticmethod
    def rounded_shape(canvas, x, y, w, h, radius, color):
        r = min(radius, w/2, h/2)
        for cx, cy in ((x,y), (x+w-2*r,y), (x,y+h-2*r), (x+w-2*r,y+h-2*r)):
            canvas.create_oval(cx,cy,cx+2*r,cy+2*r,fill=color,outline='')
        canvas.create_rectangle(x+r,y,x+w-r,y+h,fill=color,outline='')
        return canvas.create_rectangle(x,y+r,x+w,y+h-r,fill=color,outline='')

    def rect(self, x, y, w, h, color=None, radius=16):
        return self.rounded_shape(self.canvas, x*self.sx, y*self.sy,
                                  w*self.sx, h*self.sy, radius*min(self.sx,self.sy),
                                  color or self.PANEL)

    def draw_zigbee_button(self):
        zigbee = self.monitor.zigbee.status()
        enabled = zigbee['enabled']
        error = enabled and zigbee['last_error'] is not None
        w, h = max(1,round(212*self.sx)), max(1,round(44*self.sy))
        self.zigbee_button.place(x=792*self.sx, y=548*self.sy, width=w, height=h)
        key = (w,h,enabled,error)
        if key == self._zigbee_style:
            return
        self._zigbee_style = key
        color = '#e6ac52' if error else ('#28bd8b' if enabled else '#314968')
        foreground = '#071c16' if enabled else self.TEXT
        self.zigbee_image = self.tk.PhotoImage(width=w,height=h)
        radius = h/2
        for row in range(h):
            inset = math.ceil(radius-math.sqrt(max(0,radius*radius-(row+.5-radius)**2)))
            self.zigbee_image.put(color,to=(inset,row,w-inset,row+1))
        size = max(8, round(11*min(self.sx,self.sy)))
        self.zigbee_button.configure(image=self.zigbee_image,
                                     text='Zigbee: '+('ON' if enabled else 'OFF'),
                                     foreground=foreground,activeforeground=foreground,
                                     font=('DejaVu Sans',size,'bold'))

    def toggle_zigbee(self, event=None):
        self.monitor.zigbee.set_enabled(not self.monitor.zigbee.status()['enabled'])
        self.draw_zigbee_button()
        return 'break'

    def line(self, points, color, width=1):
        if len(points) >= 4:
            self.canvas.create_line(*[v*(self.sx if i%2 == 0 else self.sy)
                                      for i,v in enumerate(points)], fill=color, width=width)

    @staticmethod
    def number(value, digits=1):
        return '--' if value is None else f'{value:.{digits}f}'

    def gauge(self, x, y, value, low, high, color, diameter=76):
        coords = (x*self.sx, y*self.sy, (x+diameter)*self.sx, (y+diameter)*self.sy)
        self.canvas.create_arc(*coords, start=225, extent=-270, style='arc', outline='#293c55', width=6)
        if value is not None:
            fraction = min(1, max(0, (value-low)/(high-low)))
            self.canvas.create_arc(*coords, start=225, extent=-270*fraction,
                                   style='arc', outline=color, width=6)
        self.text(x+diameter/2, y+diameter*.44, self.number(value, 0), 17, color, 'bold', anchor='center')
        self.text(x+diameter/2, y+diameter*.71, f'{low} - {high}', 8, self.MUTED, anchor='center')

    def small_card(self, y, title, value, unit, color):
        self.rect(892, y, 112, 86, radius=12)
        self.text(904, y+8, title, 8, self.MUTED, width=88)
        self.text(904, y+36, self.number(value), 17, color, 'bold')
        self.text(992, y+66, unit, 8, self.MUTED, anchor='ne')

    def graph(self, x, title, points, color, message='', volts=False):
        self.rect(x, 323, 410, 215)
        self.text(x+14, 333, title, 10, color, 'bold')
        left, top, width, height = x+14, 364, 382, 140
        for i in range(7):
            gx = left+i*width/6
            self.line([gx, top, gx, top+height], '#21324a')
        for i in range(5):
            gy = top+i*height/4
            self.line([left, gy, left+width, gy], '#21324a')
        now = time.monotonic()
        points = [(t, v) for t, v in points if now-8 <= t <= now]
        if len(points) >= 4 and now-points[-1][0] < 1:
            values = np.array([v for _, v in points])
            if volts:
                conditioned = filtered_ecg(points)
                if conditioned is None:
                    self.text(left+width/2, top+height/2, 'Collecting ECG waveform', 12,
                              self.MUTED, anchor='center')
                    return
                times, values, _ = conditioned
                points = list(zip(times, values))
                high = max(.05, float(np.max(np.abs(values)))*1.1)
                low = -high
            else:
                values = detrend(values)
                low, high = float(np.min(values)), float(np.max(values))
                padding = max(10, (high-low)*.1)
                low, high = low-padding, high+padding
            plot = []
            for (t, _), value in zip(points, values):
                px = left+width*(t-(now-8))/8
                py = top+height*(1-min(1, max(0, (value-low)/(high-low))))
                plot.extend([px, py])
            self.line(plot, color, 2)
            caption = f'8 s / filtered +/-{high*1000:.0f} mV at ADC | {message}' if volts else 'Relative pulse amplitude  |  8 seconds'
            self.text(left, 512, caption, 8, self.BLUE if volts and message == 'ECG beats detected'
                      else (self.GOLD if volts else self.MUTED), width=382)
        else:
            self.text(left+width/2, top+height/2, message or 'Waiting for signal', 12,
                      self.MUTED, anchor='center', width=352)

    def render(self):
        if self.monitor.stop.is_set():
            self.root.destroy()
            return
        self.sx = self.canvas.winfo_width()/1024
        self.sy = self.canvas.winfo_height()/600
        self.canvas.delete('all')
        data = self.monitor.snapshot(traces=True)
        states = data['sensors']
        p, d, b, m, e = [states[n]['values'] for n in ('pulse','dht','bmp','mlx','ecg')]
        bpm, ecg_bpm = p.get('heart_rate_bpm'), e.get('heart_rate_bpm')
        tentative_ecg = ecg_bpm is None and e.get('candidate_bpm') is not None
        if tentative_ecg:
            ecg_bpm = e['candidate_bpm']
        heart_status = states['pulse']['status']
        spo2 = p.get('spo2_percent')
        self.text(20, 15, 'IMMORTALS', 20, self.TEXT, 'bold')
        self.text(205, 23, 'LIVE PATIENT MONITOR', 10, self.MUTED)
        self.text(688, 24, datetime.now().strftime('%d %b  %H:%M:%S'), 10, self.MUTED)
        self.rect(861, 14, 95, 31, '#263b56')
        self.text(909, 29, 'Full screen', 9, anchor='center')
        self.rect(967, 14, 37, 31, '#513644')
        self.text(985, 29, 'X', 11, anchor='center')

        # Patient information stays in the top header; these are UI-only demos.
        self.rect(20, 58, 984, 66)
        self.text(36, 66, 'Patient Information', 11, self.TEXT, 'bold')
        self.rect(854, 65, 134, 22, '#3c3240', radius=11)
        self.text(921, 76, 'PLACEHOLDER', 8, self.GOLD, 'bold', anchor='center')
        self.text(36, 101, 'Name', 9, self.MUTED)
        self.text(88, 91, self.PATIENT_NAME, 19, self.TEXT, 'bold')
        self.text(380, 101, 'Patient ID', 9, self.MUTED)
        self.text(464, 91, self.PATIENT_ID, 19, self.BLUE, 'bold')
        self.text(688, 101, 'Age  --', 10, self.MUTED)
        self.text(804, 101, 'Sex  --', 10, self.MUTED)

        # Vitals occupy the main area; environment is a compact right-hand rail.
        self.text(20, 137, 'Patient Vitals', 12, self.GREEN, 'bold')
        for x in (20, 304, 588):
            self.rect(x, 164, 272, 146)
        self.text(36, 175, 'HEART RATE / MAX30102', 10, self.MUTED)
        self.text(36, 195, self.number(bpm, 0), 37, self.GREEN, 'bold')
        self.text(40, 251, 'beats / minute', 10, self.MUTED)
        self.gauge(198, 187, bpm, 40, 220, self.GREEN)
        self.text(36, 282, heart_status, 9, self.GREEN if bpm else self.GOLD, width=240)

        self.text(320, 175, 'BLOOD OXYGEN / SpO2', 10, self.MUTED)
        self.text(320, 195, self.number(spo2), 37, self.BLUE, 'bold')
        self.text(324, 251, '%  saturation estimate', 10, self.MUTED)
        self.gauge(482, 187, spo2, 70, 100, self.BLUE)
        self.text(320, 282, p.get('spo2_status', states['pulse']['status']), 9,
                  self.BLUE if spo2 else self.GOLD, width=240)

        surface = m.get('object_c')
        self.text(604, 175, 'BODY TEMPERATURE', 10, self.MUTED)
        self.text(604, 195, self.number(surface), 37, self.GOLD, 'bold')
        self.text(608, 251, 'C / infrared surface', 10, self.MUTED)
        self.gauge(766, 187, surface, 0, 50, self.GOLD)
        self.text(604, 282, 'MLX90614: measured surface' if m else states['mlx']['status'],
                  9, self.MUTED, width=240)

        quality = p.get('quality_percent', 0)
        self.graph(20, f'PULSE WAVE   |   Signal quality {quality}%', data['pulse_trace'], self.GREEN,
                   states['pulse']['status'])
        ecg_points = data['ecg_trace'] if self.monitor.ecg_enabled else []
        ecg_title = f'ECG  |  {"~" if tentative_ecg else ""}{self.number(ecg_bpm, 0)} bpm'
        if 'voltage_min_v' in e:
            low = round(e['voltage_min_v'], 2) or 0.
            high = round(e['voltage_max_v'], 2) or 0.
            ecg_title += f"  |  {low:.2f} to {high:.2f} V"
        ecg_status = ('UNRELIABLE: ' if tentative_ecg else '') + states['ecg']['status']
        self.graph(450, ecg_title, ecg_points, self.BLUE, ecg_status, volts=True)

        self.text(892, 130, 'Environmental\nData', 9, self.MUTED, 'bold', width=112)
        self.small_card(166, 'ROOM\nTEMPERATURE', d.get('temperature_c'), 'C', self.GREEN)
        self.small_card(260, 'RELATIVE\nHUMIDITY', d.get('humidity_percent'), '% RH', self.BLUE)
        self.small_card(354, 'AIR PRESSURE', b.get('pressure_hpa'), 'hPa', self.GOLD)
        self.small_card(448, 'BOARD\nTEMPERATURE', b.get('temperature_c'), 'C', self.TEXT)

        failed = [f'{n.upper()}: {s["status"]}' for n,s in states.items()
                  if n in ('bmp','mlx','dht') and s['status'] != 'Live']
        if states['dht']['status'] != 'Live' and d:
            failed = [f'DHT22 retrying | showing last valid reading ({states["dht"]["age_seconds"]:.0f} s old)']
        footer = failed[0] if failed else 'Sensors live  |  SpO2 is an uncalibrated estimate, not for diagnosis'
        self.text(20, 551, footer, 8, self.GOLD if failed else self.MUTED, width=750)
        self.text(20, 578, 'F11: full screen   |   Esc: window   |   Ctrl+Q: close', 8, self.MUTED)
        radio = data['zigbee']
        self.text(773, 578, radio['status'], 8,
                  self.GOLD if radio['enabled'] and radio['last_error'] else self.MUTED, anchor='ne')
        self.draw_zigbee_button()
        self.frame += 1
        self.root.after(200, self.render)

    def fullscreen(self):
        self.set_fullscreen(not self.is_fullscreen)

    def set_fullscreen(self, enabled):
        # Wayfire/XWayland can draw native fullscreen at (0,0) while retaining
        # an old X11 client origin (10,78), misrouting all touch/mouse clicks.
        # Use a borderless window with an explicit origin instead.
        self.is_fullscreen = bool(enabled)
        self.root.attributes('-fullscreen', False)
        # Keep the same borderless X11 surface in windowed mode too; toggling
        # window-manager decoration can restore the stale Wayfire client offset.
        self.root.overrideredirect(True)
        if self.is_fullscreen:
            self.root.geometry(f'{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0')
        else:
            self.root.geometry('960x520+32+30')
        self.root.after_idle(self.root.focus_force)

    def click(self, event):
        x, y = event.x/self.sx, event.y/self.sy
        if 967 <= x <= 1004 and 14 <= y <= 45:
            self.close()
        elif 861 <= x <= 956 and 14 <= y <= 45:
            self.fullscreen()

    def close(self):
        self.monitor.stop.set()

    def run(self):
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless', action='store_true', help='Hardware diagnostics without a window')
    parser.add_argument('--seconds', type=float, default=0, help='Stop a diagnostic run after N seconds')
    parser.add_argument('--windowed', action='store_true')
    parser.add_argument('--zigbee-on', action='store_true', help='Enable Zigbee at startup (default OFF)')
    args = parser.parse_args()
    (BASE/'logs').mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[RotatingFileHandler(BASE/'logs/monitor.log', maxBytes=512000, backupCount=2)])
    # A single hardware owner, including if a desktop icon is clicked twice.
    lock_path = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp'))/f'immortals-monitor-{os.getuid()}.lock'
    lock_file = lock_path.open('w')
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('Immortals Monitor is already running on the display.')
        return
    monitor = SensorMonitor()
    monitor.zigbee.set_enabled(args.zigbee_on)
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: monitor.stop.set())
    try:
        dashboard = None if args.headless else Dashboard(monitor, not args.windowed)
        monitor.start()
        if args.seconds > 0:
            timer = threading.Timer(args.seconds, monitor.stop.set)
            timer.daemon = True
            timer.start()
        if dashboard:
            dashboard.run()
        else:
            while not monitor.stop.wait(1):
                print(json.dumps(monitor.snapshot(), allow_nan=False), flush=True)
    finally:
        monitor.close()
        lock_file.close()
        logging.info('Monitor stopped cleanly')


if __name__ == '__main__':
    main()
