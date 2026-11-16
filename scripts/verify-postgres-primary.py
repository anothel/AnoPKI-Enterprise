#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Fail-closed disposable primary qualification. Export only typed measurements."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import signal
import uuid

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'github.com/anothel/anopki/service/internal/lifecycle'
TESTS = tuple('TestPostgresPrimary'+name+'Integration' for name in
              ('IssuanceFailover','CRLFailover','OutboxTrafficShift','AsyncLoss'))
FIELDS = {'scenario','fence_seconds','promotion_seconds','reconnect_seconds','acknowledged_lost','state_digest'}

def parse_events(output):
    terminal = {name: [] for name in TESTS}
    metrics = {}
    packages = []
    for line in output.splitlines():
        try: event = json.loads(line)
        except ValueError: continue
        if not isinstance(event, dict) or event.get('Package') != PACKAGE: continue
        name, action = event.get('Test'), event.get('Action')
        if action in ('pass','fail','skip'):
            if name in terminal: terminal[name].append(action)
            elif not name: packages.append(action)
        content = event.get('Output','')
        if name in terminal and isinstance(content,str) and 'PHASE3_METRIC ' in content:
            if name in metrics: raise ValueError('duplicate metric')
            metric = json.loads(content.split('PHASE3_METRIC ',1)[1])
            if not isinstance(metric,dict) or set(metric) != FIELDS or metric['scenario'] != name:
                raise ValueError('invalid metric fields')
            times = [metric[key] for key in ('fence_seconds','promotion_seconds','reconnect_seconds')]
            if any(type(v) not in (float,int) or not math.isfinite(v) or v < 0 for v in times) or times != sorted(times):
                raise ValueError('invalid recovery times')
            loss = int('Async' in name)
            if type(metric['acknowledged_lost']) is not int or metric['acknowledged_lost'] != loss:
                raise ValueError('unexpected data loss')
            digest = metric['state_digest']
            if not isinstance(digest,str) or (digest != 'not-applicable' if loss else re.fullmatch('[a-f0-9]{64}',digest) is None):
                raise ValueError('invalid state digest')
            metrics[name] = metric
    if packages != ['pass'] or any(v != ['pass'] for v in terminal.values()) or set(metrics) != set(TESTS):
        raise ValueError('missing, skipped, failed or conflicting required results')
    return [metrics[name] for name in TESTS]

def run_process(args, **kwargs):
    # Kill/reap the whole test process group before enumerating owned Docker resources.
    timeout=kwargs.pop('timeout')
    with subprocess.Popen(args,start_new_session=True,**kwargs) as process:
        try:
            stdout,stderr=process.communicate(timeout=timeout)
        except BaseException:
            try: os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            process.communicate()
            raise
        return subprocess.CompletedProcess(args,process.returncode,stdout,stderr)

def run(out, explicit=''):
    out.mkdir(parents=True,exist_ok=True)
    report = {'schema_version':1,'evidence_type':'enterprise_postgres_primary_failover',
              'result':'failed','commit':'unavailable','measurements':[],
              'cryptographic_backend_executed':False,'blocker':'incomplete'}
    target = out/'postgres-primary-verification.json'
    run_id=uuid.uuid4().hex
    started=False
    def save():
        report['completed_at']=datetime.now(timezone.utc).isoformat()
        target.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    save()  # Replace old success before any fallible preflight.
    def command(args, cwd=ROOT, timeout=30, env=None):
        result=run_process(args,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout)
        if result.returncode: raise ValueError('qualification command failed; diagnostics omitted')
        return result.stdout.strip()
    try:
        commit=command(['git','rev-parse','HEAD'])
        if not re.fullmatch('[a-f0-9]{40}',commit) or (explicit and explicit != commit):
            raise ValueError('exact checkout commit mismatch')
        report['commit']=commit
        report['tree']=command(['git','rev-parse','HEAD^{tree}'])
        if command(['git','status','--porcelain']): raise ValueError('clean checkout required')
        report['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__),ROOT/'service/internal/lifecycle/enterprise_postgres_primary_test.go',
                      ROOT/'service/internal/lifecycle/enterprise_postgres_topology_test.go']}
        environment={key:value for key,value in os.environ.items() if not key.startswith('PG')}
        environment['ANOPKI_POSTGRES_PRIMARY_DISPOSABLE']='1'
        environment['ANOPKI_POSTGRES_PRIMARY_RUN_ID']=run_id
        environment['GOTOOLCHAIN']='local'
        environment['GOWORK']='off'
        environment['GOFLAGS']=''
        environment['GOENV']='off'
        version=command(['go','version'],env=environment)
        match=re.search(r'go(\d+)\.(\d+)\.(\d+)',version)
        if not match or tuple(map(int,match.groups())) < (1,26,11): raise ValueError('Go 1.26.11+ required')
        report['go_version']='.'.join(match.groups())
        started=True
        output=command(['go','test','-race','-json','-count=1','-timeout=12m','-run','^('+'|'.join(TESTS)+')$','./internal/lifecycle'],cwd=ROOT/'service',timeout=780,env=environment)
        report['measurements']=parse_events(output)
        # Do not export raw diagnostics or arbitrary subprocess output.
        if command(['git','rev-parse','HEAD']) != commit or command(['git','status','--porcelain']):
            raise ValueError('source changed during qualification')
        report['result']='passed'
        report['blocker']=''
    except (OSError,subprocess.SubprocessError,ValueError):
        report['result']='failed'
        report['measurements']=[]
        report['blocker']='qualification failed or incomplete; diagnostics omitted'
    finally:
        if started:
            try:
                label='label=com.anopki.phase3.run='+run_id
                containers=command(['docker','ps','-aq','--filter',label]).split()
                if containers: command(['docker','rm','-f','-v',*containers])
                networks=command(['docker','network','ls','-q','--filter',label]).split()
                if networks: command(['docker','network','rm',*networks])
                report['owned_resources_removed']=True
            except (OSError,subprocess.SubprocessError,ValueError):
                report['result']='failed'
                report['blocker']='owned resource cleanup failed; diagnostics omitted'
                report['owned_resources_removed']=False
    save()
    return report

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'.tmp/postgres-primary')
    parser.add_argument('--commit',default='')
    args=parser.parse_args()
    result=run(args.out_dir,args.commit)
    print('PostgreSQL primary qualification: '+result['result'])
    raise SystemExit(0 if result['result']=='passed' else 1)
