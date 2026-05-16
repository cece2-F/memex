# MemEx (外载记忆)

> Obsidian Diary → Chronicle Auto-Compilation System

[![中文文档](https://img.shields.io/badge/README-中文-red.svg)](README_zh.md)

**MemEx** (Memory Extension) is a [Claude Code](https://claude.ai/code) skill that connects to your local Obsidian vault, automatically compiles daily diary entries into a structured chronicle, and supports conversational backfill, semantic search, and entity association — all within your existing Markdown files.

---

## Why MemEx?

You write daily notes in Obsidian. They pile up. Weeks pass. You forget what you wrote. MemEx transforms your scattered `.md` diary files into a navigable personal chronicle — organized by year, month, week, and day — so you can revisit any moment of your life with a simple search.

- **No database.** Everything stays in local Markdown files.
- **No new app.** Works entirely through Claude Code.
- **No manual organizing.** One cron job compiles your week, every week.

---

## Features

| Command | Trigger | What it does |
|---|---|---|
| **init** | `/memex init` | Creates vault structure (`日记/`, `编年史/`, `实体/`, `记忆体定义/`) and generates the current year's chronicle skeleton |
| **compile** | `/memex compile` | Scans all uncompiled diaries, inserts entries into the year chronicle by date and time-of-day period (上午/下午/晚上), links registered entities, and generates weekly/monthly/yearly expense summaries |
| **backfill** | `/memex backfill --date 2026-05-16 --period 上午 --content "..."` | Writes content directly into the chronicle at a specific date + period |
| **search** | `/memex search --query "keyword"` | Cross-year full-text search with optional entity and date-range filters |
| **register** | `/memex register --name "Entity Name" --type 人物` | Registers an entity (person/event/place) and creates an index page with automatic backlinks |
| **catchup** | `/memex catchup` | Manual compile for when the cron job was missed (e.g., computer off) |
| **status** | `/memex status` | Shows vault stats: pending diaries, chronicle files, registered entities |

### Automatic Cron

One cron job runs every Monday at 00:00 — that's it. Month-end and year-end reviews are automatically detected and triggered during the weekly compile.

---

## Vault Structure

```
[Obsidian Vault]/
├── 日记/                        # Daily notes (Obsidian native)
│   ├── 2026-05-15.md
│   └── 2026-05-16.md
├── 编年史/                      # Compiled chronicles
│   └── 2026年编年史.md
├── 实体/                        # Entity index pages
│   ├── 人物/
│   ├── 事件/
│   └── 地点/
└── 记忆体定义/                  # Memory type definitions
    └── 日记记忆体.md
```

---

## Chronicle Format

Each year gets one file. The hierarchy follows the time axis:

```markdown
# 2026年
## 5月
### 第20周 (05-11 ~ 05-17)
#### 05-15 周五
- 今日消费：50 元
##### 上午
- 09:00 - Team standup meeting
##### 下午
- 14:30 - Finished project proposal [[实体/人物/张工|张工]]
##### 晚上
- 本日无事
```

---

## Design Principles

- **Append-only.** Existing content in the chronicle is never overwritten. Hand-written entries are permanently preserved.
- **Physical isolation.** User diary files ≠ Skill-managed chronicle files. No conflicts.
- **7-day buffer.** Compiled diaries older than 7 days are auto-cleaned; recent ones stay for editing.
- **Explicit dates only.** Backfill requires clear dates (`2026-04-15`, `yesterday`, `the day before yesterday`). Vague references (`"last Wednesday"`) trigger a clarification prompt — no guessing.
- **Entity matching.** Registered entity names are auto-linked (`[[实体/人物/Name|Name]]`) during compile.

---

## Installation

### Prerequisites

- [Obsidian](https://obsidian.md/) with the Daily Notes core plugin enabled
- [Claude Code](https://claude.ai/code) (VS Code or JetBrains extension)
- Python 3.9+

### Setup

```bash
# 1. Copy skill files into Claude Code's skills directory
cp -r memex ~/.claude/skills/memex

# 2. Restart Claude Code (or reload skills)

# 3. Initialize your vault
/memex init
```

### Configure Cron

In Claude Code, set up one recurring task:

```
/memex compile
```

Schedule: Every Monday at 00:00 (local time).

---

## CLI Reference

```bash
python memex.py --vault-path "/path/to/obsidian/vault" <command> [options]
```

| Command | Options |
|---|---|
| `init` | — |
| `compile` | `--dry-run` |
| `backfill` | `--date YYYY-MM-DD` `--period 上午|下午|晚上` `--content "..."` |
| `search` | `--query "keyword"` `--entity "name"` `--start-date` `--end-date` |
| `register` | `--name "Name"` `--type 人物|事件|地点` `--relationship "..."` `--first-seen` |
| `catchup` | — |
| `status` | — |
| `summarize` | `--year 2026` (force expense recalculation) |

---

## v1 Scope & Future

### v1 (Current)
- Timeline memory type only (diary → chronicle)
- Manual entity registration
- One cron job (weekly compile)

### Planned for v2
- Auto-detection of entities from diary content
- Support for non-timeline memory types (knowledge graphs, project logs, etc.)
- Memory-type definition wizard
- Semantic search beyond keyword matching

---

## Background

MemEx was designed through a structured product-development workflow between user and Claude (acting as product manager). The full decision record — including brainstorming rounds, structured outlines, challenges, and design trade-offs — is documented in the original Obsidian vault.

Two key conversations shaped this project:
1. **"Establish working record document workflow"** — A product manager workflow was established. Through 4 rounds of brainstorming, the core concept evolved from "external memory storage" to a memory-type-agnostic system with definition wizards, timeline-based chronicles, and conversational interaction.
2. **"Memex diary template and command execution issues"** — The engineering implementation prompt was executed. All 6 v1 features were built across 4 phases, from environment setup to the complete entity system with auto-linking and backlinks.

---

## License

MIT
