<div align="center">

# 🧹 MacBroom

**Open-source macOS cleaner — free up disk space safely**

An **open-source CleanMyMac alternative**: scan reclaimable space → group it by app → tick and clean. Deletions go to the Trash by default and can be restored. Local-only, zero-dependency, no telemetry.

[简体中文](./README.md) · English

[![CI](https://github.com/mythkiven/MacBroom/actions/workflows/ci.yml/badge.svg)](https://github.com/mythkiven/MacBroom/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
![Platform: macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)

</div>

> 📸 **Screenshot placeholder**: drop a main-window screenshot and a demo GIF here (put them under `docs/` and reference them).
>
> ```markdown
> ![MacBroom main window](docs/screenshot.png)
> ![MacBroom demo](docs/demo.gif)
> ```

---

## ✨ Features

- **Local only · zero dependencies**: pure Python 3 standard library, no network calls, no telemetry.
- **Safety first**: files go to the macOS Trash (not `rm`), restorable from Trash; system-critical paths (`/System`, Keychains, SSH keys, …) are hard-blocked.
- **Risk grading**: every item is tagged `safe / moderate / risky`. Risky items (personal data, irreversible actions) are **hidden by default** until you tick "Show risky items".
- **Confirm before delete (dry-run)**: a dialog lists the total item count and reclaimable size; large totals (>10 GB) or risky selections get an extra warning.
- **Audit log**: every scan and deletion is written to `~/Library/Logs/MacBroom/macbroom.log` (override the directory with `MACBROOM_LOG_DIR`).
- **Grouped by app**: caches and the like are grouped per app; your selection is preserved across rescans.
- **No forced deletion**: items that can't be removed are listed with a copy-paste Terminal command for you to run.
- **Clean web UI**: collapsible groups, group-level select-all, live reclaimable-space totals.

## 🔍 What it detects

| Category | Description |
|---|---|
| 🧹 **App Caches** | Rebuildable caches grouped by app (incl. npm/pip/Gradle/CocoaPods/Homebrew dev caches and Chrome/Edge/Brave/Arc/Firefox browser caches) |
| 👻 **App Leftovers** | Support files, containers, logs and preferences likely left by uninstalled apps (heuristic; review first) |
| 🐘 **Large Files** | Single files larger than 100 MB — find space-hungry videos / images / archives |
| 🛠️ **Dev Clutter** | Build products, caches, simulators and SDK temp dirs for iOS/Xcode, Android/Android Studio, HarmonyOS/DevEco Studio |
| 🧬 **Duplicate Files** | Byte-for-byte identical files (size → partial hash → full SHA-256), keeping the newest copy per group |
| ✨ **Other Cleanup** | Diagnostic reports, iOS device backups, Homebrew leftovers, Docker images, Time Machine local snapshots, scattered `node_modules`, mail attachment caches, old downloads |

## 🚀 Usage

### Option A: pipx / pip (recommended)

```bash
pipx install macbroom      # or: pip install macbroom
macbroom                   # starts and opens the browser
```

### Option B: run from source (no install)

```bash
git clone https://github.com/mythkiven/MacBroom.git
cd MacBroom
./run.sh                   # or: python -m macbroom
```

The browser opens at `http://127.0.0.1:37700`. Click "Start Scan", then "Clean Selected".

```bash
macbroom --port 40000      # custom port
macbroom --no-open         # don't open the browser
```

## 🛡️ Security

See [SECURITY.md](./SECURITY.md) for the full security model and how to report vulnerabilities. In short: local-only, Trash-by-default, protected-path hard blocks, risk grading, audit log, loopback-only with Host validation + per-session CSRF token on the delete endpoint.

## 🖥️ Compatibility

- Python 3.9+ (standard library only).
- macOS 12 (Monterey) through 15 (Sequoia) / 26 (Tahoe). On older systems, any missing path or command (e.g. `simctl runtime`, `tmutil thinlocalsnapshots`) is skipped automatically without affecting other categories.

## 🤝 Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). MacBroom needs no third-party packages; run tests with:

```bash
MACBROOM_LOG_DIR=/tmp/macbroom-test python -m unittest discover -s tests -v
```

## 📄 License

[MIT](./LICENSE)
