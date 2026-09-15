"""Storage layer: one JSON file per project in ~/.proj/<name>.json.

The JSON files are the source of truth — AI agents read them directly.
All writes are atomic (temp file + os.replace).
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date
from pathlib import Path

DIR = Path(os.environ.get("CAPY_DIR", Path.home() / ".proj"))

DEFAULT_STEPS = ["MVP", "v0", "v1"]
STATUSES = ("todo", "in progress", "paused", "done", "abandoned")
TASK_TYPES = ("feat", "bug", "chore")


class ProjError(Exception):
    """User-facing error; the CLI prints it and exits non-zero."""


def path(name: str) -> Path:
    return DIR / f"{name}.json"


def all_names() -> list[str]:
    if not DIR.is_dir():
        return []
    return sorted(
        p.stem for p in DIR.glob("*.json") if not p.name.startswith(".")
    )


def resolve(name: str) -> str:
    """Exact name or unique prefix."""
    names = all_names()
    if name in names:
        return name
    matches = [n for n in names if n.startswith(name)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ProjError(f"ambiguous '{name}': {', '.join(matches)}")
    have = ", ".join(names) or "none"
    raise ProjError(f"unknown project '{name}' (have: {have})")


def load(name: str) -> dict:
    p = path(name)
    if not p.exists():
        raise ProjError(f"unknown project '{name}' (see: capy)")
    with p.open() as f:
        return json.load(f)


def save(name: str, data: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=DIR)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path(name))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def new_project(name: str, steps: list[str]) -> dict:
    if path(name).exists():
        raise ProjError(f"project '{name}' already exists")
    data = {
        "date": date.today().isoformat(),
        "status": "todo",
        "steps": steps,
        "pointer": 0,
        "tasks": [],
    }
    save(name, data)
    return data


def next_step(name: str) -> tuple[str, str]:
    """Advance the pointer. Returns (just_finished, current_or_done)."""
    p = load(name)
    steps = p["steps"]
    if p["pointer"] >= len(steps):
        raise ProjError(f"'{name}' already at the end ({steps[-1]})")
    p["pointer"] += 1
    save(name, p)
    done = steps[p["pointer"] - 1]
    cur = steps[p["pointer"]] if p["pointer"] < len(steps) else "done"
    return done, cur


def set_status(name: str, status: str) -> None:
    if status not in STATUSES:
        raise ProjError(f"status must be one of: {', '.join(STATUSES)}")
    p = load(name)
    p["status"] = status
    save(name, p)


def add_task(name: str, typ: str, title: str) -> dict:
    if typ not in TASK_TYPES:
        raise ProjError(f"type must be one of: {', '.join(TASK_TYPES)}")
    p = load(name)
    p["tasks"] = p.get("tasks", [])
    tid = max((t["id"] for t in p["tasks"]), default=0) + 1
    task = {
        "id": tid,
        "type": typ,
        "title": title,
        "status": "open",
        "created": date.today().isoformat(),
    }
    p["tasks"].append(task)
    save(name, p)
    return task


def done_task(name: str, tid: int) -> dict:
    p = load(name)
    for t in p.get("tasks", []):
        if t["id"] == tid:
            t["status"] = "done"
            save(name, p)
            return t
    raise ProjError(f"no task #{tid} in '{name}'")


def open_tasks(p: dict) -> list[dict]:
    return [t for t in p.get("tasks", []) if t["status"] == "open"]


def infer_name() -> str:
    """Infer the project from the current directory.

    Uses the git toplevel name (or the cwd name as fallback), then
    resolves it as usual (exact or unique prefix).
    """
    import subprocess

    base = None
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=2,
        )
        if out.returncode == 0:
            base = Path(out.stdout.strip()).name
    except (OSError, subprocess.SubprocessError):
        pass
    if base is None:
        base = Path.cwd().name
    return resolve(base)