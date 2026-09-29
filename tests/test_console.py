from __future__ import annotations
import importlib.util
import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import configure
import install


class ConsoleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.target = Path(self.temp.name)
        self.assertEqual(install.main([str(self.target)]), 0)
        self.settings = configure.Settings(install, ROOT, self.target)

    def tearDown(self):
        self.temp.cleanup()

    def payload(self):
        read = self.settings.read()
        return {'preset': 'economy', 'routing': read['presets']['economy'], 'max_parallelism': 2}

    def test_preview_save_restore_preserves_unrelated_settings(self):
        path = self.target / '.claude/settings.json'
        original = json.loads(path.read_text())
        original['permissions'] = {'deny': ['Write(secret)']}
        original['env']['KEEP_PRIVATE'] = 'do-not-return'
        path.write_text(json.dumps(original))
        before = path.read_bytes()
        payload = self.payload()
        preview = self.settings.plan(payload)[2]
        self.assertEqual(path.read_bytes(), before)
        self.assertNotIn('do-not-return', json.dumps(preview))
        payload['revision'] = preview['revision']
        self.settings.save(payload)
        changed = json.loads(path.read_text())
        self.assertEqual(changed['permissions'], original['permissions'])
        self.assertEqual(changed['env']['KEEP_PRIVATE'], 'do-not-return')
        self.assertEqual(changed['env']['CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS'], '2')
        self.settings.restore()
        self.assertEqual(path.read_bytes(), before)

    def test_fresh_project_save_installs_and_preserves_shared_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            (target / '.claude').mkdir()
            (target / '.claude/settings.json').write_text(json.dumps({'permissions': {'deny':['Read(secret)']}}))
            settings = configure.Settings(install, ROOT, target)
            payload = self.payload()
            preview = settings.plan(payload)[2]
            self.assertTrue(preview['initial_install'])
            self.assertFalse((target / install.MANIFEST_RELATIVE).exists())
            payload['revision'] = preview['revision']
            settings.save(payload)
            self.assertTrue((target / '.claude/tools/console/app.js').exists())
            self.assertEqual(json.loads((target / '.claude/settings.json').read_text())['permissions']['deny'], ['Read(secret)'])
            settings.restore()
            self.assertEqual(json.loads((target / '.claude/settings.json').read_text()), {'permissions': {'deny':['Read(secret)']}})

    def test_initial_save_rejects_all_symlink_destinations_before_any_write(self):
        cases = [('.claude/tools', True), ('.claude/tools/console', True),
                 ('.claude/tools/local_eval.py', False),
                 ('.claude/skills/ui-design', True), ('CLAUDE.md', False),
                 ('.claude/bounded-orchestrator.settings.example.json', False),
                 ('.claude/.bounded-orchestrator', True),
                 ('.claude/.bounded-orchestrator/backups', True),
                 ('.claude/.bounded-orchestrator/install.json', False),
                 ('.claude/.bounded-orchestrator/console-update.json', False)]
        def snapshot(root):
            records = {}
            for path in sorted(root.rglob('*')):
                name = str(path.relative_to(root))
                if path.is_symlink():
                    records[name] = ('symlink', str(path.readlink()))
                elif path.is_file():
                    records[name] = ('file', path.read_bytes())
                else:
                    records[name] = ('directory', None)
            return records
        for relative, directory in cases:
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                target, outside = root / 'project', root / 'outside'
                target.mkdir(); outside.mkdir()
                (outside / 'sentinel.txt').write_text('unchanged')
                (target / '.claude').mkdir()
                (target / '.claude/settings.json').write_text('{"permissions":{"deny":["Read(secret)"]}}')
                settings = configure.Settings(install, ROOT, target)
                payload = self.payload()
                payload['revision'] = settings.plan(payload)[2]['revision']
                link = target / relative
                link.parent.mkdir(parents=True, exist_ok=True)
                destination = outside if directory else outside / 'destination.json'
                if not directory:
                    # A valid empty manifest allows the attack to reach initial-install preflight.
                    destination.write_text(json.dumps({'schema': 1, 'files': {}, 'claude_block': False}))
                link.symlink_to(destination, target_is_directory=directory)
                before = snapshot(root)
                with self.assertRaises(ValueError): settings.plan(payload)
                with self.assertRaises(ValueError): settings.save(payload)
                self.assertEqual(snapshot(root), before, 'Rejection must precede target/external writes')

    def test_restore_refuses_changed_manifest_preserving_external_provider(self):
        payload = self.payload()
        payload['revision'] = self.settings.plan(payload)[2]['revision']
        self.settings.save(payload)
        self.assertEqual(install.main([str(self.target), '--preset', 'economy', '--external-openai']), 0)
        manifest_path = self.target / install.MANIFEST_RELATIVE
        mcp_path = self.target / '.mcp.json'
        before_manifest, before_mcp = manifest_path.read_bytes(), mcp_path.read_bytes()
        self.assertTrue(json.loads(before_manifest)['external_openai'])
        settings_path = self.target / '.claude/settings.json'
        before_settings = settings_path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'manifest changed'):
            self.settings.restore()
        self.assertEqual(manifest_path.read_bytes(), before_manifest)
        self.assertEqual(mcp_path.read_bytes(), before_mcp)
        self.assertEqual(settings_path.read_bytes(), before_settings)

    def test_stale_preview_agent_conflict_restore_conflict(self):
        payload = self.payload()
        payload['revision'] = self.settings.plan(payload)[2]['revision']
        path = self.target / '.claude/settings.json'
        path.write_text(path.read_text() + ' ')
        with self.assertRaises(ValueError): self.settings.save(payload)
        payload['revision'] = self.settings.plan(payload)[2]['revision']
        self.settings.save(payload)
        path.write_text(path.read_text() + ' ')
        with self.assertRaises(ValueError): self.settings.restore()
        agent = self.target / '.claude/agents/explorer.md'
        agent.write_text(agent.read_text() + 'changed')
        with self.assertRaises(ValueError): self.settings.plan(self.payload())

    def test_validation_symlink_and_missing_install(self):
        payload = self.payload()
        for count in [0, 21, True, '2']:
            payload['max_parallelism'] = count
            with self.assertRaises(ValueError): self.settings.plan(payload)
        payload = self.payload()
        payload['routing']['owner']['model'] = 'gpt-test'
        with self.assertRaises(install.InstallError): self.settings.plan(payload)
        path = self.target / '.claude/settings.json'
        path.unlink()
        path.symlink_to(ROOT / '.claude/settings.json')
        with self.assertRaises(ValueError): self.settings.read()

    def test_installer_dry_run_and_safe_uninstall_assets(self):
        payload = self.payload()
        payload['revision'] = self.settings.plan(payload)[2]['revision']
        self.settings.save(payload)
        before = (self.target / '.claude/settings.json').read_bytes()
        self.assertEqual(install.main([str(self.target), '--uninstall', '--dry-run']), 0)
        self.assertTrue((self.target / '.claude/tools/console/app.js').exists())
        self.assertEqual(install.main([str(self.target), '--uninstall']), 0)
        self.assertFalse((self.target / '.claude/tools/console/app.js').exists())
        self.assertEqual((self.target / '.claude/settings.json').read_bytes(), before)

    def test_actual_http_auth_origin_body_and_usage(self):
        server, token = configure.make_server(self.target)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f'http://127.0.0.1:{server.server_port}'
        def request(path, payload=None, authenticated=True, remote=False):
            headers = {'Origin': 'https://example.com' if remote else origin}
            if authenticated: headers['X-Console-Token'] = token
            if payload is not None: headers['Content-Type'] = 'application/json'
            req = urllib.request.Request(origin + path, headers=headers, data=json.dumps(payload).encode() if payload is not None else None)
            return urllib.request.urlopen(req, timeout=3)
        try:
            self.assertIn('Görev Ayrıntıları', request('/').read().decode())
            self.assertEqual(json.load(request('/api/settings'))['scope'], 'project')
            self.assertEqual(json.load(request('/api/usage', {}))['status'], 'unavailable')
            for kwargs in [{'authenticated': False}, {'remote': True}]:
                with self.assertRaises(urllib.error.HTTPError) as caught: request('/api/preview', self.payload(), **kwargs)
                self.assertEqual(caught.exception.code, 403)
            payload = self.payload()
            preview = json.load(request('/api/preview', payload))
            payload['revision'] = preview['revision']
            self.assertTrue(json.load(request('/api/save', payload))['saved'])
            self.assertTrue(json.load(request('/api/restore', {}))['restored'])
            self.assertEqual(json.load(request('/api/tasks'))['status'], 'unavailable')
            with self.assertRaises(urllib.error.HTTPError): request('/api/save', {'wrong': True})
        finally:
            server.shutdown(); server.server_close(); thread.join(3)


