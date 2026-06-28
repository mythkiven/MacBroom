#!/usr/bin/env bash
# 构建 MacBroom.app（py2app）→ 可选签名 / 公证 → 打 dmg。
#
# 证书与公证全部参数化：
#   DEVELOPER_ID_APP  形如 "Developer ID Application: Your Name (TEAMID)"
#   NOTARY_PROFILE    notarytool 钥匙串配置名（xcrun notarytool store-credentials 预存）
# 二者都不设时，只构建「未签名」.app，可在本机双击测试，但分发给他人会被 Gatekeeper 拦。
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(cd ../.. && pwd)"

# 本地签名配置（含 Team ID 等敏感信息，已 .gitignore，不会进 Git）
if [[ -f signing.local.env ]]; then
  # shellcheck disable=SC1091
  source signing.local.env
fi

VENV=".build-venv"
PYTHON="${PYTHON:-python3}"

echo "==> 准备隔离构建 venv"
"$PYTHON" -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install -U pip wheel >/dev/null
pip install -U py2app pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit
# 非 editable 安装：py2app 的 modulegraph 无法追踪 editable(.pth) 包，会漏收集 macbroom
pip install "$ROOT"

echo "==> py2app 打包"
rm -rf build dist
python setup_app.py py2app
# py2app 依 CFBundleName 命名为 MacBroom.app；个别版本按脚本名，做兼容重命名
[ -d dist/macbroom_app.app ] && mv dist/macbroom_app.app dist/MacBroom.app

APP="dist/MacBroom.app"
[ -d "$APP" ] || { echo "未找到 $APP"; exit 1; }
echo "==> 已生成 $APP"

if [[ -n "${DEVELOPER_ID_APP:-}" ]]; then
  echo "==> codesign（hardened runtime + entitlements）"
  codesign --force --deep --options runtime --timestamp \
    --entitlements entitlements.plist \
    --sign "$DEVELOPER_ID_APP" "$APP"
  codesign --verify --strict --verbose=2 "$APP"

  echo "==> 打 dmg"
  rm -f dist/MacBroom.dmg
  hdiutil create -volname MacBroom -srcfolder "$APP" -ov -format UDZO dist/MacBroom.dmg
  codesign --force --sign "$DEVELOPER_ID_APP" dist/MacBroom.dmg

  if [[ -n "${NOTARY_PROFILE:-}" ]]; then
    echo "==> 公证 + 订书"
    xcrun notarytool submit dist/MacBroom.dmg --keychain-profile "$NOTARY_PROFILE" --wait
    xcrun stapler staple dist/MacBroom.dmg
    xcrun stapler staple "$APP"
  else
    echo "（跳过公证：未设 NOTARY_PROFILE）"
  fi
else
  echo "（跳过签名/公证/dmg：未设 DEVELOPER_ID_APP；当前 .app 未签名，仅供本机测试）"
fi

echo "==> 完成"
