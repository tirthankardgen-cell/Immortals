#!/usr/bin/env python3
"""Immortals Zigbee receiver and read-only LAN dashboard. Run: python main.py."""
import argparse
import copy
from datetime import datetime, timezone
from collections import OrderedDict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from logging.handlers import RotatingFileHandler
import math
import os
from pathlib import Path
import signal
import struct
import sys
import threading
import time
import zlib

BASE = Path(__file__).resolve().parent
ENV_PYTHON = BASE/'.venv/bin/python'
if __name__ == '__main__' and ENV_PYTHON.exists() and Path(sys.prefix) != BASE/'.venv':
    os.execv(str(ENV_PYTHON), [str(ENV_PYTHON), str(BASE/'main.py'), *sys.argv[1:]])

HEADER = struct.Struct('!2sBBIIHHI')
MAX_COMPRESSED = 65536
MAX_JSON = 262144
SENSORS = ('pulse', 'ecg', 'bmp', 'mlx', 'dht')
LIVE_FIELDS = ('heart_rate_bpm', 'spo2_percent', 'perfusion_percent', 'quality_percent',
               'spo2_status', 'sample_count', 'fifo_overflows', 'sample_rate_hz',
               'voltage_v', 'voltage_min_v', 'voltage_max_v', 'rail_percent',
               'candidate_bpm', 'max_sample_gap_ms', 'temperature_c', 'pressure_hpa',
               'ambient_c', 'object_c', 'humidity_percent')
DEFAULTS = dict(
    port='/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0',
    baud_rate=115200, receiver_address='0013A200408DF0CE',
    sender_address='0013A200408DF0F0', bind_host='0.0.0.0', http_port=8080,
    stale_after_seconds=3, assembly_timeout_seconds=2)

UNITS = dict(heart_rate_bpm='bpm', candidate_bpm='bpm (unreliable)',
             spo2_percent='%', perfusion_percent='%', quality_percent='%',
             temperature_c='degC', ambient_c='degC', object_c='degC',
             humidity_percent='%RH', pressure_hpa='hPa', voltage_v='V',
             voltage_min_v='V', voltage_max_v='V', rail_percent='%',
             max_sample_gap_ms='ms', age_seconds='s', sample_rate_hz='Hz',
             sample_count='count', fifo_overflows='count')


def expand_live_message(wire, source, session, sequence):
    if not isinstance(wire, list) or len(wire) != 4:
        raise ValueError('Invalid live envelope')
    captured, enabled, states, waves = wire
    if not isinstance(states, list) or len(states) != 5 or not isinstance(waves, list) or len(waves) != 2:
        raise ValueError('Invalid live groups')
    sensors, waveforms = {}, {}
    for name, state in zip(SENSORS, states):
        if not isinstance(state, list) or len(state) != 3:
            raise ValueError('Invalid live sensor')
        sensors[name] = dict(zip(('status', 'age_seconds', 'values'), state))
        if not isinstance(state[2], dict):
            raise ValueError('Invalid live values')
        fields = {}
        for key, value in state[2].items():
            if key.startswith('#'):
                if not key[1:].isdigit() or not 0 <= int(key[1:]) < len(LIVE_FIELDS):
                    raise ValueError('Invalid compact measurement field')
                key = LIVE_FIELDS[int(key[1:])]
            if key in fields:
                raise ValueError('Duplicate measurement field')
            fields[key] = value
        sensors[name]['values'] = fields
    for name, wave in zip(('pulse', 'ecg'), waves):
        if not isinstance(wave, list) or len(wave) != 4 or not isinstance(wave[1], bool):
            raise ValueError('Invalid live waveform')
        waveforms[name] = dict(zip(('status', 'clear', 'time_offset_ms', 'values'), wave),
                              unit='mV at ADC' if name == 'ecg' else 'relative IR counts')
        if wave[1] and wave[3]:
            raise ValueError('Cleared waveform contains samples')
    return dict(schema_version=1, message_type='sensor_snapshot', sender_id=source,
                session_id=f'{session:08x}', sequence=sequence, timestamp=captured,
                ecg_enabled=enabled, units=dict(UNITS), sensors=sensors,
                waveforms=waveforms, waveform_mode='append')


def utc_now():
    return datetime.now(timezone.utc)


