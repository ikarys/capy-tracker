"""Command-line interface for capy-tracker (stage 1)."""
from __future__ import annotations

import argparse
import sys

from . import store
from .store import ProjError

BAR_WIDTH = 10
ARROW = "\u2192"
CHECK = "\u2713"
TRI = "\u25b8"


def bar(done: int, total: int) -> str:
    if total == 0:
        return "[" + " " * BAR_WIDTH + "]"
    filled = round(done / total * BAR_WIDTH)
    return "[" + "#" * filled + " " * (BAR_WIDTH - filled) + "]"


def line(name: str, p: dict) -> str:
    steps = p["steps"]
    ptr = p.get("pointer", 0)
    cur = steps[ptr] if ptr < len(steps) else "done"
    n_open = len(store.open_tasks(p))
    open_part = f"  {n_open} open" if n_open else ""
    return (
        f"{name:<12} {p.get('status', '?'):<12} "
        f"{bar(ptr, len(steps))}  {ptr}/{len(steps)}  {ARROW} {cur}{open_part}"
    )


# ---------- command handlers ----------

def cmd_new(args) -> int:
    steps = args.steps or store.DEFAULT_STEPS
    store.new_project(args.name, steps)
    print(f"created '{args.name}' (steps: {ARROW.join(steps)})")
    return 0


def cmd_status(args) -> int:
    name = store.resolve(args.name)
    store.set_status(name, args.status)
    print(f"'{name}' status: {args.status}")
    return 0


def cmd_next(args) -> int:
    name = store.resolve(args.name)
    done, cur = store.next_step(name)
    print(f"'{name}': {CHECK} {done}  {ARROW}  {cur}")
    return 0


def cmd_add(args) -> int:
    tokens = args.tokens
    typ = None
    rest = []
    for tok in tokens:
        if typ is None and tok in store.TASK_TYPES:
            typ = tok
        else:
            rest.append(tok)
    if typ is None:
        raise ProjError("missing type (feat|bug|chore)")
    name = None
    if rest:
        try:
            name = store.resolve(rest[0])
            rest = rest[1:]
        except ProjError:
            pass
    if name is None:
        name = store.infer_name()
    title = " ".join(rest)
    if not title:
        raise ProjError("missing title")
    task = store.add_task(name, typ, title)
    print(f"[{name}] #{task['id']} {task['type']}: {task['title']}")
    return 0


def cmd_done(args) -> int:
    name = store.resolve(args.name)
    task = store.done_task(name, args.id)
    print(f"[{name}] #{task['id']} done: {task['title']}")
    return 0


def cmd_tasks(args) -> int:
    names = [store.resolve(args.name)] if args.name else store.all_names()
    printed = False
    for name in names:
        opens = store.open_tasks(store.load(name))
        if not opens:
            continue
        printed = True
        print(f"{name} ({len(opens)} open)")
        for t in opens:
            print(f"  #{t['id']:<3} {t['type']:<5} {t['title']}")
        print()
    if not printed:
        print("no open tasks")
    return 0


def cmd_show(args) -> int:
    name = store.resolve(args.name)
    p = store.load(name)
    steps = p["steps"]
    ptr = p.get("pointer", 0)
    print(f"{name}  ({p.get('date', '?')})  [{p.get('status', '?')}]")
    for i, s in enumerate(steps):
        mark = CHECK if i < ptr else (TRI if i == ptr else " ")
        print(f"  {mark} {s}")
    opens = store.open_tasks(p)
    if opens:
        print(f"  open tasks ({len(opens)}):")
        for t in opens:
            print(f"    #{t['id']:<3} {t['type']:<5} {t['title']}")
    return 0


def cmd_list(_args) -> int:
    names = store.all_names()
    if not names:
        print("no projects (capy new <name> to start)")
        return 0
    print("PROJETS")
    for name in names:
        print(line(name, store.load(name)))
    return 0


# ---------- parser ----------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="capy",
        description="Local project + task tracker (JSON in ~/.proj/).",
    )
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("new", help="create a project")
    p.add_argument("name")
    p.add_argument("steps", nargs="*", help="step names (default: MVP v0 v1)")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("status", help="set project status")
    p.add_argument("name")
    p.add_argument("status", choices=store.STATUSES)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("next", help="advance to the next step")
    p.add_argument("name")
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("add", help="add a task (project inferred from cwd)")
    p.add_argument(
        "tokens",
        nargs="+",
        help="[project] {feat|bug|chore} title... (project optional)",
    )
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("done", help="mark a task done")
    p.add_argument("name")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_done)

    p = sub.add_parser("tasks", help="list open tasks")
    p.add_argument("name", nargs="?")
    p.set_defaults(func=cmd_tasks)

    p = sub.add_parser("show", help="show one project")
    p.add_argument("name")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("list", help="global view (default)")
    p.set_defaults(func=cmd_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        args = parser.parse_args(["list"])
    try:
        return args.func(args)
    except ProjError as e:
        print(f"capy: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())