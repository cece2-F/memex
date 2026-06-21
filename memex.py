#!/usr/bin/env python
"""MemEx (外载记忆) — Core Engine for Obsidian Vault Chronicle Compilation.

Handles: init, compile, backfill, search, register, catchup, status.
v1.2 — no expense tracking.
"""

import argparse
import io
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

# Fix Windows GBK encoding issue — force UTF-8 on stdout/stderr
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Constants ──────────────────────────────────────────────────────
# Period markers: canonical names + variant patterns (with Chinese colon, etc.)
PERIOD_CANONICAL = {
    "上午": "上午", "上午：": "上午",
    "下午": "下午", "下午：": "下午",
    "晚上": "晚上", "晚间": "晚上", "晚上：": "晚上", "晚间：": "晚上",
}
PERIOD_ORDER = ["上午", "下午", "晚上"]  # canonical display order
DEFAULT_ENTRY = "本日无事"
WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
CHRONICLE_DIR = "编年史"
DIARY_DIR = "日记"
ENTITY_DIR = "实体"
ENTITY_TYPES = ["人物", "事件", "地点"]  # entity subdirectories under 实体/
MEMETYPE_DIR = "记忆体定义"
CHRONICLE_SUFFIX = "年编年史"
DIARY_BUFFER_DAYS = 7
SEPARATOR_RE = re.compile(r"^_{2,}\s*$")  # matches ___ separators


# ── Helpers ────────────────────────────────────────────────────────
def get_week_label(monday_date: date) -> str:
    sunday_date = monday_date + timedelta(days=6)
    iso_year, iso_week, _ = monday_date.isocalendar()
    return f"第{iso_week}周 ({monday_date.strftime('%m-%d')} ~ {sunday_date.strftime('%m-%d')})"


def get_month_name(month: int) -> str:
    return f"{month}月"


def days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    next_month = date(year, month, 1) + timedelta(days=32)
    return (next_month.replace(day=1) - timedelta(days=1)).day


def parse_diary_filename(filename: str) -> Optional[date]:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})\.md$", os.path.basename(filename))
    if not m:
        return None
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def get_year_from_chronicle_filename(filename: str) -> Optional[int]:
    m = re.match(r"^(\d{4})年编年史\.md$", os.path.basename(filename))
    if not m:
        return None
    return int(m.group(1))


def match_period(line: str) -> Optional[str]:
    """Check if a line is a period marker, return canonical name (上午/下午/晚上)."""
    stripped = line.strip()
    # Remove markdown heading prefixes
    cleaned = re.sub(r"^#+\s*", "", stripped)
    for variant, canonical in PERIOD_CANONICAL.items():
        if cleaned == variant or cleaned.startswith(variant + " ") or cleaned.startswith(variant + "："):
            return canonical
    # Fuzzy: line contains only the period marker
    for variant, canonical in PERIOD_CANONICAL.items():
        if variant in cleaned:
            return canonical
    return None


# ── Vault Manager ──────────────────────────────────────────────────
class VaultManager:
    def __init__(self, vault_path: str):
        self.root = Path(vault_path).resolve()
        self.diary_dir = self.root / DIARY_DIR
        self.chronicle_dir = self.root / CHRONICLE_DIR
        self.entity_dir = self.root / ENTITY_DIR
        self.memetype_dir = self.root / MEMETYPE_DIR

    def ensure_dirs(self):
        for d in [self.diary_dir, self.chronicle_dir, self.entity_dir, self.memetype_dir]:
            d.mkdir(parents=True, exist_ok=True)
        # Ensure entity type subdirectories
        for et in ENTITY_TYPES:
            (self.entity_dir / et).mkdir(parents=True, exist_ok=True)

    def list_diary_files(self) -> list[Path]:
        """List all diary files sorted by date (from diary/ dir + vault root)."""
        files = []
        search_dirs = [self.diary_dir, self.root] if self.diary_dir.exists() else [self.root]
        seen = set()
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            for f in search_dir.glob("*.md"):
                d = parse_diary_filename(f.name)
                if d and f.name not in seen:
                    seen.add(f.name)
                    files.append((d, f))
        files.sort(key=lambda x: x[0])
        return [f for _, f in files]

    def list_chronicle_files(self) -> list[Path]:
        if not self.chronicle_dir.exists():
            return []
        files = []
        for f in self.chronicle_dir.glob(f"*{CHRONICLE_SUFFIX}.md"):
            y = get_year_from_chronicle_filename(f.name)
            if y:
                files.append((y, f))
        return [f for _, f in sorted(files)]

    def list_entities(self) -> list[dict]:
        """Return list of {name, type, path} for all registered entities."""
        if not self.entity_dir.exists():
            return []
        entities = []
        for et in ENTITY_TYPES:
            type_dir = self.entity_dir / et
            if type_dir.exists():
                for f in type_dir.glob("*.md"):
                    entities.append({
                        "name": f.stem,
                        "type": et,
                        "path": f,
                    })
        return sorted(entities, key=lambda e: e["name"])

    def get_entity_by_name(self, name: str) -> Optional[dict]:
        """Find an entity by name, checking all type subdirectories."""
        for e in self.list_entities():
            if e["name"] == name:
                return e
        return None

    def get_diary_by_date(self, d: date) -> Optional[Path]:
        for base in [self.root, self.diary_dir]:
            f = base / d.strftime("%Y-%m-%d.md")
            if f.exists():
                return f
        return None

    def get_chronicle(self, year: int) -> Path:
        return self.chronicle_dir / f"{year}{CHRONICLE_SUFFIX}.md"


