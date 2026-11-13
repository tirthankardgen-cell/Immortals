"""Source-only synchronization of this v2 role to its own Raspberry Pi."""
import argparse
from getpass import getpass
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import paramiko
ROOT=Path(__file__).resolve().parent
HOST,REMOTE,PIN={
 'Sender_v2':('192.168.137.88','/home/pi/Desktop/Immortals_Monitor_v2','451ef3f32e84752ed6a654d74e5e684c'),
 'Receiver_v2':('immortals-recv.local','/home/pi/Desktop/Immortals_Receiver_v2','c089f27e5237d13e6418f6bb45279457')
}[ROOT.name]
EXCLUDED={'__pycache__','.venv','venv','logs','settings.json','latest_readings.json','last_packet.json','source-sha256.json'}

def synchronize(client,push=False):
    sources=sorted(p for p in ROOT.rglob('*') if p.is_file() and p.suffix in ('.py','.md','.json','.txt','.html','.service','.desktop')
                   and not any(part in EXCLUDED for part in p.relative_to(ROOT).parts))
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    failures=[]
    with client.open_sftp() as s:
        for p in sources:
            relative=p.relative_to(ROOT).as_posix();target=REMOTE+'/'+relative
            try:
                with s.open(target,'rb') as f:actual=hashlib.sha256(f.read()).hexdigest()
            except FileNotFoundError:actual=None
            if push and actual!=hashes[relative]:
                for directory in reversed(list(PurePosixPath(target).parents)):
                    if str(directory)==REMOTE or str(directory).startswith(REMOTE+'/'):
                        try:s.stat(str(directory))
                        except FileNotFoundError:s.mkdir(str(directory))
                s.put(str(p),target+'.sync-tmp');s.posix_rename(target+'.sync-tmp',target)
                with s.open(target,'rb') as f:actual=hashlib.sha256(f.read()).hexdigest()
            if actual!=hashes[relative]:failures.append(relative)
        if failures:raise RuntimeError('Source mismatch: '+', '.join(failures))
        if push:
            data=json.dumps(hashes,indent=2)+'\n'
            (ROOT/'source-sha256.json').write_text(data)
            with s.open(REMOTE+'/source-sha256.json','w') as f:f.write(data)
    print(f'{ROOT.name}: {len(hashes)} source files match {HOST}')
    return hashes

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--push',action='store_true');args=parser.parse_args()
    class Pinned(paramiko.MissingHostKeyPolicy):
        def missing_host_key(self,client,hostname,key):
            if key.get_fingerprint().hex()!=PIN:raise RuntimeError('Pi SSH identity changed')
    client=paramiko.SSHClient();client.set_missing_host_key_policy(Pinned())
    try:
        client.connect(HOST,username='pi',password=os.environ.get('PI_SSH_PASSWORD') or getpass(f'Password for pi@{HOST}: '),timeout=15,allow_agent=False,look_for_keys=False)
        synchronize(client,args.push)
    finally:client.close()
if __name__=='__main__':main()
