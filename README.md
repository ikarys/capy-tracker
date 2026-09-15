# capy-tracker

A local, terminal-first project and task tracker.

capy tracks **projects** (name, date, status, and a pointer over an ordered
list of steps like `MVP → v0 → v1`) and **tasks** (feat / bug / chore) per
project. No server, no database, no SaaS — one JSON file per project on disk.

## Why

The design goal is a single source of truth that both **humans** (via the
`capy` CLI) and **AI agents** (by reading the JSON files directly) can use.
Agents working on a project read `~/.proj/<project>.json` to see its state,
and never need to touch other projects — no token waste, no API.

## Install

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```sh
git clone git@github.com:ikarys/capy-tracker.git
cd capy-tracker
uv tool install --editable .
```

`capy` is then available on your PATH. Because the install is editable, code
changes take effect immediately.

## Usage

```
capy                                  global view (status + bar + next step)
capy new <name> [steps...]            create a project (default steps: MVP v0 v1)
capy [status] <status>                set status: todo | in progress | paused | done | abandoned
capy [next]                           advance to the next step
capy add [project] <feat|bug|chore> <title...>
capy done [project] <task-id>         mark a task done
capy tasks [name]                     list open tasks (all, or one project)
capy show [name]                      one project: steps + open tasks
```

`[project]` is optional everywhere: it is **inferred from the current
directory** (the git repo name, or the directory name). So inside
`~/workspace/projects/capy-tracker/` you can just:

```sh
$ capy add feat "develop TUI to improve UX"
[capy-tracker] #1 feat: develop TUI to improve UX
$ capy done 1
[capy-tracker] #1 done: develop TUI to improve UX
$ capy status in progress
'capy-tracker' status: in progress
$ capy next
'capy-tracker': ✓ MVP  →  v0
```

Project names may also be a **unique prefix** (`capy next iron` matches
`ironman`).

### Global view

```
$ capy
PROJETS
capy-tracker in progress  [###       ]  1/3  → MVP  2 open
ironman      in progress  [          ]  0/4  → spec
```

The bar shows step progress (pointer / total steps); the arrow points at the
current step; the trailing count is open tasks.

## Storage

One JSON file per project in `~/.proj/` (override with `CAPY_DIR`):

```json
{
  "date": "2026-09-15",
  "status": "in progress",
  "steps": ["MVP", "v0", "v1"],
  "pointer": 1,
  "tasks": [
    {
      "id": 1,
      "type": "feat",
      "title": "develop TUI to improve UX",
      "status": "open",
      "created": "2026-09-15"
    }
  ]
}
```

- **`steps` + `pointer`** — the project's progress. `pointer` is the index of
  the current step; steps before it are done. Advances manually via `capy
  next`; completing tasks does not move the pointer.
- **`status`** — the project's life state, orthogonal to progress: `todo`,
  `in progress`, `paused`, `done`, `abandoned`.
- **`tasks`** — flat list with auto-incremented ids; `status` is `open` or
  `done`.

Writes are atomic (temp file + rename), so a crash never leaves a half-written
file. The files are plain JSON on purpose: any agent or script can read them
without dependencies.

## Roadmap

- [x] Stage 1 — CLI
- [ ] Stage 2 — TUI (interactive, same data)
- [ ] Sync (git-backed, multi-machine)