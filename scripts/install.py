#!/usr/bin/env python3
"""Safely install Claude Bounded Orchestrator into an existing repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
START_MARKER = "<!-- claude-bounded-orchestrator:start -->"
END_MARKER = "<!-- claude-bounded-orchestrator:end -->"
MANIFEST_RELATIVE = Path(".claude/.bounded-orchestrator/install.json")
BACKUP_RELATIVE = Path(".claude/.bounded-orchestrator/backups")
SETTINGS_RELATIVE = Path(".claude/settings.json")
SETTINGS_EXAMPLE_RELATIVE = Path(".claude/bounded-orchestrator.settings.example.json")
MCP_RELATIVE = Path(".mcp.json")
MCP_EXAMPLE_RELATIVE = Path(".claude/bounded-orchestrator.mcp.example.json")
OPENAI_BRIDGE_RELATIVE = Path(".claude/tools/openai_mcp.py")
MCP_SERVER_NAME = "openai-bounded-implementer"
MODEL_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
CLAUDE_EFFORTS = frozenset({"low", "medium", "high", "xhigh", "max"})
CLAUDE_OWNER_EFFORTS = frozenset({"low", "medium", "high", "xhigh"})
OPENAI_EFFORTS = frozenset({"none", "low", "medium", "high", "xhigh", "max"})
ROLES = (
    "owner",
    "explorer",
    "researcher",
    "implementer",
    "verifier",
    "failure-analyst",
    "qa-operator",
    "reviewer",
    "advisor",
)
ROLE_LABELS = {
    "owner": "ana yönetici",
    "explorer": "inceleyici",
    "researcher": "araştırmacı",
    "implementer": "uygulayıcı",
    "verifier": "kontrolcü",
    "failure-analyst": "hata çözümleyici",
    "qa-operator": "kullanım kontrolcüsü",
    "reviewer": "son inceleyici",
    "advisor": "danışman",
}
PRESETS = {
    "balanced": {
        "owner": ("opus", "xhigh"),
        "explorer": ("sonnet", "medium"),
        "researcher": ("sonnet", "medium"),
        "implementer": ("sonnet", "high"),
        "verifier": ("sonnet", "high"),
        "failure-analyst": ("opus", "high"),
        "qa-operator": ("sonnet", "high"),
        "reviewer": ("opus", "high"),
        "advisor": ("opus", "xhigh"),
    },
    "quality": {
        "owner": ("opus", "xhigh"),
        "explorer": ("opus", "high"),
        "researcher": ("opus", "high"),
        "implementer": ("opus", "xhigh"),
        "verifier": ("opus", "xhigh"),
        "failure-analyst": ("opus", "xhigh"),
        "qa-operator": ("opus", "high"),
        "reviewer": ("opus", "xhigh"),
        "advisor": ("opus", "xhigh"),
    },
    "economy": {
        "owner": ("sonnet", "medium"),
        "explorer": ("sonnet", "low"),
        "researcher": ("sonnet", "low"),
        "implementer": ("sonnet", "medium"),
        "verifier": ("sonnet", "medium"),
        "failure-analyst": ("sonnet", "medium"),
        "qa-operator": ("sonnet", "medium"),
        "reviewer": ("sonnet", "medium"),
        "advisor": ("sonnet", "high"),
    },
}
BASE_MANAGED_FILES = (
    Path(".claude/agents/explorer.md"),
    Path(".claude/agents/researcher.md"),
    Path(".claude/agents/implementer.md"),
    Path(".claude/agents/verifier.md"),
    Path(".claude/agents/failure-analyst.md"),
    Path(".claude/agents/qa-operator.md"),
    Path(".claude/agents/reviewer.md"),
    Path(".claude/agents/advisor.md"),
    Path(".claude/skills/ui-design/SKILL.md"),
    Path(".claude/skills/secure-change/SKILL.md"),
    Path(".claude/tools/task_ledger.py"),
    Path(".claude/.bounded-orchestrator/.gitignore"),
)
OPTIONAL_MANAGED_FILES = (OPENAI_BRIDGE_RELATIVE, MCP_EXAMPLE_RELATIVE)
RUNTIME_IGNORE_RELATIVE = Path(".claude/.bounded-orchestrator/.gitignore")
ALLOWED_UNINSTALL_FILES = frozenset(
    path.as_posix()
    for path in (*BASE_MANAGED_FILES, *OPTIONAL_MANAGED_FILES, SETTINGS_RELATIVE, SETTINGS_EXAMPLE_RELATIVE)
)


class InstallError(RuntimeError):
    """Expected installer failure."""


def configure_stdio() -> None:
    """Keep prompts usable when a terminal cannot encode Turkish characters."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(errors="replace")


