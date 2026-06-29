# Changelog

All notable user-facing changes to MacBroom are listed here.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [1.1.2] - 2026-06-29

### Fixed

- **Web UI scan progress**: category-level progress bar with indeterminate animation for slow scans (e.g. duplicates) that have no real-time percentage.
- **Web UI active tab after scan**: rescan no longer leaves the current tab blank until you switch away and back (`activateTab` after panel rebuild).
- **macOS .app launch**: bundle missing `@rpath` dylibs (`libffi.8.dylib`, OpenSSL, zlib, etc.) that caused py2app “Launch error” on startup; `bundle_dylibs.py` runs before codesign.

### Changed

- `packaging/macos/build.sh`: post-py2app dylib bundling + startup smoke test; `RELEASING-macos.md` documents launch-error debugging.

## [1.1.1] - 2026-06-28

### Fixed

- **Trash deletion security**: file paths are passed to AppleScript via `argv` instead of string interpolation, so names containing `"` no longer break deletion or pose an injection risk.
- **Delete API validation**: rejects non-list or non-string `ids` in the delete payload (`400 invalid ids`).
- **Protected paths**: expanded hard blocks for `/Applications`, `/private/etc`, and `/private/var` (via `realpath`), plus existing system and secret prefixes.
- **Trash failure fallback**: no longer suggests `rm -rf` / `sudo rm -rf`; shows a manual Finder hint instead (aligned with “Trash-by-default, not dangerous”).
- **Login items**: relative `BundleProgram` paths (e.g. `Contents/MacOS/App`) are no longer mis-flagged as orphaned startup items.
- **App index**: discovers `.app` bundles in nested folders (e.g. Setapp / vendor subdirectories), reducing false leftover reports.
- **Duplicate files**: the “keep newest” copy in each group is no longer selectable for deletion (`deletable: false` in UI).
- **Web UI delete errors**: failed delete requests (CSRF, HTTP errors, malformed responses) now show a toast instead of failing silently.
- Delete API returns `400` for malformed `Content-Length` headers instead of `500`.
- Scan / categories API calls check `res.ok` before parsing JSON.

### Changed

- README (EN/ZH): competitor narrative uses “user feedback on pain points” (no mention of issue mining); removed the Telemetry comparison row (we do not track that dimension).
- README (EN/ZH): login-items wording matches behavior (user-level → Trash; system-level → manual `sudo` command).
- CLI warns when binding to a non-loopback host (LAN exposure risk).
- Repository SEO: GitHub homepage → PyPI; Discussions enabled; removed misleading `daisydisk` topic; added `docs/social-preview.png` (1280×640, upload manually under Settings → Social preview).

### Added

- Unit tests for protected paths, delete `ids` validation, login-item relative paths, nested app indexing, duplicate keep-item `deletable`, and safe trash fallback (19 tests total).

## [1.1.0] - 2026-06-28

### Added

- `macbroom doctor` — pre-flight checks for Python, macOS, Full Disk Access, audit log directory, and Web UI port (`--json`, `--lang`).
- **App leftovers**: bundle-id exact matching; per-item `reason` and expandable `children`; confirmation dialog lists paths and reasons; skips `Public` / `Printers`.
- **Caches**: `CACHEDIR.TAG` / `CACHEDIR.txt` recognition; Telegram and Minecraft cache paths.
- **Web UI**: sort results by size or name; row drill-down; richer confirm-before-delete list.
- CLI `--version`; PyPI publishing via GitHub Actions (OIDC Trusted Publisher).
- `docs/screenshot.png` in README; expanded “Why MacBroom” comparison table.

### Changed

- `pipx install macbroom` / `pip install macbroom` is the recommended install method after PyPI release.

## [1.0.0] - 2026-06-28

### Added

- Core scanners: app caches, uninstall leftovers, large files, dev clutter (iOS/Android/HarmonyOS), duplicate files, login/startup items, and miscellaneous cleanup.
- Local Web UI and CLI (`macbroom scan`, `macbroom scan --json`).
- Safety model: Trash-by-default, protected-path blocks, risk grading (risky items hidden by default), dry-run confirmation, audit log, iCloud awareness, cancelable scans, exclusion list.
- Pure Python 3 standard library — zero runtime dependencies.

[Unreleased]: https://github.com/mythkiven/MacBroom/compare/v1.1.1...HEAD
[1.1.1]: https://github.com/mythkiven/MacBroom/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/mythkiven/MacBroom/releases/tag/v1.1.0
[1.0.0]: https://github.com/mythkiven/MacBroom/releases/tag/v1.0.0
