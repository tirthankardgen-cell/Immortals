"""Patient submission protocol v3 and durable bounded storage (no hardware imports)."""
import copy
from datetime import datetime, timezone
import json
import math
import re
from pathlib import Path
import sqlite3
import struct
import threading
import time
import uuid
import zlib

HEADER = struct.Struct('>2sBBIIHHI')
PATIENT_CODE = r'IMM-\d{8}-[0-9A-F]{8}-\d{5,9}'
SEXES = ('Female', 'Male', 'Other', 'Prefer not to say')
MAX_JSON, MAX_COMPRESSED = 262144, 65536

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def identifier(value):
    if not isinstance(value, str) or str(uuid.UUID(value)) != value:
        raise ValueError('Invalid unique ID')
    return value

def date(value):
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError('Invalid capture time')
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('Time must include timezone')
    return result

def profile(value):
    if not isinstance(value, dict):
        raise ValueError('Patient details required')
    patient_id = value.get('patient_id')
    if not isinstance(patient_id,str) or not re.fullmatch(PATIENT_CODE,patient_id):
        identifier(patient_id)  # Read legacy UUID patient records during migration.
    name, age, sex = value.get('name'), value.get('age'), value.get('sex')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or any(ord(c) < 32 for c in name):
        raise ValueError('Enter a patient name (1–80 characters)')
    if isinstance(age, bool) or not isinstance(age, int) or not 0 <= age <= 130:
        raise ValueError('Age must be a whole number from 0 to 130')
    if sex not in SEXES:
        raise ValueError('Choose sex')
    for key in ('created_at', 'age_recorded_at'):
        date(value.get(key))
    result = {key: value[key] for key in ('patient_id', 'name', 'age', 'sex', 'created_at', 'age_recorded_at')}
    code = value.get('patient_code')
    if code is not None:
        if not isinstance(code, str) or not re.fullmatch(PATIENT_CODE, code):
            raise ValueError('Invalid patient display ID')
        result['patient_code'] = code
    if re.fullmatch(PATIENT_CODE,patient_id) and code != patient_id:
        raise ValueError('Displayed and stored patient IDs must match')
    if value.get('patient_uuid') is not None:
        result['patient_uuid'] = identifier(value['patient_uuid'])
    return result

def event(kind, source, session, sequence, request_id=None, **data):
    return dict(schema_version=3, message_type=kind, sender_id=source,
                session_id=f'{session:08x}', sequence=sequence,
                request_id=request_id or str(uuid.uuid4()), **data)

def validate_event(message, source, session, sequence):
    if not isinstance(message, dict) or message.get('schema_version') != 3:
        raise ValueError('Unsupported patient protocol')
    if (message.get('sender_id') != source or message.get('session_id') != f'{session:08x}'
            or message.get('sequence') != sequence):
        raise ValueError('Patient identity differs from radio header')
    identifier(message.get('request_id'))
    kind = message.get('message_type')
    if kind == 'patient_submit':
        patient = profile(message.get('patient'))
        identifier(message.get('monitoring_session_id'))
        date(message.get('started_at'))
        reading = message.get('reading')
        if not isinstance(reading, dict) or reading.get('patient_id') != patient['patient_id'] or reading.get('monitoring_session_id') != message['monitoring_session_id']:
            raise ValueError('Reading has a different patient or session')
        if reading.get('sender_id') != source or reading.get('session_id') != message['session_id'] or reading.get('sequence') != sequence:
            raise ValueError('Reading identity differs from submission')
        if date(reading.get('timestamp')) < date(message['started_at']):
            raise ValueError('Capture precedes patient selection')
    elif kind == 'patient_list_request':
        offset = message.get('offset')
        if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= 10000:
            raise ValueError('Invalid list offset')
    elif kind == 'patient_list_page':
        if not isinstance(message.get('patients'), list) or len(message['patients']) > 10:
            raise ValueError('Invalid patient page')
        for item in message['patients']:
            profile(item)
        if type(message.get('next_offset')) is not int or not 0 <= message['next_offset'] <= 10000 or type(message.get('more')) is not bool:
            raise ValueError('Invalid patient page cursor')
    elif kind in ('submission_ack', 'submission_status'):
        if message.get('state') not in ('pending', 'uploaded', 'rejected', 'unknown'):
            raise ValueError('Invalid submission status')
        if not isinstance(message.get('detail', ''), str) or len(message.get('detail', '')) > 300:
            raise ValueError('Invalid submission detail')
    elif kind != 'submission_status_request':
        raise ValueError('Unknown patient message')
    return message

