# 贡献指南 / Contributing

感谢你愿意为 MacBroom 做贡献！

## 开发环境

MacBroom **仅依赖 Python 3 标准库**，无需安装任何第三方包。建议 Python 3.9+。

```bash
git clone <your-fork>
cd macbroom
python -m macbroom           # 本地启动，浏览器访问 http://127.0.0.1:37700
# 或可编辑安装后用 console 命令： pip install -e . && macbroom
```

## 运行测试

```bash
# 把审计日志隔离到临时目录，避免写到真实用户目录
MACBROOM_LOG_DIR=/tmp/macbroom-test python -m unittest discover -s tests -v

# 语法编译检查
python -m compileall macbroom
```

提交 PR 前请确保上述两步都通过；CI 会在 Linux（多版本 Python）与 macOS 上自动复跑。

## 新增一个扫描器

1. 在 `macbroom/scanners/` 下新建模块，暴露：
   - `CATEGORY: macbroom.core.model.Category`
   - `scan(lang: str = "zh") -> list[macbroom.core.model.ScanItem]`
2. 每个 `ScanItem` 必须显式设置 `risk`（`RISK_SAFE / RISK_MODERATE / RISK_RISKY`）。
3. 在 `macbroom/scanners/__init__.py` 的 `_MODULES` 登记。
4. 在 `macbroom/core/i18n.py` 同时补 `zh` 与 `en` 文案。

## 安全红线（务必遵守）

- 删除一律走废纸篓（`ACTION_TRASH`）或工具内部生成的固定命令（`ACTION_RUN`）；需要权限/有风险的标 `ACTION_MANUAL`，只展示命令、不替用户执行。
- 任何可能触达系统关键路径的逻辑，必须经过 `core/fsutil.is_protected` 校验。
- 个人数据、不可逆操作一律标 `RISK_RISKY`，默认不勾选。
- 自测时用 `MACBROOM_LOG_DIR` 指向 `/tmp`，绝不污染真实数据目录。

## 代码风格

- 模块单一职责，按业务域拆分；避免无边界的 `utils` 堆放。
- 中文注释优先，只解释「为什么」，不复述「做了什么」。
