#!/usr/bin/env bash
# Installs the runtime dependencies for the agent tooling vendored in .claude/.
# Idempotent and safe to run repeatedly: everything already present is skipped.
#
#   ./.claude/scripts/setup-agent-tools.sh          # fast path (pip only)
#   ./.claude/scripts/setup-agent-tools.sh --full   # also installs ffmpeg via apt
#
# Runs on SessionStart (fast path) so Claude Code web/cloud containers, which are
# rebuilt from scratch each session, come back with the tools available.

set -uo pipefail

FULL=0
[[ "${1:-}" == "--full" ]] && FULL=1

pip_install() {
  local bin=$1 pkg=$2
  command -v "$bin" >/dev/null 2>&1 && return 0
  echo "setup-agent-tools: installing ${pkg}" >&2
  pip install --quiet --break-system-packages "$pkg" >/dev/null 2>&1 \
    || pip install --quiet "$pkg" >/dev/null 2>&1 \
    || { echo "setup-agent-tools: could not install ${pkg}" >&2; return 1; }
}

# prism-scanner -> `prism` CLI, used by the prism-scanner skill
pip_install prism prism-scanner

# yt-dlp -> used by the watch (claude-video) and transcribe skills
pip_install yt-dlp yt-dlp

# ffmpeg -> used by watch and transcribe. Only via --full: the apt install is
# slow enough to be noticeable at session start.
if ! command -v ffmpeg >/dev/null 2>&1; then
  if [[ $FULL -eq 1 ]] && command -v apt-get >/dev/null 2>&1; then
    echo "setup-agent-tools: installing ffmpeg" >&2
    apt-get update -qq >/dev/null 2>&1
    apt-get install -y -qq ffmpeg >/dev/null 2>&1 \
      || echo "setup-agent-tools: could not install ffmpeg" >&2
  else
    echo "setup-agent-tools: ffmpeg not found — run '.claude/scripts/setup-agent-tools.sh --full' before using /watch or /transcribe" >&2
  fi
fi

exit 0
