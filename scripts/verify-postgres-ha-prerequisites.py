#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Disposable required-watchdog bootstrap refusal; never full HA qualification."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/ha'
LABEL = 'com.anopki.phase4.prerequisite'
INTERNAL_PROXY_ENV = {key:'' for key in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy')}
INTERNAL_PROXY_ENV.update(NO_PROXY='*',no_proxy='*')
_spec = importlib.util.spec_from_file_location('primary_runner', ROOT/'scripts/verify-postgres-primary.py')
_primary = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_primary)


def process(args, **kwargs):
    # Never let inherited Docker context redirect owned-resource operations remotely.
    env = {k:v for k,v in os.environ.items() if not k.startswith(('PG', 'PATRONI_', 'DOCKER_'))}
    if args[0]=='docker':
        args=['docker','--host=unix:///var/run/docker.sock',*args[1:]]
    return _primary.run_process(args,env=env,**kwargs)


def command(args, timeout=60):
    # Share the Phase 3 process-group timeout handling, not its HA policy.
    result = process(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                     text=True, timeout=timeout)
    if result.returncode:
        raise ValueError('command failed; diagnostics omitted')
    return result.stdout.strip()


def assess(quorum, watchdog_refused, postgres_stopped, leader_absent):
    if any(v is not True for v in (quorum, watchdog_refused, postgres_stopped, leader_absent)):
        raise ValueError('required observation absent')
    return {'result':'passed', 'ha_qualified':False,
            'observations':{'three_member_quorum':True, 'watchdog_bootstrap_refused':True,
                            'postgres_stopped':True, 'leader_key_absent':True}}


def leader_absent(state):
    if not isinstance(state,dict) or not isinstance(state.get('header'),dict):
        raise ValueError('missing DCS observation')
    if any(type(state['header'].get(k)) is not int or state['header'][k] <= 0
           for k in ('revision','cluster_id','member_id','raft_term')):
        raise ValueError('invalid DCS header')
    # etcd omits protobuf default count=0 and empty kvs; a header is still required.
    if type(state.get('count',0)) is not int or state.get('count',0)!=0 or state.get('kvs',[])!=[]:
        raise ValueError('leader present or invalid response')
    return True


def patroni_config(password):
    params = {'synchronous_commit':'remote_apply', 'fsync':'on', 'full_page_writes':'on',
              'password_encryption':'scram-sha-256', 'unix_socket_directories':'/tmp', 'ssl':'on',
              'ssl_cert_file':'/run/ha/node.crt', 'ssl_key_file':'/run/ha/node.key',
              'ssl_ca_file':'/run/ha/ca.crt'}
    return {'scope':'phase4', 'name':'pg1', 'namespace':'/anopki/',
        'restapi':{'listen':'127.0.0.1:8008', 'connect_address':'pg1:8008',
                   'authentication':{'username':'observer','password':password},
                   'certfile':'/run/ha/node.crt', 'keyfile':'/run/ha/node.key'},
        'etcd3':{'hosts':['e1:2379','e2:2379','e3:2379'], 'protocol':'https',
                 'cacert':'/run/ha/ca.crt', 'cert':'/run/ha/node.crt','key':'/run/ha/node.key'},
        'watchdog':{'mode':'required','device':'/dev/watchdog','safety_margin':-1},
        'bootstrap':{'dcs':{'ttl':30,'loop_wait':5,'retry_timeout':5,
                            'synchronous_mode':True,'synchronous_mode_strict':True,
                            'synchronous_node_count':1,'failsafe_mode':False,
                            'postgresql':{'parameters':params}},
                     'initdb':[{'encoding':'UTF8'},'data-checksums',{'auth-local':'scram-sha-256'},
                               {'auth-host':'scram-sha-256'}]},
        'postgresql':{'listen':'127.0.0.1:5432','connect_address':'pg1:5432',
                      'pgpass':'/run/ha/pgpass',
                      'data_dir':'/var/lib/postgresql/data/pgdata','bin_dir':'/usr/lib/postgresql/16/bin',
                      'authentication':{'superuser':{'username':'postgres','password':password,
                                                     'sslmode':'verify-full','sslrootcert':'/run/ha/ca.crt'},
                                        'replication':{'username':'replicator','password':password,
                                                       'sslmode':'verify-full','sslrootcert':'/run/ha/ca.crt'}},
                      'parameters':params,
                      'pg_hba':['local all all scram-sha-256',
                                'hostssl all all 127.0.0.1/32 scram-sha-256',
                                'hostssl replication replicator 127.0.0.1/32 scram-sha-256']}}


