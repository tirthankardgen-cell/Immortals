"""Durable patient submissions and an independent Firebase/Firestore worker."""
import copy
import json
import logging
import os
from pathlib import Path
import queue
import threading
import time
import uuid
from patient_common import Store, date, event, profile, utc_now, validate_event

BASE = Path(__file__).resolve().parent
CONFIG_PATH = Path('/home/pi/.config/immortals/firebase.json')

class FirestoreBackend:
    def __init__(self, config):
        import firebase_admin
        from firebase_admin import credentials, firestore
        credential = config.get('credential_path') or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if credential and not Path(credential).is_file():
            raise RuntimeError('Gateway Firebase credential file missing')
        app = firebase_admin.initialize_app(credentials.Certificate(credential) if credential else credentials.ApplicationDefault(),
                                           {'projectId': config['project_id']}, name='immortals-gateway-'+uuid.uuid4().hex)
        self.db = firestore.client(app=app)
        self.firestore, self.timeout = firestore, config.get('request_timeout_seconds', 10)

    def patients(self):
        # Limit the synchronized cache; radio pagination is ten patients per page.
        return [profile(doc.to_dict()) for doc in self.db.collection('patients').limit(10000).stream(timeout=self.timeout, retry=None)]

    def upload(self, submission):
        patient = profile(submission['patient'])
        reading = copy.deepcopy(submission['reading'])
        reading.update(received_at=submission['received_at'], uploaded_at=utc_now())
        patient_ref = self.db.collection('patients').document(patient['patient_id'])
        latest_ref = patient_ref.collection('monitoring').document('latest')
        history_ref = patient_ref.collection('readings').document(submission['request_id'])
        session_ref = patient_ref.collection('sessions').document(submission['monitoring_session_id'])
        def commit(tx):
            saved_patient = patient_ref.get(transaction=tx, timeout=self.timeout, retry=None)
            latest = latest_ref.get(transaction=tx, timeout=self.timeout, retry=None)
            if saved_patient.exists:
                old = saved_patient.to_dict()
                if any(old.get(k) != patient[k] for k in ('name', 'age', 'sex')):
                    raise ValueError('Firebase patient ID already has different details')
            else:
                tx.set(patient_ref, dict(patient, updated_at=patient['created_at'], device_id=reading['device_id']))
            tx.set(history_ref, reading)
            tx.set(session_ref, dict(patient_id=patient['patient_id'], monitoring_session_id=submission['monitoring_session_id'],
                                     device_id=reading['device_id'], started_at=submission['started_at'], recording_mode='submitted_snapshot'), merge=True)
            old_capture = latest.to_dict().get('captured_at') if latest.exists else None
            if old_capture is None or date(old_capture) <= date(reading['captured_at']):
                tx.set(latest_ref, reading)
            # SDK transaction helpers omit timeout options; use the same GAPIC
            # calls explicitly so both begin and atomic commit have deadlines.
            self.db._firestore_api.commit(request={'database':self.db._database_string,
                                                  'writes':tx._write_pbs,'transaction':tx.id},
                                          metadata=self.db._rpc_metadata,timeout=self.timeout,retry=None)
        from google.api_core.exceptions import Aborted
        for attempt in range(3):
            try:
                transaction = self.db.transaction(max_attempts=1)
                begun = self.db._firestore_api.begin_transaction(request={'database':self.db._database_string},
                                                                 metadata=self.db._rpc_metadata,timeout=self.timeout,retry=None)
                transaction._id = begun.transaction
                commit(transaction)
                return
            except Aborted:
                if attempt == 2:
                    raise

