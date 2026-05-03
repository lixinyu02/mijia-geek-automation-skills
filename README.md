# 米家自动化极客版 Codex 技能

这是一组面向 Codex 和 AI 智能体的米家自动化极客版工作流技能，用来安全地读取、解析、审计、重构和验证米家自动化极客版规则图。

项目重点不是让 AI 直接“接管”智能家居，而是给 AI 一套更稳的工作方式：

- 先只读导出；
- 再把规则图解析成人和 AI 都能理解的 Markdown / JSON；
- 需要真实修改时，必须先试运行；
- 保存前检查变量和节点错误；
- 保存后重新读回验证。

## 仓库内容

```text
skills/
  mijia-geek-login/
  mijia-geek-rules-parser/
  mijia-geek-automation-builder/
docs/
  CONFIGURATION.md
  SAFETY.md
  RELEASE_CHECKLIST.md
```

## 技能说明

### `mijia-geek-login`

用于登录本地米家自动化极客版页面。它会指导 Codex 从小米 Home 里获取短时有效的 6 位登录码，并完成本地网页登录。

公开版使用占位配置，不包含任何真实家庭信息：

- `MIJIA_GEEK_URL`，例如 `http://<gateway-ip>:8086/`
- `MIJIA_HOME_ROOM`
- `MIJIA_HUB_DEVICE`

### `mijia-geek-rules-parser`

用于只读导出和解析米家自动化极客版规则。

它会从本地网页编辑器里导出：

- 自动化规则图；
- 设备列表；
- 变量作用域；
- 局部变量和全局变量。

然后生成：

- 原始压缩 JSON；
- 格式化 JSON；
- 标准化中间 JSON；
- 可读 Markdown 摘要。

这个技能是只读的，不应该调用保存、启用、停用或修改图结构的接口。

### `mijia-geek-automation-builder`

用于在用户明确要求时创建、复制、修改、保存和验证真实米家自动化规则。

它采用比较保守的安全流程：

1. 先导出当前真实状态；
2. 确认目标规则的 ID、名称和启用状态；
3. 在克隆图上试运行；
4. 检查缺失变量、节点校验错误和关键连线；
5. 试运行通过后才保存；
6. 保存后重新读回并再次导出验证。

新创建的规则默认保持停用，除非用户明确要求启用。

## 安装方式

把 `skills/` 下面的技能目录复制到 Codex 的技能目录：

```bash
mkdir -p ~/.codex/skills
cp -R skills/mijia-geek-* ~/.codex/skills/
```

然后重启 Codex，或重新加载技能。

## 基本用法

### 导出并解析规则

```bash
python3 ~/.codex/skills/mijia-geek-rules-parser/scripts/export_mijia_geek_rules.py \
  --out mijia_rules_export.json \
  --pretty-out mijia_rules_export.pretty.json

python3 ~/.codex/skills/mijia-geek-rules-parser/scripts/parse_mijia_rules.py \
  --input mijia_rules_export.json \
  --json-output mijia_rules_intermediate.json \
  --markdown-output mijia_rules_summary.md
```

### 让 Codex 做只读审计

```text
使用 $mijia-geek-rules-parser 导出我的米家自动化极客版规则，并总结循环、未知设备、变量依赖和可疑逻辑。
```

### 让 Codex 创建一个禁用的新规则副本

```text
使用 $mijia-geek-automation-builder 创建一条禁用的新规则副本，在副本上做小范围重构，先试运行，通过后再保存并读回验证。
```

## 为什么需要这个项目

米家自动化极客版很强，但节点图一复杂，就会遇到这些问题：

- 变量名难以理解；
- 设备动作和触发条件互相缠绕；
- 条件触发容易被误解成“任意变化触发”；
- 临时图复制后可能出现“变量已丢失”；
- 保存时未使用变量会被自动清理；
- 规则看起来改了，但不一定真的保存成功。

这些技能把实际踩坑经验沉淀成流程，让 AI 在处理真实智能家居规则时更克制、更可验证。

## 安全原则

这个仓库不包含任何真实家庭导出、真实设备 ID、真实房间名、真实规则 ID 或本地 IP。

发布你自己的输出前，不要提交：

- `mijia_rules_export*.json`
- `mijia_rules_intermediate*.json`
- `mijia_rules_summary*.md`
- 本地浏览器配置目录
- 包含真实设备 ID 的一次性补丁脚本
- 包含房间、设备、IP 或登录码的截图

更多说明见：[docs/SAFETY.md](docs/SAFETY.md)。

## 许可证

MIT。见 [LICENSE](LICENSE)。