def atomic_json(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')), encoding='utf-8')
    temp.replace(path)


def configuration():
    config = dict(DEFAULTS)
    if (BASE/'receiver_config.json').exists():
        config.update(json.loads((BASE/'receiver_config.json').read_text()))
    for key in ('receiver_address', 'sender_address'):
        value = config[key]
        if not isinstance(value, str) or len(value) != 16:
            raise ValueError(f'{key} must be a 16-digit radio address')
        int(value, 16)
        config[key] = value.upper()
    if config['sender_address'] == config['receiver_address']:
        raise ValueError('Sender and receiver must be different radios')
    for key, low, high in (('baud_rate', 9600, 115200), ('http_port', 1024, 65535),
                           ('stale_after_seconds', 1, 120), ('assembly_timeout_seconds', .5, 120)):
        value = config[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'Invalid {key}')
    if not isinstance(config['http_port'], int) or not isinstance(config['baud_rate'], int):
        raise ValueError('Port and baud rate must be integers')
    if not isinstance(config['port'], str) or not config['port'].startswith('/dev/'):
        raise ValueError('Invalid serial path')
    return config


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def timestamp(value):
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError('Invalid timestamp')
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('Timestamp must include timezone')
    return result


def validate_message(message, source, session, sequence):
    if not isinstance(message, dict):
        raise ValueError('JSON object required')
    if message.get('schema_version') != 1 or message.get('message_type') != 'sensor_snapshot':
        raise ValueError('Unsupported sensor schema')
    if (message.get('sender_id') != source or message.get('session_id') != f'{session:08x}'
            or message.get('sequence') != sequence):
        raise ValueError('JSON identity differs from radio/header')
    timestamp(message.get('timestamp'))
    if not isinstance(message.get('ecg_enabled'), bool) or not isinstance(message.get('units'), dict):
        raise ValueError('Missing ECG state or units')
    sensors = message.get('sensors')
    if not isinstance(sensors, dict) or set(sensors) != set(SENSORS):
        raise ValueError('Missing sensor groups')
    for state in sensors.values():
        if not isinstance(state, dict) or not isinstance(state.get('status'), str) or len(state['status']) > 1024:
            raise ValueError('Invalid sensor status')
        age = state.get('age_seconds')
        if not finite_number(age) or not 0 <= age <= 1e10:
            raise ValueError('Invalid sensor age')
        values = state.get('values')
        if not isinstance(values, dict) or len(values) > 64:
            raise ValueError('Invalid sensor values')
        for key, value in values.items():
            if len(key) > 80 or not (value is None or finite_number(value)
                                    or isinstance(value, str) and len(value) <= 1024):
                raise ValueError('Invalid measurement')
    waves = message.get('waveforms')
    if not isinstance(waves, dict) or set(waves) != {'pulse', 'ecg'}:
        raise ValueError('Missing waveforms')
    for name, wave in waves.items():
        if not isinstance(wave, dict) or not isinstance(wave.get('status'), str) or not isinstance(wave.get('unit'), str):
            raise ValueError('Invalid waveform metadata')
        times, values = wave.get('time_offset_ms'), wave.get('values')
        if not isinstance(times, list) or not isinstance(values, list) or len(times) != len(values) or len(times) > 1500:
            raise ValueError('Invalid waveform length')
        if any(not finite_number(t) or not -8100 <= t <= 10 for t in times):
            raise ValueError('Invalid waveform time')
        if any(a >= b for a, b in zip(times, times[1:])) or any(not finite_number(v) for v in values):
            raise ValueError('Invalid waveform samples')
        if name == 'ecg' and not message['ecg_enabled'] and values:
            raise ValueError('Disabled ECG contains a waveform')
    return message


class Reassembler:
    """Bounded, single-worker assembly of untrusted RF fragments."""
    def __init__(self, sender, timeout=60):
        self.sender = sender
        self.timeout = timeout
        self.pending = OrderedDict()
        self.completed_keys = deque(maxlen=64)
        self.stats = dict(frames_received=0, invalid_frames=0, duplicate_frames=0,
                          expired_assemblies=0, completed_messages=0)

    def expire(self, now):
        for key, item in list(self.pending.items()):
            if now-item['started'] >= self.timeout:
                del self.pending[key]
                self.stats['expired_assemblies'] += 1

    def feed(self, source, data, now=None):
        now = time.monotonic() if now is None else now
        self.expire(now)
        self.stats['frames_received'] += 1
        key = None
        try:
            if source != self.sender or not 21 <= len(data) <= 255:
                raise ValueError('Unexpected source or RF payload size')
            magic, version, flags, session, sequence, index, count, crc = HEADER.unpack(data[:20])
            if magic != b'IM' or version not in (1, 2) or flags != 1 or not 0 <= index < count <= 2048:
                raise ValueError('Invalid RF header')
            key = source, session, sequence
            if key in self.completed_keys:
                self.stats['duplicate_frames'] += 1
                return None
            if key not in self.pending:
                if len(self.pending) >= 4:
                    self.pending.popitem(last=False)
                    self.stats['expired_assemblies'] += 1
                self.pending[key] = dict(started=now, count=count, crc=crc, version=version, parts={}, size=0)
            item = self.pending[key]
            if (count, crc, version) != (item['count'], item['crc'], item['version']):
                raise ValueError('Conflicting fragment metadata')
            payload = data[20:]
            if index in item['parts']:
                if item['parts'][index] != payload:
                    raise ValueError('Conflicting duplicate')
                self.stats['duplicate_frames'] += 1
                return None
            item['parts'][index] = payload
            item['size'] += len(payload)
            if item['size'] > MAX_COMPRESSED:
                raise ValueError('Compressed message too large')
            if len(item['parts']) != count:
                return None
            del self.pending[key]
            raw = b''.join(item['parts'][i] for i in range(count))
            if zlib.crc32(raw) != crc:
                raise ValueError('CRC mismatch')
            decoder = zlib.decompressobj()
            decoded = decoder.decompress(raw, MAX_JSON+1)
            if len(decoded) > MAX_JSON or decoder.unconsumed_tail or not decoder.eof or decoder.unused_data:
                raise ValueError('Invalid or oversized compressed stream')
            def invalid_constant(value):
                raise ValueError(f'Non-finite JSON number {value}')
            message = json.loads(decoded, parse_constant=invalid_constant)
            if version == 2:
                message = expand_live_message(message, source, session, sequence)
            validate_message(message, source, session, sequence)
            self.completed_keys.append(key)
            self.stats['completed_messages'] += 1
            return message
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError, zlib.error, struct.error) as exc:
            if key is not None:
                self.pending.pop(key, None)
            self.stats['invalid_frames'] += 1
            logging.warning('Rejected Zigbee packet: %s', exc)
            return None


