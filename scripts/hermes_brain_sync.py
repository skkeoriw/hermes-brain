#!/usr/bin/env python3
"""Portable Hermes Brain sync helper.

Copies selected durable Hermes Agent state between a local HERMES_HOME and this
private repository's brain/hermes-home directory.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import signal
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BRAIN_HOME = REPO_ROOT / "brain" / "hermes-home"

EXCLUDE_DIR_NAMES = {
    ".git",
    "logs",
    "log",
    "cache",
    "audio_cache",
    "tmp",
    "temp",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".envs",
    "hermes-agent",
    "checkpoints",
}

EXCLUDE_FILE_SUFFIXES = (
    ".lock",
    ".pid",
    ".log",
    ".pyc",
    "-wal",
    "-shm",
    ".tmp",
    ".temp",
)

EXCLUDE_FILE_NAMES = {
    ".DS_Store",
    ".update_check",
}

SECRET_FILE_NAMES = {
    ".env",
    "auth.json",
    "config.yaml",
    "webhook_subscriptions.json",
    "gateway_state.json",
    "channel_directory.json",
}


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser().resolve()


def rel(path: Path, root: Path) -> Path:
    return path.relative_to(root)


def excluded(path: Path, root: Path) -> bool:
    r = rel(path, root)
    parts = set(r.parts)
    if parts & EXCLUDE_DIR_NAMES:
        return True
    name = path.name
    if name in EXCLUDE_FILE_NAMES:
        return True
    if any(name.endswith(s) for s in EXCLUDE_FILE_SUFFIXES):
        return True
    return False


def tree_signature(root: Path) -> str:
    """Return a content signature for non-excluded files under root."""
    h = hashlib.sha256()
    if not root.exists():
        return "missing"
    for base, dirnames, filenames in os.walk(root):
        basep = Path(base)
        dirnames[:] = [d for d in dirnames if not excluded(basep / d, root)]
        for fn in sorted(filenames):
            p = basep / fn
            if excluded(p, root):
                continue
            rp = str(rel(p, root)).replace(os.sep, "/")
            h.update(rp.encode("utf-8") + b"\0")
            if p.is_symlink():
                h.update(b"SYMLINK\0" + os.readlink(p).encode("utf-8") + b"\0")
            else:
                with p.open("rb") as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(chunk)
                h.update(b"\0")
    return h.hexdigest()


def copy_tree(src: Path, dst: Path, dry_run: bool = False) -> tuple[int, int]:
    files = 0
    dirs = 0
    if not src.exists():
        raise SystemExit(f"source does not exist: {src}")
    if dry_run:
        print(f"DRY RUN: would clear and copy {src} -> {dst}")
    else:
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True, exist_ok=True)

    for root, dirnames, filenames in os.walk(src):
        rootp = Path(root)
        dirnames[:] = [d for d in dirnames if not excluded(rootp / d, src)]
        target_dir = dst / rel(rootp, src)
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
        dirs += 1
        for fn in filenames:
            sp = rootp / fn
            if excluded(sp, src):
                continue
            rp = rel(sp, src)
            dp = dst / rp
            files += 1
            if dry_run:
                print(f"COPY {rp}")
                continue
            dp.parent.mkdir(parents=True, exist_ok=True)
            if sp.is_symlink():
                if dp.exists() or dp.is_symlink():
                    dp.unlink()
                os.symlink(os.readlink(sp), dp)
            else:
                shutil.copy2(sp, dp)
    return files, dirs


def backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup_root = Path.home() / ".hermes-brain-backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = backup_root / f"hermes-home-{stamp}"
    shutil.copytree(path, dest, symlinks=True, ignore=shutil.ignore_patterns("logs", "cache", "audio_cache", "*.lock", "*.pid", "*.log", "*-wal", "*-shm"))
    return dest


def fix_permissions(home: Path) -> None:
    if home.exists():
        home.chmod(0o700)
    for p in home.rglob("*"):
        if p.is_dir():
            try:
                p.chmod(0o700)
            except PermissionError:
                pass
    for name in SECRET_FILE_NAMES:
        p = home / name
        if p.exists() and p.is_file():
            p.chmod(0o600)
    for p in [home / "memories" / "MEMORY.md", home / "memories" / "USER.md"]:
        if p.exists():
            p.chmod(0o600)


def run(cmd: list[str], cwd: Path | None = None, check: bool = False) -> int:
    print("+ " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    if check and proc.returncode:
        raise SystemExit(proc.returncode)
    return proc.returncode


def local_to_repo(args: argparse.Namespace) -> None:
    home = hermes_home()
    files, dirs = copy_tree(home, BRAIN_HOME, dry_run=args.dry_run)
    if not args.dry_run:
        fix_permissions(BRAIN_HOME)
    print(f"synced local -> repo: {files} files, {dirs} dirs")
    if args.git:
        run(["git", "status", "--short"], REPO_ROOT)
        run(["git", "add", "."], REPO_ROOT, check=True)
        msg = args.message or "sync: update Hermes brain"
        if run(["git", "diff", "--cached", "--quiet"], REPO_ROOT) == 0:
            print("no staged changes")
        else:
            run(["git", "commit", "-m", msg], REPO_ROOT, check=True)
        if args.push:
            run(["git", "push", "-u", "origin", "HEAD"], REPO_ROOT, check=True)


def repo_to_local(args: argparse.Namespace) -> None:
    home = hermes_home()
    if args.pull:
        run(["git", "pull", "--ff-only"], REPO_ROOT, check=True)
    if not BRAIN_HOME.exists():
        raise SystemExit(f"repo brain not found: {BRAIN_HOME}")
    if args.skip_if_same:
        src_sig = tree_signature(BRAIN_HOME)
        dst_sig = tree_signature(home) if home.exists() else None
        if src_sig == dst_sig:
            print("repo and local Hermes home already match; skipping restore")
            return
    if args.backup and not args.dry_run:
        b = backup(home)
        if b:
            print(f"backup created: {b}")
    files, dirs = copy_tree(BRAIN_HOME, home, dry_run=args.dry_run)
    if not args.dry_run:
        fix_permissions(home)
    print(f"synced repo -> local: {files} files, {dirs} dirs")


def doctor(_: argparse.Namespace) -> None:
    home = hermes_home()
    print(f"repo={REPO_ROOT}")
    print(f"brain_home={BRAIN_HOME}")
    print(f"HERMES_HOME={home}")
    print(f"brain_exists={BRAIN_HOME.exists()}")
    for cmd in (["git", "--version"], ["python3", "--version"]):
        run(cmd)
    if shutil.which("hermes"):
        run(["hermes", "doctor"])
    else:
        print("hermes command not found; bootstrap can install it")


def main() -> None:
    try:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="Sync Hermes persistent brain data with this repo")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("local-to-repo")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--git", action="store_true", help="git add/commit after copying")
    p.add_argument("--push", action="store_true", help="push after commit; implies --git")
    p.add_argument("-m", "--message")
    p.set_defaults(func=local_to_repo)

    p = sub.add_parser("repo-to-local")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-backup", dest="backup", action="store_false", default=True)
    p.add_argument("--pull", action="store_true")
    p.add_argument("--skip-if-same", action="store_true", help="skip restore/backup when repo brain and local Hermes home already match")
    p.set_defaults(func=repo_to_local)

    p = sub.add_parser("doctor")
    p.set_defaults(func=doctor)

    args = ap.parse_args()
    if getattr(args, "push", False):
        args.git = True
    args.func(args)


if __name__ == "__main__":
    main()