class UsageSemanticsTests(unittest.TestCase):
    def report(self, docs, **kwargs):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'sanitized.jsonl'
            path.write_text('\n'.join(json.dumps(doc) for doc in docs))
            return configure.report(path, **kwargs)

    def metric(self, value, day, mode=2, epoch='1', session='s1'):
        from datetime import datetime, timezone
        stamp = str(int(datetime(2026, 9, day, tzinfo=timezone.utc).timestamp() * 1e9))
        attrs = [{'key': key, 'value': {'stringValue': val}} for key, val in {'model':'claude-test', 'type':'input', 'agent.name':'implementer'}.items()]
        return {'resourceMetrics':[{'resource':{'attributes':[{'key':'session.id','value':{'stringValue':session}}]},'scopeMetrics':[{'metrics':[{'name':'claude_code.token.usage','sum':{'aggregationTemporality':mode,'dataPoints':[{'asInt':str(value),'attributes':attrs,'timeUnixNano':stamp,'startTimeUnixNano':epoch}]}}]}]}]}

    def test_timestamp_order_duplicates_reset_and_filter(self):
        docs = [self.metric(150, 2), self.metric(100, 1), self.metric(150, 2), self.metric(20, 3)]
        result = self.report(docs)
        self.assertEqual(result['totals']['input'], 170)
        self.assertEqual(result['counter_resets_observed'], 1)
        self.assertEqual(result['duplicate_exports_or_points_skipped'], 1)
        self.assertTrue(all(result['dimensions'].values()))
        result = self.report(docs, start='2026-09-02', end='2026-09-02')
        self.assertEqual(result['totals']['input'], 50)

    def test_delta_vs_cumulative_independent_streams(self):
        docs = [self.metric(100, 1), self.metric(150, 2), self.metric(100, 1, 1, session='s2'), self.metric(150, 2, 1, session='s2')]
        self.assertEqual(self.report(docs)['totals']['input'], 400)
        unknown = self.metric(100, 1, 0)
        self.assertEqual(self.report([unknown])['status'], 'unavailable')

    def test_duplicate_points_across_different_envelopes(self):
        one = self.metric(100, 1, 1)
        two = dict(one, extra='ignored')
        self.assertEqual(self.report([one, two])['totals']['input'], 100)


if __name__ == '__main__': unittest.main()