# ── Init ───────────────────────────────────────────────────────────
def generate_year_skeleton(year: int) -> str:
    """Generate full year chronicle skeleton with months/weeks/days."""
    lines = [f"# {year}年", ""]
    today = date.today()

    for month in range(1, 13):
        lines.append(f"## {get_month_name(month)}")
        lines.append("")

        month_start = date(year, month, 1)
        month_end = date(year, month, days_in_month(year, month))

        monday = month_start - timedelta(days=month_start.isoweekday() - 1)
        while monday <= month_end:
            sunday = monday + timedelta(days=6)
            week_days_in_month = []
            for i in range(7):
                d = monday + timedelta(days=i)
                if d.month == month and d.year == year:
                    week_days_in_month.append(d)

            if week_days_in_month:
                lines.append(f"### {get_week_label(monday)}")
                lines.append("")

                for d in week_days_in_month:
                    if d > today:
                        continue
                    weekday = WEEKDAY_NAMES[d.isoweekday() - 1]
                    lines.append(f"#### {d.strftime('%m-%d')} {weekday}")
                    for period in PERIOD_ORDER:
                        lines.append(f"##### {period}")
                        lines.append(f"- {DEFAULT_ENTRY}")
                        lines.append("")
                    lines.append("")
            monday += timedelta(days=7)

    content = "\n".join(lines)
    return content.rstrip() + "\n"


def cmd_init(vault: VaultManager):
    """Initialize vault directories and generate current year skeleton."""
    vault.ensure_dirs()

    today = date.today()
    chronicle_path = vault.get_chronicle(today.year)

    if chronicle_path.exists():
        print(f"[SKIP] 编年史文件已存在: {chronicle_path.name}")
    else:
        skeleton = generate_year_skeleton(today.year)
        chronicle_path.write_text(skeleton, encoding="utf-8")
        print(f"[OK] 已创建编年史: {chronicle_path.name}")

    # Create diary memory type definition
    memetype_path = vault.memetype_dir / "日记记忆体.md"
    if not memetype_path.exists():
        memetype_path.write_text("""# 日记记忆体

## 类型名称
日记记忆体

## 文件命名规则
`YYYY-MM-DD.md`，存放于 `日记/` 目录

## 标题层级
- 年 = H1 (`#`)
- 月 = H2 (`##`)
- 周 = H3 (`###`)
- 日 = H4 (`####`)
- 时段 = H5 (`#####`)

## 时段标记
- 上午 / 上午：
- 下午 / 下午：
- 晚上 / 晚间 / 晚间：

## 归档规则
- 每周一 00:00 自动编译上周日记 → 年文档
- 编译后删除原始日记（保留最近 7 天缓冲区）
- 每年一个独立文档：`编年史/YYYY年编年史.md`
""", encoding="utf-8")
        print(f"[OK] 已创建记忆体定义: 日记记忆体.md")

    print(f"\n[OK] MemEx 初始化完成")
    print(f"  Vault: {vault.root}")
    print(f"  日记: {vault.diary_dir}")
    print(f"  编年史: {vault.chronicle_dir}")
    print(f"  实体: {vault.entity_dir}")
    for et in ENTITY_TYPES:
        print(f"    - {et}/")


