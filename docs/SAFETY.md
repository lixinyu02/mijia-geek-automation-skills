# Safety Model

These skills are designed for smart-home automation work, where mistakes can affect real devices.

## Read-Only First

Use `mijia-geek-rules-parser` before any write. It exports live rules and turns node graphs into a readable model so the agent can reason about the current state.

## Write Actions Need Explicit Intent

Use `mijia-geek-automation-builder` only when the user explicitly asks to create, save, enable, disable, replace, or apply a real rule change.

## Dry-Run Before Save

Every write script should support an `APPLY` flag or equivalent:

- `APPLY=false`: clone and validate only,
- `APPLY=true`: save only if validation passes.

Validation should include:

- exact target rule ID/name/enabled state,
- node count and loop count,
- required edges,
- removed edges/nodes,
- missing local variables,
- node check errors,
- unused local variables that the editor will clean.

## Save Through the Editor

Prefer `window.editor.graphTool.save()` over raw server calls, because the editor performs validation and variable cleanup.

## Verify After Save

After saving:

- read back the saved rule,
- recompute missing variables,
- verify critical edges,
- export the live state again,
- parse the after-export.

## Never Commit Private Home Data

Do not publish:

- real device IDs,
- room names,
- rule IDs,
- local IPs,
- login codes,
- exported rule JSON,
- parsed rule summaries from a private home,
- one-off scripts containing real device or rule IDs.