def frames(message, max_packet_bytes=84):
    raw = json.dumps(message, separators=(',', ':'), allow_nan=False).encode()
    if len(raw) > MAX_JSON:
        raise ValueError('Submission too large')
    compressed = zlib.compress(raw)
    if len(compressed) > MAX_COMPRESSED or not 64 <= max_packet_bytes <= 255:
        raise ValueError('Submission exceeds radio capacity')
    size = max_packet_bytes-HEADER.size
    count = math.ceil(len(compressed)/size)
    session, sequence = int(message['session_id'], 16), message['sequence']
    return [HEADER.pack(b'IM', 3, 1, session, sequence, index, count, zlib.crc32(compressed))
            + compressed[index*size:(index+1)*size] for index in range(count)]

class Assembler:
    def __init__(self, source, timeout=60):
        self.source, self.timeout = source, timeout
        self.pending = {}

    def feed(self, source, data):
        now = time.monotonic()
        self.pending = {k: v for k, v in self.pending.items() if now-v['time'] < self.timeout}
        key = None
        try:
            if source != self.source or not 21 <= len(data) <= 255:
                raise ValueError('Invalid source/size')
            magic, version, flags, session, sequence, index, count, crc = HEADER.unpack(data[:20])
            if (magic, version, flags) != (b'IM', 3, 1) or not 0 <= index < count <= 1024:
                raise ValueError('Invalid header')
            key = session, sequence
            if key not in self.pending:
                if len(self.pending) >= 4:
                    del self.pending[next(iter(self.pending))]
                self.pending[key] = dict(time=now, count=count, crc=crc, parts={})
            item = self.pending[key]
            if (count, crc) != (item['count'], item['crc']):
                raise ValueError('Conflicting fragment')
            if index in item['parts'] and item['parts'][index] != data[20:]:
                raise ValueError('Conflicting duplicate')
            item['parts'][index] = data[20:]
            if sum(map(len, item['parts'].values())) > MAX_COMPRESSED:
                raise ValueError('Compressed size exceeded')
            if len(item['parts']) < count:
                return None
            del self.pending[key]
            raw = b''.join(item['parts'][i] for i in range(count))
            if zlib.crc32(raw) != crc:
                raise ValueError('CRC mismatch')
            decoder = zlib.decompressobj()
            decoded = decoder.decompress(raw, MAX_JSON+1)
            if len(decoded) > MAX_JSON or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                raise ValueError('Invalid compression')
            def invalid(value):
                raise ValueError('Non-finite JSON')
            return validate_event(json.loads(decoded, parse_constant=invalid), source, session, sequence)
        except (ValueError, TypeError, KeyError, struct.error, zlib.error, OverflowError, RecursionError):
            self.pending.pop(key, None)
            return None

