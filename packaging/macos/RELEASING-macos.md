# 打包为 macOS .app 并签名分发（Developer ID 路线）

把 MacBroom 的本地 Web UI 装进原生 .app（WKWebView 壳），通过 **Developer ID 直签 + 公证**
在 Mac App Store 之外分发（官网 / GitHub Release 下载 .dmg）。这是 Mac 清理工具的通行做法——
不进商店，从而保住「完全磁盘访问、清其它 App 缓存/残留」的核心能力（沙盒会阉割这些）。

- **Bundle ID**：`com.mythkiven.MacBroom`
- **形态**：py2app 打包 Python + PyObjC 原生窗口（`macbroom/desktop.py`），内部跑现有 server + Web UI
- **图标**：`MacBroom.icns`（由 `make_icns.py` 从方形源图生成）

---

## 一、一次性准备（你来做）

1. 加入 **Apple Developer Program**（$99/年）。
2. 在钥匙串/开发者后台创建 **Developer ID Application** 证书（**不是** App Store 那套）：
   - Xcode → Settings → Accounts → Manage Certificates → ＋ → **Developer ID Application**；
   - 或开发者后台 Certificates 页创建后下载导入钥匙串。
3. 在开发者后台为 `com.mythkiven.MacBroom` 创建 App ID（Developer ID 分发其实不强制预注册 App ID，但建议登记占位）。
4. 存一份公证凭证给 `notarytool`（用 App 专用密码或 API Key）：
   ```bash
   xcrun notarytool store-credentials macbroom-notary \
     --apple-id "you@example.com" --team-id "TEAMID" --password "app-专用密码"
   ```
   这里的 `macbroom-notary` 即下文 `NOTARY_PROFILE`。

查看本机可用签名身份：
```bash
security find-identity -v -p codesigning
```

---

## 二、构建

未签名（本机测试，双击即跑）：
```bash
bash packaging/macos/build.sh
# 产物：packaging/macos/dist/MacBroom.app
```

签名 + 公证 + 出 dmg（分发用）：
```bash
DEVELOPER_ID_APP="Developer ID Application: Your Name (TEAMID)" \
NOTARY_PROFILE="macbroom-notary" \
bash packaging/macos/build.sh
# 产物：dist/MacBroom.app（已签名公证）+ dist/MacBroom.dmg（已订书）
```

脚本会在 `packaging/macos/.build-venv` 建隔离环境，装 `py2app` + `pyobjc`，
非 editable 安装本仓库后用 py2app 打包。`PYTHON=python3.13` 可指定解释器。

---

## 三、验证

```bash
codesign -dv --verbose=4 dist/MacBroom.app          # 看签名与 hardened runtime
codesign --verify --strict --verbose=2 dist/MacBroom.app
spctl -a -vvv -t install dist/MacBroom.app          # Gatekeeper 评估（公证后应 accepted）
xcrun stapler validate dist/MacBroom.dmg            # 订书校验
```

不签名时可直接本机跑验证（无需 Gatekeeper）：
```bash
open dist/MacBroom.app                               # 开原生窗口
# 或命令行看输出：
./dist/MacBroom.app/Contents/MacOS/MacBroom
```

---

## 四、更新图标

替换方形源图后重新生成（脚本会套 macOS 圆角/留白/轻阴影并转多尺寸 .icns）：
```bash
python packaging/macos/make_icns.py <source.png> packaging/macos/MacBroom.icns
```

---

## 五、已知约束 / 注意

- **完全磁盘访问（FDA）**：即便 Developer ID 签名，FDA 也必须用户手动在
  「系统设置 › 隐私与安全性 › 完全磁盘访问」授予，无法自动化。首启可引导（`doctor.py` 已有检测逻辑）。
- **hardened runtime entitlements**：`entitlements.plist` 放行了嵌入 Python runtime 所需的
  `allow-jit` / `allow-unsigned-executable-memory` / `disable-library-validation`；公证若因此被拒需复核。
- **`--deep` 签名**：当前脚本用 `--deep` 一次性签整包，对 py2app 简单结构可用；若公证报某个嵌套
  dylib/framework 未签名，改为由内而外逐个签再签外层。
- **端口**：原生壳用系统动态端口（`bind 0`），不与 CLI 版固定端口 37700 冲突。
- **入口脚本命名**：py2app 入口是 `macbroom_app.py`，**不可**改名为 `MacBroom.py`——
  在大小写不敏感文件系统上会与包 `macbroom` 同名冲突，导致整个包被覆盖、web 资源丢失。