# ── Entity Helpers ─────────────────────────────────────────────────
def entity_link(text: str, entities: list[dict]) -> str:
    """Wrap first occurrence of each entity name in Obsidian link with type subdir."""
    for ent in entities:
        name = ent["name"]
        etype = ent["type"]
        if name in text:
            link = f"[[{ENTITY_DIR}/{etype}/{name}|{name}]]"
            if link not in text:
                text = text.replace(name, link, 1)
    return text


def update_entity_backlinks(vault: VaultManager, entity_name: str, entity_type: str,
                            diary_date: date, description: str):
    """Add a backlink entry to an entity's index page."""
    entity_path = vault.entity_dir / entity_type / f"{entity_name}.md"
    if not entity_path.exists():
        return

    content = entity_path.read_text(encoding="utf-8")
    weekday = WEEKDAY_NAMES[diary_date.isoweekday() - 1]
    date_label = diary_date.strftime("%m-%d") + " " + weekday
    chronicle_filename = f"{diary_date.year}年编年史.md"

    backlink = f"[[../../编年史/{chronicle_filename}#{date_label}|{diary_date}]] — {description}"

    if backlink in content:
        return

    mention_header = "## 提及记录"
    if mention_header in content:
        insert_pos = content.find(mention_header)
        next_line = content.find("\n", insert_pos) + 1
        content = content[:next_line] + f"\n- {backlink}" + content[next_line:]
    else:
        content = content.rstrip() + f"\n\n{mention_header}\n- {backlink}\n"

    entity_path.write_text(content, encoding="utf-8")


# ── Diary Parsing ──────────────────────────────────────────────────
def parse_diary_content(content: str) -> dict:
    """Parse diary content into structured data.

    Returns dict with:
      - periods: {上午: [entries], 下午: [entries], 晚上: [entries]}
      - manual: [lines outside any period]
    """
    periods: dict[str, list[str]] = {p: [] for p in PERIOD_ORDER}
    manual: list[str] = []

    current_period: Optional[str] = None
    lines = content.split("\n")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip separators
        if SEPARATOR_RE.match(stripped):
            continue

        # Check for period markers
        period = match_period(stripped)
        if period:
            current_period = period
            continue

        # If we're inside a period section
        if current_period and current_period in periods:
            periods[current_period].append(stripped)
        else:
            manual.append(stripped)

    return {"periods": periods, "manual": manual}


