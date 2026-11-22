# Pstack models

For pstack roles in this project, read `C:/Users/Fluke/.agents/pstack-models.md` for role assignments. When spawning a subagent, use only these model and reasoning-effort combinations:

- `gpt-6-luna`: `xhigh` by default; `max` for the hardest tasks.
- `gpt-6.1-sol`: `medium`.

These combinations override pstack's automatic effort adjustments and fallback model choices. If the assigned combination is unavailable, report the limitation instead of selecting another model or effort.
