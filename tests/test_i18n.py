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
        keep_items = [it for it in items if "keep" in it.note.lower()]
        self.assertEqual(len(keep_items), 1)
        for it in items:
            self.assertEqual(it.risk, "risky")
        # 「保留项」必须不可勾选删除，其余副本可删
        self.assertFalse(keep_items[0].deletable)
        self.assertEqual(sum(1 for it in items if it.deletable), 2)


class FsutilTests(unittest.TestCase):
    def test_cachedir_marker_detected(self):
        import os
        from macbroom.core.fsutil import is_marked_cache_dir

        with TemporaryDirectory() as tmp:
            self.assertFalse(is_marked_cache_dir(tmp))
            with open(os.path.join(tmp, "CACHEDIR.TAG"), "w", encoding="utf-8") as f:
                f.write("Signature: 8a477f597d28d172789f4688f9ccdfda")
            self.assertTrue(is_marked_cache_dir(tmp))


class AppIndexTests(unittest.TestCase):
    def test_installed_bundle_matches_exact_bundle_id_only(self):
        import macbroom.scanners.appindex as appindex

        appindex._cache = {
            "bundle_to_name": {"com.example.myapp": "MyApp"},
            "names": {"myapp"},
        }
        try:
            self.assertTrue(appindex.is_installed_bundle("com.example.myapp"))
            self.assertTrue(appindex.is_installed_bundle("COM.Example.MyApp"))  # 大小写无关
            # 末段与 App 名相同但 bundle id 不同：不得误判为已安装（否则残留会被漏报）
            self.assertFalse(appindex.is_installed_bundle("com.other.myapp"))
        finally:
            appindex._cache = None


class TrashTests(unittest.TestCase):
    def test_trash_passes_paths_as_argv_without_interpolation(self):
        import macbroom.core.trash as trash

        captured = {}

        class _Proc:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_run(argv, *args, **kwargs):
            captured["argv"] = argv
            return _Proc()

        # 含双引号、单引号、AppleScript 注入意图的恶意文件名
        evil = '/tmp/x" & (do shell script "touch /tmp/pwned") & ".cache'
        with mock.patch.object(trash.subprocess, "run", fake_run):
            ok, err = trash._osascript_trash([evil])

        self.assertTrue(ok)
        argv = captured["argv"]
        # 恶意路径必须作为独立 argv 参数原样传入，绝不拼进脚本字符串
        self.assertIn(evil, argv)
        script = argv[2]  # ["osascript", "-e", <script>, *paths]
        self.assertNotIn(evil, script)
        self.assertNotIn("do shell script", script)

    def test_failed_trash_never_returns_destructive_command(self):
        """删除失败时坚持「不强删」：不得返回 rm -rf 等不可逆命令，只给手动引导。"""
        import os
        import macbroom.core.trash as trash

        evil = "/tmp/macbroom-test/a b'c\"d"
        os.makedirs(os.path.dirname(evil), exist_ok=True)
        with open(evil, "w", encoding="utf-8") as f:
            f.write("x")
        try:
            with mock.patch.object(trash, "_osascript_trash",
                                   lambda paths: (False, "not allowed")):
                with mock.patch.object(trash.os, "access", lambda *a, **k: False):
                    r = trash.trash_path(evil)
            self.assertFalse(r["ok"])
            # 绝不生成 rm / rm -rf 这类不可逆命令
            self.assertEqual(r.get("command", ""), "")
            self.assertNotIn("rm -rf", str(r))
            self.assertNotIn("rm ", str(r.get("command", "")))
            # 父目录不可写时标记需管理员权限，并给出手动引导
            self.assertTrue(r["needs_sudo"])
            self.assertTrue(r.get("hint"))
        finally:
            os.remove(evil)


class DoctorTests(unittest.TestCase):
    def test_doctor_returns_expected_checks(self):
        from macbroom.doctor import run_checks

        checks = run_checks(port=37700)
        ids = {c["id"] for c in checks}
        self.assertEqual(ids, {"python", "macos", "full_disk_access", "log_dir", "port"})


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


class ProtectedPathTests(unittest.TestCase):
    def test_blocks_system_and_secret_prefixes(self):
        import os
        from macbroom.core.fsutil import HOME, is_protected

        self.assertTrue(is_protected("/System/Library/Foo"))
        self.assertTrue(is_protected("/usr/local/bin/x"))
        self.assertTrue(is_protected("/Applications/Safari.app"))
        # /etc、/var 会被 realpath 解析到 /private 下，仍应命中
        self.assertTrue(is_protected("/private/var/db/anything"))
        self.assertTrue(is_protected(os.path.join(HOME, ".ssh", "id_rsa")))
        self.assertTrue(is_protected(os.path.join(HOME, "Library", "Keychains", "x")))

    def test_allows_ordinary_user_paths(self):
        import os
        from macbroom.core.fsutil import HOME, is_protected

        # 普通可清理路径（用户缓存目录下的某项）不应被保护拦截。
        self.assertFalse(is_protected(os.path.join(HOME, "Library", "Caches", "com.macbroom.test-xyz")))
        self.assertFalse(is_protected(os.path.join(HOME, "Downloads", "big.zip")))


class LoginItemsExecutableTests(unittest.TestCase):
    def test_relative_bundleprogram_not_flagged_as_orphan(self):
        from macbroom.scanners.login_items import _executable_exists

        # BundleProgram 常是相对 bundle 的路径，无法定位 → 不得判为孤儿（不删）
        self.assertTrue(_executable_exists("Contents/MacOS/Helper"))
        # 系统前缀始终存在
        self.assertTrue(_executable_exists("/usr/bin/true"))
        # 绝对且不存在的路径 → 判为孤儿
        self.assertFalse(_executable_exists("/Applications/NopeNope.app/Contents/MacOS/Nope"))


class AppIndexRecursiveTests(unittest.TestCase):
    def test_discovers_apps_in_subdirectories(self):
        import os
        import macbroom.scanners.appindex as appindex

        def make_app(root, rel, bundle_id):
            app = os.path.join(root, rel)
            os.makedirs(os.path.join(app, "Contents"))
            import plistlib
            with open(os.path.join(app, "Contents", "Info.plist"), "wb") as f:
                plistlib.dump({"CFBundleIdentifier": bundle_id}, f)

        with TemporaryDirectory() as tmp:
            make_app(tmp, "Top.app", "com.example.top")
            make_app(tmp, "Setapp/Nested.app", "com.example.nested")
            with mock.patch.object(appindex, "APP_DIRS", [tmp]):
                appindex._cache = None
                try:
                    self.assertTrue(appindex.is_installed_bundle("com.example.top"))
                    self.assertTrue(appindex.is_installed_bundle("com.example.nested"))
                finally:
                    appindex._cache = None


class ServerValidationTests(unittest.TestCase):
    def test_valid_ids_accepts_only_string_lists(self):
        from macbroom.core.server import valid_ids

        self.assertTrue(valid_ids([]))
        self.assertTrue(valid_ids(["a", "b"]))
        self.assertFalse(valid_ids("abc"))      # 字符串会被按字符迭代
        self.assertFalse(valid_ids([1, 2]))     # 非字符串元素
        self.assertFalse(valid_ids({"a": 1}))   # dict
        self.assertFalse(valid_ids(None))


if __name__ == "__main__":
    import unittest as _ut
    _ut.main()