class PatientGateway:
    def __init__(self, receiver, validate_reading, config=None, storage=None, backend_factory=FirestoreBackend):
        self.receiver, self.validate_reading = receiver, validate_reading
        self.config = dict(project_id='immortals-3', request_timeout_seconds=10,
                           max_pending_records=500, max_pending_bytes=32*1024*1024)
        if CONFIG_PATH.exists():
            self.config.update(json.loads(CONFIG_PATH.read_text()))
        if config:
            self.config.update(config)
        self.store = Store((storage or BASE)/'gateway_data.sqlite3', self.config['max_pending_records'], self.config['max_pending_bytes'])
        self.backend_factory = backend_factory
        self.responses = queue.Queue(maxsize=64)
        self.lock = threading.Lock()
        self.session = int.from_bytes(uuid.uuid4().bytes[:4], 'big')
        self.sequence = 0
        self.state = dict(status='Connecting to Firebase', last_error=None, last_uploaded_at=None,
                          uploaded_count=0, unsaved_count=0, project_id=self.config['project_id'])
        with self.store.lock:
            saved = self.store.db.execute('SELECT data,detail FROM outbox ORDER BY created DESC LIMIT 1').fetchone()
        if saved:
            prior = json.loads(saved[0])
            self.receiver.latest = copy.deepcopy(prior['reading'])
            self.receiver.capture_age_at_receive = max(0,(date(utc_now())-date(prior['reading']['timestamp'])).total_seconds())

    def status(self):
        with self.lock:
            result = dict(self.state)
        result['queue'] = self.store.counts()
        result['patient_count'] = len(self.store.patients())
        return result

    def respond(self, kind, key, **data):
        with self.lock:
            self.sequence = (self.sequence+1) & 0xffffffff
            response = event(kind, self.receiver.config['receiver_address'], self.session, self.sequence, key, **data)
        try:
            self.responses.put_nowait(response)
        except queue.Full:
            # Sender retries controls/status; never block RF reception for an ACK.
            logging.warning('Gateway response queue full')

    def accept(self, message):
        kind, key = message['message_type'], message['request_id']
        if kind == 'patient_list_request':
            offset = message['offset']
            patients = self.store.patients(offset=offset, limit=11)
            self.respond('patient_list_page', key, patients=patients[:10], more=len(patients)>10,
                         next_offset=offset+min(10, len(patients)))
        elif kind == 'submission_status_request':
            receipt = self.store.receipt(key)
            if receipt['state'] == 'pending':
                receipt['detail'] = 'Saved on gateway; waiting for Firebase'
            self.respond('submission_status', key, **receipt)
        elif kind == 'patient_submit':
            try:
                validate_event(message,message['sender_id'],int(message['session_id'],16),message['sequence'])
                self.validate_reading(message['reading'], message['sender_id'], int(message['session_id'],16), message['sequence'])
                captured = date(message['reading']['timestamp'])
                if (captured-date(utc_now())).total_seconds() > 5:
                    raise ValueError('Sender clock ahead — synchronize clocks')
                patient = self.store.cache(message['patient'])
                # Persist the exact wire message before ACK; reception metadata is stored separately at upload.
                added = self.store.enqueue(message)
                if added:
                    self.store.set_state(key, 'pending', utc_now())
                    with self.receiver.lock:
                        prior = self.receiver.latest
                        is_latest = not prior or captured >= date(prior['timestamp'])
                        if is_latest:
                            self.receiver.latest = copy.deepcopy(message['reading'])
                            self.receiver.received_mono = time.monotonic()
                            self.receiver.received_at = utc_now()
                            self.receiver.capture_age_at_receive = max(0, (date(utc_now())-captured).total_seconds())
                        self.receiver.state['snapshots_received'] += 1
                receipt = self.store.receipt(key)
                # Internal receipt detail holds original received_at for queue recovery.
                if receipt['state'] == 'pending':
                    receipt['detail'] = 'Saved on gateway; waiting for Firebase'
                self.respond('submission_ack', key, **receipt)
            except (ValueError, OSError) as exc:
                with self.lock:
                    self.state['unsaved_count'] += 1
                self.respond('submission_ack', key, state='rejected', detail=str(exc)[:300])

    def cloud_worker(self):
        backend, retry, next_sync = None, 2., 0.
        while not self.receiver.stop.is_set():
            try:
                if backend is None:
                    backend = self.backend_factory(self.config)
                pending = self.store.pending()
                if pending:
                    item = pending[0]
                    received = self.store.receipt(item['request_id'])['detail']
                    try:
                        date(received)
                    except ValueError:
                        received = item['reading']['timestamp']
                    try:
                        backend.upload(dict(item, received_at=received))
                    except ValueError as exc:
                        self.store.set_state(item['request_id'], 'rejected', str(exc))
                        continue
                    self.store.set_state(item['request_id'], 'uploaded', 'Saved to Firebase')
                    with self.lock:
                        self.state.update(status='Connected to Firebase', last_error=None, last_uploaded_at=utc_now())
                        self.state['uploaded_count'] += 1
                    retry = 2.
                    # Notification rides the same Zigbee worker; sender also polls persisted status.
                    self.respond('submission_status', item['request_id'], state='uploaded', detail='Saved to Firebase')
                    continue
                if time.monotonic() >= next_sync:
                    for patient in backend.patients():
                        try:
                            self.store.cache(patient)
                        except ValueError:
                            logging.warning('Cloud patient cache conflict')
                    next_sync = time.monotonic()+60
                    with self.lock:
                        self.state.update(status='Connected to Firebase', last_error=None)
                self.receiver.stop.wait(.5)
            except Exception as exc:
                logging.warning('Firebase upload pending: %s: %s', type(exc).__name__, exc)
                with self.lock:
                    self.state.update(status='Firebase unavailable — submissions saved locally', last_error=str(exc)[:200])
                self.receiver.stop.wait(retry)
                retry = min(60, retry*2)
