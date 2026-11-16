#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
import importlib.util
import json
from pathlib import Path
import unittest
import tempfile
import subprocess
import sys
import time

spec = importlib.util.spec_from_file_location('primary', Path(__file__).with_name('verify-postgres-primary.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class EvidenceTests(unittest.TestCase):
    def events(self):
        events = []
        for name in m.TESTS:
            metric = dict(scenario=name, fence_seconds=.1, promotion_seconds=.2,
                          reconnect_seconds=.3, acknowledged_lost=int('Async' in name),
                          state_digest='not-applicable' if 'Async' in name else 'a'*64)
            events += [dict(Action='output', Package=m.PACKAGE, Test=name, Output='PHASE3_METRIC '+json.dumps(metric)+'\n'),
                       dict(Action='pass', Package=m.PACKAGE, Test=name)]
        events.append(dict(Action='pass', Package=m.PACKAGE))
        return events
    def parse(self, events):
        return m.parse_events('\n'.join(json.dumps(e) for e in events))
    def test_complete(self):
        self.assertEqual(len(self.parse(self.events())), 4)
    def test_missing_skip_conflict_duplicate(self):
        for action in ('skip','fail','pass'):
            events=self.events()+[dict(Action=action,Package=m.PACKAGE,Test=m.TESTS[0])]
            with self.assertRaises(ValueError): self.parse(events)
        with self.assertRaises(ValueError): self.parse(self.events()[1:])
        with self.assertRaises(ValueError): self.parse(self.events()[:-1])
    def test_metrics_rejected(self):
        for field,value in [('reconnect_seconds',-.1),('promotion_seconds',float('nan')),
                            ('acknowledged_lost',1),('state_digest','secret'),('credential','hidden')]:
            events=self.events()
            metric=json.loads(events[0]['Output'].split('PHASE3_METRIC ')[1])
            metric[field]=value
            events[0]['Output']='PHASE3_METRIC '+json.dumps(metric)
            with self.assertRaises(ValueError): self.parse(events)
    def test_wrong_package_and_missing_metric(self):
        events=self.events();events[0]['Package']='other'
        with self.assertRaises(ValueError): self.parse(events)
        events=self.events();events[0]['Output']='ordinary diagnostic'
        with self.assertRaises(ValueError): self.parse(events)
    def test_failed_preflight_replaces_previous_success(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            report=out/'postgres-primary-verification.json'
            report.write_text('{"result":"passed"}')
            result=m.run(out,'0'*40)
            self.assertEqual(result['result'],'failed')
            self.assertEqual(json.loads(report.read_text())['measurements'],[])
    def test_timeout_terminates_descendants(self):
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/'survivor'
            code="import os,time; child=os.fork(); time.sleep(.5 if child==0 else 10); open("+repr(str(marker))+",'w').write('alive')"
            with self.assertRaises(subprocess.TimeoutExpired):
                m.run_process([sys.executable,'-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=.1)
            time.sleep(.6)
            self.assertFalse(marker.exists())
    def test_arbitrary_diagnostics_not_exported(self):
        events=self.events()+[dict(Action='output',Package=m.PACKAGE,Output='password=do-not-export')]
        self.assertNotIn('do-not-export',json.dumps(self.parse(events)))

if __name__ == '__main__': unittest.main()
