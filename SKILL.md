---
name: memex
description: >
  MemEx (外载记忆) — Obsidian 日记 → 编年史自动编译系统。
  支持初始化、周编译、对话式补录、检索、实体注册、手动补编译。
  Triggers on: /memex, /memex-init, /memex-compile, /memex-backfill,
  /memex-search, /memex-register, /memex-catchup, /memex-status,
  编译日记, 初始化外载记忆, 补录, 搜索记忆, 注册实体.
---

# MemEx — 外载记忆 Skill

将 Obsidian 每日日记自动编译为结构化编年史，支持对话式补录、检索和实体关联。

## 使用方式

用户调用 `/memex <子命令>`，Claude 根据子命令执行对应操作。

## 核心脚本

所有操作通过 Python 脚本完成：

```
python ~/.claude/skills/memex/memex.py --vault-path "<vault路径>" <子命令> [参数...]
```

**Vault 路径**：`c:/Users/17552/iCloudDrive/iCloud~md~obsidian/记忆外载`

## 子命令

### init — 初始化 Vault

```
python ~/.claude/skills/memex/memex.py --vault-path "..." init
```

创建 `日记/`、`编年史/`、`实体/`、`记忆体定义/` 目录，生成当前年份编年史骨架。

触发词：`/memex-init`, `/memex init`, "初始化外载记忆", "初始化MemEx"

---

### compile — 周编译

```
python ~/.claude/skills/memex/memex.py --vault-path "..." compile [--dry-run]
```

扫描 `日记/` 目录中所有未编译的日记文件，按日期归档到对应年文档。
- 先使用 `--dry-run` 预览，确认无误后去掉该参数执行
- 编译后自动删除已归档日记（保留最近 7 天缓冲区）
- 月末/年末自动检测并提示审阅

触发词：`/memex-compile`, `/memex compile`, "编译日记", "周编译"

---

### backfill — 对话式补录

```
python ~/.claude/skills/memex/memex.py --vault-path "..." backfill --date "YYYY-MM-DD" --period "上午|下午|晚上" --content "内容"
```

将用户内容写入年文档指定日期+时段。

**重要规则：**
- 用户必须提供明确日期（`2026-04-15`）或明确锚点（`昨天`、`前天`）
- 禁止自行解析"上周三"、"前几天"等模糊表达
- 遇到模糊日期→必须追问确认具体日期
- 内容前面自动加上时间戳格式 `HH:MM - `

触发词：`/memex-backfill`, `/memex backfill`, "补录", "我要补充"

---

### search — 检索

```
python ~/.claude/skills/memex/memex.py --vault-path "..." search [--query "关键词"] [--entity "实体名"] [--start-date "YYYY-MM-DD"] [--end-date "YYYY-MM-DD"]
```

跨年文档搜索，支持关键词、实体、时间段过滤。

触发词：`/memex-search`, `/memex search`, "搜索记忆", "查找", "搜索编年史"

---

### register — 注册实体

```
python ~/.claude/skills/memex/memex.py --vault-path "..." register --name "实体名" [--relationship "关系"] [--first-seen "YYYY-MM-DD"]
```

生成实体索引页到 `实体/` 目录，后续编译时自动匹配并插入 `[[实体/xx]]` 链接。

触发词：`/memex-register`, `/memex register`, "注册实体", "添加人物"

---

### catchup — 手动补编译

```
python ~/.claude/skills/memex/memex.py --vault-path "..." catchup
```

与 compile 相同，用于 Cron 因关机等错过时手动补齐。执行前先列出待处理日记。

触发词：`/memex-catchup`, `/memex catchup`, "补编译", "手动编译"

---

### status — 查看状态

```
python ~/.claude/skills/memex/memex.py --vault-path "..." status
```

显示当前 Vault 状态：未编译日记数、编年史文件数、已注册实体数。

触发词：`/memex-status`, `/memex status`, "查看状态", "MemEx状态"

## Cron 调度

仅 1 个定时任务：每周一 00:00 触发编译。

```
/memex compile
```

## 关键规则

1. **只追加不覆盖**：写入前检查目标位置是否已有内容，手动内容永久保留
2. **日期歧义**：遇到模糊表达必须追问确认，禁止自行解析
3. **空日记**：内容为空的日记文件跳过不编译
4. **实体匹配**：仅匹配已注册实体名，精确字符串匹配
5. **iCloud 同步**：操作前检查文件是否被占用，避免冲突版本
