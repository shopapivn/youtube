# Agent builder principles

These are product patterns to apply, not code to copy.

- Bolt.diy: offer starter templates without limiting free-form building; expose preview/runtime failures as actionable feedback the Agent can fix; restore project state from snapshots.
- Dyad: keep the customer project local, portable, and free of provider lock-in; make installation a download-and-run experience.
- OpenHands extensions: package repeatable specialist knowledge as discoverable Markdown skills instead of one giant prompt.
- Claude Code hooks: load project context at session start, validate after tool use, and enforce a completion check before the Agent stops.

Sources:
- https://github.com/stackblitz-labs/bolt.diy
- https://github.com/dyad-sh/dyad
- https://github.com/openhands/extensions
- https://github.com/anthropics/claude-code/blob/main/plugins/plugin-dev/skills/hook-development/SKILL.md
