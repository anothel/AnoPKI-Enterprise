#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess

SPEC = importlib.util.spec_from_file_location('ha_prerequisites', Path(__file__).with_name('verify-postgres-ha-prerequisites.py'))

class PrerequisiteTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(Path(SPEC.origin).exists(), 'prerequisite runner must exist')
        self.m = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(self.m)

    def test_config_transfer_uses_unprivileged_exec(self):
        calls=[]
        def fake(args, **kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, b'', b'')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            (path/'node.key').write_text('synthetic-secret')
            with patch.object(self.m.subprocess, 'run', side_effect=fake), patch.object(self.m._primary, 'run_process', side_effect=fake):
                self.m.copy_config('owned-container',path)
        self.assertEqual(calls[0][:4], ['docker','--host=unix:///var/run/docker.sock','exec','-i'])
        self.assertNotIn('synthetic-secret',str(calls))

    def test_interrupt_during_postflight_never_preserves_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            responses=['a'*40,'b'*40,'',KeyboardInterrupt()]
            with patch.object(self.m,'command',side_effect=responses), patch.object(self.m,'live',return_value=self.m.assess(True,True,True,True)), patch.object(self.m,'cleanup'):
                with self.assertRaises(KeyboardInterrupt):
                    self.m.run(out)
            self.assertEqual(json.loads((out/'postgres-ha-prerequisites.json').read_text())['result'],'failed')

    def test_interrupt_during_cleanup_never_preserves_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            responses=['a'*40,'b'*40,'','a'*40,'']
            with patch.object(self.m,'command',side_effect=responses), patch.object(self.m,'live',return_value=self.m.assess(True,True,True,True)), patch.object(self.m,'cleanup',side_effect=KeyboardInterrupt()):
                with self.assertRaises(KeyboardInterrupt):
                    self.m.run(out)
            report=json.loads((out/'postgres-ha-prerequisites.json').read_text())
            self.assertEqual(report['result'],'failed')
            self.assertIs(report['owned_resources_removed'],False)

    def test_missing_leader_response_is_not_absence(self):
        self.assertTrue(hasattr(self.m,'leader_absent'), 'leader response validator required')
        good={'header':{'revision':1,'cluster_id':2,'member_id':3,'raft_term':4}}
        self.assertTrue(self.m.leader_absent(good))
        for state in ({}, {'header':{}}, {'header':{'revision':True}},
                      dict(good,count=1,kvs=[{'key':'leader'}]), dict(good,count=False)):
            with self.subTest(state=state), self.assertRaises(ValueError):
                self.m.leader_absent(state)

    def test_internal_network_never_uses_inherited_proxy(self):
        self.assertTrue(hasattr(self.m,'INTERNAL_PROXY_ENV'), 'explicit internal proxy overrides required')
        values=self.m.INTERNAL_PROXY_ENV
        for key in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
            self.assertEqual(values[key],'')
        self.assertEqual(values['NO_PROXY'],'*')
        self.assertEqual(values['no_proxy'],'*')

    def test_docker_target_is_local_even_with_host_override(self):
        calls=[]
        def fake(args,**kwargs):
            calls.append((args,kwargs))
            return subprocess.CompletedProcess(args,0,'ok','')
        with patch.dict(self.m.os.environ,{'DOCKER_HOST':'tcp://external.invalid:2375','PATRONI_SCOPE':'external'}), patch.object(self.m._primary,'run_process',side_effect=fake):
            self.m.command(['docker','info'])
        self.assertIn('--host=unix:///var/run/docker.sock',calls[0][0])
        self.assertNotIn('DOCKER_HOST',calls[0][1]['env'])
        self.assertNotIn('PATRONI_SCOPE',calls[0][1]['env'])

    def test_success_never_qualifies_ha(self):
        evidence = self.m.assess(True, True, True, True)
        self.assertEqual(evidence['result'], 'passed')
        self.assertIs(evidence['ha_qualified'], False)

    def test_every_observation_required(self):
        for i in range(4):
            observations = [True] * 4
            observations[i] = False
            with self.subTest(i=i), self.assertRaises(ValueError):
                self.m.assess(*observations)

    def test_no_truthy_substitutes(self):
        for bad in (1, 'true', None, [], {}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.m.assess(bad, True, True, True)

    def test_config_is_strict_and_not_trust(self):
        c = self.m.patroni_config('fixture-password')
        self.assertEqual(c['watchdog'], {'mode':'required', 'device':'/dev/watchdog', 'safety_margin':-1})
        d = c['bootstrap']['dcs']
        self.assertIs(d['synchronous_mode_strict'], True)
        self.assertIs(d['synchronous_mode'], True)
        self.assertEqual(d['postgresql']['parameters']['synchronous_commit'], 'remote_apply')
        self.assertTrue(all('trust' not in h for h in c['postgresql']['pg_hba']))
        self.assertEqual(c['etcd3']['protocol'], 'https')
        self.assertEqual(c['postgresql']['pgpass'], '/run/ha/pgpass')

    def test_failed_preflight_replaces_success_and_omits_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            target = path / 'postgres-ha-prerequisites.json'
            target.write_text('{"result":"passed","password":"old-secret"}')
            result = self.m.run(path, '0'*40)
            self.assertEqual(result['result'], 'failed')
            self.assertIs(result['ha_qualified'], False)
            self.assertNotIn('old-secret', target.read_text())
            self.assertEqual(json.loads(target.read_text()), result)

if __name__ == '__main__': unittest.main()
