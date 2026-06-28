"""py2app 配置：把 MacBroom 打成原生 .app（Developer ID 直签分发）。

不要直接 `python setup_app.py`；请走同目录 build.sh 的隔离 venv 构建。
"""

import os

from setuptools import setup

from macbroom import __version__

HERE = os.path.dirname(os.path.abspath(__file__))

APP = ["macbroom_app.py"]

OPTIONS = {
    "argv_emulation": False,
    "packages": ["macbroom"],
    "includes": ["macbroom.desktop"],
    # 测试扩展与 setuptools 测试树不应打进分发包（公证也会拒未签名的 _test*.so）
    "excludes": [
        "test", "tests", "unittest", "doctest", "setuptools.tests",
        "_testcapi", "_testlimitedcapi", "_testbuffer", "_testimportmultiple",
        "_testmultiphase", "_testinternalcapi",
    ],
    "plist": {
        "CFBundleIdentifier": "com.mythkiven.MacBroom",
        "CFBundleName": "MacBroom",
        "CFBundleDisplayName": "MacBroom",
        "CFBundleShortVersionString": __version__,
        "CFBundleVersion": __version__,
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.utilities",
        "NSHumanReadableCopyright": "MIT License · github.com/mythkiven/MacBroom",
        # 仅放行本机回环，WKWebView 才能加载 http://127.0.0.1
        "NSAppTransportSecurity": {"NSAllowsLocalNetworking": True},
    },
}

_icon = os.path.join(HERE, "MacBroom.icns")
if os.path.exists(_icon):
    OPTIONS["iconfile"] = _icon

setup(
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
