# MemEx (外载记忆)

> Obsidian 日记 → 编年史自动编译系统

[![English Docs](https://img.shields.io/badge/README-English-blue.svg)](README.md)

**MemEx**（Memory Extension / 外载记忆）是一个 [Claude Code](https://claude.ai/code) Skill，连接本地 Obsidian Vault 将每日日记自动编译为结构化编年史，并支持对话式补录、检索与实体关联——所有操作均在本地 Markdown 文件中完成。

---

## 为什么需要 MemEx？

你在 Obsidian 中写日记。日记越积越多，数周过去，你已忘记当初写了什么。MemEx 将零散的 `.md` 日记文件转化为可导航的个人编年史——按年、月、周、日组织——让你随时回溯人生中的任意片段，只需一句搜索。

- **无数据库。** 一切存储于本地 Markdown 文件。
- **无新应用。** 完全通过 Claude Code 驱动。
- **无需手动整理。** 一个定时任务，每周自动编译。

---

## 功能介绍

| 命令 | 触发词 | 功能 |
|---|---|---|
| **init** | `/memex init` | 创建 Vault 目录（`日记/`、`编年史/`、`实体/`、`记忆体定义/`）并生成当年编年史骨架 |
| **compile** | `/memex compile` | 扫描所有未编译日记，按日期+时段（上午/下午/晚上）插入年文档，自动关联已注册实体，生成周/月/年消费汇总 |
| **backfill** | `/memex backfill --date 2026-05-16 --period 上午 --content "..."` | 将内容直接写入年文档指定日期+时段 |
| **search** | `/memex search --query "关键词"` | 跨年全文检索，支持关键词、实体、日期范围过滤 |
| **register** | `/memex register --name "实体名" --type 人物` | 注册实体（人物/事件/地点），生成索引页并自动维护反向链接 |
| **catchup** | `/memex catchup` | Cron 因关机等错过时手动补齐编译 |
| **status** | `/memex status` | 查看 Vault 状态：待编译日记数、编年史文件数、已注册实体数 |

### 自动调度

仅 1 个 Cron 任务——每周一 00:00 触发编译。月末/年末审阅在周编译末尾自动检测并提示，无需独立定时任务。

---

## Vault 目录结构

```
[Obsidian Vault]/
├── 日记/                        # Obsidian 日记（用户编辑区）
│   ├── 2026-05-15.md
│   └── 2026-05-16.md
├── 编年史/                      # 编译后的年文档
│   └── 2026年编年史.md
├── 实体/                        # 实体索引页
│   ├── 人物/
│   ├── 事件/
│   └── 地点/
└── 记忆体定义/                  # 记忆体类型说明
    └── 日记记忆体.md
```

---

## 编年史格式

每年一个独立文档，层级严格对应时间轴：

```markdown
# 2026年
## 5月
### 第20周 (05-11 ~ 05-17)
#### 05-15 周五
- 今日消费：50 元
##### 上午
- 09:00 - 团队站会
##### 下午
- 14:30 - 完成项目方案 [[实体/人物/张工|张工]]
##### 晚上
- 本日无事
```

---

## 设计原则

- **只追加不覆盖。** 年文档中已有内容永不覆盖，手动书写内容永久保留。
- **物理隔离。** 用户日记文件 ≠ Skill 管理年文档，天然不冲突。
- **7天缓冲区。** 编译后仅删除 7 天前的日记文件，近期日记保留供编辑。
- **日期必须明确。** 补录仅接受精确日期（`2026-04-15`、`昨天`、`前天`），模糊表达（`上周三`）会触发追问确认——不允许猜测。
- **实体自动匹配。** 编译时自动检测已注册实体名并插入 `[[实体/类型/名称|名称]]` 链接。

---

## 安装

### 环境要求

- [Obsidian](https://obsidian.md/)（已开启 Daily Notes 核心插件）
- [Claude Code](https://claude.ai/code)（VS Code 或 JetBrains 扩展）
- Python 3.9+

### 安装步骤

```bash
# 1. 将 skill 文件复制到 Claude Code skills 目录
cp -r memex ~/.claude/skills/memex

# 2. 重启 Claude Code（或重新加载 skills）

# 3. 初始化 Vault
/memex init
```

### 配置 Cron

在 Claude Code 中设置一个周期性任务：

```
/memex compile
```

调度时间：每周一 00:00（本地时间）。

---

## CLI 参考

```bash
python memex.py --vault-path "/path/to/obsidian/vault" <命令> [参数]
```

| 命令 | 参数 |
|---|---|
| `init` | — |
| `compile` | `--dry-run`（预览模式） |
| `backfill` | `--date YYYY-MM-DD` `--period 上午|下午|晚上` `--content "..."` |
| `search` | `--query "关键词"` `--entity "实体名"` `--start-date` `--end-date` |
| `register` | `--name "名称"` `--type 人物|事件|地点` `--relationship "关系"` `--first-seen` |
| `catchup` | — |
| `status` | — |
| `summarize` | `--year 2026`（强制重算消费汇总） |

---

## v1 范围与未来规划

### v1（当前版本）
- 仅支持时间轴型记忆体（日记→编年史）
- 手动注册实体
- 单一 Cron 任务（周编译）

### 规划中的 v2
- 从日记内容自动检测实体
- 支持非时间轴记忆体（知识图谱、项目日志等）
- 记忆体类型定义向导
- 超越关键词匹配的语义检索

---

## 项目背景

MemEx 通过用户与 Claude（扮演产品经理角色）之间的结构化产品开发工作流设计完成。完整的决策记录——包括灵感轮次、结构化概要、设计挑战与权衡——保存在原始 Obsidian Vault 中。

两个关键对话塑造了此项目：

1. **"Establish working record document workflow"** — 建立了产品经理工作流。通过 4 轮头脑风暴，核心概念从"外载记忆存储"逐步演进为一个记忆类型无关的系统，具备定义向导、时间轴编年史和对话式交互能力。
2. **"Memex diary template and command execution issues"** — 执行了工程实现 Prompt。全部 6 项 v1 功能在 4 个阶段中完成，从环境确认到完整的实体系统（自动链接 + 反向链接）。

---

## 许可证

MIT
