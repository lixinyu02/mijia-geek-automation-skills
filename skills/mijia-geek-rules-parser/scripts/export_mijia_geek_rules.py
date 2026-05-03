#!/usr/bin/env python3
"""Read-only export of Mi Home Automation Geek Edition rules from Chrome."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


OUT_ID = "codex-mijia-geek-export"


def chrome_js(js: str) -> str:
    applescript = f'''
tell application "Google Chrome"
    if not (exists front window) then error "No Google Chrome window is open"
    tell active tab of front window to execute javascript {json.dumps(js)}
end tell
'''
    proc = subprocess.run(
        ["osascript", "-e", applescript],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "osascript failed")
    return proc.stdout.strip()


EXPORT_JS = r"""
(() => {
  const OUT_ID = "codex-mijia-geek-export";
  const ensureOut = () => {
    let el = document.getElementById(OUT_ID);
    if (!el) {
      el = document.createElement("textarea");
      el.id = OUT_ID;
      el.style.cssText = "position:fixed;left:-9999px;top:-9999px;width:1px;height:1px;opacity:0";
      document.documentElement.appendChild(el);
    }
    return el;
  };
  const setOut = (obj) => {
    ensureOut().value = JSON.stringify(obj);
  };
  const unwrap = (value) => {
    if (value && typeof value === "object") {
      if (Object.prototype.hasOwnProperty.call(value, "data")) return unwrap(value.data);
      if (Object.prototype.hasOwnProperty.call(value, "result")) return unwrap(value.result);
      if (Object.prototype.hasOwnProperty.call(value, "value")) return unwrap(value.value);
    }
    return value;
  };
  const asArray = (value) => {
    value = unwrap(value);
    if (Array.isArray(value)) return value;
    if (!value) return [];
    if (Array.isArray(value.list)) return value.list;
    if (Array.isArray(value.rules)) return value.rules;
    if (Array.isArray(value.graphs)) return value.graphs;
    return [];
  };
  const deviceMap = (value) => {
    value = unwrap(value);
    if (!value) return {};
    if (!Array.isArray(value)) return value;
    const out = {};
    for (const dev of value) {
      if (dev && dev.did != null) out[String(dev.did)] = dev;
    }
    return out;
  };
  const graphId = (cfg) => String((cfg && (cfg.id || cfg.graphId || cfg.ruleId)) || "");
  const normalizeGraph = (cfg, graph) => {
    graph = unwrap(graph);
    if (graph && graph.cfg && Array.isArray(graph.nodes)) return graph;
    if (graph && graph.data && graph.data.cfg && Array.isArray(graph.data.nodes)) return graph.data;
    if (graph && Array.isArray(graph.nodes)) return { cfg: graph.cfg || cfg, nodes: graph.nodes };
    return { cfg, nodes: [] };
  };

  setOut({ status: "running", message: "export started" });
  const runner = document.createElement("script");
  runner.textContent = `
    (async () => {
      const OUT_ID = ${JSON.stringify(OUT_ID)};
      const setOut = (obj) => {
        let el = document.getElementById(OUT_ID);
        if (!el) {
          el = document.createElement("textarea");
          el.id = OUT_ID;
          el.style.cssText = "position:fixed;left:-9999px;top:-9999px;width:1px;height:1px;opacity:0";
          document.documentElement.appendChild(el);
        }
        el.value = JSON.stringify(obj);
      };
      const unwrap = ${unwrap.toString()};
      const asArray = ${asArray.toString()};
      const deviceMap = ${deviceMap.toString()};
      const graphId = ${graphId.toString()};
      const normalizeGraph = ${normalizeGraph.toString()};
      try {
        const editor = window.editor;
        const server = editor && editor.gateway && editor.gateway.server;
        if (!editor) throw new Error("window.editor is not available. Open the logged-in Geek Edition editor page first.");
        if (!server || typeof server.callAPI !== "function") throw new Error("window.editor.gateway.server.callAPI is not available.");
        const callAPI = server.callAPI.bind(server);
        const call = async (name, args) => {
          if (args === undefined) return await callAPI(name);
          return await callAPI(name, args);
        };

        let cfgs = [];
        try {
          cfgs = asArray(await call("getGraphList"));
        } catch (err) {
          if (editor.graphTool && Array.isArray(editor.graphTool.rules)) {
            cfgs = editor.graphTool.rules.map((rule) => rule.cfg || rule);
          } else {
            throw err;
          }
        }

        const graphs = [];
        for (let i = 0; i < cfgs.length; i++) {
          const cfg = cfgs[i];
          const id = graphId(cfg);
          setOut({ status: "running", message: "exporting graphs", index: i + 1, total: cfgs.length, id });
          let graph;
          try {
            graph = await call("getGraph", { id });
          } catch (err1) {
            try {
              graph = await call("getGraph", id);
            } catch (err2) {
              graph = { cfg, nodes: [], exportError: String(err2 && err2.message || err2) };
            }
          }
          graphs.push(normalizeGraph(cfg, graph));
        }

        let devices = {};
        try {
          devices = deviceMap(await call("getDevList"));
        } catch (err) {
          devices = { __exportError: String(err && err.message || err) };
        }

        let scopes = [];
        try {
          scopes = asArray(await call("getVarScopeList"));
        } catch (err) {
          scopes = [];
        }

        const variables = {};
        for (const scope of scopes) {
          try {
            variables[String(scope)] = unwrap(await call("getVarList", { scope }));
          } catch (err1) {
            try {
              variables[String(scope)] = unwrap(await call("getVarList", scope));
            } catch (err2) {
              variables[String(scope)] = { __exportError: String(err2 && err2.message || err2) };
            }
          }
        }

        setOut({
          status: "done",
          ok: true,
          exportedAt: new Date().toISOString(),
          location: String(window.location.href),
          cfgCount: cfgs.length,
          graphs,
          devices,
          scopes,
          variables
        });
      } catch (err) {
        setOut({
          status: "error",
          ok: false,
          message: String(err && err.message || err),
          stack: String(err && err.stack || "")
        });
      }
    })();
  `;
  document.documentElement.appendChild(runner);
  runner.remove();
  return "started";
})()
"""


READ_JS = f"""
(() => {{
  const el = document.getElementById({json.dumps(OUT_ID)});
  return el ? el.value : "";
}})()
"""


def wait_for_export(timeout: float, interval: float) -> dict:
    deadline = time.time() + timeout
    last_message = ""
    while time.time() < deadline:
        raw = chrome_js(READ_JS)
        if raw and raw != "missing value":
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                last_message = raw[:500]
            else:
                status = data.get("status")
                if status == "done":
                    data.pop("status", None)
                    return data
                if status == "error":
                    raise RuntimeError(data.get("message") or json.dumps(data, ensure_ascii=False))
                message = data.get("message") or status or ""
                if message != last_message:
                    print(f"[export] {message}", file=sys.stderr)
                    last_message = message
        time.sleep(interval)
    raise TimeoutError(f"Timed out waiting for export. Last page response: {last_message}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="mijia_rules_export.json", help="compact export JSON path")
    parser.add_argument("--pretty-out", default=None, help="pretty export JSON path")
    parser.add_argument("--timeout", type=float, default=90, help="seconds to wait for page export")
    parser.add_argument("--interval", type=float, default=1, help="poll interval in seconds")
    args = parser.parse_args()

    try:
      chrome_js(EXPORT_JS)
      data = wait_for_export(args.timeout, args.interval)
    except Exception as exc:
      print(f"export failed: {exc}", file=sys.stderr)
      print(
          "Check that Chrome is on the logged-in Mi Home Geek Edition page and that "
          "`允许 Apple 事件中的 JavaScript` is enabled.",
          file=sys.stderr,
      )
      raise SystemExit(1)

    out = Path(args.out)
    pretty_out = Path(args.pretty_out) if args.pretty_out else out.with_name(out.stem + ".pretty" + out.suffix)
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    pretty_out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out}")
    print(f"wrote {pretty_out}")
    print(
        f"ok={data.get('ok')} cfgCount={data.get('cfgCount')} "
        f"graphs={len(data.get('graphs') or [])} devices={len(data.get('devices') or {})} "
        f"scopes={len(data.get('scopes') or [])}"
    )


if __name__ == "__main__":
    main()
