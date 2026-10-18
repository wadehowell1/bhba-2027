# Claude Code plugins for this project

Plugins are declared in `.claude/settings.json` (project scope), so anyone who
clones this repo and opens Claude Code gets the same set. Claude Code fetches
each marketplace on first use — nothing plugin-related is vendored here.

## Installed

| Plugin | Marketplace | Source | What it does |
| --- | --- | --- | --- |
| `claude-mem` | `thedotmack` | [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) | Persistent memory across sessions; context compression, `/mem-search`, timeline reports |
| `headroom` | `headroom-marketplace` | [headroomlabs-ai/headroom](https://github.com/headroomlabs-ai/headroom) | Startup hooks for Claude Code and GitHub Copilot CLI |
| `claude-code-setup` | `claude-plugins-official` | [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-code-setup) | Analyzes the codebase and recommends hooks, subagents, skills, and MCP servers |

The official marketplace is checked out sparsely (`.claude-plugin` plus
`plugins/claude-code-setup`) so we don't pull the entire ~200-plugin catalog.

To reproduce the setup by hand:

```sh
claude plugin marketplace add thedotmack/claude-mem --scope project
claude plugin marketplace add headroomlabs-ai/headroom --scope project
claude plugin marketplace add anthropics/claude-plugins-official --scope project \
  --sparse .claude-plugin plugins/claude-code-setup

claude plugin install claude-mem@thedotmack --scope project
claude plugin install headroom@headroom-marketplace --scope project
claude plugin install claude-code-setup@claude-plugins-official --scope project
```

Verify with `claude plugin list`. Restart Claude Code after a change.

## Not installed: OmniRoute

[OmniRoute](https://github.com/diegosouzapw/OmniRoute) was requested alongside
the plugins above, but it is not a Claude Code plugin — the repo has no
`.claude-plugin/plugin.json` or `marketplace.json`, so `claude plugin install`
cannot resolve it. It is a self-hosted AI gateway (an OpenAI-compatible router
across many providers) that you run as a service and then point a CLI at:

```sh
npm i -g omniroute        # server boots on http://localhost:20128
omniroute run claude      # launches Claude Code against the gateway
```

That is a machine-level tool choice rather than a repo dependency, so it is
deliberately left out of `.claude/settings.json`. The repo does ship ~46 Claude
Code *skills* under its `skills/` directory, which could be copied into
`.claude/skills/` if we ever want them — but that is a separate decision.
