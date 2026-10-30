# Repository working agreement

Use Codex for repository maintenance. Keep changes focused and preserve the profile asset generation workflow.

## Models and delegation

Default to `gpt-6.1-sol` with high reasoning. Respect explicit user model and effort selection. Allowed models are `gpt-6-astra`, `gpt-6.1-sol`, and `gpt-6.1-terra`. Use no subagent for small changes, one for a useful independent check, and at most two for independent work. Keep one writer per file and serialize shared checks.

## Commit and PR attribution

Do not add AI coauthor trailers, assistant session trailers, or assistant session links to commit messages or pull requests. Preserve human attribution and existing historical authorship metadata unless the owner explicitly authorizes a scoped rewrite.