def build_image(work, tag):
    context = work/'build'; context.mkdir(); inputs = context/'inputs'; inputs.mkdir()
    manifest = json.loads((FIXTURE/'inputs.json').read_text())
    for item in manifest['artifacts']:
        filename = item['filename']
        if Path(filename).name != filename or not item['url'].startswith('https://files.pythonhosted.org/'):
            raise ValueError('invalid fixture artifact')
        # Downloads bounded to reviewed package files, never execute host package setup.
        with urllib.request.urlopen(item['url'], timeout=30) as response:
            data = response.read(20*1024*1024+1)
        if len(data)>20*1024*1024 or hashlib.sha256(data).hexdigest()!=item['sha256']:
            raise ValueError('fixture artifact hash mismatch')
        (inputs/filename).write_bytes(data)
    for name in ('Dockerfile','requirements.txt','build-requirements.txt'):
        shutil.copyfile(FIXTURE/name, context/name)
    command(['docker','build','--network=none','--label',LABEL+'='+tag,'-t',tag,str(context)], timeout=300)
    return command(['docker','image','inspect','-f','{{.Id}}',tag])


def certificates(work):
    ca = work/'ca'; ca.mkdir(mode=0o700)
    command(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
             '-subj','/CN=disposable-phase4-ca','-keyout',str(ca/'ca.key'),'-out',str(ca/'ca.crt')])
    for name in ('e1','e2','e3','pg1'):
        directory = work/name; directory.mkdir(mode=0o700)
        command(['openssl','req','-newkey','rsa:2048','-nodes','-subj','/CN='+name,
                 '-keyout',str(directory/'node.key'),'-out',str(directory/'node.csr')])
        (directory/'extensions').write_text('subjectAltName=DNS:'+name+',DNS:localhost,IP:127.0.0.1\nextendedKeyUsage=serverAuth,clientAuth\n')
        command(['openssl','x509','-req','-in',str(directory/'node.csr'),'-CA',str(ca/'ca.crt'),
                 '-CAkey',str(ca/'ca.key'),'-CAcreateserial','-days','1','-extfile',str(directory/'extensions'),
                 '-out',str(directory/'node.crt')])
        shutil.copyfile(ca/'ca.crt', directory/'ca.crt')
        (directory/'node.key').chmod(0o600)
    return work