# ── Compile ─────────────────────────────────────────────────────────
def compile_diary_to_chronicle(
    vault: VaultManager,
    diary_path: Path,
    diary_date: date,
    dry_run: bool = False,
):
    """Compile a single diary file into the appropriate year chronicle."""
    content = diary_path.read_text(encoding="utf-8")
    if not content.strip():
        return None

    entities = vault.list_entities()
    parsed = parse_diary_content(content)
    periods = parsed["periods"]

    year = diary_date.year
    chronicle_path = vault.get_chronicle(year)

    if not chronicle_path.exists():
        if dry_run:
            print(f"  [WOULD CREATE] {chronicle_path.name}")
            return diary_path
        skeleton = generate_year_skeleton(year)
        chronicle_path.write_text(skeleton, encoding="utf-8")
        print(f"  [NEW] 创建 {chronicle_path.name}")

    chronicle_content = chronicle_path.read_text(encoding="utf-8")
    weekday = WEEKDAY_NAMES[diary_date.isoweekday() - 1]
    day_header = f"#### {diary_date.strftime('%m-%d')} {weekday}"

    # Build the day entry
    entry_lines = [day_header]

    for period in PERIOD_ORDER:
        entry_lines.append(f"##### {period}")
        entries_list = periods.get(period, [])
        if entries_list:
            for line in entries_list:
                linked_line = entity_link(line, entities)
                entry_lines.append(f"- {linked_line}")
        else:
            entry_lines.append(f"- {DEFAULT_ENTRY}")
    entry_lines.append("")

    # Check if day already exists in chronicle
    if day_header in chronicle_content:
        day_pos = chronicle_content.find(day_header)
        after_day = chronicle_content[day_pos:]
        next_section_match = re.search(r"\n(?=####\s|###\s|##\s)", after_day[len(day_header):])
        if next_section_match:
            day_content = after_day[:len(day_header) + next_section_match.start()]
        else:
            day_content = after_day

        # Check if day content has non-default entries
        has_real_content = False
        for line in day_content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("-") and DEFAULT_ENTRY not in stripped and stripped != "-":
                if "**" not in stripped:  # summary lines don't count
                    has_real_content = True
                    break

        if has_real_content:
            print(f"  [SKIP] {diary_date.strftime('%m-%d')} 已有非默认内容，跳过")
            return None
        else:
            if dry_run:
                print(f"  [WOULD REPLACE] {diary_date.strftime('%m-%d')} -> {chronicle_path.name}")
                return diary_path

            new_day_block = "\n".join(entry_lines) + "\n"
            if next_section_match:
                end_pos = day_pos + len(day_header) + next_section_match.start()
            else:
                end_pos = day_pos + len(day_content)

            new_content = chronicle_content[:day_pos] + new_day_block + chronicle_content[end_pos:]
            chronicle_path.write_text(new_content, encoding="utf-8")

            # Update entity backlinks
            for ent in entities:
                for period in PERIOD_ORDER:
                    for line in periods.get(period, []):
                        if ent["name"] in line:
                            update_entity_backlinks(vault, ent["name"], ent["type"],
                                                    diary_date, line.strip().lstrip("- "))
            print(f"  [OK] {diary_date.strftime('%m-%d')} -> {chronicle_path.name} (替换默认骨架)")
            return diary_path

    # Day header doesn't exist — insert new day entry
    month_header = f"## {get_month_name(diary_date.month)}"
    month_pos = chronicle_content.find(month_header)
    if month_pos == -1:
        print(f"  [WARN] 找不到月份标题: {month_header}")
        return None

    monday = diary_date - timedelta(days=diary_date.isoweekday() - 1)
    week_label = get_week_label(monday)
    week_header = f"### {week_label}"
    week_pos = chronicle_content.find(week_header, month_pos)
    if week_pos == -1:
        print(f"  [WARN] 找不到周标题: {week_header}")
        return None

    next_section = re.search(r"\n(?=##\s|\###\s)", chronicle_content[week_pos + len(week_header):])
    if next_section:
        insert_pos = week_pos + len(week_header) + next_section.start()
    else:
        insert_pos = len(chronicle_content)
        chronicle_content = chronicle_content.rstrip() + "\n\n"

    entry_block = "\n".join(entry_lines) + "\n"

    if dry_run:
        print(f"  [WOULD INSERT] {diary_date.strftime('%m-%d')} -> {chronicle_path.name}")
        return diary_path

    new_content = chronicle_content[:insert_pos] + "\n" + entry_block + chronicle_content[insert_pos:]
    chronicle_path.write_text(new_content, encoding="utf-8")

    # Update entity backlinks
    for ent in entities:
        for period in PERIOD_ORDER:
            for line in periods.get(period, []):
                if ent["name"] in line:
                    update_entity_backlinks(vault, ent["name"], ent["type"],
                                            diary_date, line.strip().lstrip("- "))
    print(f"  [OK] {diary_date.strftime('%m-%d')} -> {chronicle_path.name}")
    return diary_path


# ── Compile Command ────────────────────────────────────────────────
def cmd_compile(vault: VaultManager, dry_run: bool = False):
    """Scan all unprocessed diaries and compile to chronicle."""
    diary_files = vault.list_diary_files()
    if not diary_files:
        print("没有找到未编译的日记文件。")
        return

    entities = vault.list_entities()
    if entities:
        names = [f"{e['name']}({e['type']})" for e in entities]
        print(f"已注册实体: {', '.join(names)}\n")

    compiled = []
    skipped = []
    today = date.today()
    buffer_date = today - timedelta(days=DIARY_BUFFER_DAYS)

    for diary_path in diary_files:
        diary_date = parse_diary_filename(diary_path.name)
        if diary_date is None:
            continue

        result = compile_diary_to_chronicle(vault, diary_path, diary_date, dry_run)
        if result:
            compiled.append(diary_path)
        else:
            skipped.append(diary_path)

    print(f"\n编译完成: {len(compiled)} 篇, 跳过 {len(skipped)} 篇")

    # Cleanup: delete compiled diary files older than buffer
    if not dry_run and compiled:
        for diary_path in compiled:
            diary_date = parse_diary_filename(diary_path.name)
            if diary_date and diary_date < buffer_date:
                print(f"  [清理] 删除 {diary_path.name}")
                diary_path.unlink()

    # Check for month/year transitions
    _check_review_triggers(vault, today)


