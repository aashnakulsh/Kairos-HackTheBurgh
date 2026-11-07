# TeamRelay-Hackathon

Human-directed coding with a shared GitHub issue and a notification-only listener.

Board: https://github.com/aashnakulsh/TeamRelay-Hackathon/issues/1

1. Read AGENTS.md. Choose your task with your human.
2. In a separate Bash terminal, run `bash tools/board listen` (60-second polling).
3. In your coding agent, ask it to read `bash tools/board inbox` and summarize requests.
4. Decide what to implement, then use an issue branch and PR.
5. After handling a message, archive its local copy with `bash tools/board ack COMMENT_ID`.

The listener never codes, invokes an LLM, posts, commits, pushes or merges. It writes only ignored local notification files. It does not inject messages into an idle Codex extension. Claude hooks can surface the local inbox when a human sends a prompt. Keep normal permission checks enabled.

Flexible roles and focus areas are in AGENTS.md. No application runtime or stack has been selected yet.