def copy_config(container, directory):
    # Extract as the unprivileged container user into tmpfs, retaining read-only root.
    with tempfile.TemporaryFile() as stream:
        with tarfile.open(fileobj=stream, mode='w') as archive:
            for name in ('ca.crt','node.crt','node.key','patroni.json'):
                path = directory/name
                if path.exists():
                    info = archive.gettarinfo(str(path), arcname=name)
                    info.uid = info.gid = 999
                    info.mode = 0o600
                    with path.open('rb') as data: archive.addfile(info,data)
        stream.seek(0)
        result = process(['docker','exec','-i',container,'tar','xf','-',
                                     '--no-same-owner','-C','/run/ha'],stdin=stream,
                                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        if result.returncode: raise ValueError('config copy failed; diagnostics omitted')


def live(work, tag):
    image = build_image(work, tag)
    certificates(work)
    network = tag+'-net'
    command(['docker','network','create','--internal','--label',LABEL+'='+tag,network])
    containers = {}
    for node in ('e1','e2','e3','pg1'):
        name = tag+'-'+node
        command(['docker','run','-d','--init','--name',name,'--label',LABEL+'='+tag,
                 '--network',network,'--network-alias',node,'--restart=no',
                 '--security-opt','no-new-privileges','--cap-drop=ALL',
                 '--user','999:999', '--read-only',
                 '--tmpfs','/run/ha:rw,mode=0700,uid=999,gid=999',
                 '--tmpfs','/var/lib/postgresql/data:rw,mode=0700,uid=999,gid=999',
                 '--tmpfs','/tmp:rw,mode=1777',
                 *[arg for k,v in INTERNAL_PROXY_ENV.items() for arg in ('-e',k+'='+v)], image])
        containers[node] = name
        if node=='pg1':
            (work/node/'patroni.json').write_text(json.dumps(patroni_config(uuid.uuid4().hex)))
        copy_config(name,work/node)
    initial = ','.join(n+'=https://'+n+':2380' for n in ('e1','e2','e3'))
    for node in ('e1','e2','e3'):
        args = ['docker','exec','-d',containers[node],'etcd','--name',node,
                '--data-dir','/tmp/etcd','--log-outputs','/tmp/etcd.log','--listen-client-urls','https://0.0.0.0:2379',
                '--advertise-client-urls','https://'+node+':2379',
                '--listen-peer-urls','https://0.0.0.0:2380',
                '--initial-advertise-peer-urls','https://'+node+':2380',
                '--initial-cluster',initial,'--initial-cluster-token',tag,
                '--client-cert-auth','--trusted-ca-file','/run/ha/ca.crt',
                '--cert-file','/run/ha/node.crt','--key-file','/run/ha/node.key',
                '--peer-client-cert-auth','--peer-trusted-ca-file','/run/ha/ca.crt',
                '--peer-cert-file','/run/ha/node.crt','--peer-key-file','/run/ha/node.key']
        command(args)
    ctl = ['docker','exec',containers['e1'],'etcdctl',
           '--endpoints=https://e1:2379,https://e2:2379,https://e3:2379',
           '--cacert=/run/ha/ca.crt','--cert=/run/ha/node.crt','--key=/run/ha/node.key']
    deadline = time.monotonic()+45
    while True:
        try:
            health=json.loads(command(ctl+['endpoint','health','-w','json'],timeout=10))
            if len(health)==3 and all(x.get('health') is True for x in health): break
        except (ValueError,subprocess.SubprocessError): pass
        if time.monotonic()>=deadline: raise ValueError('quorum unavailable')
        time.sleep(.2)
    # Deliberately absent device. No host device is mounted or opened.
    command(['docker','exec',containers['pg1'],'test','!','-e','/dev/watchdog'])
    started=time.monotonic()
    # Patroni's bootstrap cancellation exits nonzero; retain only an exact recognized event.
    result=process(['docker','exec',containers['pg1'],'patroni','/run/ha/patroni.json'],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=90)
    refused=(result.returncode!=0 and 'Cancelling bootstrap because watchdog activation failed' in result.stderr)
    stopped=command(['docker','exec',containers['pg1'],'python','-c',
        'import psutil; print(int(not any(p.name() == "postgres" and p.status() != psutil.STATUS_ZOMBIE for p in psutil.process_iter())))'])=='1'
    state=json.loads(command(ctl+['get','/anopki/phase4/leader','-w','json']))
    absent=leader_absent(state)
    report=assess(True,refused,stopped,absent)
    report['observation_seconds']=time.monotonic()-started
    report['image_id']=image
    return report


def cleanup(tag):
    selector='label='+LABEL+'='+tag
    ids=command(['docker','ps','-aq','--filter',selector]).split()
    if ids: command(['docker','rm','-f','-v',*ids])
    ids=command(['docker','network','ls','-q','--filter',selector]).split()
    if ids: command(['docker','network','rm',*ids])
    # Only the unique local test tag; never prune shared images or cache.
    ids=command(['docker','image','ls','-q','--filter','reference='+tag]).split()
    if ids: command(['docker','image','rm',tag])


def run(out, explicit=''):
    out.mkdir(parents=True,exist_ok=True)
    target=out/'postgres-ha-prerequisites.json'
    report={'schema_version':1,'evidence_type':'enterprise_postgres_ha_watchdog_prerequisite',
            'result':'failed','ha_qualified':False,'commit':'unavailable','observations':{},
            'blocker':'incomplete','cryptographic_backend_executed':False}
    def save():
        report['completed_at']=datetime.now(timezone.utc).isoformat()
        target.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    save()
    tag='anopki-p4-'+uuid.uuid4().hex
    started=False
    try:
        commit=command(['git','rev-parse','HEAD'])
        report['commit']=commit
        report['tree']=command(['git','rev-parse','HEAD^{tree}'])
        if not re.fullmatch('[a-f0-9]{40}',commit) or explicit and explicit!=commit:
            raise ValueError('commit mismatch')
        if command(['git','status','--porcelain']): raise ValueError('clean checkout required')
        sources=[Path(__file__),ROOT/'scripts/verify-postgres-primary.py',*sorted(FIXTURE.iterdir())]
        report['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources if p.is_file()}
        report['patroni_source_commit']=json.loads((FIXTURE/'inputs.json').read_text())['patroni_source_commit']
        started=True
        with tempfile.TemporaryDirectory(prefix='anopki-p4-') as directory:
            report.update(live(Path(directory),tag))
        if command(['git','rev-parse','HEAD'])!=commit or command(['git','status','--porcelain']):
            raise ValueError('source changed')
        report['blocker']=''
    except BaseException as error:
        report.update(result='failed',observations={},blocker='prerequisite failed; diagnostics omitted')
        if not isinstance(error,Exception):
            raise
    finally:
        if started:
            try:
                cleanup(tag)
                report['owned_resources_removed']=True
            except BaseException as error:
                report.update(result='failed',owned_resources_removed=False,blocker='owned cleanup failed')
                if not isinstance(error,Exception):
                    save()
                    raise
        save()
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'.tmp/postgres-ha-prerequisites')
    parser.add_argument('--commit',default='')
    args=parser.parse_args()
    report=run(args.out_dir,args.commit)
    print('Watchdog prerequisite: '+report['result']+'; HA remains unqualified')
    raise SystemExit(0 if report['result']=='passed' else 1)