def source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def version(root: Path) -> str:
    try:
        return (root / "VERSION").read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise InstallError("VERSION is missing") from exc


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def same_file(left: Path, right: Path) -> bool:
    return left.is_file() and right.is_file() and digest(left) == digest(right)


def same_text(path: Path, content: str) -> bool:
    try:
        return path.is_file() and path.read_text(encoding="utf-8") == content
    except (OSError, UnicodeDecodeError):
        return False


def atomic_copy(source: Path, destination: Path, dry_run: bool) -> None:
    if dry_run:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_text(destination: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_manifest(target: Path) -> dict[str, Any]:
    path = target / MANIFEST_RELATIVE
    if not path.exists():
        return {"schema": SCHEMA_VERSION, "files": {}, "claude_block": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallError(f"cannot read install manifest: {path}") from exc
    if data.get("schema") != SCHEMA_VERSION or not isinstance(data.get("files"), dict):
        raise InstallError(f"unsupported install manifest: {path}")
    return data


def remember(manifest: dict[str, Any], relative: Path, destination: Path, owned: bool) -> None:
    manifest.setdefault("files", {})[relative.as_posix()] = {"sha256": digest(destination), "owned": owned}


def backup(target: Path, destination: Path, dry_run: bool) -> Path:
    relative = destination.relative_to(target)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = target / BACKUP_RELATIVE / stamp / relative
    index = 1
    while candidate.exists():
        candidate = candidate.with_name(f"{destination.name}.{index}")
        index += 1
    if not dry_run:
        candidate.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destination, candidate)
    return candidate


def ensure_sources(root: Path) -> None:
    required = [root / item for item in (*BASE_MANAGED_FILES, OPENAI_BRIDGE_RELATIVE)]
    required += [root / SETTINGS_RELATIVE, root / "templates/CLAUDE.block.md", root / "VERSION"]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise InstallError("installer source is incomplete:\n  - " + "\n  - ".join(missing))


def install_one(root: Path, target: Path, relative: Path, manifest: dict[str, Any], force: bool, dry_run: bool, output: list[str], content: str | None = None) -> None:
    source = root / relative
    destination = target / relative
    previous = manifest.get("files", {}).get(relative.as_posix(), {})
    if destination.exists() and destination.is_dir():
        output.append(f"SKIP {relative}: destination is a directory")
    elif not destination.exists():
        output.append(f"INSTALL {relative}")
        if content is None:
            atomic_copy(source, destination, dry_run)
        else:
            atomic_text(destination, content, dry_run)
        if not dry_run:
            remember(manifest, relative, destination, True)
    elif (same_text(destination, content) if content is not None else same_file(source, destination)):
        output.append(f"UNCHANGED {relative}")
        if not dry_run:
            remember(manifest, relative, destination, bool(previous.get("owned")))
    elif not force:
        output.append(f"SKIP {relative}: existing file differs; use --force to replace")
    else:
        saved = backup(target, destination, dry_run)
        output.append(f"BACKUP {relative} -> {saved.relative_to(target)}")
        output.append(f"REPLACE {relative}")
        if content is None:
            atomic_copy(source, destination, dry_run)
        else:
            atomic_text(destination, content, dry_run)
        if not dry_run:
            remember(manifest, relative, destination, True)


def install_settings(root: Path, target: Path, manifest: dict[str, Any], force_settings: bool, dry_run: bool, output: list[str], content: str) -> None:
    destination = target / SETTINGS_RELATIVE
    if not destination.exists():
        output.append(f"INSTALL {SETTINGS_RELATIVE}")
        atomic_text(destination, content, dry_run)
        if not dry_run:
            remember(manifest, SETTINGS_RELATIVE, destination, True)
        return
    if same_text(destination, content):
        previous = manifest.get("files", {}).get(SETTINGS_RELATIVE.as_posix(), {})
        output.append(f"UNCHANGED {SETTINGS_RELATIVE}")
        if not dry_run:
            remember(manifest, SETTINGS_RELATIVE, destination, bool(previous.get("owned")))
        return
    if force_settings:
        saved = backup(target, destination, dry_run)
        output.append(f"BACKUP {SETTINGS_RELATIVE} -> {saved.relative_to(target)}")
        output.append(f"REPLACE {SETTINGS_RELATIVE}")
        atomic_text(destination, content, dry_run)
        if not dry_run:
            remember(manifest, SETTINGS_RELATIVE, destination, True)
        return
    output.append(f"PRESERVE {SETTINGS_RELATIVE}")
    output.append(f"INSTALL {SETTINGS_EXAMPLE_RELATIVE} (merge manually)")
    example = target / SETTINGS_EXAMPLE_RELATIVE
    if example.exists() and not same_text(example, content) and not dry_run:
        output.append(f"SKIP {SETTINGS_EXAMPLE_RELATIVE}: existing example differs")
        return
    atomic_text(example, content, dry_run)
    if not dry_run:
        remember(manifest, SETTINGS_EXAMPLE_RELATIVE, example, True)


def validate_model_token(value: str, option: str) -> str:
    if not MODEL_TOKEN.fullmatch(value):
        raise InstallError(
            f"invalid model for {option}: use 1-128 letters, digits, dots, underscores, or hyphens"
        )
    return value


def validate_effort(value: str, option: str, allowed: frozenset[str]) -> str:
    if value not in allowed:
        raise InstallError(f"invalid effort for {option}: choose {', '.join(sorted(allowed))}")
    return value


def parse_override(values: list[str], option: str, *, effort: bool = False) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise InstallError(f"{option} must use ROLE=VALUE: {value}")
        role, selected = (part.strip() for part in value.split("=", 1))
        if role not in ROLES:
            raise InstallError(f"unknown role for {option}: {role}")
        if effort:
            allowed = CLAUDE_OWNER_EFFORTS if role == "owner" else CLAUDE_EFFORTS
            result[role] = validate_effort(selected, option, allowed)
        else:
            result[role] = validate_model_token(selected, option)
    return result


def prompt_choice(prompt: str, choices: list[tuple[str, str]], default: str) -> str:
    print(prompt)
    for index, (value, label) in enumerate(choices, 1):
        suffix = " (önerilen)" if value == default else ""
        print(f"  {index}. {label}{suffix}")
    raw = input(f"Seçiminiz [{next(i for i, item in enumerate(choices, 1) if item[0] == default)}]: ").strip()
    if not raw:
        return default
    if raw.isdigit() and 1 <= int(raw) <= len(choices):
        return choices[int(raw) - 1][0]
    for value, _ in choices:
        if raw == value:
            return value
    raise InstallError(f"geçersiz seçim: {raw}")


def interactive_options(args: argparse.Namespace) -> None:
    print("\nClaude Bounded Orchestrator kurulum ayarları")
    args.preset = prompt_choice(
        "Hazır profil seçin:",
        [
            ("balanced", "Dengeli"),
            ("quality", "Yüksek kalite"),
            ("economy", "Ekonomik"),
            ("custom", "Özel - rolleri tek tek seç"),
        ],
        args.preset,
    )
    if args.preset == "custom":
        base = PRESETS["balanced"]
        for role in ROLES:
            default_model, default_effort = base[role]
            label = ROLE_LABELS[role]
            model = input(f"{label} ({role}) modeli [{default_model}]: ").strip() or default_model
            effort = input(f"{label} ({role}) düşünme düzeyi [{default_effort}]: ").strip() or default_effort
            args.role_model.append(f"{role}={model}")
            args.role_effort.append(f"{role}={effort}")
    external = prompt_choice(
        "OpenAI GPT dış uygulama önericisi eklensin mi?",
        [("no", "Hayır"), ("yes", "Evet")],
        "yes" if args.external_openai else "no",
    )
    args.external_openai = external == "yes"
    if args.external_openai:
        args.external_model = input(f"OpenAI modeli [{args.external_model}]: ").strip() or args.external_model
        args.external_effort = input(f"OpenAI düşünme düzeyi [{args.external_effort}]: ").strip() or args.external_effort
        if not os.environ.get("OPENAI_API_KEY"):
            print("Bilgi: OPENAI_API_KEY şu anda ayarlı değil; anahtar dosyaya kaydedilmeyecek.")


def routing_for(args: argparse.Namespace) -> dict[str, tuple[str, str]]:
    preset = "balanced" if args.preset == "custom" else args.preset
    routing = dict(PRESETS[preset])
    models = parse_override(args.role_model, "--role-model")
    efforts = parse_override(args.role_effort, "--role-effort", effort=True)
    for role in ROLES:
        model, effort = routing[role]
        routing[role] = (models.get(role, model), efforts.get(role, effort))
    return routing


def render_agent(source: Path, model: str, effort: str) -> str:
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("model:"):
            lines[index] = f"model: {model}\n"
        elif line.startswith("effort:"):
            lines[index] = f"effort: {effort}\n"
    return "".join(lines)


def settings_content(routing: dict[str, tuple[str, str]]) -> str:
    model, effort = routing["owner"]
    validate_effort(effort, "owner settings", CLAUDE_OWNER_EFFORTS)
    return json.dumps(
        {
            "model": model,
            "effortLevel": effort,
            "env": {"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1"},
        },
        indent=2,
    ) + "\n"


def mcp_server(target: Path, model: str, effort: str) -> dict[str, Any]:
    return {
        "type": "stdio",
        "command": sys.executable,
        "args": [str(target / OPENAI_BRIDGE_RELATIVE)],
        "env": {"OPENAI_MODEL": model, "OPENAI_REASONING_EFFORT": effort},
    }


def write_mcp_example(target: Path, manifest: dict[str, Any], desired: dict[str, Any], dry_run: bool, output: list[str]) -> None:
    content = json.dumps({"mcpServers": {MCP_SERVER_NAME: desired}}, indent=2) + "\n"
    path = target / MCP_EXAMPLE_RELATIVE
    if path.is_symlink():
        output.append(f"SKIP {MCP_EXAMPLE_RELATIVE}: destination is a symlink")
        return
    if path.exists() and not same_text(path, content):
        output.append(f"SKIP {MCP_EXAMPLE_RELATIVE}: existing example differs")
        return
    output.append(f"INSTALL {MCP_EXAMPLE_RELATIVE} (merge manually)")
    atomic_text(path, content, dry_run)
    if not dry_run:
        remember(manifest, MCP_EXAMPLE_RELATIVE, path, True)


def install_mcp(target: Path, manifest: dict[str, Any], model: str, effort: str, dry_run: bool, output: list[str]) -> bool:
    desired = mcp_server(target, model, effort)
    path = target / MCP_RELATIVE
    if path.is_symlink():
        output.append(f"PRESERVE {MCP_RELATIVE}: destination is a symlink")
        write_mcp_example(target, manifest, desired, dry_run, output)
        return False
    if not path.exists():
        output.append(f"INSTALL {MCP_RELATIVE}")
        atomic_text(path, json.dumps({"mcpServers": {MCP_SERVER_NAME: desired}}, indent=2) + "\n", dry_run)
        if not dry_run:
            manifest["mcp_entry"] = {"owned_file": True, "server": desired}
        return True
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON root must be an object")
        servers = data.get("mcpServers")
        if not isinstance(servers, dict):
            raise ValueError("mcpServers must be an object")
    except (OSError, json.JSONDecodeError, ValueError):
        output.append(f"PRESERVE {MCP_RELATIVE}: invalid or unsupported structure")
        write_mcp_example(target, manifest, desired, dry_run, output)
        return False
    existing = servers.get(MCP_SERVER_NAME)
    if existing is not None and existing != desired:
        output.append(f"PRESERVE {MCP_RELATIVE}: {MCP_SERVER_NAME} already differs")
        write_mcp_example(target, manifest, desired, dry_run, output)
        return False
    if existing == desired:
        output.append(f"UNCHANGED {MCP_RELATIVE} entry")
        return True
    output.append(f"UPDATE {MCP_RELATIVE}: add {MCP_SERVER_NAME}")
    data["mcpServers"][MCP_SERVER_NAME] = desired
    atomic_text(path, json.dumps(data, indent=2) + "\n", dry_run)
    if not dry_run:
        manifest["mcp_entry"] = {"owned_file": False, "server": desired}
    return True


def disable_mcp(target: Path, manifest: dict[str, Any], dry_run: bool, output: list[str]) -> tuple[bool, bool]:
    entry = manifest.get("mcp_entry")
    path = safe_uninstall_path(target, MCP_RELATIVE)
    if not isinstance(entry, dict):
        if not path.exists():
            return True, False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return True, False
        servers = data.get("mcpServers") if isinstance(data, dict) else None
        if isinstance(servers, dict) and MCP_SERVER_NAME in servers:
            output.append(f"KEEP {MCP_RELATIVE}: {MCP_SERVER_NAME} is not installer-owned")
            return True, True
        return True, False
    if not path.exists():
        if not dry_run:
            manifest.pop("mcp_entry", None)
        return True, False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        output.append(f"KEEP {MCP_RELATIVE}: modified after installation; OpenAI remains configured")
        return False, True
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    if not isinstance(servers, dict) or servers.get(MCP_SERVER_NAME) != entry.get("server"):
        output.append(f"KEEP {MCP_RELATIVE}: {MCP_SERVER_NAME} changed after installation; OpenAI remains configured")
        return False, True
    output.append(
        f"REMOVE {MCP_RELATIVE}"
        if entry.get("owned_file") and len(servers) == 1 and set(data) == {"mcpServers"}
        else f"UPDATE {MCP_RELATIVE}: remove {MCP_SERVER_NAME}"
    )
    if not dry_run:
        del servers[MCP_SERVER_NAME]
        if entry.get("owned_file") and not servers and set(data) == {"mcpServers"}:
            path.unlink()
        else:
            atomic_text(path, json.dumps(data, indent=2) + "\n", False)
        manifest.pop("mcp_entry", None)
    return True, False


def remove_optional_file(target: Path, manifest: dict[str, Any], relative: Path, dry_run: bool, output: list[str]) -> None:
    entry = manifest.get("files", {}).get(relative.as_posix())
    if not isinstance(entry, dict) or not entry.get("owned"):
        return
    path = safe_uninstall_path(target, relative)
    if not path.exists():
        if not dry_run:
            manifest["files"].pop(relative.as_posix(), None)
        return
    if not path.is_file() or digest(path) != entry.get("sha256"):
        output.append(f"KEEP {relative}: modified after installation")
        return
    output.append(f"REMOVE {relative}")
    if not dry_run:
        path.unlink()
        manifest["files"].pop(relative.as_posix(), None)


def disable_external_openai(target: Path, manifest: dict[str, Any], dry_run: bool, output: list[str]) -> bool:
    disabled, preserve_bridge = disable_mcp(target, manifest, dry_run, output)
    if not disabled:
        return False
    if preserve_bridge:
        output.append(f"KEEP {OPENAI_BRIDGE_RELATIVE}: an unowned MCP entry may still use it")
    else:
        remove_optional_file(target, manifest, OPENAI_BRIDGE_RELATIVE, dry_run, output)
    remove_optional_file(target, manifest, MCP_EXAMPLE_RELATIVE, dry_run, output)
    return True


def uninstall_mcp(target: Path, manifest: dict[str, Any], dry_run: bool, output: list[str]) -> None:
    entry = manifest.get("mcp_entry")
    if not isinstance(entry, dict):
        return
    path = safe_uninstall_path(target, MCP_RELATIVE)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        output.append(f"KEEP {MCP_RELATIVE}: modified after installation")
        return
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    if not isinstance(servers, dict) or servers.get(MCP_SERVER_NAME) != entry.get("server"):
        output.append(f"KEEP {MCP_RELATIVE}: modified after installation")
        return
    output.append(f"REMOVE {MCP_RELATIVE}" if entry.get("owned_file") and len(servers) == 1 else f"UPDATE {MCP_RELATIVE}: remove {MCP_SERVER_NAME}")
    if dry_run:
        return
    del servers[MCP_SERVER_NAME]
    if entry.get("owned_file") and not servers and set(data) == {"mcpServers"}:
        path.unlink()
    else:
        atomic_text(path, json.dumps(data, indent=2) + "\n", False)


def remove_managed_block(text: str) -> tuple[str, bool]:
    start = text.find(START_MARKER)
    end = text.find(END_MARKER)
    if start < 0 or end < 0 or end < start:
        return text, False
    end += len(END_MARKER)
    before = text[:start].rstrip()
    after = text[end:].lstrip("\n")
    if before and after:
        result = before + "\n\n" + after
    elif before:
        result = before + "\n"
    else:
        result = after
    return result, True


def install_claude_block(root: Path, target: Path, manifest: dict[str, Any], dry_run: bool, output: list[str]) -> None:
    destination = target / "CLAUDE.md"
    block = (root / "templates/CLAUDE.block.md").read_text(encoding="utf-8").strip()
    existing = destination.read_text(encoding="utf-8") if destination.exists() else ""
    cleaned, had_block = remove_managed_block(existing)
    content = (cleaned.rstrip() + "\n\n" + block + "\n").lstrip("\n")
    if existing == content:
        output.append("UNCHANGED CLAUDE.md block")
    else:
        output.append("UPDATE CLAUDE.md block" if had_block else "INSTALL CLAUDE.md block")
        atomic_text(destination, content, dry_run)
    if not dry_run:
        manifest["claude_block"] = True


def save_manifest(target: Path, manifest: dict[str, Any], root: Path, dry_run: bool) -> None:
    if dry_run:
        return
    manifest.update({"schema": SCHEMA_VERSION, "tool_version": version(root), "installed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()})
    atomic_text(target / MANIFEST_RELATIVE, json.dumps(manifest, indent=2, sort_keys=True) + "\n", False)


def safe_uninstall_path(target: Path, relative: Path) -> Path:
    """Return a contained non-symlink path or reject the uninstall."""
    if relative.is_absolute() or ".." in relative.parts:
        raise InstallError(f"unsafe uninstall path: {relative}")
    current = target
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise InstallError(f"refusing uninstall through symlinked directory: {current}")
    candidate = target / relative
    if candidate.is_symlink():
        raise InstallError(f"refusing to uninstall symlink: {candidate}")
    try:
        candidate.resolve(strict=False).relative_to(target)
    except ValueError as exc:
        raise InstallError(f"uninstall path escapes target: {relative}") from exc
    return candidate


def uninstall(target: Path, manifest: dict[str, Any], dry_run: bool, output: list[str]) -> None:
    entries = manifest.get("files", {})
    safe_paths: dict[str, Path] = {}
    for name, entry in entries.items():
        if not isinstance(name, str) or name not in ALLOWED_UNINSTALL_FILES:
            raise InstallError(f"manifest contains unmanaged uninstall path: {name!r}")
        if not isinstance(entry, dict):
            raise InstallError(f"manifest contains invalid entry for: {name}")
        safe_paths[name] = safe_uninstall_path(target, Path(name))
    manifest_path = safe_uninstall_path(target, MANIFEST_RELATIVE)
    claude = safe_uninstall_path(target, Path("CLAUDE.md"))

    uninstall_mcp(target, manifest, dry_run, output)

    for name, entry in sorted(entries.items(), reverse=True):
        path = safe_paths[name]
        if not entry.get("owned") or not path.exists():
            continue
        if Path(name) == RUNTIME_IGNORE_RELATIVE:
            output.append(f"KEEP {name}: protects retained private runtime data")
            continue
        if not path.is_file() or digest(path) != entry.get("sha256"):
            output.append(f"KEEP {name}: modified after installation")
            continue
        output.append(f"REMOVE {name}")
        if not dry_run:
            path.unlink()
    if manifest.get("claude_block") and claude.is_file():
        current = claude.read_text(encoding="utf-8")
        cleaned, removed = remove_managed_block(current)
        if removed:
            output.append("REMOVE CLAUDE.md block")
            if not dry_run:
                if cleaned:
                    atomic_text(claude, cleaned, False)
                else:
                    claude.unlink()
    output.append(f"REMOVE {MANIFEST_RELATIVE}")
    if not dry_run and manifest_path.exists():
        manifest_path.unlink()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="existing project directory")
    parser.add_argument("--dry-run", action="store_true", help="preview without writing")
    parser.add_argument("--force", action="store_true", help="replace conflicting managed files after backup")
    parser.add_argument("--force-settings", action="store_true", help="replace .claude/settings.json after backup")
    parser.add_argument("--uninstall", action="store_true", help="remove unchanged files installed by this tool")
    parser.add_argument("--interactive", action="store_true", help="show Turkish profile and provider choices")
    parser.add_argument(
        "--preset",
        choices=("balanced", "quality", "economy", "custom"),
        default="balanced",
        help="prepared model/effort profile (default: balanced)",
    )
    parser.add_argument("--role-model", action="append", default=[], metavar="ROLE=MODEL", help="override one role model; repeatable")
    parser.add_argument("--role-effort", action="append", default=[], metavar="ROLE=EFFORT", help="override one role effort; repeatable")
    external = parser.add_mutually_exclusive_group()
    external.add_argument("--external-openai", dest="external_openai", action="store_true", help="configure the proposal-only OpenAI MCP role")
    external.add_argument("--no-external-openai", dest="external_openai", action="store_false", help="remove an unchanged installer-owned OpenAI MCP role")
    parser.set_defaults(external_openai=None)
    parser.add_argument("--external-model", default="gpt-5.6-sol", help="OpenAI Responses API model")
    parser.add_argument("--external-effort", default="high", help="OpenAI reasoning effort")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    args = parse_args(argv)
    root = source_root()
    try:
        if args.interactive and not args.uninstall:
            interactive_options(args)
        target = args.target.expanduser().resolve()
        if not target.is_dir():
            raise InstallError(f"target must be an existing directory: {target}")
        if target == root:
            raise InstallError("target must differ from the installer repository")
        ensure_sources(root)
        manifest = load_manifest(target)
        output: list[str] = []
        if args.uninstall:
            if not (target / MANIFEST_RELATIVE).exists():
                raise InstallError("no installation manifest found")
            uninstall(target, manifest, args.dry_run, output)
        else:
            routing = routing_for(args)
            if args.external_openai is True:
                validate_model_token(args.external_model, "--external-model")
                validate_effort(args.external_effort, "--external-effort", OPENAI_EFFORTS)
            for relative in BASE_MANAGED_FILES:
                content = None
                if relative.parent == Path(".claude/agents"):
                    model, effort = routing[relative.stem]
                    content = render_agent(root / relative, model, effort)
                install_one(root, target, relative, manifest, args.force, args.dry_run, output, content)
            install_settings(
                root,
                target,
                manifest,
                args.force_settings,
                args.dry_run,
                output,
                settings_content(routing),
            )
            external_effective = bool(manifest.get("external_openai", False))
            if args.external_openai is True:
                install_one(root, target, OPENAI_BRIDGE_RELATIVE, manifest, args.force, args.dry_run, output)
                external_effective = install_mcp(
                    target, manifest, args.external_model, args.external_effort, args.dry_run, output
                )
            elif args.external_openai is False:
                external_effective = not disable_external_openai(target, manifest, args.dry_run, output)
            install_claude_block(root, target, manifest, args.dry_run, output)
            if not args.dry_run:
                manifest["preset"] = args.preset
                manifest["routing"] = {role: {"model": model, "effort": effort} for role, (model, effort) in routing.items()}
                manifest["external_openai"] = external_effective
            save_manifest(target, manifest, root, args.dry_run)
        print("\n".join(output))
        return 0
    except InstallError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
