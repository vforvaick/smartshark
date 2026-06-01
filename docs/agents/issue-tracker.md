# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues in `vforvaick/smartshark`.

Use the `gh` CLI for all operations. Because this working directory may not be a git clone, pass the repository explicitly when needed: `--repo vforvaick/smartshark`.

## Conventions

- **Create an issue**: `gh issue create --repo vforvaick/smartshark --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --repo vforvaick/smartshark --comments`, filtering comments by `jq` and also fetching labels when needed.
- **List issues**: `gh issue list --repo vforvaick/smartshark --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --repo vforvaick/smartshark --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --repo vforvaick/smartshark --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --repo vforvaick/smartshark --comment "..."`

## When a skill says "publish to the issue tracker"

Create a GitHub issue in `vforvaick/smartshark`.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --repo vforvaick/smartshark --comments`.
