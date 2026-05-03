# Release Checklist

Use this before publishing a fork or example.

## Privacy Scan

Run from the repo root:

```bash
rg -n "192\\.168|10\\.|172\\.(1[6-9]|2[0-9]|3[0-1])\\.|did=|登录码|mijia_rules_export|mijia_rules_intermediate|mijia_rules_summary" .
```

Review every match. Placeholders such as `<gateway-ip>` are fine; real values are not.

## Files That Should Not Be Included

- Browser profiles: `.mijia-*profile`
- Live exports: `mijia_rules_export*.json`
- Parsed models: `mijia_rules_intermediate*.json`
- Rule summaries from a real home: `mijia_rules_summary*.md`
- One-off patch scripts with device IDs
- Screenshots from a private home

## Functional Checks

```bash
python3 -m py_compile skills/mijia-geek-rules-parser/scripts/export_mijia_geek_rules.py
python3 -m py_compile skills/mijia-geek-rules-parser/scripts/parse_mijia_rules.py
```

## GitHub Release Text

Suggested description:

```text
Safety-first Codex skills for reading, visualizing, refactoring, and validating Xiaomi Home / Mi Home Automation Geek Edition rule graphs.
```

