---
name: mijia-geek-rules-parser
description: Export and parse Mi Home / Xiaomi Home Automation Geek Edition rules from the local web editor. Use when Codex needs to inspect, summarize, normalize, audit, temporarily visualize, refactor-plan, or convert existing 米家自动化极客版 rule graphs from http://<gateway-ip>:8086/ into readable Markdown, intermediate JSON, trigger/action summaries, device inventories, variable maps, module diagrams, or home-state explanations.
---

# Mi Home Geek Rules Parser

## Scope

Use this skill for read-only analysis of the Mi Home Automation Geek Edition web editor. It covers:

- logging in first if needed,
- exporting all existing rule graphs, devices, scopes, and variables from the page,
- parsing the export into a normalized JSON model,
- generating a human-readable Markdown summary of the home state and automation rules,
- creating temporary browser-only visualization drafts for complex rule review when explicitly requested.

Do not create, save, enable, disable, or modify rules while using this skill unless the user explicitly asks and confirms the exact write action. Never call `graphTool.save`, `setGraph`, or other write APIs during a parse/export task.

## Workflow

1. Open or use Chrome at `http://<gateway-ip>:8086/`.
2. If the page asks for a login code, use `$mijia-geek-login` to retrieve and enter the code from Xiaomi Home.
3. Make sure Chrome allows JavaScript from Apple Events:
   `显示/查看 -> 开发者 -> 允许 Apple 事件中的 JavaScript`.
4. Export from the page using the bundled script:

   ```bash
   python3 ~/.codex/skills/mijia-geek-rules-parser/scripts/export_mijia_geek_rules.py \
     --out mijia_rules_export.json
   ```

   The script injects a temporary `<script>` tag into Chrome's page context so it can access `window.editor`. It then calls read-only APIs:
   `getGraphList`, `getGraph`, `getDevList`, `getVarScopeList`, and `getVarList`.

5. Parse the export:

   ```bash
   python3 ~/.codex/skills/mijia-geek-rules-parser/scripts/parse_mijia_rules.py \
     --input mijia_rules_export.json \
     --json-output mijia_rules_intermediate.json \
     --markdown-output mijia_rules_summary.md
   ```

6. Read `mijia_rules_summary.md` for the user-facing explanation and `mijia_rules_intermediate.json` for follow-up analysis.

## Temporary Visual Refactor Drafts

Use this only when the user asks to explore, split, or refactor a rule visually. Treat these drafts as browser-memory review aids: do not save, enable/disable, or replace any gateway rule without a separate action-time confirmation.

Hard-won rules from the Mi Home Geek editor:

- Prefer one temporary overview canvas with module note cards over many temporary tabs. Too many tabs make review harder and are easy for the user to delete.
- Open the source saved graph first, for example `#/graph/<source-rule-id>`, so the editor loads the real graph and device metadata before creating drafts.
- Run JavaScript in the page's main context by injecting a temporary `<script>` tag; AppleScript's direct `execute javascript` context may not expose `window.editor`.
- Do not rely on `graphTool.appendTempGraph` alone for copied real nodes. It can display device nodes, but local variables often show as `变量已丢失`.
- After creating a temporary graph, call `window.editor.varTool.copyCardsVars(sourceRuleId, tempRuleId, nodes)`. This copies local variables into the temporary graph and rewrites local scopes from `R<sourceRuleId>` to `R<tempRuleId>`.
- If variables still look stale, switch away and back to the temp graph; the React variable map sometimes needs a route refresh after `copyCardsVars`.
- When adding new note cards or replacing a temporary graph in place, also update the temporary graph's `userData.transform` so the new cards are in the current viewport. A graph can update correctly in memory while the visible canvas remains panned far away from the new cards.
- For reliable visual refresh, mutate the graph, copy vars, set the temp graph config/transform, briefly switch `location.hash` to the source graph, then switch back to the temp graph and call `editor.update()`. This forces the React canvas to remount instead of only updating `window.editor` data.
- For variable-name preview cards, changing only `varTool._virtual_store` is not enough. The editor may merge old and new variable records with the same id; card summaries can show the new name while variable selectors still show the first old name. For a visual-only rename preview, create fresh temporary variable ids, rewrite all temp-card local variable references to those ids, add matching virtual vars with the desired names, and then force the route refresh.
- Saving a graph automatically cleans variables that are not referenced by any card. Before any save or real migration, compute used variables from the final card set and expect unused local variables in that rule scope to be removed by the editor/gateway.
- Validate in memory before reporting success: saved rule count unchanged, original rule still enabled, `missing` local variables empty, and the temp graph is visible.

Recommended single-canvas pattern:

```js
(() => {
  const script = document.createElement("script");
  script.textContent = `(async () => {
    const ed = window.editor;
    const gt = ed && ed.graphTool;
    const vt = ed && ed.varTool;
    const sourceId = "<source-rule-id>";
    const tempId = String(Date.now());
    const nodes = /* cloned source nodes plus nop note cards */;
    const cfg = {
      id: tempId,
      userData: {
        name: "<room-name>拆分-总览-Codex",
        transform: { x: 0, y: 0, scale: 0.42, rotate: 0 },
        lastUpdateTime: Date.now()
      },
      uiType: "test",
      enable: true
    };
    gt.setGraph(tempId, nodes);
    gt.addTempRule(cfg);
    await vt.copyCardsVars(sourceId, tempId, nodes);
    await gt.setGraphConfig(tempId);
    location.hash = "#/graph/" + tempId;
    ed.update && ed.update();
  })();`;
  document.documentElement.appendChild(script);
  script.remove();
})();
```

Validation snippet:

```js
const gt = window.editor.graphTool;
const vt = window.editor.varTool;
const nodes = gt.getGraph(gt.id);
const localVars = await vt.listAvailVars(gt.id, false);
const used = vt.getBeusedVarsFromCards(nodes, false);
const localSet = new Set(localVars.map(v => `${v.scope}:${v.id}`));
const missing = used.filter(v => v.scope !== "global" && !localSet.has(`${v.scope}:${v.id}`));
({
  savedRules: gt.rules.length,
  tempRules: gt.tempRules.length,
  activeId: gt.id,
  missing
});
```

## Outputs

Use these standard filenames unless the user requests another destination:

- `mijia_rules_export.json`: compact raw export from the live page.
- `mijia_rules_export.pretty.json`: pretty raw export, created by the export script.
- `mijia_rules_intermediate.json`: normalized model for machine analysis.
- `mijia_rules_summary.md`: readable rule inventory and home-state summary.

## Interpretation Guidance

- Treat `siid`, `piid`, `eiid`, and `aiid` as MIoT identifiers. Keep them raw unless a reliable spec dictionary is available.
- Device names, rooms, online state, variables, and rule names come from the export and can be trusted as current at export time.
- A device ID shown as `未知设备(...)` means the rule references a device/group not present in the exported device list.
- Short interval loops are not automatically wrong; flag them as review targets when auditing reliability or performance.
- Time ranges that cross midnight, such as `18:00` to `04:30`, should be described as spanning into the next day.

## Common Follow-Ups

For a high-level explanation, summarize:

- enabled/disabled rule counts,
- online/offline device counts,
- rooms with many devices,
- global variables and important local variables,
- the purpose of each rule,
- risks such as offline devices, unknown devices, test rules, and tight polling loops.

For a single complex rule, use `mijia_rules_intermediate.json` and focus on:

- triggers and entry nodes,
- variables read/written,
- device actions,
- loops and delays,
- key edges that connect triggers to actions.
