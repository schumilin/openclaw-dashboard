# OpenClaw Dashboard

> A beautiful, real-time personal dashboard for your [OpenClaw](https://github.com/openclaw/openclaw) AI agent.

![Dashboard Preview](preview.png)

---

## What is this?

If you use [OpenClaw](https://github.com/openclaw/openclaw) to run a personal AI agent, this dashboard gives you a live window into everything your agent is doing:

- 💰 **How much did my agent cost today?**
- 📅 **What did it work on yesterday and today?**
- 🟩 **How active has it been over the past 24 weeks?**
- ⚡ **What skills does it have?**
- 📋 **What scheduled tasks are running?**

It reads directly from your OpenClaw workspace — no database, no cloud, no setup beyond `pip install flask`.

---

## Preview

| Activity Feed | Skills | Plan |
|---|---|---|
| _(screenshot)_ | _(screenshot)_ | _(screenshot)_ |

---

## Requirements

- Python 3.8+
- [OpenClaw](https://github.com/openclaw/openclaw) installed and configured
- Your OpenClaw workspace at `~/clawd` (or a custom path)

---

## Install via OpenClaw (Easiest)

If you're already using OpenClaw, just tell your agent:

> "Install this for me: https://github.com/schumilin/openclaw-dashboard"

Your agent will read the `SKILL.md`, clone the repo, configure it, and start the server automatically. Done.

---

## Manual Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/schumilin/openclaw-dashboard.git
cd openclaw-dashboard
```

### 2. Install the only dependency

```bash
pip install flask
```

### 3. Configure

Copy the example config and fill it in:

```bash
cp config.example.json config.json
```

Open `config.json` and edit:

```json
{
  "agent_name": "Yi",
  "agent_tagline": "My OpenClaw AI Agent",
  "agent_about": "A short description of what your agent does.",
  "join_date": "2026-01-15",
  "workspace": "~/clawd",
  "port": 8765
}
```

> **Tip:** `join_date` is just for the "Days Since Joining" counter — set it to whenever you started using OpenClaw.

### 4. Add your avatar (optional)

Drop any square image (JPG) into the project folder and name it `avatar.jpg`. If you skip this, the dashboard will use a placeholder.

```bash
cp ~/Downloads/my-photo.jpg avatar.jpg
```

### 5. Run

```bash
python3 server.py
```

### 6. Open

Visit [http://localhost:8765](http://localhost:8765) in your browser.

That's it. The dashboard auto-refreshes every 30 seconds via SSE.

---

## How It Works

The dashboard reads **entirely from your local filesystem** — no API calls, no cloud sync.

```
Your OpenClaw workspace (default: ~/clawd)
│
├── memory/
│   ├── 2026-03-06.md    ← "Today" activity card
│   ├── 2026-03-05.md    ← "Yesterday" activity card
│   └── ...              ← 24-week heatmap data
│
└── skills/
    ├── weather/
    │   └── SKILL.md     ← appears in Skills tab
    ├── github/
    │   └── SKILL.md
    └── ...

~/.openclaw/
├── agents/main/sessions/
│   └── *.jsonl          ← cost is calculated from here
└── openclaw.json        ← model and channel info
```

### Activity Feed

Every time your agent does something, you (or it) can write a daily note at `~/clawd/memory/YYYY-MM-DD.md`. The dashboard parses these files and extracts the `##` headings and their content as activity items.

Example memory file:

```markdown
# 2026-03-06

## Drafted weekly report
Summarized team updates and sent to Slack.

## Checked emails
Found 3 important messages, summarized and flagged for follow-up.
```

### Heatmap

The heatmap shows the past 24 weeks. A day is "active" if a memory file exists for that date. The intensity (color depth) reflects the file size — a longer note = darker green.

### Cost Tracking

OpenClaw logs every API call to `~/.openclaw/agents/main/sessions/*.jsonl`. The dashboard reads today's files and sums up `message.usage.cost.total` to show your real-time spend.

---

## Configuration Reference

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `agent_name` | string | Your agent's display name | `"My Agent"` |
| `agent_tagline` | string | One-line description shown under the name | `"OpenClaw AI Agent"` |
| `agent_about` | string | Paragraph in the About Me section | — |
| `join_date` | string | Start date in `YYYY-MM-DD` format | `"2026-01-01"` |
| `workspace` | string | Absolute or `~`-prefixed path to your OpenClaw workspace | `"~/clawd"` |
| `port` | number | Local server port | `8765` |

---

## Auto-Start on Login (macOS)

If you want the dashboard to start automatically when you log in:

**1. Create a launchd plist:**

```bash
cat > ~/Library/LaunchAgents/com.openclaw.dashboard.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.openclaw.dashboard</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/YOUR_USERNAME/openclaw-dashboard/server.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/openclaw-dashboard</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/openclaw-dashboard.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/openclaw-dashboard.log</string>
</dict>
</plist>
EOF
```

Replace `YOUR_USERNAME` with your macOS username.

**2. Load it:**

```bash
launchctl load ~/Library/LaunchAgents/com.openclaw.dashboard.plist
```

Now the dashboard starts automatically on every login and restarts if it crashes.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python + Flask |
| Live updates | Server-Sent Events (SSE) |
| Frontend | [Alpine.js](https://alpinejs.dev) + [Tailwind CSS](https://tailwindcss.com) |
| Data | Local files only — no database |
| Build step | None |

The entire frontend is a single `index.html`. No webpack, no npm, no build pipeline. If you want to tweak the UI, just edit the file directly.

---

## FAQ

**Q: Do I need OpenClaw installed first?**  
Yes. This dashboard is a companion to [OpenClaw](https://github.com/openclaw/openclaw). Without it, there's no data to display.

**Q: My cost shows $0.00. Why?**  
Cost tracking requires your OpenClaw session logs at `~/.openclaw/agents/main/sessions/`. If this folder doesn't exist yet, start a conversation with your agent first. Also make sure your model has pricing configured in OpenClaw.

**Q: The Activity feed is empty.**  
The feed reads from `~/clawd/memory/YYYY-MM-DD.md`. If your agent doesn't write daily notes, you can write them yourself, or add a heartbeat task to your agent that writes a note at the end of each day.

**Q: Can I change the workspace path?**  
Yes — set `"workspace"` in `config.json` to any path, e.g. `"/Users/alice/my-agent-workspace"`.

**Q: Can I run this on a server?**  
Yes, but note that it currently only listens on `127.0.0.1`. If you want remote access, change `host="127.0.0.1"` to `host="0.0.0.0"` in `server.py` and make sure your firewall is configured appropriately.

---

## Contributing

Contributions are welcome. The project is intentionally simple — a single Python file and a single HTML file. To contribute:

1. Fork the repo
2. Make your changes
3. Open a pull request with a clear description

Ideas welcome: more tab types, better cost charts, mobile layout, dark mode.

---

## License

MIT — do whatever you want with it.

---

Built with ❤️ by [@Schumilin](https://github.com/schumilin) · Powered by [OpenClaw](https://github.com/openclaw/openclaw)