class Store:
    """SQLite WAL commits before an application ACK; bounded count and bytes."""
    def __init__(self, path, limit=500, byte_limit=32*1024*1024):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, timeout=2, check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS patients(id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS counters(id TEXT PRIMARY KEY, value INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY, data TEXT NOT NULL, state TEXT NOT NULL,
            detail TEXT NOT NULL DEFAULT '', created REAL NOT NULL);''')
        self.limit, self.byte_limit = limit, byte_limit

    def create_patient(self, name, age, sex, device):
        now = datetime.now(timezone.utc)
        # Registration date is shown in the operator's India timezone.
        from datetime import timedelta
        day = now.astimezone(timezone(timedelta(hours=5, minutes=30))).strftime('%Y%m%d')
        prefix = f'IMM-{day}-{device[-8:].upper()}'
        with self.lock, self.db:
            row = self.db.execute('SELECT value FROM counters WHERE id=?', (prefix,)).fetchone()
            counter = (row[0] if row else 0)+1
            existing = {json.loads(row[0]).get('patient_code') for row in self.db.execute('SELECT data FROM patients')}
            while f'{prefix}-{counter:05d}' in existing:
                counter += 1
            code = f'{prefix}-{counter:05d}'
            item = profile(dict(patient_id=code, patient_code=code, patient_uuid=str(uuid.uuid4()),
                                name=name.strip(), age=age, sex=sex, created_at=now.isoformat(), age_recorded_at=now.isoformat()))
            self.db.execute('INSERT OR REPLACE INTO counters VALUES (?,?)', (prefix, counter))
            self.db.execute('INSERT INTO patients VALUES (?,?)', (item['patient_id'], json.dumps(item)))
        return item

    def cache(self, patient):
        patient = profile(patient)
        with self.lock, self.db:
            old = self.db.execute('SELECT data FROM patients WHERE id=?', (patient['patient_id'],)).fetchone()
            if old and any(json.loads(old[0])[k] != patient[k] for k in ('name', 'age', 'sex')):
                raise ValueError('Patient ID already has different details')
            code = patient.get('patient_code')
            if code and any(json.loads(row[0]).get('patient_code') == code and json.loads(row[0])['patient_id'] != patient['patient_id']
                            for row in self.db.execute('SELECT data FROM patients')):
                raise ValueError('Patient display ID already belongs to another patient')
            self.db.execute('INSERT OR REPLACE INTO patients VALUES (?,?)', (patient['patient_id'], json.dumps(patient)))
        return patient

    def patients(self, search='', offset=0, limit=10000):
        with self.lock:
            items = [json.loads(row[0]) for row in self.db.execute('SELECT data FROM patients')]
        search = search.strip().casefold()
        items = [item for item in items if search in (item['name']+' '+item['patient_id']+' '+item.get('patient_code', '')).casefold()]
        return sorted(items, key=lambda p: (p['name'].casefold(), p['patient_id']))[offset:offset+limit]

    def enqueue(self, message, state='pending'):
        raw = json.dumps(message, separators=(',', ':'), allow_nan=False)
        with self.lock, self.db:
            previous = self.db.execute('SELECT data FROM outbox WHERE id=?', (message['request_id'],)).fetchone()
            if previous:
                if previous[0] != raw:
                    raise ValueError('Submission ID reused with different data')
                return False
            # Keep bounded recent receipts; pending/rejected records are never dropped.
            self.db.execute("DELETE FROM outbox WHERE id IN (SELECT id FROM outbox WHERE state='uploaded' ORDER BY created DESC LIMIT -1 OFFSET 50)")
            count, size = self.db.execute("SELECT COUNT(*),COALESCE(SUM(LENGTH(data)),0) FROM outbox WHERE state!='uploaded'").fetchone()
            if count >= self.limit or size+len(raw.encode()) > self.byte_limit:
                raise ValueError('Storage full — submission was not saved. Retry after uploads complete.')
            self.db.execute('INSERT INTO outbox VALUES (?,?,?, ?,?)', (message['request_id'], raw, state, '', time.time()))
        return True

    def set_state(self, key, state, detail=''):
        with self.lock, self.db:
            self.db.execute('UPDATE outbox SET state=?,detail=? WHERE id=?', (state, detail[:300], key))

    def receipt(self, key):
        # Draft cancellation never removes a record released for delivery.
        with self.lock:
            row = self.db.execute('SELECT state,detail FROM outbox WHERE id=?', (key,)).fetchone()
        return dict(state=row[0], detail=row[1]) if row else dict(state='unknown', detail='Not yet received')

    def discard_draft(self,key):
        with self.lock,self.db:
            self.db.execute("DELETE FROM outbox WHERE id=? AND state='draft'",(key,))

    def pending(self, states=('pending',), limit=1):
        with self.lock:
            rows = self.db.execute('SELECT data FROM outbox WHERE state IN ('+','.join('?' for _ in states)+') ORDER BY created LIMIT ?', (*states, limit)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def counts(self):
        with self.lock:
            return dict(self.db.execute('SELECT state,COUNT(*) FROM outbox GROUP BY state').fetchall())
