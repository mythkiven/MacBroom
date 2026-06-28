<div align="center">

# 🧹 MacBroom

**Open-source macOS cleaner — free up disk space safely**
<br>**开源 macOS 清理工具 — 安全、可视化地释放磁盘空间**

An **open-source CleanMyMac alternative**: scan reclaimable space → group it by app → tick and clean. Deletions go to the Trash by default and can be restored. Local-only, zero-dependency, no telemetry.

> 一个 **开源的 CleanMyMac 替代品**：扫描可释放空间 → 按软件分组 → 勾选一键清理。默认移入废纸篓、可还原；纯本地、零依赖、不联网。**完整中文文档见 [README.zh.md](./README.zh.md)。**

[简体中文](./README.zh.md) · English

[![CI](https://github.com/mythkiven/MacBroom/actions/workflows/ci.yml/badge.svg)](https://github.com/mythkiven/MacBroom/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
![Platform: macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)

</div>

![MacBroom main window](docs/screenshot.png)

---

## ✨ Features

- **Local only · zero dependencies**: pure Python 3 standard library, no network calls, no telemetry.
- **Safety first**: files go to the macOS Trash (not `rm`), restorable from Trash; system-critical paths (`/System`, Keychains, SSH keys, …) are hard-blocked.
- **Risk grading**: every item is tagged `safe / moderate / risky`. Risky items (personal data, irreversible actions) are **hidden by default** until you tick "Show risky items".
- **Explainable leftovers**: each suspected uninstall leftover shows *why* it was flagged (bundle id with no matching app) and can be **expanded to inspect the actual files** before you decide.
- **Confirm before delete (dry-run)**: the dialog lists every selected item with its path and reason, total count and reclaimable size; large totals (>10 GB) or risky selections get an extra warning.
- **Sort & drill-down**: sort results by size or name, expand any group or item to see what is inside.
- **Audit log**: every scan and deletion is written to `~/Library/Logs/MacBroom/macbroom.log` (override the directory with `MACBROOM_LOG_DIR`).
- **Grouped by app**: caches and the like are grouped per app; your selection is preserved across rescans.
- **Customizable**: toggle each scan category on/off; a persistent **exclusion list** for false positives; long scans are **cancelable**.
- **iCloud-aware**: detects iCloud-synced folders to avoid breaking cross-device sync.
- **Respects `CACHEDIR.TAG`**: standard cache markers are recognized so the right directories are treated as cache.
- **Covers popular apps**: beyond browser/dev caches, also Slack, Discord, VS Code, Microsoft Teams, Spotify, Steam, Telegram, Minecraft.
- **Login items check**: finds orphaned launch-at-login items pointing to deleted programs (the "background items" macOS warns about). User-level entries move to the Trash; system-level ones come with a `sudo` command for you to run yourself (never auto-elevated).
- **CLI / scripting friendly**: `macbroom scan --json` prints a report right in the terminal for automation and CI.
- **`macbroom doctor`**: pre-flight checks for Python, Full Disk Access, log directory, and port availability before you scan.
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
| 🚀 **Login / Startup Items** | Launch-at-login LaunchAgents / LaunchDaemons, focusing on orphaned entries pointing to deleted programs |
| ✨ **Other Cleanup** | Diagnostic reports, iOS device backups, Homebrew leftovers, Docker images, Time Machine local snapshots, scattered `node_modules`, mail attachment caches, old downloads |

## 📊 How MacBroom compares

A focused comparison on what MacBroom is built for: safe, open-source, scriptable everyday cleanup.

|  | **MacBroom** | CleanMyMac | Pearcleaner | Mole |
|---|:---:|:---:|:---:|:---:|
| **Price** | Free | $39.95/yr | Free | Free |
| **Open source** | ✅ MIT | ❌ | ✅ Fair-code | ✅ MIT |
| **Runtime deps** | ✅ Python 3 stdlib · zero deps | Closed | Native | Native |
| **Install** | ✅ `pip`/`pipx` one-liner | DMG | DMG / brew | brew |
| **Interface** | Local web UI + CLI | Native app | Native app | Command line |
| **CLI / scriptable (`--json`)** | ✅ | ❌ | ❌ | ✅ |
| **Trash by default** | ✅ | ✅ | ✅ | ➖ |
| **Risk grading + risky hidden** | ✅ | ➖ | ➖ | ❌ |
| **Dry-run per-item confirm** | ✅ | ➖ | ✅ | ➖ |
| **Audit log** | ✅ | ❌ | ➖ | ❌ |
| **iCloud-sync aware** | ✅ | ➖ | ❌ | ❌ |
| **Persistent exclusion list** | ✅ | ➖ | ✅ | ❌ |
| **App cache cleanup** | ✅ | ✅ | ➖ | ✅ |
| **Uninstall leftovers (explainable)** | ✅ exact bundle-id | ✅ | ✅ focused | ✅ |
| **Large / duplicate files** | ✅ / ✅ | ✅ / ✅ | ❌ | ❌ |
| **Dev clutter (Xcode/iOS/Android/HarmonyOS)** | ✅ incl. HarmonyOS | ➖ Xcode | ❌ | ➖ |
| **Login / orphaned startup items** | ✅ | ✅ | ❌ | ➖ |

> ✅ yes · ➖ partial/limited · ❌ no. MacBroom is for people who want an open-source, zero-dependency cleaner that installs with one `pip` line, is safe by default, and can be scripted into CI.

## 💡 Why MacBroom? — built from real cleaner failures

We collected **a large amount of user feedback on pain points with rival cleaners** and designed MacBroom to *not* repeat their most painful, real, reported accidents:

| Real-world failure reported in other cleaners | How MacBroom avoids it by design |
|---|---|
| A cleaner deleted a user's **entire Chrome profile** — logins and bookmarks gone | We only target precise `Default/Cache` & `Code Cache` dirs — **never** the profile directory |
| **Apple Notes / Claude Code CLI deleted** as "leftovers" (matched by name, not identity) | Leftover detection matches **bundle id exactly**; each flagged item shows *why*, with an expandable file list to review before deleting |
| **Shell history wiped** (`~/.zsh_history`) as "junk" | We never scan or touch shell history |
| Cleanup **broke iCloud sync** (Desktop/Documents) | We **detect iCloud-synced paths**, mark them risky and hide them by default |
| Uninstall **misidentified unrelated files** (`~/Public`, printer configs, another app's data) | Bundle-id matching + risk grading + a persistent **exclusion list** to permanently skip false positives |
| **Wrong / negative free-space numbers** (sparse images counted by logical size) | Real on-disk usage via `st_blocks`, so sparse VM/disk images are not over-counted |
| **Untranslated or mistranslated UI** | Native-quality **English and Chinese** from day one, not machine-translated strings |
| **Simulator cleanup throwing errors** | iOS/Xcode simulators are cleaned through the official `xcrun simctl` interface, not by blindly deleting paths |
| **Long scans froze the app** with no way to stop | Every scan is **cancelable** mid-run |
| Orphaned **login items** left erroring in System Settings after uninstalls | Dedicated **Login Items scanner** flags startup entries pointing to deleted programs |

In short: **other cleaners delete first and apologize later. MacBroom is designed to be un-dangerous** — Trash-by-default, risky items hidden, dry-run confirmation that lists exactly what goes, and an audit log of everything it does.

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

### Option C: command-line report (headless / scripting)

```bash
macbroom doctor                                # pre-flight: Python, FDA, port, log dir
macbroom scan                                  # print per-category summary and total
macbroom scan --json                           # JSON output for scripts / CI
macbroom scan --lang en                        # force English output
macbroom scan --category caches,login_items    # scan specific categories only
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
