"""py2app 后处理：把 Python 前缀里缺失的 @rpath 依赖 dylib 补进 .app。

conda / 部分 Homebrew Python 的扩展模块链接 @rpath/libffi.8.dylib 等，
py2app 不会自动收集，导致启动即报 Launch error（ctypes 加载失败）。
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

_MACHO_SUFFIXES = {".so", ".dylib"}
_RPATH_DEP = re.compile(r"^\s+(@rpath/\S+)")


def _mach_o_files(app_root: Path) -> list[Path]:
    out: list[Path] = []
    for path in app_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in _MACHO_SUFFIXES or path.parent.name == "MacOS":
            try:
                info = subprocess.run(
                    ["file", "-b", str(path)],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout
            except (subprocess.CalledProcessError, OSError):
                continue
            if "Mach-O" in info:
                out.append(path)
    return out


def _rpath_deps(macho: Path) -> list[str]:
    try:
        lines = subprocess.check_output(
            ["otool", "-L", str(macho)], text=True, stderr=subprocess.DEVNULL
        ).splitlines()
    except (subprocess.CalledProcessError, OSError):
        return []
    deps: list[str] = []
    for line in lines[1:]:
        m = _RPATH_DEP.match(line)
        if m:
            deps.append(m.group(1).replace("@rpath/", ""))
    return deps


def _resolve_in_bundle(app_root: Path, name: str) -> Path | None:
    contents = app_root / "Contents"
    for base in (
        contents / "Frameworks",
        contents / "Resources" / "lib",
        contents / "Resources" / "lib" / "python3.13",
        contents,
    ):
        candidate = base / name
        if candidate.is_file():
            return candidate
    return None


def bundle(app: Path, prefix: Path) -> list[str]:
    src_lib = prefix / "lib"
    frameworks = app / "Contents" / "Frameworks"
    res_lib = app / "Contents" / "Resources" / "lib"
    frameworks.mkdir(parents=True, exist_ok=True)
    res_lib.mkdir(parents=True, exist_ok=True)

    needed: set[str] = set()
    for macho in _mach_o_files(app):
        for dep in _rpath_deps(macho):
            if _resolve_in_bundle(app, dep) is None:
                needed.add(dep)

    copied: list[str] = []
    for name in sorted(needed):
        src = src_lib / name
        if not src.is_file():
            print(f":: 警告：bundle 需要 {name}，但在 {src_lib} 未找到", file=sys.stderr)
            continue
        for dest_dir in (frameworks, res_lib):
            dest = dest_dir / name
            if not dest.exists() or src.stat().st_mtime > dest.stat().st_mtime:
                shutil.copy2(src, dest)
        copied.append(name)
        print(f"  + {name}")
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path, help=".app 路径")
    parser.add_argument(
        "--prefix",
        type=Path,
        default=Path(sys.base_prefix),
        help="构建用 Python 的 sys.base_prefix（默认当前解释器）",
    )
    args = parser.parse_args()
    if not args.app.is_dir():
        parser.error(f"不是目录: {args.app}")
    copied = bundle(args.app.resolve(), args.prefix.resolve())
    if not copied:
        print("（无需补 dylib）")
    else:
        print(f"==> 已补 {len(copied)} 个 dylib")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