def _check_review_triggers(vault: VaultManager, today: date):
    """Check if month/year review should be triggered."""
    yesterday = today - timedelta(days=1)
    if yesterday.month != today.month:
        print(f"\n[审阅] 检测到跨月 ({get_month_name(yesterday.month)} -> {get_month_name(today.month)})")
        print(f"  建议运行月审阅：回顾 {yesterday.year}年{get_month_name(yesterday.month)} 的内容")

    if yesterday.year != today.year:
        print(f"\n[审阅] 检测到跨年 ({yesterday.year} -> {today.year})")
        print(f"  建议运行年审阅：回顾 {yesterday.year}年 的完整内容")
        new_chronicle = vault.get_chronicle(today.year)
        if not new_chronicle.exists():
            skeleton = generate_year_skeleton(today.year)
            new_chronicle.write_text(skeleton, encoding="utf-8")
            print(f"  [OK] 已自动生成 {today.year}年 编年史骨架")


# ── Backfill ────────────────────────────────────────────────────────
def cmd_backfill(vault: VaultManager, target_date: date, period: str, content: str):
    """Write content directly to chronicle at target date + period."""
    # Normalize period to canonical form
    canonical = match_period(period)
    if canonical is None:
        # Try direct match
        for variant, canon in PERIOD_CANONICAL.items():
            if period in variant or variant in period:
                canonical = canon
                break
    if canonical is None:
        print(f"[ERROR] 无效时段: {period}，可选: 上午, 下午, 晚上/晚间")
        sys.exit(1)
    period = canonical

    chronicle_path = vault.get_chronicle(target_date.year)
    if not chronicle_path.exists():
        skeleton = generate_year_skeleton(target_date.year)
        chronicle_path.write_text(skeleton, encoding="utf-8")
        print(f"[NEW] 创建 {chronicle_path.name}")

    chronicle_content = chronicle_path.read_text(encoding="utf-8")
    entities = vault.list_entities()
    linked_content = entity_link(content, entities)

    weekday = WEEKDAY_NAMES[target_date.isoweekday() - 1]
    day_header = f"#### {target_date.strftime('%m-%d')} {weekday}"

    if day_header in chronicle_content:
        day_pos = chronicle_content.find(day_header)
        period_header = f"##### {period}"
        after_day = chronicle_content[day_pos:]
        period_rel_pos = after_day.find(period_header)
        if period_rel_pos == -1:
            print(f"[ERROR] 找不到时段 '{period}' 在 {target_date.strftime('%m-%d')}")
            sys.exit(1)

        period_section_start = day_pos + period_rel_pos
        next_line_pos = chronicle_content.find("\n", period_section_start) + 1
        next_line = chronicle_content[next_line_pos:next_line_pos + 50]

        if DEFAULT_ENTRY in next_line:
            # Replace within this specific position only
            old_entry = f"- {DEFAULT_ENTRY}"
            local_pos = chronicle_content.find(old_entry, period_section_start)
            if local_pos != -1:
                chronicle_content = (
                    chronicle_content[:local_pos]
                    + f"- {linked_content}"
                    + chronicle_content[local_pos + len(old_entry):]
                )
        else:
            insert_after = chronicle_content.find("\n##### ", period_section_start + len(period_header))
            if insert_after == -1:
                insert_after = chronicle_content.find("\n#### ", period_section_start)
            if insert_after == -1:
                insert_after = chronicle_content.find("\n### ", period_section_start)
            if insert_after == -1:
                insert_after = len(chronicle_content)

            chronicle_content = (
                chronicle_content[:insert_after] + f"\n- {linked_content}" + chronicle_content[insert_after:]
            )
    else:
        # Day section doesn't exist — create full day entry with all periods
        month_header = f"## {get_month_name(target_date.month)}"
        month_pos = chronicle_content.find(month_header)
        if month_pos == -1:
            print(f"[ERROR] 找不到月份: {get_month_name(target_date.month)}")
            sys.exit(1)

        monday = target_date - timedelta(days=target_date.isoweekday() - 1)
        week_header = f"### {get_week_label(monday)}"
        week_pos = chronicle_content.find(week_header, month_pos)
        if week_pos == -1:
            print(f"[ERROR] 找不到周: {get_week_label(monday)}")
            sys.exit(1)

        next_section = re.search(r"\n(?=##\s|\###\s)", chronicle_content[week_pos + len(week_header):])
        if next_section:
            insert_pos = week_pos + len(week_header) + next_section.start()
        else:
            insert_pos = len(chronicle_content)

        entry_lines = [day_header]
        entry_lines.append(f"##### {period}")
        entry_lines.append(f"- {linked_content}")
        for other_period in PERIOD_ORDER:
            if other_period != period:
                entry_lines.append(f"##### {other_period}")
                entry_lines.append(f"- {DEFAULT_ENTRY}")
        entry_lines.append("")

        entry_block = "\n".join(entry_lines) + "\n"
        chronicle_content = chronicle_content[:insert_pos] + "\n" + entry_block + chronicle_content[insert_pos:]

    chronicle_path.write_text(chronicle_content, encoding="utf-8")

    # Update entity backlinks
    for ent in entities:
        if ent["name"] in content:
            update_entity_backlinks(vault, ent["name"], ent["type"], target_date, content)

    print(f"[OK] 补录 {target_date} {period}: {content}")


