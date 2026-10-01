from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USAGE = ROOT / ".claude/tools/usage_report.py"
LOCAL_EVAL = ROOT / ".claude/tools/local_eval.py"


class UsageAndEvalTests(unittest.TestCase):
    def test_orchestra_scopes_session_and_counts_only_explicit_helper_ids(self) -> None:
        spec = importlib.util.spec_from_file_location('usage_report', USAGE)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        def point(day, value, **fields):
            stamp = str(int(datetime(2026, 9, day, tzinfo=timezone.utc).timestamp() * 1e9))
            return {'timeUnixNano': stamp, 'asInt': str(value), 'attributes':
                    [{'key': key, 'value': {'stringValue': val}} for key, val in fields.items()]}
        base = {'session.id': 'work-one'}
        root = {**base, 'query_source': 'main', 'orchestra.agent.id': 'root-1', 'orchestra.root.id': 'root-1'}
        helper = {**base, 'query_source': 'subagent', 'orchestra.agent.id': 'helper-a',
                  'orchestra.parent.id': 'root-1', 'orchestra.root.id': 'root-1',
                  'orchestra.agent.name': '<img src=x onerror=alert(1)>', 'orchestra.agent.role': 'researcher'}
        missing_parent = {**base, 'query_source': 'subagent', 'orchestra.agent.id': 'helper-b',
                          'orchestra.root.id': 'root-1'}
        metrics = [
            {'name': 'claude_code.token.usage', 'sum': {'aggregationTemporality': 2, 'dataPoints': [
                point(27, 100, **root, type='input', model='Sonnet'), point(28, 150, **root, type='input', model='Sonnet')]}},
            {'name': 'claude_code.token.usage', 'sum': {'aggregationTemporality': 1, 'dataPoints': [
                point(27, 20, **root, type='output', model='Sonnet'),
                point(27, 40, **helper, type='input', model='Sonnet'),
                point(28, 10, **helper, type='output', model='Opus'),
                point(28, 15, **helper, type='cacheRead', model='Sonnet'),
                point(28, 30, **missing_parent, type='input', model='Sonnet'),
                point(28, 5, **base, query_source='auxiliary', type='input', model='Sonnet'),
                point(28, 7, **base, type='output', model='Sonnet'),
                point(28, 50, **root, type='cacheRead', model='Sonnet'),
                point(28, 9, **{'session.id':'work-two'}, type='input', model='Opus')]}}
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'sanitized.json';path.write_text(json.dumps({'resourceMetrics':[{'scopeMetrics':[{'metrics':metrics}]}]}))
            result = module.report(path)
            orchestra = result['analysis']['orchestra']
            self.assertEqual(orchestra['all']['primary'], 271)
            first = next(item for item in orchestra['sessions'] if item['id'] == 'work-one')
            self.assertEqual(first['counts']['primary'], 262)
            self.assertEqual(first['conductor']['counts']['primary'], 170)
            self.assertEqual(first['helpers']['counts']['primary'], 80)
            self.assertEqual(first['helpers']['observed_count'], 1)
            self.assertFalse(first['helpers']['count_complete'])
            self.assertEqual(first['helpers']['unidentified']['primary'], 30)
            self.assertEqual(first['unknown']['primary'], 12)
            self.assertEqual(first['conductor']['counts']['cacheRead'], 50)
            agent = first['helpers']['agents'][0]
            self.assertEqual(agent['name'], '<img src=x onerror=alert(1)>')
            self.assertEqual([(row['key'], row['primary']) for row in agent['models']], [('Sonnet', 40), ('Opus', 10)])
            filtered = module.report(path, start='2026-09-28', end='2026-09-28')['analysis']['orchestra']
            only = next(item for item in filtered['sessions'] if item['id'] == 'work-one')
            self.assertEqual(only['counts']['primary'], 102)
            self.assertEqual(only['conductor']['counts']['primary'], 50)
            self.assertEqual(only['helpers']['observed_count'], 1)

    def test_orchestra_standard_agent_name_is_not_an_instance(self) -> None:
        spec = importlib.util.spec_from_file_location('usage_report', USAGE)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'metrics.json'
            attrs = lambda **values: [{'key': key, 'value': {'stringValue': value}} for key, value in values.items()]
            points = [{'asInt': '20', 'attributes': attrs(**{'session.id':'one','query_source':'main','type':'input','model':'Sonnet'})},
                      {'asInt': '30', 'attributes': attrs(**{'session.id':'one','query_source':'subagent','agent.name':'explorer','type':'input','model':'Sonnet'})},
                      {'asInt': '10', 'attributes': attrs(**{'session.id':'one','query_source':'subagent','agent.name':'explorer','type':'output','model':'Opus'})}]
            path.write_text(json.dumps({'resourceMetrics':[{'scopeMetrics':[{'metrics':[{'name':'claude_code.token.usage','sum':{'aggregationTemporality':1,'dataPoints':points}}]}]}]}))
            session = module.report(path)['analysis']['orchestra']['sessions'][0]
            self.assertEqual(session['conductor']['counts']['primary'], 20)
            self.assertEqual(session['helpers']['counts']['primary'], 40)
            self.assertEqual(session['helpers']['observed_count'], 0)
            self.assertEqual(session['helpers']['agents'], [])
            self.assertEqual(session['helpers']['unidentified']['primary'], 40)
            self.assertEqual(module.report(path)['analysis']['timeline'], [
                {'observed_at': None, 'input': 50, 'output': 10, 'cacheRead': 0, 'cacheCreation': 0, 'primary': 60}])

    def test_orchestra_nested_parent_chain_counts_two_helpers(self) -> None:
        spec = importlib.util.spec_from_file_location('usage_report', USAGE)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        def point(value, **fields):
            return {'asInt': str(value), 'attributes': [{'key': key, 'value': {'stringValue': val}} for key, val in fields.items()]}
        root = {'session.id':'work','query_source':'main','orchestra.agent.id':'root','orchestra.root.id':'root'}
        a = {'session.id':'work','query_source':'subagent','orchestra.agent.id':'a','orchestra.parent.id':'root','orchestra.root.id':'root'}
        b = {'session.id':'work','query_source':'subagent','orchestra.agent.id':'b','orchestra.parent.id':'a','orchestra.root.id':'root'}
        doc = {'resourceMetrics':[{'scopeMetrics':[{'metrics':[{'name':'claude_code.token.usage','sum':{'aggregationTemporality':1,'dataPoints':[
            point(10, **root, type='input', model='Sonnet'),point(10, **a, type='input', model='Sonnet'),point(10, **b, type='output', model='Opus')]}}]}]}]}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'metrics.json';path.write_text(json.dumps(doc))
            session = module.report(path)['analysis']['orchestra']['sessions'][0]
            self.assertEqual(session['counts']['primary'], 30)
            self.assertEqual(session['helpers']['counts']['primary'], 20)
            self.assertEqual(session['helpers']['observed_count'], 2)
            self.assertEqual(session['helpers']['unidentified']['primary'], 0)
            self.assertEqual({item['id']:item['parent_id'] for item in session['helpers']['agents']}, {'a':'root','b':'a'})
            more = doc['resourceMetrics'][0]['scopeMetrics'][0]['metrics'][0]['sum']['dataPoints']
            more.extend([
                point(4, **{'session.id':'work','query_source':'subagent','orchestra.agent.id':'c','orchestra.parent.id':'d','orchestra.root.id':'root'}, type='input', model='Sonnet'),
                point(5, **{'session.id':'work','query_source':'subagent','orchestra.agent.id':'d','orchestra.parent.id':'c','orchestra.root.id':'root'}, type='input', model='Sonnet'),
                point(6, **{'session.id':'work','query_source':'subagent','orchestra.agent.id':'orphan','orchestra.parent.id':'missing','orchestra.root.id':'root'}, type='output', model='Opus')])
            path.write_text(json.dumps(doc))
            uncertain = module.report(path)['analysis']['orchestra']['sessions'][0]
            self.assertEqual(uncertain['helpers']['observed_count'], 2)
            self.assertEqual(uncertain['helpers']['unidentified']['primary'], 15)
            self.assertEqual([(item['key'],item['primary']) for item in uncertain['helpers']['unidentified_models']], [('Sonnet',9),('Opus',6)])

    def test_orchestra_conflicting_identity_goes_to_unknown(self) -> None:
        spec = importlib.util.spec_from_file_location('usage_report', USAGE)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        def point(value, **fields):
            return {'asInt': str(value), 'attributes': [{'key': key, 'value': {'stringValue': val}} for key, val in fields.items()]}
        root = {'session.id':'work','query_source':'main','orchestra.agent.id':'root','orchestra.root.id':'root'}
        false_main = {'session.id':'work','query_source':'main','orchestra.agent.id':'helper','orchestra.parent.id':'root','orchestra.root.id':'root'}
        inverse = {'session.id':'work','query_source':'subagent','orchestra.agent.id':'root','orchestra.parent.id':'root','orchestra.root.id':'root'}
        doc = {'resourceMetrics':[{'scopeMetrics':[{'metrics':[{'name':'claude_code.token.usage','sum':{'aggregationTemporality':1,'dataPoints':[
            point(10, **root, type='input', model='Sonnet'),point(7, **false_main, type='output', model='Sonnet'),
            point(5, **inverse, type='input', model='Opus')]}}]}]}]}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'metrics.json'
            first = json.loads(json.dumps(doc))
            first['resourceMetrics'][0]['scopeMetrics'][0]['metrics'][0]['sum']['dataPoints'].pop()
            path.write_text(json.dumps(first))
            before = module.report(path)['analysis']['orchestra']['sessions'][0]
            self.assertEqual(before['counts']['primary'], 17)
            self.assertEqual(before['conductor']['counts']['primary'], 10)
            self.assertEqual(before['unknown']['primary'], 7)
            path.write_text(json.dumps(doc))
            session = module.report(path)['analysis']['orchestra']['sessions'][0]
            self.assertEqual(session['counts']['primary'], 22)
            self.assertEqual(session['conductor']['counts']['primary'], 0)
            self.assertEqual(session['helpers']['counts']['primary'], 0)
            self.assertEqual(session['unknown']['primary'], 22)


    def test_model_and_style_charts_count_only_input_output_and_safe_history_joins(self) -> None:
        spec = importlib.util.spec_from_file_location('usage_report', USAGE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        def ns(day, hour):
            return str(int(datetime(2026, 9, day, hour, tzinfo=timezone.utc).timestamp() * 1_000_000_000))
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary).resolve()
            digest = module._project_hash(str(project))
            def attr(key, value):
                return {'key': key, 'value': {'stringValue': value}}
            def point(day, hour, session, project_marker, value, **extra):
                fields = [attr('session.id', session)] + [attr(key, val) for key, val in extra.items()]
                if project_marker:
                    fields.append(attr('project.path', str(project)))
                return {'timeUnixNano': ns(day, hour), 'asInt': str(value), 'attributes': fields}
            starts = [point(27, 9, 'one', True, 1, start_type='fresh'),
                      point(28, 9, 'two', True, 1, start_type='fresh'),
                      point(28, 10, 'resume', True, 1, start_type='resume'),
                      point(28, 11, 'untagged', False, 1, start_type='fresh')]
            tokens = [point(27, 10, 'one', True, 100, type='input', model='Sonnet'),
                      point(27, 11, 'one', True, 30, type='output', model='Sonnet'),
                      point(27, 12, 'one', True, 50, type='cacheRead', model='Sonnet'),
                      point(28, 10, 'two', True, 40, type='input', model='Opus'),
                      point(28, 11, 'two', True, 20, type='output', model='Opus'),
                      point(28, 12, 'resume', True, 10, type='input', model='Opus'),
                      point(28, 12, 'untagged', False, 5, type='output', model='Opus')]
            doc = {'resourceMetrics': [{'scopeMetrics': [{'metrics': [
                {'name': 'claude_code.session.count', 'sum': {'aggregationTemporality': 1, 'dataPoints': starts}},
                {'name': 'claude_code.token.usage', 'sum': {'aggregationTemporality': 1, 'dataPoints': tokens}},
            ]}]}]}
            path = project / 'metrics.json'
            path.write_text(json.dumps(doc))
            history = [{'timestamp': '2026-09-27T08:00:00+00:00', 'preset': 'balanced', 'project_hash': digest},
                       {'timestamp': '2026-09-28T08:00:00+00:00', 'preset': 'economy', 'project_hash': digest}]
            result = module.report(path, history=history, project_hash=digest)
            analysis = result['analysis']
            self.assertEqual(analysis['totals']['primary'], 205)
            self.assertEqual(analysis['totals']['cacheRead'], 50)
            self.assertEqual(sum(row['primary'] for row in analysis['timeline']), 205)
            self.assertEqual(sum(row['cacheRead'] for row in analysis['timeline']), 50)
            self.assertTrue(all(row['observed_at'] for row in analysis['timeline']))
            self.assertEqual([(row['key'], row['primary']) for row in analysis['styles']],
                             [('balanced', 130), ('economy', 60), ('unknown', 15)])
            self.assertEqual([(row['key'], row['primary']) for row in analysis['models']],
                             [('Sonnet', 130), ('Opus', 75)])
            self.assertEqual(analysis['style_attribution'], 'estimated_from_settings_history')
            day_two = module.report(path, start='2026-09-28', end='2026-09-28', history=history, project_hash=digest)
            self.assertEqual(day_two['analysis']['totals']['primary'], 75)
            self.assertEqual(sum(row['primary'] for row in day_two['analysis']['timeline']), 75)
            self.assertTrue(all(row['observed_at'].startswith('2026-09-28') for row in day_two['analysis']['timeline']))
            self.assertEqual(day_two['analysis']['styles'][0]['key'], 'economy')
            no_history = module.report(path)['analysis']
            self.assertEqual(no_history['styles'][0]['key'], 'unknown')
            self.assertEqual(no_history['style_attribution'], 'unavailable')

    def test_style_crossing_setting_change_is_unknown(self) -> None:
        spec = importlib.util.spec_from_file_location('usage_report', USAGE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            digest = module._project_hash(str(project))
            def point(hour, value, **fields):
                return {'timeUnixNano': str(int(datetime(2026, 9, 28, hour, tzinfo=timezone.utc).timestamp() * 1e9)),
                        'asInt': str(value), 'attributes': [{'key': k, 'value': {'stringValue': v}} for k, v in fields.items()]}
            attrs = {'session.id': 'cross', 'project.path': str(project)}
            doc = {'resourceMetrics': [{'scopeMetrics': [{'metrics': [
                {'name': 'claude_code.session.count', 'sum': {'aggregationTemporality': 1, 'dataPoints': [point(9, 1, **attrs, start_type='fresh')]}},
                {'name': 'claude_code.token.usage', 'sum': {'aggregationTemporality': 1, 'dataPoints': [point(10, 7, **attrs, type='input', model='Sonnet')]}},
                {'name': 'claude_code.cost.usage', 'sum': {'aggregationTemporality': 1, 'dataPoints': [point(12, 3, **attrs, model='Sonnet')]}}
            ]}]}]}
            path = project / 'metrics.json'; path.write_text(json.dumps(doc))
            history = [{'timestamp': '2026-09-28T08:00:00+00:00', 'preset': 'balanced', 'project_hash': digest},
                       {'timestamp': '2026-09-28T11:00:00+00:00', 'preset': 'economy', 'project_hash': digest}]
            first_only = json.loads(json.dumps(doc))
            first_only['resourceMetrics'][0]['scopeMetrics'][0]['metrics'].pop()
            path.write_text(json.dumps(first_only))
            self.assertEqual(module.report(path, history=history, project_hash=digest)['analysis']['styles'][0]['key'], 'balanced')
            path.write_text(json.dumps(doc))
            result = module.report(path, start='2026-09-28', end='2026-09-28', history=history, project_hash=digest)
            self.assertEqual(result['analysis']['styles'][0]['key'], 'unknown')

    def test_usage_is_unavailable_without_explicit_telemetry_input(self) -> None:
        result = subprocess.run([sys.executable, str(USAGE), "--json"], text=True, capture_output=True, check=False)
        self.assertEqual(json.loads(result.stdout)["status"], "unavailable")

    def test_usage_reads_synthetic_otlp_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "metrics.json"
            path.write_text(json.dumps({"resourceMetrics": [{"scopeMetrics": [{"metrics": [{"name": "claude_code.token.usage", "sum": {"aggregationTemporality": 1, "dataPoints": [{"asInt": "7", "attributes": [{"key": "model", "value": {"stringValue": "claude-test"}}, {"key": "type", "value": {"stringValue": "input"}}]}]}}]}]}]}))
            result = subprocess.run([sys.executable, str(USAGE), "--input", str(path), "--json"], text=True, capture_output=True, check=False)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "available")
            self.assertEqual(payload["groups"][0]["value"], 7)

    def test_delta_cumulative_streams_and_resets_are_accounted_separately(self) -> None:
        attrs = [{"key": "model", "value": {"stringValue": "claude-test"}}, {"key": "type", "value": {"stringValue": "input"}}]
        def metric(mode, values):
            return {"name": "claude_code.token.usage", "sum": {"aggregationTemporality": mode, "dataPoints": [{"asInt": str(value), "attributes": attrs} for value in values]}}
        document = {"resourceMetrics": [
            {"resource": {"attributes": [{"key": "session.id", "value": {"stringValue": "cumulative-one"}}]}, "scopeMetrics": [{"metrics": [metric(2, [100, 150])]}]},
            {"resource": {"attributes": [{"key": "session.id", "value": {"stringValue": "delta-one"}}]}, "scopeMetrics": [{"metrics": [metric(1, [100, 150])]}]},
            {"resource": {"attributes": [{"key": "session.id", "value": {"stringValue": "reset-stream"}}]}, "scopeMetrics": [{"metrics": [metric(2, [40, 10])]}]},
        ]}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "metrics.json"
            path.write_text(json.dumps(document))
            payload = json.loads(subprocess.run([sys.executable, str(USAGE), "--input", str(path), "--json"], text=True, capture_output=True, check=True).stdout)
            self.assertEqual(payload["totals"]["input"], 450)
            self.assertEqual(payload["delta_points"], 2)
            self.assertEqual(payload["cumulative_points"], 4)
            self.assertEqual(payload["counter_resets_observed"], 1)

    def test_cumulative_start_time_change_opens_a_new_epoch(self) -> None:
        attrs = [{"key": "model", "value": {"stringValue": "claude-test"}}, {"key": "type", "value": {"stringValue": "input"}}]
        points = [
            {"asInt": "100", "startTimeUnixNano": "1000", "attributes": attrs},
            {"asInt": "150", "startTimeUnixNano": "2000", "attributes": attrs},
        ]
        document = {"resourceMetrics": [{"scopeMetrics": [{"metrics": [{
            "name": "claude_code.token.usage",
            "sum": {"aggregationTemporality": 2, "dataPoints": points},
        }]}]}]}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "metrics.json"
            path.write_text(json.dumps(document))
            payload = json.loads(subprocess.run(
                [sys.executable, str(USAGE), "--input", str(path), "--json"],
                text=True, capture_output=True, check=True,
            ).stdout)
            self.assertEqual(payload["totals"]["input"], 250)
            self.assertEqual(payload["counter_resets_observed"], 1)

    def test_local_eval_writes_digest_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            manifest = repo / "eval.json"
            manifest.write_text(json.dumps({"label": "unit", "argv": [sys.executable, "-c", "print('ok')"], "timeout_seconds": 10}))
            result = subprocess.run([sys.executable, str(LOCAL_EVAL), "--repo", str(repo), "--json", str(manifest)], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads((repo / ".claude/.bounded-orchestrator/evals/unit.json").read_text())
            self.assertEqual(summary["outcome"], "pass")
            self.assertNotIn("sanitized_tail", summary)


if __name__ == "__main__":
    unittest.main()
