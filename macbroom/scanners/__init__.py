"""扫描器注册表。

每个扫描器模块需暴露：
- CATEGORY: core.model.Category
- scan() -> list[ScanItem]

新增扫描器只需在 _MODULES 里登记，无需改其它地方。
"""

from __future__ import annotations

import importlib
from typing import Callable

from macbroom.core.i18n import normalize_lang, tr
from macbroom.core.model import Category, ScanItem

_MODULES = [
    "macbroom.scanners.caches",
    "macbroom.scanners.app_leftovers",
    "macbroom.scanners.large_files",
    "macbroom.scanners.ios_dev",
    "macbroom.scanners.duplicates",
    "macbroom.scanners.login_items",
    "macbroom.scanners.system_extras",
]


def _load() -> dict[str, tuple[Category, Callable[[], list[ScanItem]]]]:
    registry: dict[str, tuple[Category, Callable[[], list[ScanItem]]]] = {}
    for mod_name in _MODULES:
        mod = importlib.import_module(mod_name)
        cat: Category = mod.CATEGORY
        registry[cat.key] = (cat, mod.scan)
    return registry


REGISTRY = _load()


def categories(lang: str = "zh") -> list[Category]:
    lang = normalize_lang(lang)
    localized: list[Category] = []
    for cat, _ in REGISTRY.values():
        localized.append(Category(
            key=cat.key,
            title=tr(lang, f"category.{cat.key}.title"),
            description=tr(lang, f"category.{cat.key}.description"),
            icon=cat.icon,
            danger=cat.danger,
        ))
    return localized


def scan_category(key: str, lang: str = "zh") -> list[ScanItem]:
    if key not in REGISTRY:
        return []
    _, fn = REGISTRY[key]
    try:
        return fn(normalize_lang(lang))
    except Exception as exc:  # 单个扫描器失败不应拖垮整体
        import traceback
        traceback.print_exc()
        from macbroom.core.model import ScanItem as _SI
        return [_SI(category=key, name=f"扫描出错：{exc}", action="manual",
                    note="该分类扫描时发生异常，可忽略", recommend=False)]
