#!/usr/bin/env python3
"""Maintain a small, private metadata-only task ledger for bounded orchestration."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = 1
STATE_RELATIVE = Path(".claude/.bounded-orchestrator/tasks.json")
LOCK_SUFFIX = ".lock"
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
MAX_SUMMARY = 160
MAX_EVIDENCE = 240
MAX_ROLE = 48
STATUSES = {"pending", "in_progress", "blocked", "complete"}


class LedgerError(RuntimeError):
    """Expected command failure."""


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_text(value: str, label: str, limit: int) -> str:
    value = " ".join(value.split())
    if not value:
        raise LedgerError(f"{label} must not be empty")
    if len(value) > limit:
        raise LedgerError(f"{label} must be at most {limit} characters")
    return value


def state_path(repo: Path) -> Path:
    root = repo.expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise LedgerError(f"repository directory does not exist: {root}")
    return root / STATE_RELATIVE


@contextmanager
def lock(path: Path, timeout: float = 5.0) -> Iterator[None]:
    lock_path = path.with_name(path.name + LOCK_SUFFIX)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise LedgerError(f"ledger is busy: {lock_path}") from None
            time.sleep(0.05)
    try:
        os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
        os.fsync(descriptor)
        yield
    finally:
        os.close(descriptor)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.chmod(temporary, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


def validate(data: dict) -> None:
    if data.get("schema") != SCHEMA_VERSION or not isinstance(data.get("tasks"), list):
        raise LedgerError("unsupported or malformed task ledger")
    ids: set[str] = set()
    for task in data["tasks"]:
        if not isinstance(task, dict):
            raise LedgerError("malformed task entry")
        task_id = task.get("id")
        if not isinstance(task_id, str) or not ID_PATTERN.fullmatch(task_id):
            raise LedgerError("malformed task id")
        if task_id in ids:
            raise LedgerError(f"duplicate task id: {task_id}")
        ids.add(task_id)
        if task.get("status") not in STATUSES:
            raise LedgerError(f"invalid status for {task_id}")
        if not isinstance(task.get("depends_on"), list) or not all(
            isinstance(item, str) for item in task["depends_on"]
        ):
            raise LedgerError(f"invalid dependencies for {task_id}")
    for task in data["tasks"]:
        missing = set(task["depends_on"]) - ids
        if missing:
            raise LedgerError(f"{task['id']} has missing dependencies: {', '.join(sorted(missing))}")


def load(path: Path) -> dict:
    if not path.exists():
        raise LedgerError("ledger is not initialized; run `init` first")
    if path.is_symlink():
        raise LedgerError("refusing to read a symlinked ledger")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LedgerError(f"cannot read task ledger: {exc}") from exc
    if not isinstance(data, dict):
        raise LedgerError("malformed task ledger")
    validate(data)
    return data


def save(path: Path, data: dict) -> None:
    data["updated_at"] = now()
    validate(data)
    atomic_write(path, data)


def find_task(data: dict, task_id: str) -> dict:
    for task in data["tasks"]:
        if task["id"] == task_id:
            return task
    raise LedgerError(f"unknown task: {task_id}")


def command_init(path: Path, force: bool) -> None:
    with lock(path):
        if path.exists() and not force:
            load(path)
            print(f"Ledger already initialized: {path}")
            return
        timestamp = now()
        atomic_write(path, {"schema": SCHEMA_VERSION, "created_at": timestamp, "updated_at": timestamp, "tasks": []})
    print(f"Initialized private task ledger: {path}")


def command_add(path: Path, task_id: str, summary: str, role: str, dependencies: list[str]) -> None:
    if not ID_PATTERN.fullmatch(task_id):
        raise LedgerError("task id must be 1-32 letters, numbers, underscores, or hyphens")
    summary = clean_text(summary, "summary", MAX_SUMMARY)
    role = clean_text(role, "role", MAX_ROLE)
    dependencies = list(dict.fromkeys(dependencies))
    if task_id in dependencies:
        raise LedgerError("a task cannot depend on itself")
    with lock(path):
        data = load(path)
        if any(item["id"] == task_id for item in data["tasks"]):
            raise LedgerError(f"task already exists: {task_id}")
        existing = {item["id"] for item in data["tasks"]}
        missing = set(dependencies) - existing
        if missing:
            raise LedgerError(f"unknown dependencies: {', '.join(sorted(missing))}")
        data["tasks"].append({
            "id": task_id,
            "summary": summary,
            "role": role,
            "status": "pending",
            "depends_on": dependencies,
            "evidence": "",
            "created_at": now(),
            "updated_at": now(),
        })
        save(path, data)
    print(f"Added {task_id}")


def command_start(path: Path, task_id: str) -> None:
    with lock(path):
        data = load(path)
        task = find_task(data, task_id)
        if task["status"] not in {"pending", "blocked"}:
            raise LedgerError(f"cannot start {task_id} from {task['status']}")
        incomplete = [dep for dep in task["depends_on"] if find_task(data, dep)["status"] != "complete"]
        if incomplete:
            raise LedgerError(f"cannot start {task_id}; incomplete dependencies: {', '.join(incomplete)}")
        task["status"] = "in_progress"
        task["evidence"] = ""
        task["updated_at"] = now()
        save(path, data)
    print(f"Started {task_id}")


def command_complete(path: Path, task_id: str, evidence: str) -> None:
    evidence = clean_text(evidence, "evidence", MAX_EVIDENCE)
    with lock(path):
        data = load(path)
        task = find_task(data, task_id)
        if task["status"] != "in_progress":
            raise LedgerError(f"cannot complete {task_id} from {task['status']}")
        incomplete = [dep for dep in task["depends_on"] if find_task(data, dep)["status"] != "complete"]
        if incomplete:
            raise LedgerError(f"cannot complete {task_id}; incomplete dependencies: {', '.join(incomplete)}")
        task["status"] = "complete"
        task["evidence"] = evidence
        task["updated_at"] = now()
        save(path, data)
    print(f"Completed {task_id}")


def command_block(path: Path, task_id: str, evidence: str) -> None:
    evidence = clean_text(evidence, "evidence", MAX_EVIDENCE)
    with lock(path):
        data = load(path)
        task = find_task(data, task_id)
        if task["status"] not in {"pending", "in_progress"}:
            raise LedgerError(f"cannot block {task_id} from {task['status']}")
        task["status"] = "blocked"
        task["evidence"] = evidence
        task["updated_at"] = now()
        save(path, data)
    print(f"Blocked {task_id}")


def command_show(path: Path, as_json: bool) -> None:
    data = load(path)
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return
    if not data["tasks"]:
        print("No tasks")
        return
    for task in data["tasks"]:
        deps = ",".join(task["depends_on"]) or "-"
        print(f"{task['id']:<16} {task['status']:<12} role={task['role']} deps={deps}  {task['summary']}")


def command_check(path: Path) -> None:
    data = load(path)
    unfinished = [task for task in data["tasks"] if task["status"] != "complete"]
    if unfinished:
        details = ", ".join(f"{task['id']}={task['status']}" for task in unfinished)
        raise LedgerError(f"completion gate failed: {details}")
    print(f"Completion gate passed: {len(data['tasks'])} task(s) complete")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo", type=Path, default=Path.cwd(), help="target repository (default: current directory)")
    subparsers = result.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init", help="create an empty ledger")
    init.add_argument("--force", action="store_true", help="replace an existing ledger")
    add = subparsers.add_parser("add", help="add a pending task")
    add.add_argument("task_id")
    add.add_argument("--summary", required=True)
    add.add_argument("--role", required=True)
    add.add_argument("--depends-on", action="append", default=[], metavar="TASK_ID")
    start = subparsers.add_parser("start", help="start a ready task")
    start.add_argument("task_id")
    complete = subparsers.add_parser("complete", help="complete an in-progress task")
    complete.add_argument("task_id")
    complete.add_argument("--evidence", required=True)
    blocked = subparsers.add_parser("block", help="mark a task blocked")
    blocked.add_argument("task_id")
    blocked.add_argument("--evidence", required=True)
    show = subparsers.add_parser("show", help="show ledger state")
    show.add_argument("--json", action="store_true")
    subparsers.add_parser("check", help="require all tasks to be complete")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        path = state_path(args.repo)
        if args.command == "init":
            command_init(path, args.force)
        elif args.command == "add":
            command_add(path, args.task_id, args.summary, args.role, args.depends_on)
        elif args.command == "start":
            command_start(path, args.task_id)
        elif args.command == "complete":
            command_complete(path, args.task_id, args.evidence)
        elif args.command == "block":
            command_block(path, args.task_id, args.evidence)
        elif args.command == "show":
            command_show(path, args.json)
        elif args.command == "check":
            command_check(path)
        else:
            raise LedgerError(f"unsupported command: {args.command}")
    except LedgerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
