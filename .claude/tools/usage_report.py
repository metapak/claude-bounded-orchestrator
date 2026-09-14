#!/usr/bin/env python3
"""Summarize explicitly supplied Claude Code OpenTelemetry metric exports."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def attributes(value) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items() if isinstance(v, (str, int, float))}
    result = {}
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict) or not isinstance(item.get("key"), str):
                continue
            raw = item.get("value")
            if isinstance(raw, dict):
                raw = next((v for k, v in raw.items() if k.endswith("Value")), None)
            if isinstance(raw, (str, int, float)):
                result[item["key"]] = str(raw)
    return result


def walk_metrics(obj, identity: tuple = ()):
    if isinstance(obj, dict):
        current = identity
        resource = obj.get("resource")
        if isinstance(resource, dict):
            current += (("resource", tuple(sorted(attributes(resource.get("attributes")).items()))),)
        scope = obj.get("scope")
        if isinstance(scope, dict):
            scope_fields = attributes(scope.get("attributes"))
            for key in ("name", "version"):
                if isinstance(scope.get(key), str):
                    scope_fields[key] = scope[key]
            current += (("scope", tuple(sorted(scope_fields.items()))),)
        if isinstance(obj.get("name"), str) and ("token" in obj["name"].lower() or "cost" in obj["name"].lower()):
            yield obj, current
        for value in obj.values():
            yield from walk_metrics(value, current)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_metrics(value, identity)


def temporality(metric: dict) -> tuple[str, list[dict]]:
    body = metric.get("sum")
    if not isinstance(body, dict):
        return "unknown", []
    raw = body.get("aggregationTemporality")
    if raw in (1, "1", "AGGREGATION_TEMPORALITY_DELTA", "DELTA", "delta"):
        mode = "delta"
    elif raw in (2, "2", "AGGREGATION_TEMPORALITY_CUMULATIVE", "CUMULATIVE", "cumulative"):
        mode = "cumulative"
    else:
        return "unknown", []
    return mode, [point for point in body.get("dataPoints", []) if isinstance(point, dict)]


def report(path: Path | None) -> dict:
    if path is None:
        return {"status": "unavailable", "source": "none",
                "message": "No sanitized OpenTelemetry metric export was supplied. Use Claude Code /usage for the official interactive view, or configure OpenTelemetry yourself and pass an exported OTLP JSON/JSONL file.",
                "groups": [], "totals": {}}
    totals, groups, rows = defaultdict(float), defaultdict(float), 0
    previous: dict[tuple, tuple[float, str | None]] = {}
    delta_points = cumulative_points = resets = unknown_metrics = 0
    text = path.read_text(encoding="utf-8", errors="replace")
    documents = []
    try:
        documents = [json.loads(text)]
    except json.JSONDecodeError:
        for line in text.splitlines():
            try:
                documents.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    for document in documents:
        for metric, resource_identity in walk_metrics(document):
            name = metric.get("name", "unknown")
            mode, metric_points = temporality(metric)
            if mode == "unknown":
                unknown_metrics += 1
                continue
            for point in metric_points:
                raw = point.get("asInt", point.get("asDouble", point.get("value")))
                try:
                    value = float(raw)
                except (TypeError, ValueError):
                    continue
                attrs = attributes(point.get("attributes"))
                model = attrs.get("model", attrs.get("model_name", "unknown"))
                token_type = attrs.get("type", attrs.get("token_type", name))
                stream = (name, resource_identity, tuple(sorted(attrs.items())))
                if mode == "delta":
                    increment = value
                    delta_points += 1
                else:
                    start_raw = point.get("startTimeUnixNano")
                    start_time = str(start_raw) if isinstance(start_raw, (str, int)) else None
                    prior = previous.get(stream)
                    if prior is None:
                        increment = value
                    elif start_time is not None and prior[1] is not None and start_time != prior[1]:
                        increment = value
                        resets += 1
                    elif value >= prior[0]:
                        increment = value - prior[0]
                    else:
                        increment = value
                        resets += 1
                    previous[stream] = (value, start_time)
                    cumulative_points += 1
                groups[(model, token_type)] += increment
                totals[token_type] += increment
                rows += 1
    return {"status": "available" if rows else "unavailable", "source": str(path),
            "metric_points_observed": rows,
            "delta_points": delta_points,
            "cumulative_points": cumulative_points,
            "counter_resets_observed": resets,
            "unknown_temporality_metrics_skipped": unknown_metrics,
            "groups": [{"model": m, "type": t, "value": v} for (m, t), v in sorted(groups.items())],
            "totals": dict(sorted(totals.items())),
            "limitations": "Only supplied OTLP Sum metrics with explicit delta or cumulative temporality are reported. Cumulative streams are differenced independently and counter resets start a new sequence. This does not enable telemetry, read transcripts, or convert usage to quota percentages or cost."}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = report(args.input.expanduser().resolve() if args.input else None)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Claude usage report: {result['status']}")
        if result["status"] == "unavailable":
            print(result.get("message", "No token metrics were found."))
        for item in result["groups"]:
            print(f"- model={item['model']} type={item['type']}: {item['value']:g}")
        if result.get("limitations"):
            print(result["limitations"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