class Receiver:
    def __init__(self, config, storage=BASE):
        self.config = config
        self.storage = storage
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.latest = None
        self.received_mono = None
        self.received_at = None
        self.capture_age_at_receive = 0
        self.retired_sessions = deque(maxlen=64)
        self.wave_history = {name: OrderedDict() for name in ('pulse', 'ecg')}
        self.wave_last_capture = {}
        self.delivery_samples = deque(maxlen=256)
        self.state = dict(radio_status='Starting', last_error=None, snapshots_received=0,
                          rejected_snapshots=0, reconnects=0, frames_received=0,
                          invalid_frames=0, duplicate_frames=0, expired_assemblies=0,
                          completed_messages=0, incomplete_assemblies=0)
        from patient_gateway import PatientGateway
        self.gateway = PatientGateway(self, validate_message, storage=storage)

    def update(self, **values):
        with self.lock:
            self.state.update(values)

    def accept(self, message, now=None, now_utc=None):
        now = time.monotonic() if now is None else now
        now_utc = utc_now() if now_utc is None else now_utc
        captured = timestamp(message['timestamp'])
        age = (now_utc-captured).total_seconds()
        with self.lock:
            previous = self.latest
            reason = None
            if age < -5:
                reason = 'Sender clock is ahead; synchronize both Pi clocks'
            elif age >= self.config['stale_after_seconds']:
                reason = 'Received snapshot is already stale'
            elif message['session_id'] in self.retired_sessions:
                reason = 'Old sender session'
            elif previous:
                if message['session_id'] == previous['session_id']:
                    delta = (message['sequence']-previous['sequence']) & 0xffffffff
                    if not 0 < delta < 0x80000000:
                        reason = 'Duplicate or older sequence'
                if captured < timestamp(previous['timestamp']):
                    reason = 'Older capture timestamp'
            if reason:
                self.state['rejected_snapshots'] += 1
                self.state['last_error'] = reason
                return False
            if previous and message['session_id'] != previous['session_id']:
                self.retired_sessions.append(previous['session_id'])
            packet = copy.deepcopy(message)
            if packet.get('waveform_mode') == 'append':
                capture_ms = round(captured.timestamp()*1000)
                for name, wave in packet['waveforms'].items():
                    history = self.wave_history[name]
                    if (not previous or message['session_id'] != previous['session_id']
                            or wave.get('clear') or not message['ecg_enabled'] and name == 'ecg'):
                        history.clear()
                    last_capture = self.wave_last_capture.get(name)
                    if last_capture is not None and capture_ms-last_capture > 800:
                        # A visible gap prevents drawing a heartbeat through lost RF batches.
                        history.clear()
                    for offset, value in zip(wave['time_offset_ms'], wave['values']):
                        history[capture_ms+offset] = value
                    for t in list(history):
                        if t < capture_ms-8000:
                            del history[t]
                    points = sorted(history.items())[-1500:]
                    wave['time_offset_ms'] = [t-capture_ms for t, _ in points]
                    wave['values'] = [v for _, v in points]
                    self.wave_last_capture[name] = capture_ms
            self.latest = packet
            self.received_mono = now
            self.received_at = now_utc.isoformat()
            self.capture_age_at_receive = max(0, age)
            self.state['snapshots_received'] += 1
            self.state['last_delivery_ms'] = round(max(0, age)*1000, 1)
            self.delivery_samples.append(self.state['last_delivery_ms'])
            self.state['last_error'] = None
        # Disk persistence belongs to the once-per-second main worker. RF reception
        # must not wait on filesystem writes for every 200 ms live update.
        logging.info('Received snapshot session=%s seq=%s age=%.2fs', message['session_id'], message['sequence'], age)
        return True

    def snapshot(self, now=None):
        now = time.monotonic() if now is None else now
        with self.lock:
            packet = copy.deepcopy(self.latest)
            status = dict(self.state)
            received_mono = self.received_mono
            received_at = self.received_at
            initial_age = self.capture_age_at_receive
            delivery = sorted(self.delivery_samples)
        elapsed = None if received_mono is None else max(0, now-received_mono)
        capture_age = (max(0,(utc_now()-timestamp(packet['timestamp'])).total_seconds()) if packet and elapsed is None
                       else None if elapsed is None else initial_age+elapsed)
        stale = packet is None or received_mono is None or self.stop.is_set() or capture_age >= self.config['stale_after_seconds']
        status.update(state=('stopped' if self.stop.is_set() else 'waiting' if packet is None
                             else 'stale' if stale else 'receiving'),
                      received_timestamp=received_at,
                      receive_age_seconds=None if elapsed is None else round(elapsed, 2),
                      capture_age_seconds=None if capture_age is None else round(capture_age, 2),
                      stale_after_seconds=self.config['stale_after_seconds'],
                      sender_address=self.config['sender_address'],
                      receiver_address=self.config['receiver_address'])
        if delivery:
            status['delivery_latency_ms'] = dict(samples=len(delivery), minimum=delivery[0],
                median=(delivery[(len(delivery)-1)//2]+delivery[len(delivery)//2])/2,
                p95=delivery[math.ceil(len(delivery)*.95)-1], maximum=delivery[-1])
        if packet:
            for name, state in packet['sensors'].items():
                state['age_seconds'] = round(state['age_seconds']+capture_age, 2)
                if stale or state['age_seconds'] >= (7 if name == 'dht' else 3):
                    state.update(values={}, status='Receiver stopped' if self.stop.is_set() else 'Stale - waiting for sender')
                    if name in packet['waveforms']:
                        packet['waveforms'][name].update(values=[], time_offset_ms=[], status=state['status'])
        with self.lock:
            recorded = copy.deepcopy(self.latest) if self.latest and self.latest.get('recording_mode') == 'submitted_snapshot' else None
        return dict(schema_version=1, timestamp=utc_now().isoformat(), receiver=status, snapshot=packet,
                    recorded_snapshot=recorded, cloud=self.gateway.status())

    def radio_worker(self):
        from digi.xbee.devices import XBeeDevice, RemoteXBeeDevice
        from digi.xbee.models.address import XBee64BitAddress
        from patient_common import Assembler, frames
        assembler = Reassembler(self.config['sender_address'], self.config['assembly_timeout_seconds'])
        patient_assembler = Assembler(self.config['sender_address'], 60)
        while not self.stop.is_set():
            device = None
            try:
                self.update(radio_status='Connecting')
                device = XBeeDevice(self.config['port'], self.config['baud_rate'])
                device.set_sync_ops_timeout(2)
                device.serial_port.write_timeout = 2
                device.open()
                address = str(device.get_64bit_addr())
                if address != self.config['receiver_address']:
                    raise RuntimeError(f'Unexpected receiver radio {address}')
                if int.from_bytes(device.get_parameter('AI'), 'big') != 0:
                    raise RuntimeError('Receiver radio has not joined Zigbee network')
                self.update(radio_status='Listening', last_error=None)
                sender = RemoteXBeeDevice(device, XBee64BitAddress.from_hex_string(self.config['sender_address']))
                while not self.stop.is_set():
                    # Polling the SDK queue avoids blocking its serial listener callback.
                    message = device.read_data()
                    if message:
                        source = str(message.remote_device.get_64bit_addr())
                        data = bytes(message.data)
                        patient_packet = len(data) > 2 and data[2] == 3
                        packet = patient_assembler.feed(source, data) if patient_packet else assembler.feed(source, data)
                        if packet is not None:
                            if patient_packet:
                                self.gateway.accept(packet)
                            else:
                                self.accept(packet)
                    else:
                        assembler.expire(time.monotonic())
                        # The listener can stop after USB removal without read_data raising.
                        # Digi 1.5.0 exposes listener liveness only on this object.
                        if not device.is_open() or not device._packet_listener.is_running():
                            raise OSError('Receiver USB listener stopped')
                        self.stop.wait(.02)
                    self.update(**assembler.stats, incomplete_assemblies=len(assembler.pending))
                    # Only this worker owns the radio; cloud worker queues responses.
                    try:
                        response = self.gateway.responses.get_nowait()
                    except __import__('queue').Empty:
                        response = None
                    if response:
                        for part in frames(response):
                            if self.stop.is_set():
                                break
                            device.send_data(sender, part)
            except Exception as exc:
                logging.warning('Receiver radio: %s: %s', type(exc).__name__, exc)
                with self.lock:
                    self.state['reconnects'] += 1
                self.update(radio_status='Disconnected - retrying', last_error=f'{type(exc).__name__}: {exc}')
            finally:
                if device is not None:
                    try:
                        device.close()
                    except Exception:
                        logging.exception('Cannot close receiver radio')
            self.stop.wait(3)
        self.update(radio_status='Stopped')


def handler_for(receiver):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split('?', 1)[0]
            if path == '/api/readings':
                data = json.dumps(receiver.snapshot(), allow_nan=False, separators=(',', ':')).encode()
                kind = 'application/json; charset=utf-8'
            elif path in ('/', '/index.html'):
                data = (BASE/'dashboard.html').read_bytes()
                kind = 'text/html; charset=utf-8'
            elif path == '/health':
                data = json.dumps({'running': not receiver.stop.is_set(), 'radio': receiver.snapshot()['receiver']['radio_status']}).encode()
                kind = 'application/json'
            elif path == '/api/patients':
                data = json.dumps(receiver.gateway.store.patients(), allow_nan=False).encode()
                kind = 'application/json'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *args):
            pass
    return Handler


def main():
    import digi.xbee.devices  # Fail startup clearly if runtime dependencies are missing.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=0, help='Bounded diagnostic duration')
    args = parser.parse_args()
    config = configuration()
    (BASE/'logs').mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[RotatingFileHandler(BASE/'logs/receiver.log', maxBytes=512000, backupCount=2),
                                  logging.StreamHandler()])
    import fcntl
    # Share the existing role lock so the preserved original cannot also own USB.
    legacy = Path('/home/pi/Desktop/Immortals_Receiver')
    lock = ((legacy if legacy.exists() else BASE)/'.receiver.lock').open('w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('Immortals receiver is already running.')
        return
    receiver = Receiver(config)
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: receiver.stop.set())
    server = ThreadingHTTPServer((config['bind_host'], config['http_port']), handler_for(receiver))
    server.daemon_threads = True
    radio = threading.Thread(target=receiver.radio_worker, name='zigbee-receiver', daemon=True)
    web = threading.Thread(target=server.serve_forever, name='receiver-http', daemon=True)
    cloud = threading.Thread(target=receiver.gateway.cloud_worker, name='firebase-upload', daemon=True)
    try:
        radio.start()
        web.start()
        cloud.start()
        logging.info('Receiver dashboard listening on port %s', config['http_port'])
        start = time.monotonic()
        while not receiver.stop.wait(1):
            try:
                atomic_json(BASE/'latest_readings.json', receiver.snapshot())
                with receiver.lock:
                    packet = copy.deepcopy(receiver.latest)
                if packet is not None:
                    atomic_json(BASE/'last_packet.json', packet)
            except OSError:
                logging.exception('Cannot write receiver state')
            if args.seconds and time.monotonic()-start >= args.seconds:
                receiver.stop.set()
    finally:
        receiver.stop.set()
        server.shutdown()
        server.server_close()
        radio.join(8)
        cloud.join(12)
        receiver.update(radio_status='Stopped')
        atomic_json(BASE/'latest_readings.json', receiver.snapshot())
        lock.close()
        logging.info('Receiver stopped')


if __name__ == '__main__':
    main()
