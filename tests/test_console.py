from __future__ import annotations
import importlib.util
import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import configure
import install
SECURE_UNINSTALL = (
    install.SECURE_UNINSTALL_DIR_FD
    and isinstance(getattr(install.os, 'O_DIRECTORY', None), int)
    and isinstance(getattr(install.os, 'O_NOFOLLOW', None), int)
)


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

    def test_console_paths_match_installer_manifest_keys(self):
        manifest = install.load_manifest(self.target)
        preview = self.settings.plan(self.payload())[2]
        agent_names = {name for name in preview['files'] if name.startswith('.claude/agents/')}
        self.assertEqual(agent_names, {name for name in manifest['files'] if name.startswith('.claude/agents/')})
        self.assertTrue(all('\\' not in name for name in preview['files']))

    @unittest.skipUnless(SECURE_UNINSTALL, 'secure uninstall unavailable on this platform')
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
        self.assertIn(first_slot.relative_to(self.target).as_posix(), first['files'])
        payload['revision'] = first['revision']
        self.settings.save(payload)
        self.assertIn('name: orchestra-slot-01', first_slot.read_text())
        self.assertEqual(first_slot.read_bytes(), self.settings.render_slot(roster[0]).encode('utf-8'))
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

    def test_larger_than_fifty_saved_helper_team_is_read_only(self):
        manifest_path = self.target / install.MANIFEST_RELATIVE
        manifest = json.loads(manifest_path.read_text())
        manifest['roster'] = [{'id': f'slot-{index:02d}', 'role': 'explorer', 'model': 'sonnet', 'effort': 'low', 'label': ''} for index in range(1, 52)]
        for slot in manifest['roster']:
            relative = self.settings.slot_path(slot['id'])
            path = self.target / relative
            path.write_text(self.settings.render_slot(slot))
            manifest['files'][relative.as_posix()] = {'owned': True, 'sha256': install.digest(path)}
        manifest_path.write_text(json.dumps(manifest))
        read = self.settings.read()
        self.assertEqual(len(read['roster']), 51)
        self.assertTrue(read['roster_read_only'])
        payload = {**self.payload(), 'roster': read['roster'][:50]}
        with self.assertRaisesRegex(ValueError, 'read-only'):
            self.settings.plan(payload)
        # An oversized legacy roster remains intact while chief routing can change.
        payload['roster'] = read['roster']
        payload['routing']['owner'] = {'model': 'sonnet', 'effort': 'low'}
        self.assertEqual(self.settings.plan(payload)[2]['roster'], read['roster'])
        ui = (ROOT / '.claude/tools/console/app.js').read_text(encoding='utf-8')
        self.assertIn("card.disabled=!!config?.roster_read_only", ui)
        self.assertIn("if(!preset||config.roster_read_only)return", ui)

    @unittest.skipUnless(SECURE_UNINSTALL, 'secure uninstall unavailable on this platform')
    def test_fifty_slots_save_reload_shrink_restore_and_uninstall(self):
        roster = [{'id': f'slot-{index:02d}', 'role': 'implementer' if index % 2 else 'reviewer',
                   'model': 'sonnet', 'effort': 'medium', 'label': f'Work {index}'} for index in range(1, 51)]
        payload = {**self.payload(), 'roster': roster}
        payload['revision'] = self.settings.plan(payload)[2]['revision']
        self.settings.save(payload)
        self.assertEqual(self.settings.read()['roster'], roster)
        self.assertFalse(self.settings.read()['roster_read_only'])
        self.assertIn('orchestra-slot-50', (self.target / 'CLAUDE.md').read_text())
        self.assertTrue((self.target / '.claude/agents/orchestra-slot-50.md').is_file())
        smaller = {**self.payload(), 'roster': roster[:7]}
        smaller['revision'] = self.settings.plan(smaller)[2]['revision']
        self.settings.save(smaller)
        self.assertFalse((self.target / '.claude/agents/orchestra-slot-50.md').exists())
        self.settings.restore()
        self.assertEqual(len(self.settings.read()['roster']), 50)
        self.assertEqual(install.main([str(self.target), '--uninstall']), 0)
        self.assertFalse((self.target / '.claude/agents/orchestra-slot-50.md').exists())

    def test_fifty_slot_conflict_or_mid_save_failure_keeps_manifest_and_files(self):
        import os
        roster = [{'id': f'slot-{index:02d}', 'role': 'implementer', 'model': 'sonnet',
                   'effort': 'medium', 'label': ''} for index in range(1, 51)]
        payload = {**self.payload(), 'roster': roster}
        foreign = self.target / '.claude/agents/orchestra-slot-50.md'
        foreign.write_text('user owned\n')
        manifest_path = self.target / install.MANIFEST_RELATIVE
        original_manifest = manifest_path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'conflict'):
            self.settings.plan(payload)
        self.assertEqual(foreign.read_text(), 'user owned\n')
        self.assertEqual(manifest_path.read_bytes(), original_manifest)
        foreign.unlink()
        payload['revision'] = self.settings.plan(payload)[2]['revision']
        settings_path = self.target / install.SETTINGS_RELATIVE
        original_settings = settings_path.read_bytes()
        original_agent = (self.target / '.claude/agents/implementer.md').read_bytes()
        real_link = os.link
        failed = False
        def fail_once(source, destination):
            nonlocal failed
            if not failed and Path(destination).name == 'orchestra-slot-25.md':
                failed = True
                raise OSError('injected write failure')
            return real_link(source, destination)
        with patch('console_settings.os.link', side_effect=fail_once):
            with self.assertRaisesRegex(OSError, 'injected write failure'):
                self.settings.save(payload)
        self.assertTrue(failed)
        self.assertEqual(manifest_path.read_bytes(), original_manifest)
        self.assertEqual(settings_path.read_bytes(), original_settings)
        self.assertEqual((self.target / '.claude/agents/implementer.md').read_bytes(), original_agent)
        self.assertFalse((self.target / '.claude/agents/orchestra-slot-01.md').exists())
        self.assertFalse((self.target / '.claude/.bounded-orchestrator/console-update.json').exists())

    def test_fresh_fifty_slot_failure_restores_initial_project_content(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / '.claude').mkdir()
            settings_path = target / '.claude/settings.json'
            original = '{"permissions":{"deny":["Read(secret)"]}}\n'
            settings_path.write_text(original)
            target.joinpath('CLAUDE.md').write_text('User instructions\n')
            settings = configure.Settings(install, ROOT, target)
            roster = [{'id': f'slot-{index:02d}', 'role': 'implementer', 'model': 'sonnet',
                       'effort': 'medium', 'label': ''} for index in range(1, 51)]
            payload = {**self.payload(), 'roster': roster}
            payload['revision'] = settings.plan(payload)[2]['revision']
            real_link = os.link
            failed = False
            def fail_once(source, destination):
                nonlocal failed
                if not failed and Path(destination).name == 'orchestra-slot-25.md':
                    failed = True
                    raise OSError('injected fresh write failure')
                return real_link(source, destination)
            with patch('console_settings.os.link', side_effect=fail_once):
                with self.assertRaisesRegex(OSError, 'injected fresh write failure'):
                    settings.save(payload)
            self.assertTrue(failed)
            self.assertEqual(settings_path.read_text(), original)
            self.assertEqual(target.joinpath('CLAUDE.md').read_text(), 'User instructions\n')
            self.assertFalse((target / install.MANIFEST_RELATIVE).exists())
            self.assertFalse((target / '.claude/agents/orchestra-slot-01.md').exists())
            payload['revision'] = settings.plan(payload)[2]['revision']
            settings.save(payload)
            self.assertEqual(len(settings.read()['roster']), 50)
            self.assertEqual(json.loads(settings_path.read_text())['permissions'], {'deny': ['Read(secret)']})

    def test_new_helper_created_after_preflight_is_not_overwritten(self):
        import os
        roster = [{'id': f'slot-{index:02d}', 'role': 'implementer', 'model': 'sonnet',
                   'effort': 'medium', 'label': ''} for index in range(1, 51)]
        payload = {**self.payload(), 'roster': roster}
        payload['revision'] = self.settings.plan(payload)[2]['revision']
        foreign = self.target / '.claude/agents/orchestra-slot-25.md'
        manifest_path = self.target / install.MANIFEST_RELATIVE
        original_manifest = manifest_path.read_bytes()
        real_link = os.link
        def race_link(source, destination):
            if Path(destination).name == foreign.name:
                foreign.write_text('User created during save\n')
            return real_link(source, destination)
        with patch('console_settings.os.link', side_effect=race_link):
            with self.assertRaises(FileExistsError):
                self.settings.save(payload)
        self.assertEqual(foreign.read_text(), 'User created during save\n')
        self.assertFalse((self.target / '.claude/agents/orchestra-slot-01.md').exists())
        self.assertEqual(manifest_path.read_bytes(), original_manifest)

    def test_manifest_symlink_inserted_mid_save_is_preserved(self):
        import os
        roster = [{'id': f'slot-{index:02d}', 'role': 'implementer', 'model': 'sonnet',
                   'effort': 'medium', 'label': ''} for index in range(1, 51)]
        payload = {**self.payload(), 'roster': roster}
        payload['revision'] = self.settings.plan(payload)[2]['revision']
        manifest_path = self.target / install.MANIFEST_RELATIVE
        outside = self.target.parent / (self.target.name + '-external-manifest')
        outside.write_text('external owner\n')
        real_link = os.link
        def insert_link(source, destination):
            if Path(destination).name == 'orchestra-slot-25.md':
                manifest_path.unlink()
                manifest_path.symlink_to(outside)
            return real_link(source, destination)
        try:
            with patch('console_settings.os.link', side_effect=insert_link):
                with self.assertRaisesRegex(ValueError, 'manual repair'):
                    self.settings.save(payload)
            self.assertTrue(manifest_path.is_symlink())
            self.assertEqual(outside.read_text(), 'external owner\n')
            self.assertFalse((self.target / '.claude/agents/orchestra-slot-01.md').exists())
        finally:
            outside.unlink(missing_ok=True)

    def test_fifty_slot_restore_failure_rolls_back_and_can_retry(self):
        roster = [{'id': f'slot-{index:02d}', 'role': 'implementer', 'model': 'sonnet',
                   'effort': 'medium', 'label': ''} for index in range(1, 51)]
        payload = {**self.payload(), 'roster': roster}
        payload['revision'] = self.settings.plan(payload)[2]['revision']
        self.settings.save(payload)
        manifest_path = self.target / install.MANIFEST_RELATIVE
        state_path = self.target / '.claude/.bounded-orchestrator/console-update.json'
        explorer_path = self.target / '.claude/agents/explorer.md'
        reviewer_path = self.target / '.claude/agents/reviewer.md'
        before = {path: path.read_bytes() for path in (manifest_path, state_path, explorer_path, reviewer_path)}
        real_atomic = install.atomic_text
        failed = False
        def fail_once(path, content, dry_run):
            nonlocal failed
            if not failed and Path(path).name == 'reviewer.md':
                failed = True
                raise OSError('injected restore failure')
            return real_atomic(path, content, dry_run)
        with patch.object(install, 'atomic_text', side_effect=fail_once):
            with self.assertRaisesRegex(OSError, 'injected restore failure'):
                self.settings.restore()
        self.assertTrue(failed)
        self.assertTrue(all(path.read_bytes() == content for path, content in before.items()))
        self.assertEqual(len(self.settings.read()['roster']), 50)
        self.assertTrue(self.settings.restore()['restored'])
        self.assertEqual(self.settings.read()['roster'], [])

    def test_cli_rejects_symlink_manifest_before_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / 'project'
            (target / '.claude/.bounded-orchestrator').mkdir(parents=True)
            outside = base / 'external-manifest.json'
            content = (self.target / install.MANIFEST_RELATIVE).read_text()
            outside.write_text(content)
            (target / install.MANIFEST_RELATIVE).symlink_to(outside)
            self.assertEqual(install.main([str(target)]), 2)
            self.assertEqual(outside.read_text(), content)
            self.assertFalse((target / '.claude/agents').exists())

    def test_preview_save_restore_preserves_unrelated_settings(self):
        path = self.target / '.claude/settings.json'
        original = json.loads(path.read_text())
        original['permissions'] = {'deny': ['Write(secret)']}
        original['env']['KEEP_PRIVATE'] = 'do-not-return'
        path.write_bytes(json.dumps(original, indent=2).replace('\n', '\r\n').encode('utf-8'))
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

    @unittest.skipUnless(SECURE_UNINSTALL, 'secure uninstall unavailable on this platform')
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

    @unittest.skipUnless(SECURE_UNINSTALL, 'secure uninstall unavailable on this platform')
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
          if(!source.includes("function modelCards(value,onChoose)")||!source.includes("aria-pressed',String(choice.value===current)"))process.exit(4);
          if(source.includes("const select=node('select');select.dataset.roleModel='';"))process.exit(5);"""
        result = subprocess.run(['node', '-e', program, str(ROOT / '.claude/tools/console/app.js')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_task_drafts_are_distinct_and_low_intensity_never_selects_opus(self):
        import shutil
        import subprocess
        if not shutil.which('node'):
            self.skipTest('Node unavailable; browser QA covers task drafts')
        presets = {key: {role: {'model': model, 'effort': effort} for role, (model, effort) in routing.items()}
                   for key, routing in install.PRESETS.items()}
        program = """const fs=require('fs'),vm=require('vm');const source=fs.readFileSync(process.argv[1],'utf8');
          const templates=source.slice(source.indexOf('const TASK_TEMPLATES='),source.indexOf('function t(')).replace('let selectedTaskProfile=null,taskDraftBefore=null,stagePage=0;','');
          const apply=source.slice(source.indexOf('function applyTaskTemplate('),source.indexOf('function setRosterCount('));
          const context={config:{presets:JSON.parse(process.argv[2])},routingState:{},rosterState:[],rosterPresetSeeded:false,
            selectedTeamSlot:'owner',stagePage:0,selectedTaskProfile:null,preset:{value:'balanced'},parallel:{value:'1'},
            selectedPreset:()=>context.preset.value,roles:value=>{context.routingState=JSON.parse(JSON.stringify(value))},
            $:id=>id==='preset'?context.preset:context.parallel};
          vm.createContext(context);vm.runInContext(templates+apply+';globalThis.run=applyTaskTemplate;globalThis.templates=TASK_TEMPLATES;',context);
          const expected={game:'quality',website:'balanced',research:'balanced',backend:'quality',mobile:'balanced',data:'balanced',bug:'economy',security:'quality'};
          if(context.templates.length!==8||context.templates.some(x=>expected[x.id]!==x.intensity))process.exit(1);
          const signatures=new Set(context.templates.map(x=>JSON.stringify([x.roles,x.effort,x.parallel])));
          if(signatures.size!==8)process.exit(2);
          for(const task of context.templates){
            context.preset.value='quota-saver';context.selectedTaskProfile=task.id;context.run();
            if(context.preset.value!==task.intensity)process.exit(3);
            if(context.rosterState.length!==task.roles.length||Number(context.parallel.value)!==task.parallel)process.exit(4);
            if(context.rosterState.some((slot,i)=>slot.id!=='slot-'+String(i+1).padStart(2,'0')||slot.role!==task.roles[i]||slot.model!==context.config.presets[task.intensity][slot.role].model||slot.effort!==context.config.presets[task.intensity][slot.role].effort))process.exit(5);
            if(context.routingState.owner.model!==context.config.presets[task.intensity].owner.model)process.exit(6);
            context.parallel.value='9';context.rosterState[0].label='manual';
            for(const style of ['economy','quota-saver']){
              context.preset.value=style;context.run(true);
              if(context.preset.value!==style)process.exit(7);
              if([context.routingState.owner.model,...context.rosterState.map(x=>x.model)].some(x=>x==='opus'||x.includes('opus')))process.exit(8);
              if(context.parallel.value!=='9'||context.rosterState[0].label!=='manual'||context.rosterState.length!==task.roles.length)process.exit(11);
            }
          }
          if(!source.includes('rosterPresetSeeded,selectedTeamSlot,stagePage')||!source.includes('rosterPresetSeeded=old.rosterPresetSeeded'))process.exit(9);
          if(source.includes("{id:'visual'")||source.includes("{id:'docs'"))process.exit(10);"""
        result = subprocess.run(['node', '-e', program, str(ROOT / '.claude/tools/console/app.js'), json.dumps(presets)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_selected_usage_counts_follow_only_observed_actor(self):
        import shutil
        import subprocess
        if not shutil.which('node'):
            self.skipTest('Node unavailable; browser QA covers actor selection')
        program = """const fs=require('fs'),vm=require('vm');const source=fs.readFileSync(process.argv[1],'utf8');
          const fragment=source.slice(source.indexOf('function selectedUsageCounts('),source.indexOf('function orchestraStage('));
          const selected=vm.runInNewContext(fragment+'; selectedUsageCounts');
          const session={conductor:{observed:true,counts:{primary:100,input:70,output:30,cacheRead:25}},
            helpers:{unidentified:{primary:40,input:30,output:10,cacheRead:15},agents:[
              {id:'research-a',counts:{primary:50,input:35,output:15,cacheRead:5}},
              {id:'review-b',counts:{primary:20,input:15,output:5,cacheRead:2}}]}};
          if(selected(session,'conductor').primary!==100||selected(session,'agent:research-a').primary!==50||selected(session,'agent:review-b').output!==5||selected(session,'group').primary!==40)process.exit(1);
          if(selected(null,'conductor')!==null||selected(session,'agent:missing')!==null)process.exit(2);
          session.conductor.observed=false;if(selected(session,'conductor')!==null)process.exit(3);
          if(selected(session,'agent:research-a').cacheRead!==5)process.exit(4);"""
        result = subprocess.run(['node', '-e', program, str(ROOT / '.claude/tools/console/app.js')],
                                capture_output=True, text=True)
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
        html = (ROOT / '.claude/tools/console/index.html').read_text(encoding='utf-8')
        source = script.read_text(encoding='utf-8')
        keys = set(re.findall(r'data-i18n(?:-aria|-placeholder)?="([^"]+)"', html))
        keys.update({'observedModelShort', 'observedModelFull', 'configuredEffortShort', 'configuredEffortFull',
                     'chiefClickHint', 'effortLow', 'effortMedium', 'effortHigh', 'effortXhigh', 'effortMax',
                     'helperSlot', 'helperCurrent', 'helperNone', 'helperChanged', 'helperReadonly', 'teamPreview', 'install', 'installDone', 'consoleClosed',
                     'chooseHelperHint', 'dutyExplorer', 'dutyResearcher', 'dutyImplementer', 'dutyVerifier',
                     'dutyFailure', 'dutyQa', 'dutyReviewer', 'dutyAdvisor'})
        if shutil.which('node'):
            program = """const fs=require('fs'),vm=require('vm');const s=fs.readFileSync(process.argv[1],'utf8');
              const fragment=s.slice(s.indexOf('const words ='),s.indexOf('const roleNames='));
              const labels=vm.runInNewContext(fragment+'; words');
              if(JSON.stringify(Object.keys(labels.tr).sort())!==JSON.stringify(Object.keys(labels.en).sort())) process.exit(1);
              for(const language of ['tr','en']){
                for(const key of process.argv.slice(2))if(!labels[language][key])process.exit(2);
                for(const version of ['2.1.257','2.1.280','2.1.284'])if(!labels[language].modelAccessNote.includes(version))process.exit(3);
              }"""
            result = subprocess.run(['node', '-e', program, str(script), *sorted(keys)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            subprocess.run(['node', '--check', str(script)], check=True)
        else:
            # Runtime browser QA covers the JavaScript path on systems without Node.
            self.assertIn('const words =', source)

    def test_uninstall_success_status_retranslates_after_language_change(self):
        import shutil
        import subprocess
        if not shutil.which('node'):
            self.skipTest('Node unavailable; browser QA covers language switching')
        program = """const fs=require('fs'),vm=require('vm');const s=fs.readFileSync(process.argv[1],'utf8');
          const catalog=s.slice(s.indexOf('const words ='),s.indexOf('const roleNames='));
          const status=s.slice(s.indexOf('const statusState=new Map();'),s.indexOf('async function action('));
          const translate=s.slice(s.indexOf('function translate(){'),s.indexOf('async function refresh(){'));
          const harness=`let language='tr';function t(key){return words[language][key]||key;}
            const elements={};function $(id){return elements[id]||(elements[id]={children:[],classList:{toggle(){}},replaceChildren(){this.children=[];},append(child){this.children.push(child);}});}
            function node(tag,text){return{textContent:text};}function details(){return{};}
            const document={documentElement:{},querySelectorAll(){return[];}};
            function translateRoleLabels(){}function renderTaskProfiles(){}function renderRoster(){}function renderPresetExplain(){}function renderSummary(){}function renderPreview(){}function renderUninstall(){}function renderActivity(){}function renderUsage(){}function renderTasks(){}
            settingStatus('uninstall-status','uninstallDone');
            if(elements['uninstall-status'].children[0].textContent!==words.tr.uninstallDone)throw Error('Turkish status missing');
            language='en';translate();
            if(elements['uninstall-status'].children[0].textContent!==words.en.uninstallDone)throw Error('English status missing');
            if(elements['uninstall-status'].hidden)throw Error('Result became hidden');`;
          vm.runInNewContext(catalog+status+translate+harness);"""
        result = subprocess.run(['node', '-e', program, str(ROOT / '.claude/tools/console/app.js')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

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
                for path, body in [('/api/preview', self.payload()), ('/api/uninstall-preview', {}),
                                   ('/api/uninstall', {'confirmation': 'bad', 'revision': 'bad', 'target': str(self.target)})]:
                    with self.assertRaises(urllib.error.HTTPError) as caught: request(path, body, **kwargs)
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

    @unittest.skipUnless(SECURE_UNINSTALL, 'secure uninstall unavailable on this platform')
    def test_browser_uninstall_preview_confirmation_stale_and_preservation(self):
        kept = self.target / '.claude/agents/reviewer.md'
        kept.write_text(kept.read_text(encoding='utf-8') + '\nUser edit\n', encoding='utf-8')
        claude = self.target / 'CLAUDE.md'
        edited_block = claude.read_text(encoding='utf-8').replace(
            install.END_MARKER, 'User instructions inside managed block\n' + install.END_MARKER)
        claude.write_text(edited_block, encoding='utf-8')
        backup = self.target / '.claude/.bounded-orchestrator/backups/user-note.txt'
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_text('private backup', encoding='utf-8')
        unrelated = self.target / 'project-work.txt'
        unrelated.write_text('project data', encoding='utf-8')
        server, token = configure.make_server(self.target)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f'http://127.0.0.1:{server.server_port}'
        def post(path, payload):
            req = urllib.request.Request(origin + path, data=json.dumps(payload).encode(), headers={
                'Host': f'127.0.0.1:{server.server_port}', 'Origin': origin,
                'X-Console-Token': token, 'Content-Type': 'application/json'})
            return json.load(urllib.request.urlopen(req, timeout=3))
        try:
            first = post('/api/uninstall-preview', {})
            self.assertEqual(first['target'], str(self.target.resolve()))
            self.assertTrue(any(line.startswith('KEEP .claude/agents/reviewer.md') for line in first['actions']))
            self.assertIn('KEEP CLAUDE.md block: modified after installation', first['actions'])
            self.assertTrue(any('KEEP .claude/.bounded-orchestrator/.gitignore' in line for line in first['actions']))
            self.assertTrue((self.target / install.MANIFEST_RELATIVE).exists())
            # Preview and a cancelled confirmation leave every file untouched.
            second = post('/api/uninstall-preview', {})
            with self.assertRaises(urllib.error.HTTPError) as caught:
                post('/api/uninstall', {key: first[key] for key in ('confirmation', 'revision', 'target')})
            self.assertEqual(caught.exception.code, 400)
            self.assertTrue(post('/api/uninstall-cancel', {'confirmation': second['confirmation']})['cancelled'])
            with self.assertRaises(urllib.error.HTTPError):
                post('/api/uninstall', {key: second[key] for key in ('confirmation', 'revision', 'target')})
            second = post('/api/uninstall-preview', {})
            unrelated.write_text('new project data', encoding='utf-8')
            # Unrelated project edits do not broaden or invalidate removal.
            watched = self.target / '.claude/agents/explorer.md'
            watched.write_text(watched.read_text(encoding='utf-8') + '\nChanged after preview\n', encoding='utf-8')
            with self.assertRaises(urllib.error.HTTPError) as caught:
                post('/api/uninstall', {key: second[key] for key in ('confirmation', 'revision', 'target')})
            self.assertEqual(caught.exception.code, 400)
            self.assertTrue((self.target / install.MANIFEST_RELATIVE).exists())
            fresh = post('/api/uninstall-preview', {})
            with patch.object(configure.time, 'monotonic', return_value=10**15):
                with self.assertRaises(urllib.error.HTTPError):
                    post('/api/uninstall', {key: fresh[key] for key in ('confirmation', 'revision', 'target')})
            fresh = post('/api/uninstall-preview', {})
            result = post('/api/uninstall', {key: fresh[key] for key in ('confirmation', 'revision', 'target')})
            self.assertTrue(result['removed'])
            self.assertEqual(result['actions'], fresh['actions'])
            with self.assertRaises(urllib.error.HTTPError):
                post('/api/uninstall', {key: fresh[key] for key in ('confirmation', 'revision', 'target')})
            self.assertFalse((self.target / install.MANIFEST_RELATIVE).exists())
            self.assertEqual(kept.read_text(encoding='utf-8').splitlines()[-1], 'User edit')
            self.assertEqual(claude.read_text(encoding='utf-8'), edited_block)
            self.assertTrue(watched.exists())
            self.assertEqual(backup.read_text(encoding='utf-8'), 'private backup')
            self.assertEqual(unrelated.read_text(encoding='utf-8'), 'new project data')
            self.assertTrue((self.target / install.RUNTIME_IGNORE_RELATIVE).exists())
            with self.assertRaisesRegex(ValueError, 'manifest'):
                self.settings.uninstall_preview()
        finally:
            server.shutdown(); server.server_close(); thread.join(3)

    def test_uninstall_preview_rejects_symlinked_managed_path(self):
        path = self.target / '.claude/agents/explorer.md'
        outside = self.target.parent / 'outside-uninstall-test.txt'
        outside.write_text('outside', encoding='utf-8')
        path.unlink()
        path.symlink_to(outside)
        try:
            with self.assertRaises(install.InstallError):
                self.settings.uninstall_preview()
            self.assertEqual(outside.read_text(encoding='utf-8'), 'outside')
        finally:
            outside.unlink()

    @unittest.skipUnless(SECURE_UNINSTALL, 'secure uninstall unavailable on this platform')
    def test_restore_after_two_saves_keeps_installation_until_uninstall(self):
        first = self.payload()
        first['revision'] = self.settings.plan(first)[2]['revision']
        self.settings.save(first)
        second = self.payload()
        second['max_parallelism'] = 3
        second['revision'] = self.settings.plan(second)[2]['revision']
        self.settings.save(second)
        self.settings.restore()
        self.assertTrue((self.target / install.MANIFEST_RELATIVE).exists())
        self.assertTrue(self.settings.read()['installed'])
        preview = self.settings.uninstall_preview()
        self.assertIn('REMOVE .claude/.bounded-orchestrator/install.json', preview['actions'])
        self.settings.uninstall_confirm(preview['revision'])
        self.assertFalse((self.target / install.MANIFEST_RELATIVE).exists())
        self.assertFalse((self.target / 'CLAUDE.md').exists())

    def test_uninstall_preview_rejects_symlinked_parent(self):
        agents = self.target / '.claude/agents'
        moved = self.target / '.claude/agents-original'
        agents.rename(moved)
        agents.symlink_to(moved, target_is_directory=True)
        try:
            with self.assertRaises(install.InstallError):
                self.settings.uninstall_preview()
            self.assertTrue((self.target / install.MANIFEST_RELATIVE).exists())
        finally:
            agents.unlink()
            moved.rename(agents)

    @unittest.skipUnless(SECURE_UNINSTALL, 'secure uninstall unavailable on this platform')
    def test_uninstall_rejects_parent_symlink_swap_after_validation(self):
        relative = Path('.claude/agents/reviewer.md')
        original = self.target / relative
        expected = original.read_bytes()
        agents = original.parent
        moved = self.target / '.claude/agents-original'
        outside = Path(tempfile.mkdtemp(prefix=self.target.name + '-outside-', dir=self.target.parent))
        external = outside / 'reviewer.md'
        external.write_text('Unrelated outside data', encoding='utf-8')
        real_open = install.os.open
        opens = 0
        def swap_on_recheck(path, *args, **kwargs):
            nonlocal opens
            if path == 'agents':
                opens += 1
                if opens == 2:
                    agents.rename(moved)
                    agents.symlink_to(outside, target_is_directory=True)
            return real_open(path, *args, **kwargs)
        try:
            with patch.object(install.os, 'open', side_effect=swap_on_recheck):
                with self.assertRaises((OSError, install.InstallError)):
                    install.mutate_verified_uninstall_file(self.target, relative, expected)
            self.assertEqual(external.read_text(encoding='utf-8'), 'Unrelated outside data')
            self.assertEqual((moved / 'reviewer.md').read_bytes(), expected)
        finally:
            if agents.is_symlink():
                agents.unlink()
                moved.rename(agents)
            external.unlink()
            outside.rmdir()

    @unittest.skipUnless(SECURE_UNINSTALL, 'secure uninstall unavailable on this platform')
    def test_uninstall_preserves_edit_injected_during_staging(self):
        preview = self.settings.uninstall_preview()
        real_rename = install.os.rename
        changed = []
        def edit_before_stage(source, destination, *args, **kwargs):
            if not changed and str(destination).startswith('.') and 'bounded-remove' in str(destination):
                fd = install.os.open(source, install.os.O_WRONLY | install.os.O_APPEND,
                                     dir_fd=kwargs['src_dir_fd'])
                try:
                    install.os.write(fd, b'\nUser edit during removal\n')
                finally:
                    install.os.close(fd)
                changed.append(source)
            return real_rename(source, destination, *args, **kwargs)
        with patch.object(install.os, 'rename', side_effect=edit_before_stage):
            with self.assertRaises((OSError, install.InstallError)):
                self.settings.uninstall_confirm(preview['revision'])
        self.assertTrue(changed)
        self.assertTrue((self.target / install.MANIFEST_RELATIVE).exists())
        self.assertTrue(any('User edit during removal' in path.read_text(encoding='utf-8')
                            for path in (self.target / '.claude').rglob('*') if path.is_file()))

    @unittest.skipUnless(SECURE_UNINSTALL, 'secure uninstall unavailable on this platform')
    def test_uninstall_rejects_new_file_after_final_preview(self):
        reviewer = self.target / '.claude/agents/reviewer.md'
        reviewer.unlink()
        preview = self.settings.uninstall_preview()
        real_uninstall = install.uninstall
        def appear_before_apply(target, manifest, dry_run, output, **kwargs):
            if not dry_run:
                reviewer.write_text('New user file', encoding='utf-8')
            return real_uninstall(target, manifest, dry_run, output, **kwargs)
        with patch.object(install, 'uninstall', side_effect=appear_before_apply):
            with self.assertRaises((OSError, install.InstallError)):
                self.settings.uninstall_confirm(preview['revision'])
        self.assertEqual(reviewer.read_text(encoding='utf-8'), 'New user file')
        self.assertTrue((self.target / install.MANIFEST_RELATIVE).exists())

    @unittest.skipUnless(SECURE_UNINSTALL, 'secure uninstall unavailable on this platform')
    def test_uninstall_recovery_retains_edit_at_final_unlink(self):
        relative = Path('.claude/agents/reviewer.md')
        original = self.target / relative
        expected = original.read_bytes()
        real_unlink = install.os.unlink
        def edit_at_unlink(path, *args, **kwargs):
            if isinstance(path, str) and 'bounded-remove' in path:
                fd = install.os.open(path, install.os.O_WRONLY | install.os.O_APPEND,
                                     dir_fd=kwargs['dir_fd'])
                try:
                    install.os.write(fd, b'\nLate user edit\n')
                finally:
                    install.os.close(fd)
            return real_unlink(path, *args, **kwargs)
        with patch.object(install.os, 'unlink', side_effect=edit_at_unlink):
            install.mutate_verified_uninstall_file(self.target, relative, expected)
        self.assertFalse(original.exists())
        backups = list((self.target / install.BACKUP_RELATIVE).glob('uninstall-.claude_agents_reviewer.md-*'))
        self.assertEqual(len(backups), 1)
        self.assertIn(b'Late user edit', backups[0].read_bytes())

    @unittest.skipUnless(SECURE_UNINSTALL, 'secure uninstall unavailable on this platform')
    def test_failed_replacement_keeps_edit_in_recovery(self):
        relative = Path('CLAUDE.md')
        path = self.target / relative
        original = path.read_bytes()
        def edit_then_fail(fd):
            install.os.write(fd, b'\nUser edit during replacement\n')
            raise OSError('injected fsync failure')
        with patch.object(install.os, 'fsync', side_effect=edit_then_fail):
            with self.assertRaises(OSError):
                install.mutate_verified_uninstall_file(self.target, relative, original, 'New content\n')
        self.assertEqual(path.read_bytes(), original)
        recovered = list((self.target / install.BACKUP_RELATIVE).glob('uninstall-failed-replacement-CLAUDE.md-*'))
        self.assertEqual(len(recovered), 1)
        self.assertIn(b'User edit during replacement', recovered[0].read_bytes())

    @unittest.skipUnless(SECURE_UNINSTALL, 'secure uninstall unavailable on this platform')
    def test_failed_replacement_preserves_new_leaf_collision(self):
        relative = Path('CLAUDE.md')
        path = self.target / relative
        original = path.read_bytes()
        moved_replacement = self.target / 'user-moved-replacement.md'
        def collide_then_fail(fd):
            path.rename(moved_replacement)
            path.write_text('USER COLLISION', encoding='utf-8')
            raise OSError('injected fsync failure')
        with patch.object(install.os, 'fsync', side_effect=collide_then_fail):
            with self.assertRaises(OSError):
                install.mutate_verified_uninstall_file(self.target, relative, original, 'New content\n')
        self.assertEqual(path.read_text(encoding='utf-8'), 'USER COLLISION')
        self.assertEqual(moved_replacement.read_text(encoding='utf-8'), 'New content\n')
        originals = list((self.target / install.BACKUP_RELATIVE).glob('uninstall-CLAUDE.md-*'))
        self.assertEqual(len(originals), 1)
        self.assertEqual(originals[0].read_bytes(), original)

    @unittest.skipUnless(SECURE_UNINSTALL, 'secure uninstall unavailable on this platform')
    def test_failed_replacement_keeps_atomic_save_after_recovery_link(self):
        path = self.target / 'CLAUDE.md'
        original = path.read_bytes()
        identity = path.stat()
        user_temp = self.target / 'user-atomic-save.tmp'
        user_temp.write_text('USER ATOMIC SAVE', encoding='utf-8')
        flags = install.os.O_RDONLY | install.os.O_DIRECTORY | install.os.O_NOFOLLOW
        root_fd = install.os.open(self.target, flags)
        real_retain = install.retain_uninstall_inode
        def swap_after_recovery(*args, **kwargs):
            result = real_retain(*args, **kwargs)
            if len(args) >= 6 and args[5] == 'uninstall-failed-replacement':
                staged = next(self.target.glob('.CLAUDE.md.bounded-failed-*'))
                install.os.replace(user_temp, staged)
            return result
        try:
            with patch.object(install, 'retain_uninstall_inode', side_effect=swap_after_recovery):
                install.recover_failed_replacement(root_fd, root_fd, 'CLAUDE.md', Path('CLAUDE.md'), flags,
                                                   (identity.st_dev, identity.st_ino))
        finally:
            install.os.close(root_fd)
        stages = list((self.target / install.BACKUP_RELATIVE).glob('uninstall-failed-stage-CLAUDE.md-*'))
        self.assertEqual(len(stages), 1)
        self.assertEqual(stages[0].read_text(encoding='utf-8'), 'USER ATOMIC SAVE')
        backups = list((self.target / install.BACKUP_RELATIVE).glob('uninstall-failed-replacement-CLAUDE.md-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)

    @unittest.skipUnless(SECURE_UNINSTALL, 'secure uninstall unavailable on this platform')
    def test_failed_replacement_keeps_atomic_save_after_collision_link(self):
        path = self.target / '.mcp.json'
        path.write_text('USER COLLISION', encoding='utf-8')
        user_temp = self.target / 'user-atomic-save.tmp'
        user_temp.write_text('USER ATOMIC SAVE', encoding='utf-8')
        flags = install.os.O_RDONLY | install.os.O_DIRECTORY | install.os.O_NOFOLLOW
        root_fd = install.os.open(self.target, flags)
        real_link = install.os.link
        def swap_after_collision_link(source, destination, *args, **kwargs):
            result = real_link(source, destination, *args, **kwargs)
            if source.startswith('.mcp.json.bounded-failed-') and destination == '.mcp.json':
                install.os.replace(user_temp, self.target / source)
            return result
        try:
            with patch.object(install.os, 'link', side_effect=swap_after_collision_link):
                install.recover_failed_replacement(root_fd, root_fd, '.mcp.json', Path('.mcp.json'), flags, (-1, -1))
        finally:
            install.os.close(root_fd)
        self.assertEqual(path.read_text(encoding='utf-8'), 'USER COLLISION')
        stages = list((self.target / install.BACKUP_RELATIVE).glob('uninstall-failed-stage-.mcp.json-*'))
        self.assertEqual(len(stages), 1)
        self.assertEqual(stages[0].read_text(encoding='utf-8'), 'USER ATOMIC SAVE')

    @unittest.skipUnless(SECURE_UNINSTALL, 'secure uninstall unavailable on this platform')
    def test_uninstall_rejects_parent_swap_during_staging(self):
        relative = Path('.claude/agents/reviewer.md')
        original = self.target / relative
        expected = original.read_bytes()
        agents = original.parent
        moved = self.target / '.claude/agents-original'
        outside = Path(tempfile.mkdtemp(prefix=self.target.name + '-outside-', dir=self.target.parent))
        external = outside / 'reviewer.md'
        external.write_text('Unrelated outside data', encoding='utf-8')
        real_rename = install.os.rename
        def swap_after_stage(source, destination, *args, **kwargs):
            result = real_rename(source, destination, *args, **kwargs)
            if source == 'reviewer.md' and 'bounded-remove' in destination:
                agents.rename(moved)
                agents.symlink_to(outside, target_is_directory=True)
            return result
        try:
            with patch.object(install.os, 'rename', side_effect=swap_after_stage):
                with self.assertRaises((OSError, install.InstallError)):
                    install.mutate_verified_uninstall_file(self.target, relative, expected)
            self.assertEqual(external.read_text(encoding='utf-8'), 'Unrelated outside data')
            self.assertEqual((moved / 'reviewer.md').read_bytes(), expected)
        finally:
            if agents.is_symlink():
                agents.unlink()
                moved.rename(agents)
            external.unlink()
            outside.rmdir()

    def test_uninstall_preview_rejects_unsupported_backend(self):
        with patch.object(install.os, 'O_NOFOLLOW', None, create=True):
            self.assertFalse(self.settings.read()['uninstall_supported'])
            self.assertFalse(self.settings.read()['uninstall_available'])
            with self.assertRaisesRegex(install.InstallError, 'unsupported'):
                self.settings.uninstall_preview()
        self.assertTrue((self.target / install.MANIFEST_RELATIVE).exists())

    @unittest.skipUnless(SECURE_UNINSTALL, 'secure uninstall unavailable on this platform')
    def test_uninstall_partial_failure_has_distinct_api_code(self):
        server, token = configure.make_server(self.target)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f'http://127.0.0.1:{server.server_port}'
        def post(path, payload):
            req = urllib.request.Request(origin + path, data=json.dumps(payload).encode(), headers={
                'Host': f'127.0.0.1:{server.server_port}', 'Origin': origin,
                'X-Console-Token': token, 'Content-Type': 'application/json'})
            return json.load(urllib.request.urlopen(req, timeout=3))
        real_mutate = install.mutate_verified_uninstall_file
        changed = []
        def fail_after_first(*args, **kwargs):
            result = real_mutate(*args, **kwargs)
            if not changed:
                changed.append(True)
                raise install.InstallError('changed after first removal')
            return result
        try:
            preview = post('/api/uninstall-preview', {})
            with patch.object(install, 'mutate_verified_uninstall_file', side_effect=fail_after_first):
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    post('/api/uninstall', {key: preview[key] for key in ('confirmation', 'revision', 'target')})
            self.assertEqual(caught.exception.code, 409)
            self.assertEqual(json.load(caught.exception)['kind'], 'partial_uninstall')
            self.assertTrue(changed)
            self.assertTrue((self.target / install.MANIFEST_RELATIVE).exists())
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
