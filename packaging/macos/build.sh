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

# 剔除 py2app 偶发带入的测试二进制与 setuptools 测试目录
find "$APP" -type f -name '_test*.so' -delete 2>/dev/null || true
rm -rf "$APP/Contents/Resources/lib/python3.13/setuptools/tests" 2>/dev/null || true

sign_macos_app() {
  local app="$1" identity="$2" ents="$3"
  echo "  → 签名嵌套 .so / .dylib"
  while IFS= read -r -d '' f; do
    codesign --force --options runtime --timestamp --sign "$identity" "$f"
  done < <(find "$app" -type f \( -name '*.so' -o -name '*.dylib' \) -print0)

  echo "  → 签名 Mach-O 可执行文件"
  while IFS= read -r -d '' f; do
  if file -b "$f" 2>/dev/null | grep -q Mach-O; then
    if [[ "$f" == *"/MacOS/"* ]]; then
      codesign --force --options runtime --timestamp \
        --entitlements "$ents" --sign "$identity" "$f"
    else
      codesign --force --options runtime --timestamp --sign "$identity" "$f"
    fi
  fi
  done < <(find "$app" -type f -perm +111 -print0)

  echo "  → 签名 .app 包"
  codesign --force --options runtime --timestamp \
    --entitlements "$ents" --sign "$identity" "$app"
}

if [[ -n "${DEVELOPER_ID_APP:-}" ]]; then
  echo "==> codesign（逐文件签名，满足公证要求）"
  sign_macos_app "$APP" "$DEVELOPER_ID_APP" entitlements.plist
  codesign --verify --strict --verbose=2 "$APP"

  echo "==> 打 dmg"
  rm -f dist/MacBroom.dmg
  hdiutil create -volname MacBroom -srcfolder "$APP" -ov -format UDZO dist/MacBroom.dmg
  codesign --force --sign "$DEVELOPER_ID_APP" dist/MacBroom.dmg

  if [[ -n "${NOTARY_PROFILE:-}" ]]; then
    echo "==> 公证 + 订书"
    SUBMIT_LOG="$(mktemp)"
    if ! xcrun notarytool submit dist/MacBroom.dmg \
        --keychain-profile "$NOTARY_PROFILE" --wait 2>&1 | tee "$SUBMIT_LOG"; then
      echo ":: 公证失败，见上方输出"
      exit 1
    fi
    if grep -q "status: Invalid" "$SUBMIT_LOG"; then
      SUB_ID="$(grep -oE 'id: [0-9a-f-]{36}' "$SUBMIT_LOG" | head -1 | cut -d' ' -f2)"
      echo ":: 公证被拒 (Invalid)，拉取日志："
      xcrun notarytool log "$SUB_ID" --keychain-profile "$NOTARY_PROFILE" 2>&1 | head -80
      exit 1
    fi
    xcrun stapler staple dist/MacBroom.dmg
    xcrun stapler staple "$APP"
    echo "==> Gatekeeper 评估"
    spctl -a -vvv -t install dist/MacBroom.dmg 2>&1 | tail -3 || true
  else
    echo "（跳过公证：未设 NOTARY_PROFILE）"
  fi
else
  echo "（跳过签名/公证/dmg：未设 DEVELOPER_ID_APP；当前 .app 未签名，仅供本机测试）"
fi

echo "==> 完成"
