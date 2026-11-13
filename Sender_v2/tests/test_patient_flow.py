"""Cross-role contracts: immutable patient capture, durability, ACK, outage recovery."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Receiver_v2'))
sys.path.insert(0,str(ROOT/'Sender_v2'))
from patient_common import Store, Assembler, frames, event, profile, utc_now
from patient_sender import PatientSender
from patient_gateway import PatientGateway
spec = importlib.util.spec_from_file_location('receiver_app',ROOT/'Receiver_v2/main.py')
receiver_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receiver_app)

SOURCE, DEST = '0013A200408DF0F0','0013A200408DF0CE'

def patient(name='Same Name'):
    return dict(patient_id=str(uuid.uuid4()),name=name,age=32,sex='Female',created_at=utc_now(),age_recorded_at=utc_now())

def reading(source, session, sequence):
    return dict(schema_version=1,message_type='sensor_snapshot',sender_id=source,session_id=f'{session:08x}',
                sequence=sequence,timestamp=utc_now(),ecg_enabled=True,units={'heart_rate_bpm':'bpm'},
                sensors={n:dict(status='Live',age_seconds=0,values={'heart_rate_bpm':72 if n=='pulse' else None}) for n in receiver_app.SENSORS},
                waveforms={n:dict(status='Unavailable',unit='mV at ADC' if n=='ecg' else 'relative IR counts',time_offset_ms=[],values=[]) for n in ('pulse','ecg')})

def submission(p=None, seq=1):
    p = p or patient()
    session_id = str(uuid.uuid4())
    item = event('patient_submit',SOURCE,99,seq,patient=p,monitoring_session_id=session_id,
                 started_at=(datetime.now(timezone.utc)-timedelta(seconds=10)).isoformat())
    item['reading'] = reading(SOURCE,99,seq)
    item['reading'].update(patient_id=p['patient_id'],monitoring_session_id=session_id,device_id=SOURCE,captured_at=item['reading']['timestamp'])
    return item

class FakeMonitor:
    def __init__(self):
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.pulse_trace,self.ecg_trace = [],[]
        self.samples = 0
        self.ecg_enabled = True
    def snapshot(self,traces=False):
        self.samples += 1
        return dict(timestamp=utc_now(),ecg_enabled=self.ecg_enabled,sensors={n:dict(status='Live',age_seconds=0,values={'test':self.samples}) for n in receiver_app.SENSORS},pulse_trace=list(self.pulse_trace),ecg_trace=list(self.ecg_trace))

def builder(snapshot,source,session,sequence,mono):
    value = reading(source,session,sequence)
    value['timestamp'] = snapshot['timestamp']
    value['sensors'] = snapshot['sensors']
    value['ecg_enabled'] = snapshot['ecg_enabled']
    return value

class FakeReceiver:
    def __init__(self):
        self.config = dict(sender_address=SOURCE,receiver_address=DEST)
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.latest = None
        self.state = dict(snapshots_received=0)

class PatientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.stores = []
    def tearDown(self):
        for store in self.stores:
            store.db.close()
        self.temp.cleanup()
    def store(self,limit=500):
        value = Store(self.path/'cache.sqlite3',limit)
        self.stores.append(value)
        return value
    def gateway(self,**kwargs):
        value = PatientGateway(FakeReceiver(),receiver_app.validate_message,storage=self.path,**kwargs)
        self.stores.append(value.store)
        return value
    def sender(self):
        monitor = FakeMonitor()
        sender = PatientSender(monitor,lambda:dict(sender_address=SOURCE),builder,self.path)
        self.stores.append(sender.store)
        return sender

    def test_patient_ids_sequence_persist_and_duplicate_names_search(self):
        store = self.store()
        first = store.create_patient('Same Name',32,'Female',SOURCE)
        second = store.create_patient('Same Name',32,'Female',SOURCE)
        self.assertNotEqual(first['patient_id'],second['patient_id'])
        self.assertTrue(first['patient_code'].endswith('-00001'))
        self.assertTrue(second['patient_code'].endswith('-00002'))
        reopened = self.store()
        third = reopened.create_patient('Another',45,'Male',SOURCE)
        self.assertTrue(third['patient_code'].endswith('-00003'))
        self.assertEqual(len(reopened.patients('same name')),2)
        self.assertEqual(reopened.patients(second['patient_code'])[0]['patient_id'],second['patient_id'])

    def test_invalid_form_does_not_consume_id(self):
        store = self.store()
        for name,age,sex in [('',30,'Male'),('Name',131,'Female'),('Name',True,'Other'),('Name',22,'')]:
            with self.assertRaises(ValueError):
                store.create_patient(name,age,sex,SOURCE)
        self.assertTrue(store.create_patient('Valid',0,'Other',SOURCE)['patient_code'].endswith('-00001'))

    def test_complete_fragmented_v3_repeat_reacks_corruption_and_wrong_radio(self):
        item = submission()
        parts = frames(item)
        assembler = Assembler(SOURCE)
        result = None
        for part in reversed(parts):
            result = assembler.feed(SOURCE,part) or result
        self.assertEqual(result,item)
        for part in parts:
            result = assembler.feed(SOURCE,part)
        self.assertEqual(result,item)  # A lost ACK must allow a fresh application ACK.
        self.assertIsNone(Assembler(DEST).feed(SOURCE,parts[0]))
        bad = list(parts);bad[-1]=bad[-1][:-1]+bytes([bad[-1][-1]^1])
        assembler = Assembler(SOURCE)
        for part in bad:
            self.assertIsNone(assembler.feed(SOURCE,part))

    def test_preview_immutable_and_late_queue_keeps_original_patient(self):
        sender = self.sender()
        p,q = sender.create_patient('First',30,'Male'),sender.create_patient('Second',40,'Female')
        sender.select(p)
        preview = sender.prepare_submission()
        saved = copy.deepcopy(preview)
        sender.submit(preview)
        sender.monitor.snapshot()
        sender.select(q)
        self.assertEqual(sender.store.pending()[0],saved)
        self.assertEqual(sender.store.pending()[0]['reading']['patient_id'],p['patient_id'])
        with self.assertRaises(ValueError):
            sender.submit(preview)

    def test_no_patient_no_submit_and_selection_never_enqueues(self):
        sender = self.sender()
        with self.assertRaises(ValueError):
            sender.prepare_submission()
        sender.select(sender.create_patient('Patient',20,'Other'))
        self.assertEqual(sender.store.pending(),[])
        self.assertEqual(sender.patient_snapshot()['sensors']['pulse']['values'],{})

    def test_record_is_durable_draft_and_only_send_releases_to_radio(self):
        sender = self.sender()
        p=sender.create_patient('Recorded',22,'Other')
        self.assertEqual(p['patient_id'],p['patient_code'])
        sender.select(p)
        saved=sender.record()
        self.assertEqual(sender.store.pending(),[])
        self.assertEqual(sender.store.receipt(saved['request_id'])['state'],'draft')
        sender.end_session()
        sender.submit(saved)
        self.assertEqual(sender.store.pending()[0],saved)

    def test_sync_all_retains_each_patient_and_cancel_only_discards_draft(self):
        sender=self.sender()
        records=[]
        for name in ('First','Second'):
            sender.select(sender.create_patient(name,30,'Male'))
            records.append(sender.record())
        discard=records.pop()
        sender.store.discard_draft(discard['request_id'])
        self.assertEqual(sender.store.receipt(discard['request_id'])['state'],'unknown')
        sender.select(sender.create_patient('Third',40,'Female'))
        records.append(sender.record())
        ids=sender.sync_all()
        self.assertEqual(set(ids),{r['request_id'] for r in records})
        sender.store.discard_draft(records[0]['request_id'])
        pending=sender.store.pending(limit=10)
        self.assertEqual(len(pending),2)
        self.assertEqual({r['reading']['patient_id'] for r in pending},{r['patient']['patient_id'] for r in records})

    def test_auto_record_requires_stable_complete_and_qualified_readings(self):
        sender=self.sender()
        states={'pulse':dict(heart_rate_bpm=75.,spo2_percent=98.,quality_percent=90),
                'mlx':dict(object_c=32.,ambient_c=28.),'dht':dict(temperature_c=28.,humidity_percent=60.),
                'bmp':dict(temperature_c=30.,pressure_hpa=1012.),'ecg':dict(voltage_v=1.2,heart_rate_bpm=76.,quality_percent=80)}
        def snapshot(now):
            return dict(sensors={n:dict(values=copy.deepcopy(v)) for n,v in states.items()},
                        pulse_trace=[(now-i*.04,10) for i in range(25)][::-1],
                        ecg_trace=[(now-i*.008,1.2) for i in range(100)][::-1])
        for now,expected in [(100,False),(101,False),(103.1,True)]:
            with patch.object(sender,'patient_snapshot',return_value=snapshot(now)),patch('patient_sender.time.monotonic',return_value=now):
                self.assertEqual(sender.readiness()[0],expected)
        states['ecg']['quality_percent']=0
        with patch.object(sender,'patient_snapshot',return_value=snapshot(104)),patch('patient_sender.time.monotonic',return_value=104):
            self.assertFalse(sender.readiness()[0])
        self.assertEqual(sender.stable_values,[])

    def test_ecg_disabled_does_not_block_stable_other_sensors(self):
        sender=self.sender()
        states={'pulse':dict(heart_rate_bpm=75.,spo2_percent=98.,quality_percent=90),
                'mlx':dict(object_c=32.,ambient_c=28.),'dht':dict(temperature_c=28.,humidity_percent=60.),
                'bmp':dict(temperature_c=30.,pressure_hpa=1012.),'ecg':{}}
        for now,expected in [(100,False),(103.1,True)]:
            snapshot=dict(ecg_enabled=False,sensors={n:dict(values=copy.deepcopy(v)) for n,v in states.items()},
                          pulse_trace=[(now-i*.04,10) for i in range(25)][::-1],ecg_trace=[])
            with patch.object(sender,'patient_snapshot',return_value=snapshot),patch('patient_sender.time.monotonic',return_value=now):
                ready,missing=sender.readiness()
                self.assertEqual(ready,expected)
                self.assertFalse(any('ECG' in reason or 'ecg' in reason for reason in missing))
        snapshot['ecg_enabled']=True
        with patch.object(sender,'patient_snapshot',return_value=snapshot),patch('patient_sender.time.monotonic',return_value=104):
            self.assertFalse(sender.readiness()[0])

    def test_ecg_toggle_persists_and_disabled_record_is_gateway_compatible(self):
        sender=self.sender()
        sender.select(sender.create_patient('Patient',20,'Other'))
        sender.monitor.ecg_trace=[(time.monotonic(),1.2)]
        sender.set_ecg_available(False)
        self.assertFalse(sender.monitor.ecg_enabled)
        self.assertEqual(sender.monitor.ecg_trace,[])
        import json
        self.assertFalse(json.loads((self.path/'settings.json').read_text())['ecg_enabled'])
        record=sender.record()
        self.assertFalse(record['reading']['ecg_enabled'])
        self.assertEqual(record['reading']['sensors']['ecg']['values'],{})
        self.assertEqual(record['reading']['waveforms']['ecg']['values'],[])
        self.assertTrue(record['reading']['sensors']['bmp']['values'])
        gateway=self.gateway();gateway.accept(record)
        self.assertEqual(gateway.responses.get_nowait()['state'],'pending')
        sender.set_ecg_available(True)
        self.assertTrue(sender.monitor.ecg_enabled)

    def test_gateway_restart_restores_recorded_context_and_never_marks_it_live(self):
        store=Store(self.path/'gateway_data.sqlite3');self.stores.append(store)
        item=submission();item['reading']['recording_mode']='submitted_snapshot'
        store.enqueue(item);store.set_state(item['request_id'],'uploaded')
        receiver=receiver_app.Receiver(dict(receiver_app.DEFAULTS),storage=self.path)
        self.stores.append(receiver.gateway.store)
        current=receiver.snapshot()
        self.assertEqual(current['receiver']['state'],'stale')
        self.assertEqual(current['recorded_snapshot']['patient_id'],item['patient']['patient_id'])
        self.assertEqual(current['snapshot']['sensors']['pulse']['values'],{})

    def test_gateway_ack_means_durable_idempotent_save(self):
        gateway = self.gateway()
        item = submission()
        gateway.accept(item)
        self.assertEqual(gateway.responses.get_nowait()['state'],'pending')
        gateway.accept(item)
        self.assertEqual(gateway.store.counts(),{'pending':1})
        reopened = Store(self.path/'gateway_data.sqlite3')
        self.stores.append(reopened)
        self.assertEqual(reopened.pending()[0],item)
        changed = copy.deepcopy(item);changed['reading']['sensors']['pulse']['values']['heart_rate_bpm']=999
        gateway.accept(changed)
        gateway.responses.get_nowait()
        self.assertEqual(gateway.responses.get_nowait()['state'],'rejected')

    def test_gateway_rejects_mismatched_patient_and_full_queue_without_loss(self):
        gateway = self.gateway(config={'max_pending_records':1})
        item = submission();gateway.accept(item)
        gateway.responses.get_nowait()
        gateway.accept(submission())
        self.assertEqual(gateway.responses.get_nowait()['state'],'rejected')
        self.assertEqual(gateway.store.pending()[0],item)
        self.assertEqual(gateway.status()['unsaved_count'],1)

    def test_offline_cloud_worker_does_not_block_accept_and_recovers(self):
        online = threading.Event()
        uploaded = []
        class Backend:
            def __init__(self,config):pass
            def patients(self):return []
            def upload(self,item):
                if not online.is_set():raise OSError('Offline')
                uploaded.append(item)
        gateway = self.gateway(backend_factory=Backend)
        worker = threading.Thread(target=gateway.cloud_worker)
        worker.start()
        try:
            start = time.monotonic()
            item = submission();gateway.accept(item)
            self.assertLess(time.monotonic()-start,.5)
            time.sleep(.1)
            self.assertEqual(gateway.store.receipt(item['request_id'])['state'],'pending')
            online.set()
            deadline = time.monotonic()+4
            while not uploaded and time.monotonic()<deadline:time.sleep(.02)
            self.assertEqual(len(uploaded),1)
            self.assertEqual(uploaded[0]['reading']['patient_id'],item['patient']['patient_id'])
            self.assertEqual(gateway.store.receipt(item['request_id'])['state'],'uploaded')
        finally:
            gateway.receiver.stop.set();worker.join(3)

    def test_status_does_not_downgrade_uploaded_after_delayed_ack(self):
        sender = self.sender()
        sender.select(sender.create_patient('Patient',20,'Other'))
        item = sender.prepare_submission();sender.submit(item)
        sender._received(event('submission_ack',DEST,8,1,item['request_id'],state='uploaded',detail='Saved to Firebase'))
        sender._received(event('submission_ack',DEST,8,2,item['request_id'],state='pending',detail='Pending'))
        self.assertEqual(sender.store.receipt(item['request_id'])['state'],'uploaded')

if __name__ == '__main__':unittest.main()
