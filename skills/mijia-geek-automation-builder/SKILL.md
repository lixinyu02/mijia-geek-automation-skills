---
name: mijia-geek-automation-builder
description: Create, modify, save, and verify Mi Home / Xiaomi Home Automation Geek Edition rule graphs in the local web editor. Use when Codex is explicitly asked to create a new 米家自动化极客版 automation, turn a temporary graph into a real saved rule, refactor a saved rule, enable or disable rules, or apply a real rule change after analysis.
---

# Mi Home Geek Automation Builder

## Scope

Use this skill for write actions in Mi Home Automation Geek Edition at `http://<gateway-ip>:8086/`.

This skill is for:

- creating a new automation graph,
- copying or converting a temporary graph into a real saved rule,
- modifying a saved rule,
- saving, enabling, disabling, or replacing rules,
- validating a real saved change after execution.

For read-only export, parsing, summaries, or temporary visualization, use `$mijia-geek-rules-parser` first. For login, use `$mijia-geek-login`.

## Safety Rules

- Only perform write actions when the user explicitly asks to create, save, enable, disable, replace, or apply a real rule change.
- Before any real write, export the live state and identify the exact target rule by live ID, name, and `enable` state. Do not rely on stale IDs from memory.
- Do not enable a new rule by default. New rules should stay disabled unless the user asks for an active rule.
- Avoid duplicate active rules controlling the same devices. If replacing an old rule, save and verify the new rule first, then disable the old rule only when that exact action is requested.
- Do not alter device `did`, `siid`, `piid`, `eiid`, `aiid`, or action values unless the requested change requires it.
- Saving automatically deletes local variables unused by any card. Dry-run must report which variables will be cleaned.

## Recommended Workflow

1. Ensure the editor is logged in.
   - If login is needed, use `$mijia-geek-login`.
   - Make sure Chrome allows JavaScript from Apple Events.

2. Export and parse the live state before touching anything:

   ```bash
   python3 ~/.codex/skills/mijia-geek-rules-parser/scripts/export_mijia_geek_rules.py \
     --out mijia_rules_export.before_<task>.json \
     --pretty-out mijia_rules_export.before_<task>.pretty.json

   python3 ~/.codex/skills/mijia-geek-rules-parser/scripts/parse_mijia_rules.py \
     --input mijia_rules_export.before_<task>.json \
     --json-output mijia_rules_intermediate.before_<task>.json \
     --markdown-output mijia_rules_summary.before_<task>.md
   ```

3. Resolve the write target:
   - Use the live rule list from the page or export.
   - If both an original rule and an optimized/copied rule exist, identify which one is enabled.
   - State the target rule ID, name, and enabled state before saving.

4. Build a task-specific patch script.
   - Run JavaScript in the page's main context by injecting a temporary `<script>` tag.
   - Prefer `kd.getRuleConfigList()` and `kd.getRuleContent(cfg)` from webpack module `68608` to read server-backed rule state.
   - Use `window.editor.graphTool`, `window.editor.varTool`, and `window.editor.nodeCheckTool` for graph mutation and validation.
   - Keep the script parameterized with an `APPLY` flag: dry-run first, save only when validation passes.

5. Dry-run validation before save:
   - Build a cloned patched graph; do not mutate the real graph yet.
   - Verify no card has `nodeCheckTool.run(node)` errors.
   - Verify all required edges exist and removed nodes are actually absent.
   - Verify local variables used by cards exist in `varTool.listAvailVars(ruleId, false)`.
   - Report unused local variables that will be removed by save.
   - Verify node count, loop count, target rule, and enabled state match the expected result.

6. Save through the editor:
   - Prefer `graphTool.save()` over raw server `saveRule`, because `save()` performs editor validation and variable cleanup.
   - For an existing rule, set the active graph state before saving:

     ```js
     gt.id = targetId;
     gt.graph = newCfg;
     gt.setGraph(targetId, patchedNodes);
     editor.resetData();
     editor.versionTool.run();
     if (typeof update === "function") update();
     await gt.save();
     ```

   - For a new rule, create a new config with `id: String(Date.now())`, `uiType: "test"`, and `enable: false` unless the user requested activation. Add it as a temp rule, set it active, validate, then save.

7. Verify after save:
   - Read back the target with `kd.getRuleConfigList()` and `kd.getRuleContent(cfg)`.
   - Recompute missing variables and critical edges.
   - Export the live state again to prove persistence:

     ```bash
     python3 ~/.codex/skills/mijia-geek-rules-parser/scripts/export_mijia_geek_rules.py \
       --out mijia_rules_export.after_<task>.json \
       --pretty-out mijia_rules_export.after_<task>.pretty.json
     ```

   - Parse the after-export and write a short local result record when the change is nontrivial.

## Page Injection Skeleton

Use this structure for write scripts. Keep the task-specific patch function small and explicit.

