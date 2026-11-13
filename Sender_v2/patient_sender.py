"""Manual snapshot submission. Sensor/UI workers never wait on radio delivery."""
import copy
import json
import logging
from pathlib import Path
import queue
import threading
import time
import uuid
from patient_common import Store, Assembler, event, frames, profile, utc_now

BASE = Path(__file__).resolve().parent

class PatientSender:
    def __init__(self, monitor, config_loader, snapshot_builder, storage=None):
        self.monitor = monitor
        self.storage = Path(storage or BASE)
        self.config_loader, self.snapshot_builder = config_loader, snapshot_builder
        self.store = Store((storage or BASE)/'patient_data.sqlite3')
        self.lock = threading.RLock()
        self.session = int.from_bytes(uuid.uuid4().bytes[:4], 'big')
        self.sequence = 0
        self.active = None
        self.controls = queue.Queue(maxsize=32)
        self.state = dict(enabled=True, status='Connecting to gateway', last_error=None,
                          sent_snapshots=0, failed_snapshots=0, sync_status='Using saved patient list')
        with self.store.lock:
            latest = self.store.db.execute('SELECT id FROM outbox ORDER BY created DESC LIMIT 1').fetchone()
        self.last_submission = latest[0] if latest else None
        self.last_control = None
        self.page_offset = 0
        self.stable_values = []

    def status(self):
        with self.lock:
            result = dict(self.state)
            active = copy.deepcopy(self.active)
            last = self.last_submission
        counts = self.store.counts()
        result.update(pending_count=counts.get('pending', 0), gateway_pending_count=counts.get('gateway', 0),
                      recorded_count=counts.get('draft',0),
                      rejected_count=counts.get('rejected', 0), active_patient=active,
                      submission_id=last, submission=self.store.receipt(last) if last else None)
        return result

    def set_enabled(self, enabled):
        # Radio remains available for lists/ACKs; vitals only travel after Submit.
        return None

    def set_ecg_available(self, available):
        available = bool(available)
        with self.monitor.lock:
            self.monitor.ecg_enabled = available
            self.monitor.ecg_trace.clear()
        with self.lock:
            self.stable_values = []
        path = self.storage/'settings.json'
        try:
            settings = json.loads(path.read_text())
            if not isinstance(settings,dict):
                settings = {}
        except (OSError,ValueError):
            settings = {}
        settings['ecg_enabled'] = available
        temporary = self.storage/'.settings-ecg.tmp'
        temporary.write_text(json.dumps(settings,indent=2))
        temporary.replace(path)

    def _event(self, kind, request_id=None, **data):
        config = self.config_loader()
        with self.lock:
            self.sequence = (self.sequence+1) & 0xffffffff
            return event(kind, config['sender_address'], self.session, self.sequence, request_id, **data)

    def create_patient(self, name, age, sex):
        return self.store.create_patient(name, age, sex, self.config_loader()['sender_address'])

    def select(self, patient):
        patient = profile(patient)
        if not any(p['patient_id'] == patient['patient_id'] for p in self.store.patients()):
            raise ValueError('Choose a saved or newly registered patient')
        with self.lock:
            self.active = dict(patient=patient, monitoring_session_id=str(uuid.uuid4()),
                               started_at=utc_now(), started_mono=time.monotonic())
            self.stable_values = []
        with self.monitor.lock:
            self.monitor.pulse_trace.clear()
            self.monitor.ecg_trace.clear()
        return self.active

    def end_session(self):
        with self.lock:
            self.active = None

    def patient_snapshot(self, traces=True):
        snapshot = self.monitor.snapshot(traces=traces)
        with self.lock:
            context = copy.deepcopy(self.active)
        if not context:
            for state in snapshot['sensors'].values():
                state.update(values={}, status='Choose a patient to check readings')
            snapshot.update(pulse_trace=[], ecg_trace=[])
            return snapshot
        start = context['started_mono']
        now = time.monotonic()
        for name, state in snapshot['sensors'].items():
            if now-state['age_seconds'] < start or name == 'pulse' and now-start < 8.3:
                state.update(values={}, status='Collecting for selected patient')
        for name in ('pulse', 'ecg'):
            snapshot[name+'_trace'] = [(t, v) for t, v in snapshot.get(name+'_trace', []) if t >= start]
        if not snapshot['ecg_enabled']:
            snapshot['sensors']['ecg'].update(values={},status='ECG not available — skipped')
            snapshot['ecg_trace'] = []
        return snapshot

    def prepare_submission(self):
        with self.lock:
            context = copy.deepcopy(self.active)
        if not context:
            raise ValueError('Choose a patient first')
        message = self._event('patient_submit', patient=context['patient'],
                              monitoring_session_id=context['monitoring_session_id'], started_at=context['started_at'])
        captured = time.monotonic()
        snapshot = self.patient_snapshot(traces=True)
        # The immutable preview and uploaded record are exactly this capture.
        message['reading'] = self.snapshot_builder(snapshot, message['sender_id'], self.session,
                                                  message['sequence'], captured)
        message['reading'].update(patient_id=context['patient']['patient_id'],
                                  patient_code=context['patient'].get('patient_code'),
                                  monitoring_session_id=context['monitoring_session_id'], device_id=message['sender_id'],
                                  captured_at=snapshot['timestamp'], reading_id=message['request_id'], recording_mode='submitted_snapshot')
        frames(message)  # Confirm radio size before committing the user's capture.
        return message

    def submit(self, message):
        with self.lock:
            saved_draft = self.store.receipt(message['request_id'])['state'] == 'draft'
            if not saved_draft and (not self.active or message['monitoring_session_id'] != self.active['monitoring_session_id']):
                raise ValueError('Patient changed — check readings again')
        self.store.enqueue(message)
        if self.store.receipt(message['request_id'])['state'] == 'draft':
            self.store.set_state(message['request_id'],'pending','Saved on sender — sending to gateway')
        with self.lock:
            self.last_submission = message['request_id']
            self.state.update(status='Saved on sender — sending to gateway', last_error=None)
        return message['request_id']

    def record(self):
        message = self.prepare_submission()
        self.store.enqueue(message,state='draft')
        with self.lock:
            self.last_submission = message['request_id']
        self.store.set_state(message['request_id'],'draft','Vitals recorded on this device — ready to send')
        return message

    def readiness(self):
        snapshot = self.patient_snapshot(traces=True)
        required = {'pulse':('heart_rate_bpm','spo2_percent'), 'mlx':('object_c','ambient_c'),
                    'dht':('temperature_c','humidity_percent'), 'bmp':('temperature_c','pressure_hpa'),
                    'ecg':('voltage_v',)}
        ecg_available = snapshot.get('ecg_enabled',True)
        if not ecg_available:
            required.pop('ecg')
        missing = []
        for name, fields in required.items():
            values = snapshot['sensors'][name]['values']
            if any(not isinstance(values.get(field),(int,float)) for field in fields):
                missing.append({'pulse':'heart rate / SpO2','mlx':'surface temperature','dht':'room temperature / humidity',
                                'bmp':'pressure / board temperature','ecg':'ECG samples'}[name])
        now=time.monotonic()
        for name,count in (('pulse',25),('ecg',100)):
            if name == 'ecg' and not ecg_available:
                continue
            trace=snapshot[name+'_trace']
            if len(trace)<count or now-trace[-1][0]>.5:
                missing.append(name+' waveform')
        if snapshot['sensors']['pulse']['values'].get('quality_percent',0)<70:
            missing.append('stable optical signal')
        ecg=snapshot['sensors']['ecg']['values']
        if ecg_available and (ecg.get('heart_rate_bpm') is None or ecg.get('quality_percent',0)<50):
            missing.append('stable ECG / electrode contact')
        if missing:
            self.stable_values=[]
            return False,missing
        measurements=[snapshot['sensors'][name]['values'][field] for name,fields in required.items()
                      if name!='ecg' for field in fields]
        tolerances=[5,2,.5,.5,.5,3,.5,2]
        self.stable_values.append((now,measurements))
        self.stable_values=[item for item in self.stable_values if now-item[0]<=3.5]
        if any(max(item[1][i] for item in self.stable_values)-min(item[1][i] for item in self.stable_values)>limit
               for i,limit in enumerate(tolerances)):
            self.stable_values=[(now,measurements)]
        elapsed=now-self.stable_values[0][0]
        return elapsed>=3,[] if elapsed>=3 else [f'all sensors stabilizing ({max(1,round(3-elapsed))}s)']

    def sync_all(self):
        saved=self.store.pending(('draft','pending','gateway','rejected'),500)
        for item in saved:
            if self.store.receipt(item['request_id'])['state'] in ('draft','rejected'):
                self.store.set_state(item['request_id'],'pending','Saved on sender — waiting for gateway')
        with self.lock:
            self.state.update(status='Syncing all saved records with gateway',last_error=None)
        return [item['request_id'] for item in saved]

    def request_sync(self, offset=0):
        self.page_offset = offset
        message = self._event('patient_list_request', offset=offset)
        try:
            self.controls.put_nowait(message)
        except queue.Full:
            return
        with self.lock:
            self.state['sync_status'] = 'Synchronizing patients…'

    def _received(self, message):
        kind, key = message['message_type'], message['request_id']
        if kind == 'patient_list_page':
            if not self.last_control or key != self.last_control['request_id']:
                return
            for item in message['patients']:
                try:
                    self.store.cache(item)
                except ValueError:
                    logging.warning('Patient cache conflict for %s', item['patient_id'])
            self.last_control = None
            if message['more']:
                self.request_sync(message['next_offset'])
            else:
                with self.lock:
                    self.state['sync_status'] = 'Patient list synchronized with gateway'
        elif kind in ('submission_ack', 'submission_status'):
            state = message['state']
            if state == 'unknown':
                if self.store.receipt(key)['state'] == 'gateway':
                    self.store.set_state(key, 'pending', 'Gateway receipt missing — resending original capture')
            elif state in ('pending', 'uploaded', 'rejected'):
                # Never downgrade a completed receipt after a delayed ACK.
                if self.store.receipt(key)['state'] != 'uploaded':
                    self.store.set_state(key, 'gateway' if state == 'pending' else state, message.get('detail', ''))
                with self.lock:
                    self.state.update(status={'pending':'Gateway saved — synchronization pending',
                                             'uploaded':'Gateway confirmed saved', 'rejected':'Submission needs attention'}[state])

    def run(self):
        from digi.xbee.devices import XBeeDevice, RemoteXBeeDevice
        from digi.xbee.models.address import XBee64BitAddress
        next_submit, next_sync, next_status = 0., 0., 0.
        last_sent_key = None
        retry_control_at = 0.
        while not self.monitor.stop.is_set():
            device = None
            try:
                config = self.config_loader()
                device = XBeeDevice(config['port'], config['baud_rate'])
                device.set_sync_ops_timeout(2)
                device.serial_port.write_timeout = 2
                device.open()
                if str(device.get_64bit_addr()) != config['sender_address']:
                    raise RuntimeError('Unexpected sender radio identity')
                if int.from_bytes(device.get_parameter('AI'), 'big') != 0:
                    raise RuntimeError('Sender radio has not joined Zigbee network')
                remote = RemoteXBeeDevice(device, XBee64BitAddress.from_hex_string(config['receiver_address']))
                assembler = Assembler(config['receiver_address'])
                with self.lock:
                    self.state.update(status='Ready — check readings and submit', last_error=None)
                while not self.monitor.stop.is_set():
                    received = device.read_data()
                    if received:
                        value = assembler.feed(str(received.remote_device.get_64bit_addr()), bytes(received.data))
                        if value:
                            self._received(value)
                    if not device.is_open() or not device._packet_listener.is_running():
                        raise OSError('Sender USB listener stopped')
                    now = time.monotonic()
                    if now >= next_sync:
                        if not self.last_control:
                            self.request_sync()
                        next_sync = now+120
                    outgoing = None
                    pending = self.store.pending()
                    if pending and (now >= next_submit or pending[0]['request_id'] != last_sent_key):
                        outgoing = pending[0]
                        last_sent_key = outgoing['request_id']
                        next_submit = now+25
                    elif now >= next_status:
                        waiting = self.store.pending(('gateway',), 1)
                        if waiting:
                            outgoing = self._event('submission_status_request', waiting[0]['request_id'])
                        next_status = now+10
                    if outgoing is None:
                        if not self.last_control:
                            try:
                                self.last_control = self.controls.get_nowait()
                                retry_control_at = 0
                            except queue.Empty:
                                pass
                        if self.last_control and now >= retry_control_at:
                            outgoing = self.last_control
                            retry_control_at = now+20
                    if outgoing:
                        for part in frames(outgoing, config['max_packet_bytes']):
                            if self.monitor.stop.is_set():
                                break
                            device.send_data(remote, part)
                        with self.lock:
                            if outgoing['message_type'] == 'patient_submit':
                                self.state['sent_snapshots'] += 1
                    self.monitor.stop.wait(.02)
            except Exception as exc:
                logging.warning('Patient radio: %s: %s', type(exc).__name__, exc)
                with self.lock:
                    self.state.update(status='Gateway unavailable — captures stay saved', last_error=str(exc)[:200])
                    self.state['failed_snapshots'] += 1
            finally:
                if device is not None:
                    try:
                        device.close()
                    except Exception:
                        logging.warning('Could not close sender radio')
            self.monitor.stop.wait(3)
