---
name: ship-feature
description: Orchestrates adding a new feature to this repo using the pm and dev subagents, with a human approval checkpoint between spec and implementation. Use when the user describes a new feature and wants to run the PM-then-Dev flow, e.g. "/ship-feature let borrowers place holds on titles".
---

You are the orchestrator for this flow. You run the steps yourself, invoking the `pm` and `dev` subagents via the Agent tool — they cannot invoke each other or ask the user anything, so every handoff and approval happens here.

1. Take the feature description from the user's request. Pick a short kebab-case slug for it (e.g. "borrower-holds").
2. Invoke the `pm` subagent, passing it the feature description and the slug, instructing it to write `docs/features/<slug>/spec.md`.
3. Read the resulting spec and show its key points to the user (Summary, Scope, Out of scope, Acceptance criteria, and especially any Open questions). Stop here and explicitly ask the user to approve it, request changes, or answer the open questions. Do not proceed to implementation without a clear go-ahead — this is the most important checkpoint in the flow.
4. If the user requests changes, re-invoke the `pm` subagent with the requested changes and the existing spec path, then return to step 3.
5. Once approved, invoke the `dev` subagent, passing it the path to `spec.md`, instructing it to implement the feature and write `docs/features/<slug>/impl-notes.md`.
6. Report back to the user: what was implemented, which files changed, and any open questions or deviations the dev agent flagged.
7. This skill currently only covers PM + Dev. Mention to the user that the logical next step is running the test-writer agent against the changed files, but do not invoke it automatically.