```js
(async () => {
  const TARGET_ID = "live-rule-id";
  const APPLY = false; // dry-run first
  const setOut = (obj) => {
    let el = document.getElementById("codex-mijia-write-result");
    if (!el) {
      el = document.createElement("textarea");
      el.id = "codex-mijia-write-result";
      el.style.cssText = "position:fixed;left:-9999px;top:-9999px;width:1px;height:1px;opacity:0";
      document.documentElement.appendChild(el);
    }
    el.value = JSON.stringify(obj);
  };

  let req;
  self.webpackChunkai_config.push([[Math.floor(Math.random() * 1e9)], {}, (r) => { req = r; }]);
  const kd = req(68608).kd;
  const editor = window.editor;
  const gt = editor.graphTool;
  const vt = editor.varTool;

  const cfg = (await kd.getRuleConfigList()).find((rule) => String(rule.id) === TARGET_ID);
  const before = await kd.getRuleContent(cfg);
  const patched = patchGraph(JSON.parse(JSON.stringify(before)));

  const vars = await vt.listAvailVars(TARGET_ID, false);
  const used = vt.getBeusedVarsFromCards(patched, false);
  const key = (v) => `${v.scope}:${v.id}`;
  const varSet = new Set(vars.map(key));
  const missing = used.filter((v) => v.scope !== "global" && !varSet.has(key(v)));
  const checkErrors = patched
    .map((node) => ({ id: node.id, error: editor.nodeCheckTool.run(node) }))
    .filter((item) => item.error);

  if (missing.length || checkErrors.length) {
    setOut({ ok: false, missing, checkErrors });
    return;
  }

  if (!APPLY) {
    setOut({ ok: true, apply: false, beforeNodeCount: before.length, afterNodeCount: patched.length });
    return;
  }

  const newCfg = JSON.parse(JSON.stringify(cfg));
  newCfg.userData.lastUpdateTime = Date.now();
  gt.id = TARGET_ID;
  gt.graph = newCfg;
  gt.setGraph(TARGET_ID, patched);
  editor.resetData();
  editor.versionTool.run();
  if (typeof update === "function") update();
  await gt.save();

  const afterCfg = (await kd.getRuleConfigList()).find((rule) => String(rule.id) === TARGET_ID);
  const after = await kd.getRuleContent(afterCfg);
  setOut({ ok: true, apply: true, afterNodeCount: after.length });
})();
```

## Graph Construction Guidance

- Prefer small, single-purpose rules over a large rule with unrelated concerns.
- Keep device actions in a clearly separated execution area; use variables as rule interfaces.
- Use semantic variable names. If renaming real variables, rewrite all card references and expect the old unused variables to be cleaned on save.
- Keep independent intent/state variables independent. Do not make `ModeA结束` write `ModeB=0`, or `ModeA开始` write `ModeB=1`, just to reuse an existing flow; that creates mode interference when both modes can be active. Instead add a resolver variable such as `净化需求中 = 空气净化中 OR TVOC净化中`, or add gated stop paths that only stop the shared executor when every contributing state is off.
- Treat `varChange` as a condition/edge trigger, not as a generic "any value changed" hook. A trigger like `风扇三路码 >= 0` can fail to fire when the value changes from `111` to `000`, because the condition is true on both sides. For numeric state codes with an off value, use explicit branches such as `= 0` and `>= 1`, then merge them with `signalOr`, before recomputing derived values.
- Prefer event-driven variable changes over short polling loops. If a loop is necessary, give it an explicit stop path and, where possible, a timeout/counter.
- Add `nop` note cards only for human readability; they must never be required for execution.
- Keep one readable canvas for review. Put explanation cards at the top or left, and arrange real nodes left-to-right by trigger, state, decision, action, feedback.
- Update `userData.transform` when generating or replacing a graph so the important nodes open in view.

## Shared Executor Pattern

When multiple commands or sensors can request the same devices, split the rule into three layers:

1. Intent variables: each input owns only its own state, for example `空气净化中` and `TVOC净化中`.
2. Demand resolver: one explicit derived state, for example `净化需求中`, decides whether the shared executor should run.
3. Executor: device actions watch only the derived demand and device feedback.

Avoid this shortcut:

```text
TVOC开始 -> TVOC净化中=1 -> 空气净化中=1
TVOC结束 -> TVOC净化中=0 -> 空气净化中=0
```

It is unsafe because `TVOC结束` can stop `空气净化中` while the air-cleaning mode is still active. Use a resolver or conditional stop gate instead.

## Variable Change Trigger Pattern

When a variable encodes a small state machine, enumerate the meaningful transitions explicitly:

```text
风扇三路码 >= 1 -> signalOr -> 拆分三路并同步全局码
风扇三路码 = 0  -> signalOr -> 拆分三路并同步全局码
```

Avoid this shortcut:

```text
风扇三路码 >= 0 -> 拆分三路并同步全局码
```

The shortcut looks like "all valid values", but it does not reliably represent "any change". It can miss transitions between two values that both satisfy the predicate.

## Variable Handling

- When copying cards from one rule scope to another, call:

  ```js
  await window.editor.varTool.copyCardsVars(sourceRuleId, targetRuleId, nodes);
  ```

- For temporary visual rename previews, use fresh temporary variable IDs and rewrite all local references; same-ID virtual renames can show stale names.
- For real saves, compute used variables before saving:

  ```js
  const vars = await vt.listAvailVars(ruleId, false);
  const used = vt.getBeusedVarsFromCards(nodes, false);
  ```

- Report unused locals before save because `graphTool.save()` will clean them automatically.

## Final Report

After a write, tell the user:

- which rule ID/name was saved,
- whether it is enabled,
- what changed behaviorally,
- node/loop count changes,
- variables cleaned by save,
- validation result after readback/export,
- local artifacts created for before/after evidence.