# ── Search ──────────────────────────────────────────────────────────
def cmd_search(
    vault: VaultManager,
    query: Optional[str],
    entity: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
):
    """Search across chronicle files."""
    results = []
    chronicle_files = vault.list_chronicle_files()

    if start_date:
        start_year = int(start_date[:4])
        chronicle_files = [f for f in chronicle_files
                           if get_year_from_chronicle_filename(f.name) and
                           get_year_from_chronicle_filename(f.name) >= start_year]
    if end_date:
        end_year = int(end_date[:4])
        if end_year:
            chronicle_files = [f for f in chronicle_files
                               if get_year_from_chronicle_filename(f.name) and
                               get_year_from_chronicle_filename(f.name) <= end_year]

    # If searching by entity, also check entity subdirectories
    entity_types_to_search = ENTITY_TYPES if entity else []

    for cf in sorted(chronicle_files):
        content = cf.read_text(encoding="utf-8")
        year = get_year_from_chronicle_filename(cf.name)
        lines = content.split("\n")
        current_date_str = ""
        current_period = ""

        for line in lines:
            date_match = re.match(r"^#### (\d{2}-\d{2})", line)
            if date_match:
                current_date_str = f"{year}-{date_match.group(1)}"
                current_period = ""
                continue

            period_match = re.match(r"^#####\s+(\S+)", line)
            if period_match:
                current_period = match_period(period_match.group(1)) or period_match.group(1)
                continue

            if line.startswith("#") or not line.strip():
                continue

            match = True
            if query:
                match = query.lower() in line.lower()
            if entity:
                # Check for entity in various link formats
                entity_patterns = [entity]
                for et in entity_types_to_search:
                    entity_patterns.append(f"[[{ENTITY_DIR}/{et}/{entity}")
                match = match and any(p in line for p in entity_patterns)

            if match:
                results.append({
                    "date": current_date_str,
                    "period": current_period,
                    "line": line.strip().lstrip("- "),
                    "file": cf.name,
                })

    if not results:
        print("未找到匹配结果。")
        return

    print(f"\n找到 {len(results)} 条结果:\n")
    for r in results:
        print(f"  [{r['date']}] [{r['period']}] {r['line']}  ({r['file']})")


# ── Register Entity ─────────────────────────────────────────────────
def cmd_register(vault: VaultManager, name: str, etype: str = "人物",
                 relationship: str = "", first_seen: str = ""):
    """Register a new entity and create its index page under 实体/<type>/."""
    if etype not in ENTITY_TYPES:
        print(f"[ERROR] 无效实体类型: {etype}，可选: {', '.join(ENTITY_TYPES)}")
        sys.exit(1)

    vault.ensure_dirs()
    type_dir = vault.entity_dir / etype
    type_dir.mkdir(parents=True, exist_ok=True)

    entity_path = type_dir / f"{name}.md"
    if entity_path.exists():
        print(f"[WARN] 实体 '{name}' 已存在 ({etype}): {entity_path.relative_to(vault.root)}")
        return

    content = f"""# {name}

## 相关信息
- 类型：{etype}
- 关系：{relationship or '未指定'}
- 首次出现：{first_seen or date.today().strftime('%Y-%m-%d')}

## 提及记录
<!-- 编译时自动填入反向链接 -->
"""
    entity_path.write_text(content, encoding="utf-8")
    print(f"[OK] 已注册实体: {name} ({etype})")
    print(f"  文件: {entity_path.relative_to(vault.root)}")


