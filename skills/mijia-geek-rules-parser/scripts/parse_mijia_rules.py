#!/usr/bin/env python3
"""Convert a Mi Home Automation Geek Edition export into readable summaries."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
from pathlib import Path
from typing import Any


LOCAL_TZ = dt.timezone(dt.timedelta(hours=8), "Asia/Shanghai")

TRIGGER_TYPES = {"deviceInput", "deviceInputSetVar", "alarmClock", "timeRange", "varChange", "onLoad"}
CONDITION_TYPES = {
    "deviceGet",
    "varGet",
    "condition",
    "logicAnd",
    "logicOr",
    "logicNot",
    "signalOr",
    "statusLast",
    "counter",
    "onlyNTimes",
    "eventSequence",
    "modeSwitch",
}
ACTION_TYPES = {"deviceOutput", "varSetNumber", "varSetString", "deviceGetSetVar", "delay", "loop"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def fmt_bool(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return fmt_value(value)


def fmt_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, list):
        return "[" + ", ".join(fmt_value(v) for v in value) + "]"
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def fmt_value_short(value: Any, limit: int = 120) -> str:
    text = fmt_value(value)
    if len(text) <= limit:
        return text
    return text[: limit - 12] + f"...（共 {len(text)} 字）"


def fmt_operator(props: dict[str, Any]) -> str:
    op = props.get("operator")
    has_v1 = "v1" in props
    has_v2 = "v2" in props
    if not op and not has_v1:
        return ""
    if op == "include":
        return f"包含 {fmt_value(props.get('v1'))}"
    if has_v2:
        return f"{op} {fmt_value(props.get('v1'))} ~ {fmt_value(props.get('v2'))}"
    if has_v1:
        return f"{op} {fmt_value(props.get('v1'))}"
    return str(op)


def fmt_duration(ms: Any) -> str:
    try:
        ms_float = float(ms)
    except (TypeError, ValueError):
        return fmt_value(ms)
    if ms_float % 3_600_000 == 0:
        return f"{ms_float / 3_600_000:g} 小时"
    if ms_float % 60_000 == 0:
        return f"{ms_float / 60_000:g} 分钟"
    if ms_float % 1000 == 0:
        return f"{ms_float / 1000:g} 秒"
    return f"{ms_float:g} 毫秒"


def fmt_time(obj: Any) -> str:
    if not isinstance(obj, dict):
        return fmt_value(obj)
    return f"{int(obj.get('hour', 0)):02d}:{int(obj.get('minute', 0)):02d}:{int(obj.get('second', 0)):02d}"


def fmt_timestamp(ms: Any) -> str:
    try:
        return dt.datetime.fromtimestamp(float(ms) / 1000, LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
    except (TypeError, ValueError, OSError):
        return ""


def escape_table(value: Any) -> str:
    return clean(value).replace("|", "\\|").replace("\n", "<br>")


class RuleParser:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.devices: dict[str, dict[str, Any]] = data.get("devices", {})
        self.variables: dict[str, dict[str, dict[str, Any]]] = data.get("variables", {})
        self.graph_names: dict[str, str] = {}
        for graph in data.get("graphs", []):
            cfg = graph.get("cfg", {})
            graph_id = clean(cfg.get("id"))
            if graph_id:
                self.graph_names[f"R{graph_id}"] = self.rule_name(cfg)
        self.graph_names["global"] = "全局"

    def rule_name(self, cfg: dict[str, Any]) -> str:
        return clean((cfg.get("userData") or {}).get("name")) or clean(cfg.get("name")) or clean(cfg.get("id")) or "未命名规则"

    def device_short(self, did: Any) -> str:
        did_s = clean(did)
        dev = self.devices.get(did_s)
        if not dev:
            return f"未知设备({did_s})"
        room = clean(dev.get("roomName")) or "未分房间"
        name = clean(dev.get("name")) or did_s
        return f"{room}/{name}"

    def device_full(self, did: Any) -> str:
        did_s = clean(did)
        dev = self.devices.get(did_s)
        if not dev:
            return f"未知设备({did_s})"
        room = clean(dev.get("roomName")) or "未分房间"
        name = clean(dev.get("name")) or did_s
        model = clean(dev.get("modelName")) or clean(dev.get("model"))
        online = "在线" if dev.get("online") else "离线"
        return f"{room}/{name}（{model}，{online}，did={did_s}）"

    def var_name(self, scope: Any, var_id: Any) -> str:
        scope_s = clean(scope)
        var_id_s = clean(var_id)
        var = self.variables.get(scope_s, {}).get(var_id_s)
        if not var:
            return f"{self.scope_name(scope_s)}.{var_id_s}"
        name = clean((var.get("userData") or {}).get("name")) or var_id_s
        return f"{self.scope_name(scope_s)}.{name}"

    def scope_name(self, scope: str) -> str:
        return self.graph_names.get(scope, scope or "未知作用域")

    def expr(self, elements: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        for element in elements or []:
            element_type = element.get("type")
            if element_type == "var":
                parts.append(self.var_name(element.get("scope"), element.get("id")))
            elif element_type == "const":
                parts.append(clean(element.get("value")))
            else:
                parts.append(json.dumps(element, ensure_ascii=False, sort_keys=True))
        return " ".join(p for p in parts if p != "")

    def prop_ref(self, props: dict[str, Any]) -> str:
        if "piid" in props:
            return f"服务 siid={props.get('siid')} / 属性 piid={props.get('piid')}"
        if "eiid" in props:
            return f"服务 siid={props.get('siid')} / 事件 eiid={props.get('eiid')}"
        if "aiid" in props:
            return f"服务 siid={props.get('siid')} / 动作 aiid={props.get('aiid')}"
        if "siid" in props:
            return f"服务 siid={props.get('siid')}"
        return "设备字段未标明"

    def arguments(self, props: dict[str, Any]) -> str:
        args = props.get("arguments") or []
        if not args:
            return ""
        parts = []
        for arg in args:
            if "id" in arg and "scope" in arg:
                parts.append(f"piid={arg.get('piid')} -> {self.var_name(arg.get('scope'), arg.get('id'))}")
            else:
                op = fmt_operator(arg)
                parts.append(f"piid={arg.get('piid')} {op}".strip())
        return "；参数：" + "，".join(parts)

    def describe_node(self, node: dict[str, Any]) -> str:
        node_type = node.get("type")
        props = node.get("props") or {}
        cfg = node.get("cfg") or {}

        if node_type == "deviceInput":
            detail = self.prop_ref(props)
            op = fmt_operator(props)
            preload = "，启动时预加载" if props.get("preload") else ""
            return f"设备触发：{self.device_short(props.get('did'))}，{detail}{preload}{('，条件 ' + op) if op else ''}{self.arguments(props)}"

        if node_type == "deviceInputSetVar":
            if "id" in props:
                target = self.var_name(props.get("scope"), props.get("id"))
                return f"设备状态写入变量：{self.device_short(props.get('did'))} 的 {self.prop_ref(props)} -> {target}"
            return f"设备事件写入变量：{self.device_short(props.get('did'))}，{self.prop_ref(props)}{self.arguments(props)}"

        if node_type == "deviceOutput":
            base = f"设备动作：{self.device_short(props.get('did'))}"
            if "aiid" in props:
                ins = props.get("ins") or []
                return f"{base} 执行动作 {self.prop_ref(props)}，参数 {fmt_value(ins)}"
            if "id" in props and "scope" in props:
                return f"{base} 设置 {self.prop_ref(props)} = {self.var_name(props.get('scope'), props.get('id'))}"
            if "value" in props:
                return f"{base} 设置 {self.prop_ref(props)} = {fmt_bool(props.get('value'))}"
            return f"{base} 输出，{self.prop_ref(props)}"

        if node_type == "deviceGet":
            return f"设备判断：读取 {self.device_short(props.get('did'))} 的 {self.prop_ref(props)}，要求 {fmt_operator(props)}"

        if node_type == "deviceGetSetVar":
            return f"读取设备并赋值：{self.device_short(props.get('did'))} 的 {self.prop_ref(props)} -> {self.var_name(props.get('scope'), props.get('id'))}"

        if node_type == "varGet":
            return f"变量判断：{self.var_name(props.get('scope'), props.get('id'))} {fmt_operator(props)}"

        if node_type == "varChange":
            preload = "，启动时预加载" if props.get("preload") else ""
            return f"变量变化触发：{self.var_name(props.get('scope'), props.get('id'))} {fmt_operator(props)}{preload}"

        if node_type in {"varSetNumber", "varSetString"}:
            kind = "数值" if node_type == "varSetNumber" else "字符串"
            return f"变量赋值({kind})：{self.var_name(props.get('scope'), props.get('id'))} = {self.expr(props.get('elements') or [])}"

        if node_type == "alarmClock":
            alarm_type = props.get("type", "alarm")
            return f"定时触发：{fmt_time(props)}，类型 {alarm_type}"

        if node_type == "timeRange":
            return f"时间范围：{fmt_time(props.get('start'))} 至 {fmt_time(props.get('end'))}"

        if node_type == "delay":
            return f"延迟：{fmt_duration(props.get('timeout') or cfg.get('value'))}"

        if node_type == "loop":
            return f"循环：每 {fmt_duration(props.get('interval') or cfg.get('value'))} 触发一次"

        if node_type == "condition":
            return "条件门：trigger 到达且 condition 为真时走 met，否则走 unmet"

        if node_type == "logicAnd":
            return "逻辑与：所有输入为真后输出"
        if node_type == "logicOr":
            return "逻辑或：任一输入为真后输出"
        if node_type == "logicNot":
            return "逻辑非：取反后输出"
        if node_type == "signalOr":
            return "信号汇聚：任一输入信号到达后输出"
        if node_type == "counter":
            return f"计数器：累计 {props.get('n')} 次后输出，可被 zero 清零"
        if node_type == "onlyNTimes":
            return f"限次器：最多通过 {props.get('n')} 次，可被 zero 清零"
        if node_type == "statusLast":
            return f"持续状态：输入持续 {fmt_duration(props.get('timeout') or cfg.get('value'))} 后输出"
        if node_type == "eventSequence":
            return f"事件顺序：input1 后在 {fmt_duration(props.get('timeout'))} 内收到 input2 才输出"
        if node_type == "modeSwitch":
            return "模式分流：按当前模式输出到不同分支"
        if node_type == "onLoad":
            return "规则启动触发：规则载入/启动时输出"
        if node_type == "nop":
            contents = cfg.get("contents") or []
            text = "".join(clean(item.get("insert")) for item in contents if isinstance(item, dict)).strip()
            return f"注释：{text}" if text else "注释/空节点"

        return f"{node_type or '未知节点'}：{json.dumps(props, ensure_ascii=False, sort_keys=True)}"

    def edge_targets(self, node: dict[str, Any]) -> list[dict[str, str]]:
        edges: list[dict[str, str]] = []
        outputs = node.get("outputs") or {}
        for port, targets in outputs.items():
            for target in targets or []:
                target_id, _, target_port = clean(target).partition(".")
                edges.append({"from_port": clean(port), "to": target_id, "to_port": target_port})
        return edges

    def node_variables(self, node: dict[str, Any]) -> tuple[set[str], set[str]]:
        reads: set[str] = set()
        writes: set[str] = set()
        props = node.get("props") or {}
        node_type = node.get("type")
        if node_type in {"varGet", "varChange"} and "id" in props:
            reads.add(self.var_name(props.get("scope"), props.get("id")))
        if node_type in {"varSetNumber", "varSetString", "deviceGetSetVar"} and "id" in props:
            writes.add(self.var_name(props.get("scope"), props.get("id")))
        if node_type == "deviceInputSetVar":
            if "id" in props:
                writes.add(self.var_name(props.get("scope"), props.get("id")))
            for arg in props.get("arguments") or []:
                if "id" in arg:
                    writes.add(self.var_name(arg.get("scope"), arg.get("id")))
        if node_type == "deviceOutput" and "id" in props:
            reads.add(self.var_name(props.get("scope"), props.get("id")))
        for element in props.get("elements") or []:
            if element.get("type") == "var":
                reads.add(self.var_name(element.get("scope"), element.get("id")))
        return reads, writes

    def parse_rule(self, graph: dict[str, Any]) -> dict[str, Any]:
        cfg = graph.get("cfg") or {}
        nodes = graph.get("nodes") or []
        by_id = {clean(node.get("id")): node for node in nodes}
        node_summaries = []
        devices: set[str] = set()
        reads: set[str] = set()
        writes: set[str] = set()
        edges = []
        incoming = collections.Counter()

        for node in nodes:
            node_id = clean(node.get("id"))
            props = node.get("props") or {}
            if "did" in props:
                devices.add(self.device_full(props.get("did")))
            r, w = self.node_variables(node)
            reads.update(r)
            writes.update(w)
            node_edges = self.edge_targets(node)
            for edge in node_edges:
                incoming[edge["to"]] += 1
                to_node = by_id.get(edge["to"])
                edges.append(
                    {
                        "from": node_id,
                        "from_port": edge["from_port"],
                        "to": edge["to"],
                        "to_port": edge["to_port"],
                        "summary": f"{node_id}.{edge['from_port']} -> {edge['to']}.{edge['to_port']}",
                        "from_summary": self.describe_node(node),
                        "to_summary": self.describe_node(to_node) if to_node else f"未知节点 {edge['to']}",
                    }
                )
            node_summaries.append(
                {
                    "id": node_id,
                    "type": clean(node.get("type")),
                    "summary": self.describe_node(node),
                    "outgoing": [
                        f"{node_id}.{edge['from_port']} -> {edge['to']}.{edge['to_port']}" for edge in node_edges
                    ],
                }
            )

        def pick(node_types: set[str]) -> list[str]:
            return [n["summary"] for n in node_summaries if n["type"] in node_types]

        starts = []
        for item in node_summaries:
            if incoming[item["id"]] == 0 and item["type"] not in {"nop"}:
                starts.append(item["summary"])

        return {
            "id": clean(cfg.get("id")),
            "scope": f"R{clean(cfg.get('id'))}",
            "name": self.rule_name(cfg),
            "enabled": bool(cfg.get("enable")),
            "lastUpdateTime": (cfg.get("userData") or {}).get("lastUpdateTime"),
            "lastUpdateLocal": fmt_timestamp((cfg.get("userData") or {}).get("lastUpdateTime")),
            "nodeCount": len(nodes),
            "nodeTypeCounts": dict(collections.Counter(clean(n.get("type")) for n in nodes)),
            "startNodes": starts,
            "triggers": pick(TRIGGER_TYPES),
            "conditions": pick(CONDITION_TYPES),
            "actions": pick(ACTION_TYPES),
            "variablesRead": sorted(reads),
            "variablesWritten": sorted(writes),
            "devices": sorted(devices),
            "edges": edges,
            "nodes": node_summaries,
        }

    def build_intermediate(self) -> dict[str, Any]:
        room_counter: dict[str, dict[str, Any]] = collections.defaultdict(
            lambda: {"total": 0, "online": 0, "offline": 0, "devices": []}
        )
        for did, dev in self.devices.items():
            room = clean(dev.get("roomName")) or "未分房间"
            online = bool(dev.get("online"))
            bucket = room_counter[room]
            bucket["total"] += 1
            bucket["online" if online else "offline"] += 1
            bucket["devices"].append(
                {
                    "did": did,
                    "name": clean(dev.get("name")) or did,
                    "modelName": clean(dev.get("modelName")) or clean(dev.get("model")),
                    "online": online,
                }
            )

        rules = [self.parse_rule(graph) for graph in self.data.get("graphs", [])]
        variables = []
        for scope, scope_vars in sorted(self.variables.items(), key=lambda item: self.scope_name(item[0])):
            for var_id, var in sorted(scope_vars.items(), key=lambda item: clean((item[1].get("userData") or {}).get("name"))):
                variables.append(
                    {
                        "scope": scope,
                        "scopeName": self.scope_name(scope),
                        "id": var_id,
                        "name": clean((var.get("userData") or {}).get("name")) or var_id,
                        "type": clean(var.get("type")),
                        "value": var.get("value"),
                    }
                )

        return {
            "source": {
                "exportedAt": self.data.get("exportedAt"),
                "location": self.data.get("location"),
                "rawRuleCount": self.data.get("cfgCount"),
            },
            "home": {
                "ruleCount": len(rules),
                "enabledRuleCount": sum(1 for rule in rules if rule["enabled"]),
                "deviceCount": len(self.devices),
                "onlineDeviceCount": sum(1 for dev in self.devices.values() if dev.get("online")),
                "offlineDeviceCount": sum(1 for dev in self.devices.values() if not dev.get("online")),
                "roomCount": len(room_counter),
                "rooms": dict(sorted(room_counter.items(), key=lambda item: (-item[1]["total"], item[0]))),
            },
            "variables": variables,
            "rules": rules,
        }


def bullet_lines(items: list[str], limit: int | None = None) -> list[str]:
    if not items:
        return ["- 无"]
    shown = items if limit is None else items[:limit]
    lines = [f"- {item}" for item in shown]
    if limit is not None and len(items) > limit:
        lines.append(f"- ... 另有 {len(items) - limit} 项")
    return lines


def render_markdown(model: dict[str, Any]) -> str:
    lines: list[str] = []
    home = model["home"]
    source = model["source"]
    lines.append("# 米家自动化极客版规则解析")
    lines.append("")
    lines.append("> 这是从本地导出的规则图生成的只读摘要。它解析了规则结构、设备、变量和连线；没有保存或修改任何米家配置。")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- 导出时间：{source.get('exportedAt')}")
    lines.append(f"- 导出页面：{source.get('location')}")
    lines.append(f"- 规则：{home['ruleCount']} 条，其中启用 {home['enabledRuleCount']} 条")
    lines.append(f"- 设备：{home['deviceCount']} 个，其中在线 {home['onlineDeviceCount']} 个，离线 {home['offlineDeviceCount']} 个")
    lines.append(f"- 房间/区域：{home['roomCount']} 个")
    lines.append("")
    lines.append("## 房间设备概览")
    lines.append("")
    lines.append("| 房间 | 设备数 | 在线 | 离线 | 设备样例 |")
    lines.append("| --- | ---: | ---: | ---: | --- |")
    for room, info in home["rooms"].items():
        samples = "，".join(escape_table(dev["name"]) for dev in info["devices"][:6])
        if len(info["devices"]) > 6:
            samples += f"，...另 {len(info['devices']) - 6} 个"
        lines.append(f"| {escape_table(room)} | {info['total']} | {info['online']} | {info['offline']} | {samples} |")
    lines.append("")

    offline_devices = []
    for room, info in home["rooms"].items():
        for dev in info["devices"]:
            if not dev["online"]:
                offline_devices.append(f"{room}/{dev['name']}（{dev['modelName']}，did={dev['did']}）")
    if offline_devices:
        lines.append("## 离线设备")
        lines.append("")
        lines.extend(bullet_lines(offline_devices))
        lines.append("")

    global_vars = [var for var in model["variables"] if var["scope"] == "global"]
    scoped_vars = [var for var in model["variables"] if var["scope"] != "global"]
    lines.append("## 全局变量")
    lines.append("")
    lines.append("| 变量 | 类型 | 当前值 | ID |")
    lines.append("| --- | --- | --- | --- |")
    for var in global_vars:
        lines.append(
            f"| {escape_table(var['name'])} | {escape_table(var['type'])} | {escape_table(fmt_value_short(var['value']))} | {escape_table(var['id'])} |"
        )
    lines.append("")
    lines.append("## 局部变量概览")
    lines.append("")
    grouped_vars: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for var in scoped_vars:
        grouped_vars[var["scopeName"]].append(var)
    for scope_name, vars_in_scope in sorted(grouped_vars.items()):
        values = "；".join(f"{var['name']}={fmt_value_short(var['value'], 90)}" for var in vars_in_scope)
        lines.append(f"- {scope_name}：{values}")
    lines.append("")

    lines.append("## 规则索引")
    lines.append("")
    lines.append("| 规则 | 状态 | 节点 | 涉及设备 | 主要触发 | 主要动作 |")
    lines.append("| --- | --- | ---: | ---: | --- | --- |")
    for rule in model["rules"]:
        trigger = rule["triggers"][0] if rule["triggers"] else (rule["startNodes"][0] if rule["startNodes"] else "无")
        action = rule["actions"][0] if rule["actions"] else "无"
        lines.append(
            f"| {escape_table(rule['name'])} | {'启用' if rule['enabled'] else '停用'} | {rule['nodeCount']} | {len(rule['devices'])} | {escape_table(trigger)} | {escape_table(action)} |"
        )
    lines.append("")

    lines.append("## 规则详情")
    for index, rule in enumerate(model["rules"], 1):
        lines.append("")
        lines.append(f"### {index}. {rule['name']}")
        lines.append("")
        lines.append(f"- ID：{rule['id']}")
        lines.append(f"- 状态：{'启用' if rule['enabled'] else '停用'}")
        lines.append(f"- 最后更新时间：{rule['lastUpdateLocal'] or rule['lastUpdateTime']}")
        lines.append(f"- 节点数：{rule['nodeCount']}，节点类型：{json.dumps(rule['nodeTypeCounts'], ensure_ascii=False, sort_keys=True)}")
        lines.append("")
        lines.append("触发/入口：")
        lines.extend(bullet_lines(rule["startNodes"], limit=12))
        lines.append("")
        lines.append("触发器：")
        lines.extend(bullet_lines(rule["triggers"], limit=18))
        lines.append("")
        lines.append("判断/流程控制：")
        lines.extend(bullet_lines(rule["conditions"], limit=22))
        lines.append("")
        lines.append("动作/赋值：")
        lines.extend(bullet_lines(rule["actions"], limit=28))
        lines.append("")
        if rule["variablesRead"] or rule["variablesWritten"]:
            lines.append("变量读写：")
            lines.append(f"- 读取：{'; '.join(rule['variablesRead']) if rule['variablesRead'] else '无'}")
            lines.append(f"- 写入：{'; '.join(rule['variablesWritten']) if rule['variablesWritten'] else '无'}")
            lines.append("")
        lines.append("涉及设备：")
        lines.extend(bullet_lines(rule["devices"], limit=18))
        lines.append("")
        lines.append("关键连线速览：")
        if rule["edges"]:
            for edge in rule["edges"][:24]:
                lines.append(f"- {edge['summary']}：{edge['from_summary']} -> {edge['to_summary']}")
            if len(rule["edges"]) > 24:
                lines.append(f"- ... 另有 {len(rule['edges']) - 24} 条连线")
        else:
            lines.append("- 无连线")
    lines.append("")
    lines.append("## 解析说明")
    lines.append("")
    lines.append("- 设备名称、房间、在线状态来自导出的设备列表。")
    lines.append("- 变量名称和值来自导出的变量作用域。")
    lines.append("- 设备属性暂以 siid/piid/eiid/aiid 编号表示；如果后续补充 MIoT spec 字典，可以继续翻译成更自然的中文属性名。")
    lines.append("- 这份文件是只读分析产物，不代表已经创建、修改或保存任何自动化。")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="mijia_rules_export.json", help="raw export JSON path")
    parser.add_argument("--json-output", default="mijia_rules_intermediate.json", help="normalized JSON output path")
    parser.add_argument("--markdown-output", default="mijia_rules_summary.md", help="human-readable Markdown output path")
    args = parser.parse_args()

    data = load_json(Path(args.input))
    model = RuleParser(data).build_intermediate()
    Path(args.json_output).write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.markdown_output).write_text(render_markdown(model), encoding="utf-8")
    print(f"wrote {args.json_output}")
    print(f"wrote {args.markdown_output}")
    print(
        f"rules={model['home']['ruleCount']} devices={model['home']['deviceCount']} "
        f"variables={len(model['variables'])}"
    )


if __name__ == "__main__":
    main()
