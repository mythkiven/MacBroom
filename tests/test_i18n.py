import unittest
from tempfile import TemporaryDirectory
from unittest import mock


class I18nTests(unittest.TestCase):
    def test_normalizes_browser_and_accept_language_values(self):
        from macbroom.core.i18n import normalize_lang

        self.assertEqual(normalize_lang("en-US"), "en")
        self.assertEqual(normalize_lang("zh-CN"), "zh")
        self.assertEqual(normalize_lang("zh-Hant-TW"), "zh")
        self.assertEqual(normalize_lang("fr-FR"), "en")
        self.assertEqual(normalize_lang(""), "en")

    def test_categories_can_be_localized_to_english(self):
        from macbroom.scanners import categories

        by_key = {category.key: category for category in categories("en")}

        self.assertEqual(by_key["caches"].title, "App Caches")
        self.assertIn("rebuild", by_key["caches"].description.lower())

    def test_categories_default_to_chinese(self):
        from macbroom.scanners import categories

        by_key = {category.key: category for category in categories("zh-CN")}

        self.assertEqual(by_key["dev_clutter"].title, "开发残留")

    def test_dev_clutter_supports_ios_android_and_harmony(self):
        from macbroom.scanners import categories, scan_category
        import macbroom.scanners.ios_dev as dev_clutter

        by_key = {category.key: category for category in categories("en")}
        self.assertEqual(by_key["dev_clutter"].title, "Dev Clutter")

        with TemporaryDirectory() as tmp:
            ios = f"{tmp}/ios"
            android = f"{tmp}/android"
            harmony = f"{tmp}/harmony"
            for path in (ios, android, harmony):
                import os
                os.makedirs(path)
                with open(f"{path}/blob", "wb") as f:
                    f.write(b"x")

            original_safe_dirs = dev_clutter._SAFE_DIRS
            original_pattern_dirs = dev_clutter._PATTERN_DIRS
            original_scan_runtimes = dev_clutter._scan_runtimes
            original_scan_android_builds = dev_clutter._scan_android_project_builds
            try:
                from macbroom.core.model import RISK_SAFE
                dev_clutter._SAFE_DIRS = [
                    ("ios.derived_data.name", ios, "ios.derived_data.note", "group.ios_xcode", True, RISK_SAFE),
                    ("android.sdk_temp.name", android, "android.sdk_temp.note", "group.android", True, RISK_SAFE),
                    ("harmony.sdk_temp.name", harmony, "harmony.sdk_temp.note", "group.harmonyos", True, RISK_SAFE),
                ]
                dev_clutter._PATTERN_DIRS = []
                dev_clutter._scan_runtimes = lambda lang="en": []
                dev_clutter._scan_android_project_builds = lambda lang="en": []
                groups = {item.group for item in scan_category("dev_clutter", "en")}
            finally:
                dev_clutter._SAFE_DIRS = original_safe_dirs
                dev_clutter._PATTERN_DIRS = original_pattern_dirs
                dev_clutter._scan_runtimes = original_scan_runtimes
                dev_clutter._scan_android_project_builds = original_scan_android_builds

        self.assertIn("iOS / Xcode", groups)
        self.assertIn("Android", groups)
        self.assertIn("HarmonyOS", groups)

    def test_duplicates_category_registered_and_localized(self):
        from macbroom.scanners import categories

        by_key = {category.key: category for category in categories("en")}
        self.assertIn("duplicates", by_key)
        self.assertEqual(by_key["duplicates"].title, "Duplicate Files")

        by_key_zh = {category.key: category for category in categories("zh")}
        self.assertEqual(by_key_zh["duplicates"].title, "重复文件")


class RiskTests(unittest.TestCase):
    def test_scan_item_defaults_and_validates_risk(self):
        from macbroom.core.model import RISK_MODERATE, RISK_SAFE, ScanItem

        default_item = ScanItem(category="x", name="n")
        self.assertEqual(default_item.risk, RISK_MODERATE)

        safe_item = ScanItem(category="x", name="n", risk=RISK_SAFE)
        self.assertEqual(safe_item.risk, RISK_SAFE)

        bogus = ScanItem(category="x", name="n", risk="not-a-level")
        self.assertEqual(bogus.risk, RISK_MODERATE)

    def test_stable_id_is_deterministic_across_instances(self):
        from macbroom.core.model import ScanItem

        a = ScanItem(category="caches", name="A", path="/tmp/foo")
        b = ScanItem(category="caches", name="different", path="/tmp/foo")
        self.assertEqual(a.id, b.id)


class DuplicatesScannerTests(unittest.TestCase):
    def test_detects_identical_files_and_keeps_newest(self):
        import os
        from unittest import mock

        import macbroom.scanners.duplicates as dup

        with TemporaryDirectory() as tmp:
            payload = b"D" * (2 * 1024 * 1024)  # 2MB, 超过 1MB 阈值
            paths = [os.path.join(tmp, f"copy{i}.bin") for i in range(3)]
            for p in paths:
                with open(p, "wb") as f:
                    f.write(payload)
            # 制造不同的 mtime，确保「保留最新」逻辑可判定
            os.utime(paths[0], (1000, 1000))
            os.utime(paths[1], (2000, 2000))
            os.utime(paths[2], (3000, 3000))
            # 一个内容不同的文件，不应被判为重复
            with open(os.path.join(tmp, "unique.bin"), "wb") as f:
                f.write(b"U" * (2 * 1024 * 1024))

            with mock.patch.object(dup, "_ROOTS", [tmp]):
                items = dup.scan("en")

        self.assertEqual(len(items), 3)  # 仅 3 个重复副本，unique 不计入
        keep_notes = [it for it in items if "keep" in it.note.lower()]
        self.assertEqual(len(keep_notes), 1)
        for it in items:
            self.assertEqual(it.risk, "risky")


class AuditTests(unittest.TestCase):
    def test_audit_writes_to_overridable_dir(self):
        import json
        import os
        import importlib

        with TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"MACBROOM_LOG_DIR": tmp}):
                from macbroom.core import audit
                importlib.reload(audit)
                audit.record("scan", category="caches", count=3)
                with open(audit.log_path(), encoding="utf-8") as f:
                    line = json.loads(f.readline())
        self.assertEqual(line["event"], "scan")
        self.assertEqual(line["category"], "caches")


if __name__ == "__main__":
    import unittest as _ut
    _ut.main()
