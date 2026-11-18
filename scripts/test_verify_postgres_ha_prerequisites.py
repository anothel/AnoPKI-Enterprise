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

    def test_durability_cannot_be_weakened_by_local_bootstrap_override(self):
        c = self.m.patroni_config('fixture-password')
        dcs = c['bootstrap']['dcs']
        self.assertIs(dcs['failsafe_mode'], False)
        self.assertIs(type(dcs['synchronous_node_count']), int)
        self.assertEqual(dcs['synchronous_node_count'], 1)
        # Both layers reach Patroni: a local override must not undo DCS durability.
        for parameters in (dcs['postgresql']['parameters'], c['postgresql']['parameters']):
            with self.subTest(parameters=parameters):
                self.assertEqual(parameters['synchronous_commit'], 'remote_apply')
                self.assertEqual(parameters['fsync'], 'on')
                self.assertEqual(parameters['full_page_writes'], 'on')

    def test_watchdog_timing_inputs_leave_half_ttl_slack(self):
        c = self.m.patroni_config('fixture-password')
        dcs = c['bootstrap']['dcs']
        self.assertEqual(c['watchdog']['safety_margin'], -1)
        for key in ('ttl', 'loop_wait', 'retry_timeout'):
            self.assertIs(type(dcs[key]), int)
            self.assertGreater(dcs[key], 0)
        self.assertLessEqual(dcs['loop_wait'] + 2 * dcs['retry_timeout'], dcs['ttl'])
        self.assertLess(dcs['loop_wait'] + dcs['retry_timeout'], dcs['ttl'] // 2)
        # Config arithmetic is not proof of actual reset timing or timer independence.

    def test_bootstrap_database_and_rest_api_are_loopback_only(self):
        c = self.m.patroni_config('fixture-password')
        self.assertEqual(c['postgresql']['listen'], '127.0.0.1:5432')
        self.assertEqual(c['restapi']['listen'], '127.0.0.1:8008')
        for rule in c['postgresql']['pg_hba'][1:]:
            fields = rule.split()
            self.assertEqual(fields[0], 'hostssl')
            self.assertEqual(fields[-2:], ['127.0.0.1/32', 'scram-sha-256'])

    def test_disposable_guest_commands_do_not_cross_host_boundary(self):
        calls = []
        class SetupObserved(Exception):
            pass
        def capture(args, **kwargs):
            calls.append(args)
            if args[:3] == ['docker', 'exec', '-d']:
                raise SetupObserved()  # Stop before starting etcd or Patroni.
            return ''
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            for node in ('e1', 'e2', 'e3', 'pg1'):
                (work / node).mkdir()
            with patch.object(self.m, 'build_image', return_value='sha256:fixture'), \
                 patch.object(self.m, 'certificates'), patch.object(self.m, 'copy_config'), \
                 patch.object(self.m, 'command', side_effect=capture):
                with self.assertRaises(SetupObserved):
                    self.m.live(work, 'owned-run')
        network = next(args for args in calls if args[:3] == ['docker', 'network', 'create'])
        self.assertIn('--internal', network)
        guests = [args for args in calls if args[:2] == ['docker', 'run']]
        self.assertEqual(len(guests), 4)
        for args in guests:
            with self.subTest(guest=args[args.index('--name') + 1]):
                self.assertEqual(args[args.index('--network') + 1], 'owned-run-net')
                self.assertEqual(args[args.index('--user') + 1], '999:999')
                self.assertIn('--restart=no', args)
                self.assertIn('--read-only', args)
                self.assertIn('--cap-drop=ALL', args)
                self.assertEqual(args[args.index('--security-opt') + 1], 'no-new-privileges')
                forbidden = ('--privileged', '--device', '--mount', '--volume', '-v',
                             '--publish', '--publish-all', '-p', '-P', '--pid', '--cap-add')
                self.assertFalse(any(arg.split('=', 1)[0] in forbidden for arg in args))

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
