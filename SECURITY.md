# 安全说明 / Security Policy

MacBroom 是一个会删除文件的工具，因此安全是第一优先级。本文说明它的安全模型，以及如何上报漏洞。

## 安全模型

- **纯本地、零遥测**：所有扫描与删除都在本机完成，不发起任何网络请求，不上传任何数据。
- **默认可还原**：普通文件类清理调用 macOS「废纸篓」（Finder `delete`），误删可「放回原处」，而非 `rm`。
- **受保护路径硬拦截**：`/System`、`/usr`、`/bin`、`/sbin`、`~/Library/Keychains`、`~/.ssh`、`~/.gnupg` 等在删除前被硬性拒绝（见 `core/fsutil.py` 的 `PROTECTED_PREFIXES`）。
- **风险分级 + 默认隐藏高风险项**：每一项标注 `safe / moderate / risky`，高风险项（个人数据、不可逆操作）默认不显示、默认不勾选。
- **不做不可逆的一键操作**：不提供「一键清空废纸篓」之类无法恢复的按钮。
- **删除前确认**：清理前弹窗列出总项数与预计释放空间，超大体积或含高风险项会额外警告。
- **接口防滥用**：
  - 服务默认仅监听 `127.0.0.1`。
  - 校验 `Host` 头，防 DNS rebinding（仅在绑定 loopback 时强制）。
  - 删除接口要求携带每次启动随机生成的 CSRF token；外部网页因 CORS 预检失败无法调用。
  - 删除接口只接受「本次扫描产出过的条目 id」，不能被当作任意路径删除后端。
- **可审计**：每次扫描与删除写入 `~/Library/Logs/MacBroom/macbroom.log`（可用环境变量 `MACBROOM_LOG_DIR` 覆盖目录）。

## 支持的版本

主分支（main）始终是受支持的版本。

## 上报漏洞

请通过 GitHub 的 **Security Advisories**（仓库 Security 标签页 → Report a vulnerability）私下上报，不要直接提公开 issue。我们会尽快响应并在修复后致谢。
