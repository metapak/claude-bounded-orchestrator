"""Project-scoped console updates using installer validation, backups and ownership."""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

STATE = Path('.claude/.bounded-orchestrator/console-update.json')
HISTORY = Path('.claude/.bounded-orchestrator/profile-history.json')
HISTORY_LIMIT = 1024 * 1024
CONCURRENCY = 'CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS'
SLOT_ID = re.compile(r'slot-(?:0[1-9]|[1-9][0-9])\Z')
LABEL = re.compile(r'[\w .()/-]{0,60}\Z', re.UNICODE)


class Settings:
    def __init__(self, installer, root: Path, target: Path):
        self.i, self.root, self.target = installer, root.resolve(), target.resolve()

    def path(self, relative):
        relative = Path(relative)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Refusing path outside selected project')
        path = self.target / relative
        # Reject every symlink ancestor, including links back inside the target.
        # The target itself is canonicalized once, preserving macOS /var aliases.
        for candidate in (path, *path.parents):
            if candidate == self.target:
                break
            if candidate.is_symlink():
                raise ValueError('Refusing symlink or path outside selected project')
            if candidate != path and candidate.exists() and not candidate.is_dir():
                raise ValueError('Destination ancestor is not a directory')
        if not path.resolve().is_relative_to(self.target):
            raise ValueError('Refusing symlink or path outside selected project')
        return path

    def preflight_initial_install(self):
        # Enumerate every destination touched by install.main without providers,
        # including its shared settings fallback, block, manifest and backups.
        files = (*self.i.BASE_MANAGED_FILES, self.i.SETTINGS_RELATIVE,
                 self.i.SETTINGS_EXAMPLE_RELATIVE, Path('CLAUDE.md'),
                 self.i.MANIFEST_RELATIVE, STATE, HISTORY)
        for relative in files:
            destination = self.path(relative)
            if destination.exists() and not destination.is_file():
                raise ValueError('Initial install destination is not a file: ' + str(relative))
        backups = self.path(self.i.BACKUP_RELATIVE)
        if backups.exists() and not backups.is_dir():
            raise ValueError('Backup destination is not a directory')
        # Existing descendants may be used by timestamped backup allocation.
        if backups.exists() and any(path.is_symlink() for path in backups.rglob('*')):
            raise ValueError('Refusing symlink in initial install backups')

    def slot_path(self, slot_id):
        if not isinstance(slot_id, str) or not SLOT_ID.fullmatch(slot_id):
            raise ValueError('Invalid helper slot ID')
        return Path('.claude/agents') / ('orchestra-' + slot_id + '.md')

    def roster(self, manifest):
        raw = manifest.get('roster', [])
        if not isinstance(raw, list) or len(raw) > 99:
            raise ValueError('Invalid saved helper team')
        result = []
        for index, item in enumerate(raw, 1):
            if not isinstance(item, dict) or set(item) != {'id', 'role', 'model', 'effort', 'label'}:
                raise ValueError('Invalid saved helper')
            if item['id'] != f'slot-{index:02d}' or item['role'] not in self.i.ROLES[1:]:
                raise ValueError('Invalid saved helper role or order')
            if not isinstance(item['label'], str) or not LABEL.fullmatch(item['label']):
                raise ValueError('Invalid saved helper label')
            self.i.validate_claude_model(item['model'], item['id'])
            self.i.validate_effort(item['effort'], item['id'], self.i.CLAUDE_EFFORTS)
            result.append(dict(item))
        return result

    def render_slot(self, slot):
        source = self.root / '.claude/agents' / (slot['role'] + '.md')
        content = self.i.render_agent(source, slot['model'], slot['effort'])
        return content.replace('name: ' + slot['role'] + '\n', 'name: orchestra-' + slot['id'] + '\n', 1)

    def render_team_block(self, existing, roster):
        cleaned, _ = self.i.remove_managed_block(existing)
        block = (self.root / 'templates/CLAUDE.block.md').read_text(encoding='utf-8').strip()
        if roster:
            lines = ['\n### Selected helper team',
                     'Use these configured helper names for delegated execution; their count is capacity, not a requirement to spawn all at once. Assign one writer per scope. The main session only coordinates and reads short reports.']
            for slot in roster:
                label = (' — ' + json.dumps(slot['label'], ensure_ascii=False)) if slot['label'] else ''
                lines.append(f"- `orchestra-{slot['id']}`: {slot['role']}{label}; model `{slot['model']}`, effort `{slot['effort']}`")
            block = block.replace(self.i.END_MARKER, '\n'.join(lines) + '\n' + self.i.END_MARKER)
        return (cleaned.rstrip() + '\n\n' + block + '\n').lstrip('\n')

    def read(self):
        settings_path = self.path(self.i.SETTINGS_RELATIVE)
        settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
        manifest = self.i.load_manifest(self.target)
        roster = self.roster(manifest)
        routing = {}
        for role in self.i.ROLES:
            if role == 'owner':
                routing[role] = {'model': settings.get('model', 'opus'), 'effort': settings.get('effortLevel', 'xhigh')}
            else:
                path = self.path(Path('.claude/agents') / (role + '.md'))
                fields = {}
                if path.exists():
                    header = path.read_text().split('\n---\n', 1)[0]
                    fields = dict(line.split(':', 1) for line in header.splitlines() if ':' in line)
                default = self.i.PRESETS['balanced'][role]
                routing[role] = {'model': fields.get('model', default[0]).strip(), 'effort': fields.get('effort', default[1]).strip()}
        return {'target': str(self.target), 'scope': 'project', 'preset': manifest.get('preset', 'custom'),
                'routing': routing, 'max_parallelism': settings.get('env', {}).get(CONCURRENCY),
                'roster': roster, 'roster_read_only': len(roster) > 10,
                'installed': bool(manifest.get('files')), 'restore_available': self.path(STATE).exists(),
                'presets': {key: {role: {'model': pair[0], 'effort': pair[1]} for role, pair in value.items()} for key, value in self.i.PRESETS.items()},
                'limitations': 'Project files shown. Managed/local settings, environment and CLI/session choices may override them. Concurrency requires Claude Code 2.1.217+; ultracode and resumed agents can bypass it.'}

    def project_hash(self):
        return hashlib.sha256(str(self.target).encode('utf-8')).hexdigest()

    def usage_history(self):
        path = self.path(HISTORY)
        manifest_path = self.path(self.i.MANIFEST_RELATIVE)
        if not path.exists() or not manifest_path.is_file() or path.stat().st_size > HISTORY_LIMIT:
            return []
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            entries = data['entries']
            if data.get('schema') != 1 or not isinstance(entries, list) or len(entries) > 4096:
                return []
            if not entries or entries[-1].get('manifest_sha256') != self.i.digest(manifest_path):
                return []
            previous = ''
            for entry in entries:
                if (not isinstance(entry, dict) or entry.get('project_hash') != self.project_hash()
                    or entry.get('preset') not in {*self.i.PRESETS, 'custom'}
                    or not isinstance(entry.get('timestamp'), str)
                    or entry['timestamp'] <= previous):
                    return []
                datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                previous = entry['timestamp']
            return entries
        except (OSError, ValueError, KeyError, TypeError):
            return []

    def record_history(self, preset, previous_manifest_sha256=None):
        path = self.path(HISTORY)
        manifest = self.path(self.i.MANIFEST_RELATIVE)
        if preset not in {*self.i.PRESETS, 'custom'}:
            return False
        try:
            if path.exists() and path.stat().st_size > HISTORY_LIMIT:
                return False
            old = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schema': 1, 'entries': []}
            if old.get('schema') != 1 or not isinstance(old.get('entries'), list):
                return False
            # A separate installer run creates an unobserved interval. Do not
            # bridge it with old style history after this console write.
            if old['entries'] and old['entries'][-1].get('manifest_sha256') != previous_manifest_sha256:
                old['entries'] = []
            stamp = datetime.now(timezone.utc).isoformat()
            if old['entries'] and stamp <= old['entries'][-1].get('timestamp', ''):
                return False
            old['entries'].append({'timestamp': stamp, 'preset': preset,
                                   'project_hash': self.project_hash(),
                                   'manifest_sha256': self.i.digest(manifest)})
            content = json.dumps(old, indent=2) + '\n'
            if len(content.encode('utf-8')) > HISTORY_LIMIT:
                return False
            self.i.atomic_text(path, content, False)
            return True
        except (OSError, ValueError, TypeError, KeyError):
            return False

    def plan(self, payload):
        if not isinstance(payload, dict) or set(payload) - {'preset', 'routing', 'max_parallelism', 'roster', 'revision'}:
            raise ValueError('Unknown settings fields')
        routing = payload.get('routing')
        if not isinstance(routing, dict) or set(routing) != set(self.i.ROLES):
            raise ValueError('Every known role must be specified')
        selected = {}
        for role, choice in routing.items():
            if not isinstance(choice, dict) or set(choice) != {'model', 'effort'}:
                raise ValueError('Invalid role settings')
            model, effort = choice['model'], choice['effort']
            if not isinstance(model, str) or not isinstance(effort, str):
                raise ValueError('Model and effort must be text')
            self.i.validate_claude_model(model, role)
            self.i.validate_effort(effort, role, self.i.CLAUDE_OWNER_EFFORTS if role == 'owner' else self.i.CLAUDE_EFFORTS)
            selected[role] = model, effort
        count = payload.get('max_parallelism')
        if type(count) is not int or not 1 <= count <= 20:
            raise ValueError('Parallelism must be an integer from 1 to 20')
        preset = payload.get('preset', 'custom')
        if preset not in {*self.i.PRESETS, 'custom'}:
            raise ValueError('Unknown preset')
        self.path(self.i.MANIFEST_RELATIVE)
        self.path(HISTORY)
        manifest = self.i.load_manifest(self.target)
        old_roster = self.roster(manifest)
        roster = payload.get('roster', old_roster)
        if not isinstance(roster, list) or (not 1 <= len(roster) <= 10 and roster != old_roster):
            raise ValueError('Choose 1 to 10 helpers; an existing larger team is read-only')
        roster = self.roster({'roster': roster})
        if len(old_roster) > 10 and roster != old_roster:
            raise ValueError('Existing larger helper team is read-only')
        initial = not manifest.get('files')
        if initial:
            self.preflight_initial_install()
        changes = {}
        for role in self.i.ROLES[1:]:
            relative = Path('.claude/agents') / (role + '.md')
            path = self.path(relative)
            entry = manifest['files'].get(str(relative), {})
            if initial:
                if path.exists():
                    raise ValueError('Existing agent conflict: ' + str(relative) + '; review via installer first')
                source = self.root / relative
            else:
                if not path.is_file() or not entry.get('owned') or self.i.digest(path) != entry.get('sha256'):
                    raise ValueError('Managed agent conflict: ' + str(relative) + '; review via installer first')
                source = path
            changes[str(relative)] = self.i.render_agent(source, *selected[role])
        old_slots = {slot['id']: slot for slot in old_roster}
        new_slots = {slot['id']: slot for slot in roster}
        for slot_id in sorted(set(old_slots) | set(new_slots)):
            relative = self.slot_path(slot_id)
            path = self.path(relative)
            entry = manifest['files'].get(relative.as_posix(), {})
            if slot_id in old_slots:
                if not path.is_file() or not entry.get('owned') or self.i.digest(path) != entry.get('sha256'):
                    raise ValueError('Managed helper conflict: ' + relative.as_posix())
            elif path.exists():
                raise ValueError('Existing helper file conflict: ' + relative.as_posix())
            changes[relative.as_posix()] = self.render_slot(new_slots[slot_id]) if slot_id in new_slots else None
        if roster or old_roster:
            claude = self.path(Path('CLAUDE.md'))
            if claude.exists() and not claude.is_file():
                raise ValueError('CLAUDE.md is not a file')
            current = claude.read_text(encoding='utf-8') if claude.exists() else ''
            if not initial and (self.i.START_MARKER not in current or self.i.END_MARKER not in current):
                raise ValueError('Managed CLAUDE.md block is missing')
            changes['CLAUDE.md'] = self.render_team_block(current, roster)
        path = self.path(self.i.SETTINGS_RELATIVE)
        settings = json.loads(path.read_text()) if path.exists() else {}
        if not isinstance(settings, dict) or not isinstance(settings.get('env', {}), dict):
            raise ValueError('Settings and env must be JSON objects')
        settings['model'], settings['effortLevel'] = selected['owner']
        settings.setdefault('env', {})[CONCURRENCY] = str(count)
        if initial:
            settings['env'].setdefault('CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH', '1')
        changes[str(self.i.SETTINGS_RELATIVE)] = json.dumps(settings, indent=2) + '\n'
        # Only changed fields are returned; unrelated settings and secrets never enter API responses.
        preview = {'routing': routing, 'max_parallelism': count, 'target': str(self.target),
                   'roster': roster, 'files': list(changes), 'removed_files': [name for name, content in changes.items() if content is None], 'initial_install': initial,
                   'installation': 'First Save installs the managed toolkit with existing installer conflict/backups rules; restore keeps this initial installation.' if initial else 'Existing installation',
                   'preserved': 'All unrelated settings keys, env and agent bodies'}
        identity = {name: self.i.digest(self.path(Path(name))) if self.path(Path(name)).exists() else None for name in changes}
        revision = hashlib.sha256(json.dumps([identity, routing, count, preset, roster], sort_keys=True).encode()).hexdigest()
        preview['revision'] = revision
        return changes, manifest, preview

    def save(self, payload):
        changes, manifest, preview = self.plan(payload)
        if payload.get('revision') != preview['revision']:
            raise ValueError('Preview is stale; preview again before Save')
        self.path(self.i.MANIFEST_RELATIVE)
        self.path(self.i.BACKUP_RELATIVE)
        if preview['initial_install']:
            # Repeat full preflight immediately before the installer's first write.
            self.preflight_initial_install()
            if self.i.main([str(self.target)]) != 0:
                raise ValueError('Initial installation failed; inspect installer output')
            manifest = self.i.load_manifest(self.target)
        previous_manifest_sha256 = self.i.digest(self.path(self.i.MANIFEST_RELATIVE))
        state_path = self.path(STATE)
        before = json.loads(json.dumps(manifest))
        records = {}
        for name, content in changes.items():
            path = self.path(Path(name))
            saved = self.i.backup(self.target, path, False) if path.exists() else None
            records[name] = {'backup': str(saved.relative_to(self.target)) if saved else None,
                             'after': hashlib.sha256(content.encode()).hexdigest() if content is not None else None}
        state = {'files': records, 'manifest': before}
        self.i.atomic_text(state_path, json.dumps(state, indent=2) + '\n', False)
        for name, content in changes.items():
            path = self.path(Path(name))
            if content is None:
                path.unlink()
                manifest['files'].pop(name, None)
            else:
                self.i.atomic_text(path, content, False)
                if name != 'CLAUDE.md':
                    # A merged shared settings file must survive uninstall.
                    self.i.remember(manifest, Path(name), path, name != str(self.i.SETTINGS_RELATIVE))
        manifest['routing'] = payload['routing']
        manifest['preset'] = payload.get('preset', 'custom')
        manifest['roster'] = preview['roster']
        self.i.save_manifest(self.target, manifest, self.root, False)
        state['manifest_after_sha256'] = self.i.digest(self.path(self.i.MANIFEST_RELATIVE))
        self.i.atomic_text(state_path, json.dumps(state, indent=2) + '\n', False)
        recorded = self.record_history(manifest['preset'], previous_manifest_sha256)
        return {'saved': True, 'history_recorded': recorded, 'message': 'Project saved. Restart Claude Code; unrelated settings preserved.'}

    def restore(self):
        state_path = self.path(STATE)
        state = json.loads(state_path.read_text())
        before_roster = self.roster(state['manifest'])
        manifest = self.i.load_manifest(self.target)
        after_roster = self.roster(manifest)
        allowed = {str(self.i.SETTINGS_RELATIVE)} | {str(Path('.claude/agents') / (role + '.md')) for role in self.i.ROLES[1:]}
        if before_roster or after_roster:
            allowed.add('CLAUDE.md')
            allowed.update(self.slot_path(slot['id']).as_posix() for slot in before_roster + after_roster)
        if set(state['files']) != allowed:
            raise ValueError('Invalid console restore paths')
        manifest_path = self.path(self.i.MANIFEST_RELATIVE)
        if not manifest_path.is_file() or self.i.digest(manifest_path) != state.get('manifest_after_sha256'):
            raise ValueError('Install manifest changed after save; restore refused')
        previous_manifest_sha256 = self.i.digest(manifest_path)
        if manifest.get('routing') != self.read()['routing']:
            raise ValueError('Configuration changed after save; restore refused')
        contents = {}
        for name, record in state['files'].items():
            path = self.path(Path(name))
            if record['after'] is None:
                if path.exists():
                    raise ValueError('File appeared after save; restore refused: ' + name)
            elif not path.is_file() or self.i.digest(path) != record['after']:
                raise ValueError('File changed after save; restore refused: ' + name)
            saved = record['backup']
            if saved and not Path(saved).is_relative_to(self.i.BACKUP_RELATIVE):
                raise ValueError('Invalid backup path')
            contents[name] = self.path(Path(saved)).read_text() if saved else None
        self.path(self.i.MANIFEST_RELATIVE)
        self.path(self.i.BACKUP_RELATIVE)
        for name, content in contents.items():
            path = self.path(Path(name))
            if path.exists():
                self.i.backup(self.target, path, False)
            if content is None:
                path.unlink()
            else:
                self.i.atomic_text(path, content, False)
        self.i.save_manifest(self.target, state['manifest'], self.root, False)
        state_path.unlink()
        recorded = self.record_history(state['manifest'].get('preset', 'custom'), previous_manifest_sha256)
        return {'restored': True, 'history_recorded': recorded}