# ── Catchup ─────────────────────────────────────────────────────────
def cmd_catchup(vault: VaultManager):
    """Manual catchup — same as compile but with detailed status."""
    diary_files = vault.list_diary_files()
    if not diary_files:
        print("没有待处理的日记文件。")
        return

    print(f"发现 {len(diary_files)} 个日记文件:\n")
    for f in diary_files:
        d = parse_diary_filename(f.name)
        if d:
            print(f"  {f.name} — {WEEKDAY_NAMES[d.isoweekday()-1]}")

    print(f"\n开始编译...\n")
    cmd_compile(vault, dry_run=False)


# ── Status ──────────────────────────────────────────────────────────
def cmd_status(vault: VaultManager):
    """Show current vault status."""
    print("MemEx 状态\n")
    print(f"Vault: {vault.root}")

    diary_files = vault.list_diary_files()
    print(f"未编译日记: {len(diary_files)} 篇")
    for f in diary_files:
        d = parse_diary_filename(f.name)
        if d:
            print(f"  - {f.name} ({WEEKDAY_NAMES[d.isoweekday()-1]})")

    chronicle_files = vault.list_chronicle_files()
    print(f"编年史文件: {len(chronicle_files)} 个")
    for f in chronicle_files:
        y = get_year_from_chronicle_filename(f.name)
        print(f"  - {f.name}")

    entities = vault.list_entities()
    print(f"已注册实体: {len(entities)} 个")
    by_type: dict[str, list[str]] = {}
    for e in entities:
        by_type.setdefault(e["type"], []).append(e["name"])
    for etype, names in sorted(by_type.items()):
        print(f"  [{etype}] {', '.join(names)}")


# ── CLI ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="MemEx — 外载记忆引擎")
    parser.add_argument("--vault-path", required=True, help="Obsidian Vault 根路径")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="初始化 Vault 目录和年文档骨架")

    p_compile = sub.add_parser("compile", help="编译未处理的日记到编年史")
    p_compile.add_argument("--dry-run", action="store_true", help="预览模式")

    p_backfill = sub.add_parser("backfill", help="补录内容到指定日期时段")
    p_backfill.add_argument("--date", required=True, help="日期 YYYY-MM-DD")
    p_backfill.add_argument("--period", required=True, help="时段: 上午|下午|晚上|晚间")
    p_backfill.add_argument("--content", required=True, help="补录内容")

    p_search = sub.add_parser("search", help="搜索编年史")
    p_search.add_argument("--query", help="关键词")
    p_search.add_argument("--entity", help="实体名")
    p_search.add_argument("--start-date", help="起始日期 YYYY-MM-DD")
    p_search.add_argument("--end-date", help="结束日期 YYYY-MM-DD")

    p_register = sub.add_parser("register", help="注册实体")
    p_register.add_argument("--name", required=True, help="实体名")
    p_register.add_argument("--type", default="人物", help=f"实体类型: {', '.join(ENTITY_TYPES)}")
    p_register.add_argument("--relationship", default="", help="关系")
    p_register.add_argument("--first-seen", default="", help="首次出现日期")

    sub.add_parser("catchup", help="手动补编译（Cron 错过时使用）")
    sub.add_parser("status", help="显示当前状态")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    vault = VaultManager(args.vault_path)

    if args.command == "init":
        cmd_init(vault)
    elif args.command == "compile":
        cmd_compile(vault, dry_run=args.dry_run)
    elif args.command == "backfill":
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        cmd_backfill(vault, target_date, args.period, args.content)
    elif args.command == "search":
        cmd_search(vault, args.query, args.entity, args.start_date, args.end_date)
    elif args.command == "register":
        cmd_register(vault, args.name, args.type, args.relationship, args.first_seen)
    elif args.command == "catchup":
        cmd_catchup(vault)
    elif args.command == "status":
        cmd_status(vault)


if __name__ == "__main__":
    main()
