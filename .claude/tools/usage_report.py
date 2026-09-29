#!/usr/bin/env python3
"""Summarize explicitly supplied Claude Code OpenTelemetry metric exports."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
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


def timestamp(point):
    try:
        return datetime.fromtimestamp(int(point.get("timeUnixNano")) / 1e9, timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def report(path: Path | None, start: str | None = None, end: str | None = None) -> dict:
    for date in (start, end):
        if date:
            datetime.strptime(date, "%Y-%m-%d")
    base = {"platform": "claude", "source": "explicit-otlp-file" if path else "none",
            "status": "unavailable", "groups": [], "totals": {}, "cost_totals": {}, "events": [],
            "dimensions": {"model": False, "date": False, "thread": False, "agent": False},
            "limitations": "Explicit OTLP Sum metrics only. No transcripts, telemetry activation, pricing estimates or subscription quota conversion. Date ranges exclude undated points; cumulative increments are attributed to observation dates and can span a range boundary. Runtime settings may override project settings."}
    if path is None:
        base["message"] = "No sanitized OTLP JSON/JSONL file supplied. Claude Code /usage provides the official interactive view."
        return base
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("OTLP file exceeds 32 MiB")
    text = path.read_text(encoding="utf-8")
    try:
        documents = [json.loads(text)]
    except json.JSONDecodeError:
        documents = [json.loads(line) for line in text.splitlines() if line.strip()]
    entries, seen_documents = [], set()
    unknown = duplicates = 0
    for document in documents:
        identity = json.dumps(document, sort_keys=True, separators=(",", ":"))
        if identity in seen_documents:
            duplicates += 1
            continue
        seen_documents.add(identity)
        for metric, resource_identity in walk_metrics(document):
            mode, points = temporality(metric)
            if mode == "unknown":
                unknown += 1
                continue
            for point in points:
                entries.append((metric["name"], resource_identity, mode, point))
    # Stable timestamp order avoids differencing backwards in concatenated exports.
    entries.sort(key=lambda entry: (timestamp(entry[3]) is None, timestamp(entry[3]) or ""))
    totals, costs, groups = defaultdict(float), defaultdict(float), defaultdict(float)
    previous, seen_points = {}, set()
    rows = delta = cumulative = resets = 0
    for name, resource_identity, mode, point in entries:
        try:
            value = float(point.get("asInt", point.get("asDouble", point.get("value"))))
        except (ValueError, TypeError):
            continue
        if not math.isfinite(value) or value < 0:
            continue
        attrs = attributes(point.get("attributes"))
        resource_attrs = {}
        for kind, pairs in resource_identity:
            if kind == "resource":
                resource_attrs.update(pairs)
        stamp = timestamp(point)
        stream = (name, resource_identity, tuple(sorted(attrs.items())))
        if stamp:
            signature = (stream, mode, str(point.get("startTimeUnixNano")), stamp, value)
            if signature in seen_points:
                duplicates += 1
                continue
            seen_points.add(signature)
        if mode == "delta":
            increment = value
            delta += 1
        else:
            epoch = str(point.get("startTimeUnixNano")) if point.get("startTimeUnixNano") is not None else None
            prior = previous.get(stream)
            reset = prior and ((epoch is not None and prior[1] is not None and epoch != prior[1]) or value < prior[0])
            increment = value if prior is None or reset else value - prior[0]
            resets += int(bool(reset))
            previous[stream] = (value, epoch)
            cumulative += 1
        if (start or end) and (stamp is None or (start and stamp[:10] < start) or (end and stamp[:10] > end)):
            continue
        model = attrs.get("model", attrs.get("model_name", "unknown"))[:128]
        kind = attrs.get("type", attrs.get("token_type", name))[:128]
        thread = attrs.get("session.id", resource_attrs.get("session.id"))
        agent = attrs.get("agent.name", resource_attrs.get("agent.name"))
        is_cost = "cost" in name.lower()
        (costs if is_cost else totals)[kind] += increment
        groups[(model, kind, "cost" if is_cost else "tokens")] += increment
        base["events"].append({"date": stamp, "model": model, "thread": str(thread)[:128] if thread else None,
                               "agent": str(agent)[:128] if agent else None, "type": kind,
                               "unit": "cost" if is_cost else "tokens", "value": increment})
        for dimension, available in (("model", model != "unknown"), ("date", bool(stamp)), ("thread", bool(thread)), ("agent", bool(agent))):
            base["dimensions"][dimension] |= available
        rows += 1
    base.update(status="available" if rows else "unavailable", metric_points_observed=rows,
                delta_points=delta, cumulative_points=cumulative, counter_resets_observed=resets,
                duplicate_exports_or_points_skipped=duplicates, unknown_temporality_metrics_skipped=unknown,
                totals=dict(sorted(totals.items())), cost_totals=dict(sorted(costs.items())),
                groups=[{"model": m, "type": t, "unit": u, "value": v} for (m,t,u),v in sorted(groups.items())])
    return base


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
