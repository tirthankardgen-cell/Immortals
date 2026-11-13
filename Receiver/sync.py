"""Sync this role's source to its own Pi. Runtime data and environments stay local."""
import argparse
from getpass import getpass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import time
import paramiko

ROOT=Path(__file__).resolve().parent
ROLE=ROOT.name
HOST,REMOTE,PIN={
    'Sender':('192.168.137.88','/home/pi/Desktop/Immortals_Monitor','451ef3f32e84752ed6a654d74e5e684c'),
    'Receiver':('immortals-recv.local','/home/pi/Desktop/Immortals_Receiver','c089f27e5237d13e6418f6bb45279457')
}[ROLE]
EXCLUDED={'__pycache__','.venv','venv','logs','settings.json','latest_readings.json',
          'last_packet.json','source-sha256.json','.receiver.lock'}


def sources(refresh=False):
    if ROLE=='Sender' and refresh:
        latest=ROOT/'versions/02_latest_zigbee'
        latest.mkdir(parents=True,exist_ok=True)
        for name in ('main.py','pi5_sensor_monitor.py','requirements.txt','zigbee_config.json','ZIGBEE_PROTOCOL.md'):
            if (ROOT/name).exists():shutil.copy2(ROOT/name,latest/name)
    return sorted(p for p in ROOT.rglob('*') if p.is_file()
                  and not any(part in EXCLUDED for part in p.relative_to(ROOT).parts)
                  and p.suffix in ('.py','.md','.json','.txt','.html','.desktop','.service'))


def manifest(files):
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


class Pinned(paramiko.MissingHostKeyPolicy):
    def missing_host_key(self,client,hostname,key):
        if key.get_fingerprint().hex()!=PIN:raise RuntimeError(f'{ROLE} Pi SSH identity changed')


def synchronize(client,push):
    files=sources(refresh=push)
    expected=manifest(files)
    failures=[]
    with client.open_sftp() as s:
        for file in files:
            relative=file.relative_to(ROOT).as_posix();target=REMOTE+'/'+relative
            try:
                with s.open(target,'rb') as f:actual=hashlib.sha256(f.read()).hexdigest()
            except FileNotFoundError:actual=None
            if actual!=expected[relative] and push:
                parents=list(PurePosixPath(target).parents)
                for parent in reversed(parents):
                    if str(parent)==REMOTE or str(parent).startswith(REMOTE+'/'):
                        try:s.stat(str(parent))
                        except FileNotFoundError:s.mkdir(str(parent))
                s.put(str(file),target+'.sync-tmp');s.posix_rename(target+'.sync-tmp',target)
                with s.open(target,'rb') as f:actual=hashlib.sha256(f.read()).hexdigest()
            if actual!=expected[relative]:failures.append(relative)
        if failures:raise RuntimeError('Source differs: '+', '.join(failures))
        if push:
            data=(json.dumps(expected,indent=2)+'\n').encode()
            (ROOT/'source-sha256.json').write_bytes(data)
            with s.open(REMOTE+'/source-sha256.json.sync-tmp','wb') as f:f.write(data)
            s.posix_rename(REMOTE+'/source-sha256.json.sync-tmp',REMOTE+'/source-sha256.json')
    print(f'{ROLE}: {len(expected)} source files match {HOST}',flush=True)
    return manifest(sources())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--push',action='store_true',help='Copy laptop source to Pi; default only verifies')
    parser.add_argument('--watch',action='store_true',help='Keep syncing changed laptop source until Ctrl+C')
    args=parser.parse_args()
    password=os.environ.get('PI_SSH_PASSWORD') or getpass(f'Password for pi@{HOST}: ')
    client=paramiko.SSHClient();client.set_missing_host_key_policy(Pinned())
    try:
        client.connect(HOST,username='pi',password=password,timeout=15,allow_agent=False,look_for_keys=False)
        last=synchronize(client,args.push or args.watch)
        while args.watch:
            time.sleep(1)
            current=manifest(sources())
            if current!=last:last=synchronize(client,True)
    except KeyboardInterrupt:print('Sync stopped.')
    finally:client.close()


if __name__=='__main__':main()
