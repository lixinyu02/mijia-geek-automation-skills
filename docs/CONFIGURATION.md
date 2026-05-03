# Configuration

The public skills use placeholders instead of private home details.

Recommended local values:

```bash
export MIJIA_GEEK_URL="http://<gateway-ip>:8086/"
export MIJIA_HOME_ROOM="<room-name>"
export MIJIA_HUB_DEVICE="<hub-device-name>"
```

## Chrome Requirement

For the bundled export script, Chrome must allow AppleScript JavaScript execution:

```text
View / 显示 -> Developer / 开发者 -> Allow JavaScript from Apple Events / 允许 Apple 事件中的 JavaScript
```

If this path is unreliable, use a browser session with a debugging context and run the same page-context JavaScript there. The important part is that the code runs in the page's main context, where `window.editor` is available.

## Login Code

The 6-digit login code is short-lived. Treat it as an authorization code:

- retrieve it only for the intended local Geek Edition page,
- do not store it,
- do not print it into logs,
- refresh the code if the page was reloaded after retrieval.

