# Claude Code CLI installation — macOS + Windows 11

Companion to `demo_venv_setup.md`. Install once per machine; then use
Claude Code inside any project's venv.

## Prerequisites

- Node.js 18+ required.
- Verify: `node --version` should print `v18.x` or newer.
- An Anthropic account (claude.ai or Anthropic Console). First `claude`
  run opens a browser tab for sign-in — use the account tied to the
  course access plan.

## macOS

Two paths. The native installer is smoother if you don't already
manage Node yourself; npm is the universal fallback.

### Native installer (preferred on macOS)

```bash
curl -fsSL https://claude.ai/install.sh | bash
claude --version
```

Update: re-run the install script, or use `claude update` from inside
a session.

### npm

```bash
npm install -g @anthropic-ai/claude-code
claude --version
```

Update: `npm update -g @anthropic-ai/claude-code`.

## Windows 11

npm is the recommended native path. WSL can also use the native
installer above as if it were Linux.

```powershell
npm install -g @anthropic-ai/claude-code
claude --version
```

Update: `npm update -g @anthropic-ai/claude-code`.

**If `claude --version` fails immediately after install:** close and
reopen your terminal. If you're inside VS Code, close *all* VS Code
windows and reopen. The new binary is on disk, but VS Code's integrated
terminal cached the environment at launch and doesn't see the updated
PATH until VS Code restarts. This bites Windows harder than macOS
because Windows caches process env more aggressively, but it can hit
macOS too.

## Gotchas

- **Package name matters.** The correct package is
  `@anthropic-ai/claude-code` (scoped). Don't install an unscoped or
  differently-named `claude` package — it's an unrelated project and
  installs silently while doing nothing useful. Wrong install →
  `claude --version` fails with confusing errors → 20 minutes lost.
- **Node version.** If `claude --version` runs but crashes on first
  actual use with a "Cannot find module" error or similar, your Node
  is probably too old. Upgrade to 18+.
- **`sudo` on macOS.** A bare `npm install -g` may complain about
  permissions if you're on system Node. The fix is a Node version
  manager (`nvm`, `fnm`, `volta`) — do NOT `sudo npm install -g`. It
  works, but it corrupts your global module permissions in a way
  you'll pay for later.
- **PATH after install.** If `claude --version` says "command not
  found" after a clean install and reopening the terminal didn't fix
  it: run `npm prefix -g` to see where npm put the binary. On
  macOS/Linux, add `<that path>/bin` to your shell profile. On
  Windows, that path itself goes on `%PATH%` — typically already
  configured by the Node installer, but managed laptops sometimes
  strip it.
- **Browser sign-in loop.** If the first `claude` run opens a browser
  tab that never completes the sign-in handoff, authenticate with an
  API key instead: set the `ANTHROPIC_API_KEY` environment variable
  before launching `claude`, which skips the browser flow entirely.
- **Managed/locked-down browsers.** If your default browser blocks the
  OAuth handoff (common with locked-down or education-managed
  profiles), switch your default browser to a standard Chrome/Edge/
  Firefox profile signed in with the account tied to your course
  access plan, then retry `claude`.

## Verify

```bash
claude --version   # should print a version number
claude             # in any project directory, starts a session
```

First run triggers sign-in. After that, `claude` reads `CLAUDE.md` (if
present) at session start and drops you into an interactive prompt.
