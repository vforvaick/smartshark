# 2026-05-31 GitHub Issue Publishing With Explicit Repo

## Pattern
- When the planning directory is not a git clone, GitHub issue operations still work if every `gh` command passes `--repo owner/name` explicitly.
- For mixed AFK/HITL issue breakdowns, label AFK slices `ready-for-agent` and HITL review slices `ready-for-human`.

## Validated Commands
- `gh label list --repo vforvaick/smartshark --json name --limit 100`
- `gh label create <label> --repo vforvaick/smartshark --color <hex> --description 'Triage: <label>'`
- `gh issue create --repo vforvaick/smartshark --title '...' --body '...' --label ready-for-agent`
- `gh issue create --repo vforvaick/smartshark --title '...' --body '...' --label ready-for-human`
- Verification via `gh issue list --repo vforvaick/smartshark --state open --limit 100 --json number,title,labels` confirmed issues #1-#22 exist with expected labels.

## Limits and Caveats
- Dependency references can only point to real issue numbers after blocker issues are created, so publish in dependency order.
- If labels are absent, create them before `gh issue create --label ...` or issue creation may fail.
