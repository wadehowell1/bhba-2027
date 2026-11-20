# Agent tooling

Claude Code skills, plugins and MCP servers collected for this project, with the
source links and the install status of each.

## Source links

| Tool | Repository |
|---|---|
| Prism Scanner | https://github.com/aidongise-cell/prism-scanner |
| Transcript Critic | https://github.com/jftuga/transcript-critic |
| Claude Context | https://github.com/zilliztech/claude-context |
| Self-Improving Skills | https://github.com/UniM0cha/self-improving-skills |
| Stop Slop | https://github.com/hardikpandya/stop-slop |
| Visual Explainer | https://github.com/ericblue/visual-explainer-skill |
| Claude Video | https://github.com/bradautomates/claude-video |

Shared alongside the list, kept here for reference:

- WhatsApp channel: https://whatsapp.com/channel/0029Vb7KyCPDzgTJtKYgZs2Z
- Newsletter: https://feedough.co/

## Install status

| Tool | Installed as | Invoke | Runtime deps |
|---|---|---|---|
| Prism Scanner | `.claude/skills/prism-scanner/` | `prism-scanner` skill, `prism` CLI | `prism-scanner` (pip) |
| Stop Slop | `.claude/skills/stop-slop/` | `stop-slop` skill | none |
| Transcript Critic | `.claude/skills/transcribe/` | `/transcribe <file-or-url>` | whisper.cpp, ffmpeg, yt-dlp |
| Visual Explainer | `.claude/commands/visual-explainer.md` | `/visual-explainer <topic>` | `OPENAI_API_KEY` or `GEMINI_API_KEY` |
| Claude Video | plugin `watch@claude-video` | `/watch <url-or-path>` | ffmpeg, yt-dlp |
| Self-Improving Skills | plugin `claude-code-self-improving-skills@self-improving-skills` | runs automatically | python3 |
| Claude Context | **not installed** — needs credentials | — | OpenAI key + Zilliz/Milvus endpoint |

The two plugins are declared in `.claude/settings.json` (`extraKnownMarketplaces`
plus `enabledPlugins`), so Claude Code fetches them from their upstream
marketplaces on session start. The other four are vendored into `.claude/` and
travel with the repository.

### Runtime dependencies

`.claude/scripts/setup-agent-tools.sh` installs `prism-scanner` and `yt-dlp`;
pass `--full` to also install ffmpeg through apt. Cloud sessions start from a
fresh container, so run it once per session before using `/watch` or
`/transcribe`:

```bash
./.claude/scripts/setup-agent-tools.sh --full
```

To have it run by itself, add a `SessionStart` hook to `.claude/settings.json`
pointing at the script.

### Claude Context

Claude Context is an MCP server rather than a skill, and it needs an OpenAI API
key for embeddings plus a Milvus or Zilliz Cloud vector database. Once you have
both, register it:

```bash
claude mcp add claude-context \
  -e OPENAI_API_KEY=sk-... \
  -e MILVUS_ADDRESS=your-zilliz-cloud-public-endpoint \
  -e MILVUS_TOKEN=your-zilliz-cloud-api-key \
  -- npx @zilliz/claude-context-mcp@latest
```

Use `--scope project` to record it in the repository instead of your user
settings — but keep the keys out of the committed file and read them from the
environment.

### Local modification

`.claude/skills/transcribe/SKILL.md` ships upstream with two hardcoded paths
under `~/github.com/jftuga/transcript-critic/`. Both were repointed at
`.claude/skills/transcribe/` so the skill finds its own bundled `transcribe.sh`
and `ANALYSIS_PROMPT.md`. The script still expects whisper.cpp at
`~/github.com/ggerganov/whisper.cpp`; edit `WHISPER_ROOT` at the top of
`transcribe.sh` if yours lives elsewhere.

## Pre-install security scan

Prism Scanner was installed first and used to scan the other five repositories
before they went in:

| Tool | Grade | Notes |
|---|---|---|
| Stop Slop | A | prose rules only |
| Visual Explainer | A | — |
| Transcript Critic | D | 2 HIGH on `add_permission.py`, the installer that edits `~/.claude/settings.json`. Not vendored — only `SKILL.md`, `transcribe.sh` and `ANALYSIS_PROMPT.md` were copied. |
| Claude Video | D | HIGH "unexpected shell capability", which is the skill's whole job: it shells out to yt-dlp and ffmpeg. |
| Self-Improving Skills | F | 3 critical, 18 high. Checked by hand and they are false positives — the `.zshrc`/`crontab`/`curl … \| sh` strings live in `scripts/skill_guard.py`, a guard that *detects* those writes, and in its test fixtures. A repository-wide scan for zero-width and bidi characters found none, so the P5 "prompt injection" hit is also a false positive. |

Worth knowing regardless of the grades: Self-Improving Skills installs
`SessionStart` and `PostToolUse` hooks that watch your work and write skill files
on their own, and Claude Video runs shell commands against network downloads.
Both behave as advertised, but they are active rather than passive.

Scanning the finished `.claude/` tree returns one HIGH on
`skills/prism-scanner/SKILL.md:100` — Prism matching the word "crontab" in its
own description of what it detects.

Re-scan anything new before installing it:

```bash
prism scan ./path-or-repo-url
```
