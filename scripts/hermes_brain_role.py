#!/usr/bin/env python3
"""Local role and global owner helper for hermes-brain auto sync.

Local machine role is intentionally stored outside the synced brain data:
  ~/.config/hermes-brain/sync-role
  ~/.config/hermes-brain/machine-id

The repository stores only the global push owner declaration:
  brain/sync-owner.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OWNER_FILE = REPO_ROOT / "brain" / "sync-owner.json"
CONFIG_DIR = Path(os.environ.get("HERMES_BRAIN_CONFIG_DIR", Path.home() / ".config" / "hermes-brain")).expanduser()
ROLE_FILE = CONFIG_DIR / "sync-role"
MACHINE_ID_FILE = CONFIG_DIR / "machine-id"
VALID_ROLES = {"push", "pull"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def hostname() -> str:
    return socket.gethostname()


def read_os_machine_id() -> str:
    for p in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
        try:
            value = p.read_text(encoding="utf-8").strip()
            if value:
                return value
        except OSError:
            pass
    return ""


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        CONFIG_DIR.chmod(0o700)
    except PermissionError:
        pass


def ensure_machine_id() -> str:
    ensure_config_dir()
    if MACHINE_ID_FILE.exists():
        mid = MACHINE_ID_FILE.read_text(encoding="utf-8").strip()
        if mid:
            return mid
    raw = f"{hostname()}:{read_os_machine_id()}:{Path.home()}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    mid = f"{hostname()}-{digest}"
    MACHINE_ID_FILE.write_text(mid + "\n", encoding="utf-8")
    try:
        MACHINE_ID_FILE.chmod(0o600)
    except PermissionError:
        pass
    return mid


def read_role(default: str = "pull") -> str:
    if ROLE_FILE.exists():
        role = ROLE_FILE.read_text(encoding="utf-8").strip().lower()
        if role in VALID_ROLES:
            return role
    return default


def write_role(role: str) -> None:
    if role not in VALID_ROLES:
        raise SystemExit(f"invalid role: {role}; expected push or pull")
    ensure_config_dir()
    ROLE_FILE.write_text(role + "\n", encoding="utf-8")
    try:
        ROLE_FILE.chmod(0o600)
    except PermissionError:
        pass


def read_owner() -> dict:
    if not OWNER_FILE.exists():
        return {}
    try:
        data = json.loads(OWNER_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {}


def write_owner(machine_id: str | None = None, host: str | None = None, reason: str | None = None) -> dict:
    OWNER_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "push_machine_id": machine_id,
        "push_hostname": host,
        "updated_at": utc_now(),
        "updated_by_machine_id": ensure_machine_id(),
        "updated_by_hostname": hostname(),
        "notes": "Only this machine should run hermes-brain auto sync in push mode. All other machines auto-downgrade to pull.",
    }
    if reason:
        data["reason"] = reason
    OWNER_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return data


def run_git(args: list[str], check: bool = True) -> int:
    print("+ git " + " ".join(args))
    proc = subprocess.run(["git", *args], cwd=str(REPO_ROOT))
    if check and proc.returncode:
        raise SystemExit(proc.returncode)
    return proc.returncode


def maybe_commit_push(message: str, push: bool) -> None:
    run_git(["add", "brain/sync-owner.json"], check=True)
    if run_git(["diff", "--cached", "--quiet"], check=False) == 0:
        print("no owner changes to commit")
    else:
        run_git(["commit", "-m", message], check=True)
    if push:
        run_git(["push", "-u", "origin", "HEAD"], check=True)


def cmd_status(_: argparse.Namespace) -> None:
    mid = ensure_machine_id()
    role = read_role()
    owner = read_owner()
    is_owner = bool(owner.get("push_machine_id") and owner.get("push_machine_id") == mid)
    effective_role = "push" if role == "push" and is_owner else "pull"
    print(f"repo={REPO_ROOT}")
    print(f"local_config_dir={CONFIG_DIR}")
    print(f"local_role={role}")
    print(f"machine_id={mid}")
    print(f"hostname={hostname()}")
    print(f"owner_file={OWNER_FILE}")
    print(f"owner_machine_id={owner.get('push_machine_id') or ''}")
    print(f"owner_hostname={owner.get('push_hostname') or ''}")
    print(f"effective_role={effective_role}")


def cmd_set(args: argparse.Namespace) -> None:
    role = args.role
    mid = ensure_machine_id()
    write_role(role)
    print(f"local role set to {role}: {ROLE_FILE}")
    if role == "push":
        # Pull latest owner before replacing it when possible.
        if args.pull_first:
            run_git(["pull", "--ff-only"], check=False)
        write_owner(mid, hostname(), reason=args.reason or "set current machine as push owner")
        print(f"global push owner set to this machine: {OWNER_FILE}")
        if args.git or args.push:
            maybe_commit_push(f"chore: set Hermes brain push owner to {hostname()}", push=args.push)
    else:
        print("global push owner was not changed; this machine will only pull")


def cmd_downgrade_if_needed(args: argparse.Namespace) -> None:
    mid = ensure_machine_id()
    role = read_role()
    owner = read_owner()
    owner_mid = owner.get("push_machine_id")
    if role == "push" and owner_mid and owner_mid != mid:
        write_role("pull")
        print(f"downgraded local role to pull because owner is {owner.get('push_hostname') or owner_mid}")
        if args.exit_code:
            raise SystemExit(10)
    else:
        print("no downgrade needed")


def main() -> None:
    ap = argparse.ArgumentParser(description="Manage hermes-brain local sync role and global push owner")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("status")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("set")
    p.add_argument("role", choices=sorted(VALID_ROLES))
    p.add_argument("--git", action="store_true", help="commit owner change when setting push")
    p.add_argument("--push", action="store_true", help="commit and push owner change when setting push")
    p.add_argument("--no-pull-first", dest="pull_first", action="store_false", default=True)
    p.add_argument("--reason")
    p.set_defaults(func=cmd_set)

    p = sub.add_parser("downgrade-if-needed")
    p.add_argument("--exit-code", action="store_true", help="exit 10 when downgraded")
    p.set_defaults(func=cmd_downgrade_if_needed)

    args = ap.parse_args()
    if getattr(args, "push", False):
        args.git = True
    args.func(args)


if __name__ == "__main__":
    main()
