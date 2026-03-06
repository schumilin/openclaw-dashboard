---
name: openclaw-dashboard
description: "Install and run the OpenClaw Dashboard — a beautiful real-time web UI showing your agent's activity, cost, skills, and 24-week heatmap. Activate when the user asks to install the dashboard or shares https://github.com/schumilin/openclaw-dashboard."
homepage: https://github.com/schumilin/openclaw-dashboard
---

# OpenClaw Dashboard — Install Skill

## When to Activate

Activate this skill when the user:
- Shares the link `https://github.com/schumilin/openclaw-dashboard`
- Says "install the dashboard", "set up dashboard", "I want a dashboard", or similar

## What to Do

Follow these steps **in order**. Tell the user what you're doing at each step.

### Step 1 — Clone the repo

```bash
git clone https://github.com/schumilin/openclaw-dashboard.git ~/openclaw-dashboard
```

If `~/openclaw-dashboard` already exists, `git pull` inside it instead.

### Step 2 — Install dependency

```bash
pip install flask
```

### Step 3 — Create config

```bash
cp ~/openclaw-dashboard/config.example.json ~/openclaw-dashboard/config.json
```

Then write the config with the user's actual values:

```json
{
  "agent_name": "<your agent name>",
  "agent_tagline": "<one-line description>",
  "agent_about": "<about paragraph>",
  "join_date": "<YYYY-MM-DD when you started using OpenClaw>",
  "workspace": "~/clawd",
  "port": 8765
}
```

Ask the user for their `agent_name` and `join_date` before writing. Use sensible defaults for the rest.

### Step 4 — (Optional) Custom avatar

If the user wants a custom avatar photo, ask them to send an image and save it as:

```bash
~/openclaw-dashboard/avatar.jpg
```

If they don't provide one, the default robot avatar (`default_avatar.jpg`) will be used automatically.

### Step 5 — Start the server

```bash
cd ~/openclaw-dashboard && nohup python3 server.py > /tmp/openclaw-dashboard.log 2>&1 &
```

Wait 2 seconds, then verify it's running:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/
```

If the response is `200`, the dashboard is up.

### Step 6 — Confirm to user

Tell the user:

> ✅ Dashboard is running at **http://localhost:8765** — open it in your browser!
>
> To stop it: `pkill -f "server.py"`
> To restart: `cd ~/openclaw-dashboard && nohup python3 server.py > /tmp/openclaw-dashboard.log 2>&1 &`

---

## Notes

- The dashboard auto-refreshes every 30 seconds via SSE — no manual reload needed.
- Activity feed is populated from `~/clawd/memory/YYYY-MM-DD.md` files.
- Cost tracking reads from `~/.openclaw/agents/main/sessions/*.jsonl`.
- If the port 8765 is in use, change `"port"` in `config.json` and restart.
