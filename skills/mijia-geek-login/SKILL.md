---
name: mijia-geek-login
description: Log in to the local Mi Home Automation Geek Edition page by retrieving the one-time 6-digit login code from Xiaomi Home on macOS. Use when Codex needs to open http://<gateway-ip>:8086/, find the "<room-name>" room, open the "<hub-device-name>" device, enter "澎湃智联" then "中枢功能", copy the login code, and complete the web login flow.
---

# Mijia Geek Login

## Overview

Use this skill to complete the local Mi Home Automation Geek Edition login flow for `http://<gateway-ip>:8086/`. The login code is a short-lived authorization code shown in Xiaomi Home under the router's hub feature page.

## Tool Choice

- Use Browser Use for the local web page when it works.
- If the in-app browser shows `暂不兼容您的浏览器类型` or asks for Chrome / Edge, use Computer Use with Google Chrome for the web page.
- Use Computer Use for the Xiaomi Home app (`com.xiaomi.mihome`).
- Treat the login code as an authorization code. Retrieve and enter it only when the user explicitly asks to log in to this local Mi Home Geek Edition page.

## Workflow

1. Open the web login page:
   - Target URL: `http://<gateway-ip>:8086/`
   - Expected title: `米家自动化极客版`
   - Expected login view: `输入 6 位数字登录码` with an onscreen numeric keypad.

2. Open Xiaomi Home:
   - If Xiaomi Home is already on `<hub-device-name>`, continue from there.
   - Otherwise navigate to the `<room-name>` room and open the `<hub-device-name>` device card.
   - On the `<hub-device-name>` device page, verify the IP line shows `<gateway-ip>` when visible.

3. Retrieve the login code:
   - Click `澎湃智联`.
   - Click `中枢功能`.
   - In `自动化极客版`, read the six digits displayed under `登录码`.
   - Do not click `重新获取登录码` unless the current code is missing, expired, or the web page rejected it.

4. Enter the code on the web page:
   - Return to Chrome or the working browser tab at `http://<gateway-ip>:8086/`.
   - If any digits may already be present, click `删除` several times before entering the new code.
   - Click the onscreen keypad digits in order. The page normally auto-submits after the sixth digit.

5. Verify login:
   - URL should change to `http://<gateway-ip>:8086/#/`.
   - The app should show the main interface with items such as `自动化列表`, `设备列表`, `全局变量列表`, search, `恢复与备份`, and `创建自动化`.

## Recovery

- If the page was refreshed after retrieving the code, the code may be invalid. Return to Xiaomi Home `中枢功能`, click `重新获取登录码`, and enter the new code.
- If a wrong code was entered, retrieve a new login code before retrying; the page notes that each retry needs a fresh code.
- If Xiaomi Home opens somewhere else, use visible navigation rather than hardcoded coordinates: return to the home view, select the `<room-name>` room, open `<hub-device-name>`, then continue through `澎湃智联` and `中枢功能`.
- Prefer accessibility element names where available; use screen coordinates only when the UI exposes no reliable element label.
