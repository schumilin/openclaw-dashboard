#!/usr/bin/env python3
"""
OpenClaw Dashboard Server
Flask + SSE backend for the OpenClaw personal AI agent dashboard.

Usage:
    pip install flask
    python3 server.py

Open: http://localhost:8765
"""

import json
import os
import re
import subprocess
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from flask import Flask, Response, jsonify, send_from_directory

app = Flask(__name__, static_folder=".")

# ─────────────────────────────────────────────
# Configuration — edit config.json to customize
# ─────────────────────────────────────────────

DEFAULT_CONFIG = {
    "agent_name": "Yi",
    "agent_tagline": "OpenClaw AI Agent",
    "agent_about": "Your personal AI agent powered by OpenClaw.",
    "join_date": "2026-01-28",   # YYYY-MM-DD
    "workspace": "~/clawd",      # path to your OpenClaw workspace
    "port": 8765,
}

def load_config():
    cfg_path = Path(__file__).parent / "config.json"
    if cfg_path.exists():
        try:
            return {**DEFAULT_CONFIG, **json.loads(cfg_path.read_text())}
        except Exception:
            pass
    return DEFAULT_CONFIG

CFG = load_config()
WORKSPACE = Path(CFG["workspace"]).expanduser()
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def run_cmd(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception:
        return ""


def _clean_text(text):
    """Strip internal IDs, paths, URLs, and markdown syntax from display text."""
    text = re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', text)
    text = re.sub(r'ou_[A-Za-z0-9_]{10,}', '', text)
    text = re.sub(r'oc_[A-Za-z0-9_]{10,}', '', text)
    text = re.sub(r'[（(]\s*[A-Za-z0-9_]{20,}\s*[）)]', '', text)
    text = re.sub(r'[（(]\s*[）)]', '', text)
    text = re.sub(r'[~]?/[^\s，。、）)\u3002\uff0c]+', '', text)
    text = re.sub(r'[^\s]*链接[：:]\s*https?[:/]*\S*', '', text)
    text = re.sub(r'https?[:/]*\S*', '', text)
    text = re.sub(r'记录了\S+\s*open_id\S*', '', text)
    text = re.sub(r'[\ufe0f]', '', text)
    text = re.sub(r'[\s]{2,}', ' ', text).strip()
    text = re.sub(r'^[：:、，。\s]+', '', text)
    text = text.rstrip('，。、 ：:')
    return text


# ─────────────────────────────────────────────
# Data functions
# ─────────────────────────────────────────────

def get_skills():
    """Scan workspace/skills/*/SKILL.md and return skill list."""
    skills = []
    skills_dir = WORKSPACE / "skills"
    if not skills_dir.exists():
        return skills
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        name = skill_file.parent.name
        description = ""
        try:
            content = skill_file.read_text(encoding="utf-8")
            m = re.search(r'description:\s*["\']?(.+?)["\']?\n', content)
            if m:
                description = m.group(1).strip().strip('"\'')
            else:
                lines = [l.strip() for l in content.split("\n")
                         if l.strip() and not l.startswith("#")
                         and not l.startswith("-")
                         and not l.startswith("name:")
                         and not l.startswith("description:")]
                if lines:
                    description = lines[0][:100]
        except Exception:
            pass
        skills.append({"name": name, "description": description})
    return skills


def get_cron_jobs():
    """Fetch scheduled jobs via openclaw CLI."""
    raw = run_cmd("openclaw cron list 2>/dev/null")
    jobs = []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            for j in data:
                jobs.append({
                    "name": j.get("name", "Unnamed"),
                    "description": (j.get("payload", {}).get("message", "")[:80]
                                    if isinstance(j.get("payload"), dict) else ""),
                    "schedule": _format_schedule(j.get("schedule", {})),
                    "enabled": j.get("enabled", True),
                })
            return jobs
    except Exception:
        pass
    return []


def _format_schedule(schedule):
    if not schedule:
        return ""
    kind = schedule.get("kind", "")
    if kind == "cron":
        expr = schedule.get("expr", "")
        tz = schedule.get("tz", "")
        return f"{expr} ({tz})" if tz else expr
    elif kind == "every":
        ms = schedule.get("everyMs", 0)
        minutes = ms // 60000
        return f"Every {minutes}m"
    return str(schedule)


def _parse_memory_items(content):
    """Extract activity items from a memory markdown file."""
    SKIP_TITLES = {"今天发生了什么", "工作内容", "主要事项", "今天处理的主要事项",
                   "群里的重要动态", "待跟进", "犯错记录",
                   "Today", "Work", "Tasks", "Follow-up"}
    items = []
    lines = content.split("\n")
    current_title = None
    current_desc = []

    def flush():
        nonlocal current_title, current_desc
        if current_title and current_title not in SKIP_TITLES:
            clean_title = _clean_text(current_title)
            if len(clean_title) < 2:
                current_title = None
                current_desc = []
                return
            raw = " ".join(current_desc).strip()
            desc = _clean_text(raw)
            items.append({"title": clean_title, "description": desc[:120]})
        current_title = None
        current_desc = []

    for line in lines:
        if line.startswith("### ") or line.startswith("## "):
            flush()
            current_title = line.lstrip("#").strip()
        elif current_title and line.strip() and not line.startswith("#"):
            clean = re.sub(r'^[-*•>]\s*', '', line.strip())
            if clean and not clean.startswith('`') and not clean.startswith('- ['):
                current_desc.append(clean)

    flush()
    return items[:8]


def get_activity():
    """Return activity groups for today and yesterday."""
    today = date.today()
    activity = []
    for delta in range(2):
        target = today - timedelta(days=delta)
        date_str = target.strftime("%Y-%m-%d")
        label = "Today" if delta == 0 else "Yesterday"
        md_file = WORKSPACE / "memory" / f"{date_str}.md"
        items = []
        if md_file.exists():
            try:
                items = _parse_memory_items(md_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        activity.append({"date": date_str, "label": label, "items": items})
    return activity


def get_heatmap():
    """Return 24 weeks of daily activity levels, grouped by week (column)."""
    today = date.today()
    today_weekday = today.weekday()
    this_monday = today - timedelta(days=today_weekday)
    start_monday = this_monday - timedelta(weeks=23)

    heatmap_weeks = []
    for week_i in range(24):
        week_monday = start_monday + timedelta(weeks=week_i)
        col = []
        for day_j in range(7):
            d = week_monday + timedelta(days=day_j)
            date_str = d.strftime("%Y-%m-%d")
            md_file = WORKSPACE / "memory" / f"{date_str}.md"
            level = 0
            if md_file.exists():
                size = md_file.stat().st_size
                if size > 5000:
                    level = 4
                elif size > 2000:
                    level = 3
                elif size > 500:
                    level = 2
                else:
                    level = 1
            col.append({"date": date_str, "level": level, "future": d > today})
        heatmap_weeks.append(col)
    return heatmap_weeks


def get_profile():
    join_date_str = CFG["join_date"]
    try:
        join = date.fromisoformat(join_date_str)
    except Exception:
        join = date.today()
    days_since = (date.today() - join).days

    return {
        "name": CFG["agent_name"],
        "tagline": CFG["agent_tagline"],
        "about": CFG["agent_about"],
        "join_date": join_date_str,
        "days_since_join": days_since,
        "heatmap_weeks": get_heatmap(),
    }


def get_cost_today():
    """Sum up today's API costs from OpenClaw session logs."""
    cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    sessions_dir = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
    total_cost = 0.0
    if not sessions_dir.exists():
        return "$0.00"
    for jsonl_file in sessions_dir.glob("*.jsonl"):
        try:
            if jsonl_file.stat().st_mtime < cutoff:
                continue
            with open(jsonl_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        msg = entry.get("message", {})
                        if not isinstance(msg, dict):
                            continue
                        usage = msg.get("usage", {})
                        if not isinstance(usage, dict):
                            continue
                        cost_obj = usage.get("cost", {})
                        c = cost_obj.get("total", 0) if isinstance(cost_obj, dict) else 0
                        if c and c > 0:
                            total_cost += c
                    except Exception:
                        continue
        except Exception:
            continue
    if total_cost >= 0.01:
        return f"${total_cost:.2f}"
    elif total_cost > 0:
        return f"${total_cost:.4f}"
    return "$0.00"


def get_stats():
    tasks = 0
    memory_dir = WORKSPACE / "memory"
    if memory_dir.exists():
        for md_file in memory_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                tasks += len(re.findall(r'^##\s+', content, re.MULTILINE))
            except Exception:
                pass
    return {
        "tasks_completed": tasks,
        "conversation_turns": 0,   # extend as needed
        "cost_today": get_cost_today(),
    }


def get_config():
    channels = []
    model = {"primary": "Claude Sonnet", "provider": "Anthropic", "api_mode": "API Key"}
    try:
        raw = OPENCLAW_CONFIG.read_text(encoding="utf-8")
        if "feishu" in raw:
            channels.append({"name": "Feishu", "type": "feishu", "status": "connected"})
        if "telegram" in raw:
            channels.append({"name": "Telegram", "type": "telegram", "status": "connected"})
        if "discord" in raw:
            channels.append({"name": "Discord", "type": "discord", "status": "connected"})
        if "claude-sonnet" in raw:
            model["primary"] = "Claude Sonnet"
        elif "claude-opus" in raw:
            model["primary"] = "Claude Opus"
        elif "gpt-4" in raw:
            model["primary"] = "GPT-4"
    except Exception:
        pass
    if not channels:
        channels = [{"name": "Feishu", "type": "feishu", "status": "connected"}]
    return {"model": model, "channels": channels}


# ─────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/avatar.jpg")
def avatar():
    avatar_path = Path(__file__).parent / "avatar.jpg"
    if avatar_path.exists():
        return send_from_directory(".", "avatar.jpg")
    # fallback: serve a 1x1 transparent gif
    from flask import Response as Resp
    return Resp(b'GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;',
                mimetype='image/gif')


@app.route("/api/all")
def api_all():
    skills = get_skills()
    profile = get_profile()
    return jsonify({
        "profile": profile,
        "stats": get_stats(),
        "skills": skills,
        "cron_jobs": get_cron_jobs(),
        "activity": get_activity(),
        "config": get_config(),
        "skill_count": len(skills),
    })


@app.route("/api/stream")
def api_stream():
    def generate():
        while True:
            try:
                skills = get_skills()
                profile = get_profile()
                data = {
                    "profile": profile,
                    "stats": get_stats(),
                    "skills": skills,
                    "cron_jobs": get_cron_jobs(),
                    "activity": get_activity(),
                    "config": get_config(),
                    "skill_count": len(skills),
                    "timestamp": datetime.now().isoformat(),
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                time.sleep(30)
            except GeneratorExit:
                break
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(10)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


if __name__ == "__main__":
    port = CFG.get("port", 8765)
    print(f"🎯 OpenClaw Dashboard starting...")
    print(f"📍 Open: http://localhost:{port}")
    print(f"⏹  Stop: Ctrl+C")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
