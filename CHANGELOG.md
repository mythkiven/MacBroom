# Changelog

All notable user-facing changes to MacBroom are listed here.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Fixed

- **Trash deletion security**: file paths are passed to AppleScript via `argv` instead of string interpolation, so names containing `"` no longer break deletion or pose an injection risk.
- **Web UI delete errors**: failed delete requests (CSRF, HTTP errors, malformed responses) now show a toast instead of failing silently.
- Manual fallback `rm` commands use proper shell quoting (`shlex.quote`).
- Delete API returns `400` for malformed `Content-Length` headers instead of `500`.

### Changed

- README (EN/ZH): login-items wording now matches behavior (user-level → Trash; system-level → manual `sudo` command).
- Internal maintainer planning docs removed from the public repository (kept locally only).

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

[Unreleased]: https://github.com/mythkiven/MacBroom/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/mythkiven/MacBroom/releases/tag/v1.1.0
[1.0.0]: https://github.com/mythkiven/MacBroom/releases/tag/v1.0.0
