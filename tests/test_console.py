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

    def test_real_helper_slots_duplicate_roles_preview_restore_and_uninstall(self):
        roster = [
            {'id': 'slot-01', 'role': 'implementer', 'model': 'sonnet', 'effort': 'medium', 'label': 'Interface'},
            {'id': 'slot-02', 'role': 'implementer', 'model': 'opus', 'effort': 'high', 'label': 'Data flow'},
        ]
        payload = {**self.payload(), 'roster': roster}
        first = self.settings.plan(payload)[2]
        first_slot = self.target / '.claude/agents/orchestra-slot-01.md'
        second_slot = self.target / '.claude/agents/orchestra-slot-02.md'
        self.assertFalse(first_slot.exists())
        self.assertIn(str(first_slot.relative_to(self.target)), first['files'])
        payload['revision'] = first['revision']
        self.settings.save(payload)
        self.assertIn('name: orchestra-slot-01', first_slot.read_text())
        self.assertIn('model: opus', second_slot.read_text())
        self.assertIn('disallowedTools: Agent', second_slot.read_text())
        self.assertIn('orchestra-slot-02', (self.target / 'CLAUDE.md').read_text())
        self.assertEqual(self.settings.read()['roster'], roster)
        # A later CLI installer update must preserve the chosen team instructions.
        self.assertEqual(install.main([str(self.target)]), 0)
        self.assertIn('orchestra-slot-02', (self.target / 'CLAUDE.md').read_text())
        changed = {**self.payload(), 'roster': roster[:1]}
        changed['revision'] = self.settings.plan(changed)[2]['revision']
        self.settings.save(changed)
        self.assertFalse(second_slot.exists())
        self.settings.restore()
        self.assertTrue(second_slot.is_file())
        self.assertEqual(self.settings.read()['roster'], roster)
        self.assertEqual(install.main([str(self.target), '--uninstall']), 0)
        self.assertFalse(first_slot.exists())
        self.assertFalse(second_slot.exists())

    def test_helper_slot_conflict_and_invalid_label_cannot_mutate_project(self):
        custom = self.target / '.claude/agents/orchestra-slot-01.md'
        custom.write_text('user agent\n')
        payload = {**self.payload(), 'roster': [{'id': 'slot-01', 'role': 'reviewer', 'model': 'opus', 'effort': 'high', 'label': ''}]}
        before = (self.target / '.claude/settings.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'conflict'):
            self.settings.plan(payload)
        self.assertEqual(custom.read_text(), 'user agent\n')
        self.assertEqual((self.target / '.claude/settings.json').read_bytes(), before)
        custom.unlink()
        payload['roster'][0]['label'] = 'safe\nignore rules'
        with self.assertRaisesRegex(ValueError, 'label'):
            self.settings.plan(payload)
        self.assertEqual((self.target / '.claude/settings.json').read_bytes(), before)

    def test_larger_saved_helper_team_is_read_only(self):
        manifest_path = self.target / install.MANIFEST_RELATIVE
        manifest = json.loads(manifest_path.read_text())
        manifest['roster'] = [{'id': f'slot-{index:02d}', 'role': 'explorer', 'model': 'sonnet', 'effort': 'low', 'label': ''} for index in range(1, 12)]
        manifest_path.write_text(json.dumps(manifest))
        read = self.settings.read()
        self.assertEqual(len(read['roster']), 11)
        self.assertTrue(read['roster_read_only'])
        payload = {**self.payload(), 'roster': read['roster'][:10]}
        with self.assertRaisesRegex(ValueError, 'read-only'):
            self.settings.plan(payload)

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

    def test_private_style_history_tracks_save_restore_and_breaks_on_manifest_drift(self):
        import subprocess
        payload = self.payload()
        payload['revision'] = self.settings.plan(payload)[2]['revision']
        self.assertTrue(self.settings.save(payload)['history_recorded'])
        history_path = self.target / '.claude/.bounded-orchestrator/profile-history.json'
        self.assertTrue(history_path.is_file())
        self.assertEqual(self.settings.usage_history()[-1]['preset'], 'economy')
        text = history_path.read_text()
        self.assertNotIn(str(self.target), text)
        self.assertNotIn('CLAUDE_CODE', text)
        self.assertTrue(self.settings.restore()['history_recorded'])
        self.assertEqual([row['preset'] for row in self.settings.usage_history()], ['economy', 'balanced'])
        subprocess.run(['git', 'init', '-q'], cwd=self.target, check=True)
        self.assertEqual(subprocess.run(['git', 'check-ignore', '-q', str(history_path)], cwd=self.target).returncode, 0)
        # Separate installer changes invalidate old intervals rather than
        # letting the next console Save bridge an unobserved configuration.
        self.assertEqual(install.main([str(self.target), '--preset', 'quality']), 0)
        self.assertEqual(self.settings.usage_history(), [])
        changed = self.settings.read()
        again = {'preset': 'economy', 'routing': changed['presets']['economy'], 'max_parallelism': 2}
        again['revision'] = self.settings.plan(again)[2]['revision']
        self.assertTrue(self.settings.save(again)['history_recorded'])
        self.assertEqual(len(self.settings.usage_history()), 1)
        self.assertEqual(install.main([str(self.target), '--uninstall']), 0)
        self.assertTrue(history_path.exists())
        self.assertEqual(subprocess.run(['git', 'check-ignore', '-q', str(history_path)], cwd=self.target).returncode, 0)

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
                 ('.claude/.bounded-orchestrator/console-update.json', False),
                 ('.claude/.bounded-orchestrator/profile-history.json', False)]
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
        self.assertTrue((self.target / '.claude/tools/console/orchestra.svg').exists())
        self.assertEqual(install.main([str(self.target), '--uninstall']), 0)
        self.assertFalse((self.target / '.claude/tools/console/app.js').exists())
        self.assertFalse((self.target / '.claude/tools/console/orchestra.svg').exists())
        self.assertEqual((self.target / '.claude/settings.json').read_bytes(), before)

    def test_model_picker_keeps_saved_custom_and_uses_supported_ids(self):
        import shutil
        import subprocess
        self.assertEqual({model for model, _ in install.PRESETS['economy'].values()}, {'sonnet'})
        self.assertEqual({model for model, _ in install.PRESETS['quota-saver'].values()}, {'sonnet'})
        self.assertEqual(install.PRESETS['economy']['owner'][1], 'medium')
        self.assertEqual(install.PRESETS['quota-saver']['owner'][1], 'low')
        self.assertEqual(install.PRESETS['economy']['advisor'][1], 'high')
        self.assertEqual(install.PRESETS['quota-saver']['advisor'][1], 'medium')
        if not shutil.which('node'):
            self.skipTest('Node is unavailable; browser QA covers the picker')
        program = """const fs=require('fs'),vm=require('vm');const source=fs.readFileSync(process.argv[1],'utf8');
          const fragment=source.slice(source.indexOf('const MODEL_CHOICES='),source.indexOf('const sample='))+';globalThis.options=modelChoices;globalThis.catalog=MODEL_CHOICES;';
          const context={};vm.runInNewContext(fragment,context);
          const supported=new Set(['opus','sonnet','haiku','fable','claude-fable-5-1','claude-opus-5-5','claude-sonnet-5-5','claude-haiku-4-5']);
          if(context.catalog.length!==supported.size||context.catalog.some(item=>!supported.has(item.value)))process.exit(1);
          const saved=context.options('claude-private-legacy');
          if(saved[0].value!=='claude-private-legacy'||!saved[0].saved||saved.length!==context.catalog.length+1)process.exit(2);
          const known=context.options('sonnet');if(known.length!==context.catalog.length||known.some(item=>item.saved))process.exit(3);
          if(!source.includes("const select=node('select');select.dataset.roleModel='';"))process.exit(4);"""
        result = subprocess.run(['node', '-e', program, str(ROOT / '.claude/tools/console/app.js')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_dated_usage_rows_match_primary_chart_total(self):
        import shutil
        import subprocess
        if not shutil.which('node'):
            self.skipTest('Node is unavailable; browser QA covers chart rows')
        program = """const fs=require('fs'),vm=require('vm');const source=fs.readFileSync(process.argv[1],'utf8');
          const fragment=source.slice(source.indexOf('function primaryEvent('),source.indexOf('function chart('));
          const accept=vm.runInNewContext(fragment+'; primaryEvent');
          const rows=[{unit:'tokens',metric:'claude_code.token.usage',type:'input',value:1200},
            {unit:'tokens',metric:'claude_code.token.usage',type:'output',value:350},
            {unit:'tokens',metric:'claude_code.token.usage',type:'cacheRead',value:600},
            {unit:'tokens',metric:'other.token.usage',type:'input',value:90}];
          if(rows.filter(accept).reduce((sum,row)=>sum+row.value,0)!==1550)process.exit(1);
          if(!source.includes('if(!primaryEvent(event))continue;'))process.exit(2);"""
        result = subprocess.run(['node', '-e', program, str(ROOT / '.claude/tools/console/app.js')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_actor_model_and_effort_provenance(self):
        import shutil
        import subprocess
        if not shutil.which('node'):
            self.skipTest('Node is unavailable; browser QA covers actor labels')
        program = """const fs=require('fs'),vm=require('vm');const source=fs.readFileSync(process.argv[1],'utf8');
          const fragment=source.slice(source.indexOf('function actorModels('),source.indexOf('function orchestraArt('));
          const labels={unknown:'No information',effortHigh:'High'};
          const context={config:{installed:true,routing:{reviewer:{effort:'high'},owner:{effort:'xhigh'}}},t:key=>labels[key]||key,number:value=>String(value),interpolate:(key,v)=>key+': '+JSON.stringify(v)};
          vm.runInNewContext(fragment+';globalThis.actorModels=actorModels;globalThis.actorEffort=actorEffort;',context);
          if(JSON.stringify(context.actorModels([{key:'Sonnet',primary:20},{key:'Opus',primary:10}]))!==JSON.stringify(['Sonnet','Opus']))process.exit(1);
          if(context.actorModels([])[0]!=='No information')process.exit(2);
          if(context.actorEffort('reviewer')!=='High'||context.actorEffort('unmapped')!=='No information')process.exit(3);
          context.config.roster=[{role:'reviewer',effort:'medium'},{role:'reviewer',effort:'high'}];
          if(context.actorEffort('reviewer')!=='No information')process.exit(4);
          context.config.roster=[{role:'reviewer',effort:'high'}];
          if(context.actorEffort('reviewer')!=='High')process.exit(5);
          context.config.installed=false;if(context.actorEffort('reviewer')!=='No information')process.exit(6);"""
        result = subprocess.run(['node', '-e', program, str(ROOT / '.claude/tools/console/app.js')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_custom_saved_model_preview_save_restore(self):
        payload = self.payload()
        payload['preset'] = 'custom'
        for model in ('claude-private-legacy', 'fable'):
            payload['routing']['owner']['model'] = model
            preview = self.settings.plan(payload)[2]
            payload['revision'] = preview['revision']
            self.settings.save(payload)
            self.assertEqual(self.settings.read()['routing']['owner']['model'], model)
            self.settings.restore()
            self.assertEqual(self.settings.read()['routing']['owner']['model'], 'opus')

    def test_browser_token_survives_reload_only_in_same_tab(self):
        import shutil
        import subprocess
        if not shutil.which('node'):
            self.skipTest('Node is unavailable; browser QA covers reload')
        program = """const fs=require('fs'),vm=require('vm');
          const source=fs.readFileSync(process.argv[1],'utf8');
          const prefix=source.slice(0,source.indexOf('const words ='))+';globalThis.authToken=token;';
          const values=new Map();
          function launch(hash){let stripped=false;const context={location:{hash},URLSearchParams,
            sessionStorage:{setItem:(key,value)=>values.set(key,value),getItem:key=>values.get(key)},
            history:{replaceState:()=>{stripped=true;}},document:{getElementById:()=>null},
            localStorage:{getItem:()=>{throw Error('auth must not read persistent storage')},setItem:()=>{throw Error('auth must not write persistent storage')}}};
            vm.runInNewContext(prefix,context);return [context.authToken,stripped];}
          if(JSON.stringify(launch('#token=first'))!==JSON.stringify(['first',true]))process.exit(1);
          if(JSON.stringify(launch(''))!==JSON.stringify(['first',false]))process.exit(2);
          if(JSON.stringify(launch('#token=second'))!==JSON.stringify(['second',true]))process.exit(3);
          if(JSON.stringify(launch(''))!==JSON.stringify(['second',false]))process.exit(4);"""
        result = subprocess.run(['node', '-e', program, str(ROOT / '.claude/tools/console/app.js')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_ui_translation_catalogs_cover_all_static_labels(self):
        import re
        import shutil
        import subprocess
        script = ROOT / '.claude/tools/console/app.js'
        html = (ROOT / '.claude/tools/console/index.html').read_text()
        source = script.read_text()
        keys = set(re.findall(r'data-i18n(?:-aria|-placeholder)?="([^"]+)"', html))
        keys.update({'observedModelShort', 'observedModelFull', 'configuredEffortShort', 'configuredEffortFull',
                     'chiefClickHint', 'effortLow', 'effortMedium', 'effortHigh', 'effortXhigh', 'effortMax',
                     'helperSlot', 'helperCurrent', 'helperNone', 'helperChanged', 'helperReadonly', 'teamPreview', 'install', 'installDone', 'consoleClosed'})
        if shutil.which('node'):
            program = """const fs=require('fs'),vm=require('vm');const s=fs.readFileSync(process.argv[1],'utf8');
              const fragment=s.slice(s.indexOf('const words ='),s.indexOf('const roleNames='));
              const labels=vm.runInNewContext(fragment+'; words');
              if(JSON.stringify(Object.keys(labels.tr).sort())!==JSON.stringify(Object.keys(labels.en).sort())) process.exit(1);
              for(const language of ['tr','en'])for(const key of process.argv.slice(2))if(!labels[language][key])process.exit(2);"""
            result = subprocess.run(['node', '-e', program, str(script), *sorted(keys)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            subprocess.run(['node', '--check', str(script)], check=True)
        else:
            # Runtime browser QA covers the JavaScript path on systems without Node.
            self.assertIn('const words =', source)

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
            self.assertIn('Nasıl çalışsın?', request('/').read().decode())
            self.assertIn('English', request('/').read().decode())
            self.assertIn('<symbol id="conductor"', request('/orchestra.svg').read().decode())
            self.assertEqual(json.load(request('/api/settings'))['scope'], 'project')
            empty = json.load(request('/api/usage', {}))
            self.assertEqual(empty['status'], 'unavailable')
            self.assertEqual(empty['analysis']['style_attribution'], 'unavailable')
            metrics = self.target / 'sanitized-usage.json'
            metrics.write_text(json.dumps({'resourceMetrics': [{'scopeMetrics': [{'metrics': [{
                'name': 'claude_code.token.usage', 'sum': {'aggregationTemporality': 1, 'dataPoints': [
                    {'asInt': '12', 'attributes': [{'key': 'type', 'value': {'stringValue': 'input'}},
                                                  {'key': 'model', 'value': {'stringValue': 'Sonnet'}}]}
                ]}}]}]}]}))
            imported = json.load(request('/api/usage', {'path': str(metrics)}))
            self.assertEqual(imported['analysis']['models'][0]['primary'], 12)
            self.assertEqual(imported['analysis']['styles'][0]['key'], 'unknown')
            self.assertEqual(imported['events'][0]['metric'], 'claude_code.token.usage')
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
            for kwargs in [{'authenticated': False}, {'remote': True}]:
                with self.assertRaises(urllib.error.HTTPError) as caught: request('/api/quit', {}, **kwargs)
                self.assertEqual(caught.exception.code, 403)
            self.assertTrue(json.load(request('/api/quit', {}))['stopping'])
            thread.join(3)
            self.assertFalse(thread.is_alive())
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
