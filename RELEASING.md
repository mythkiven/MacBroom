# 发布流程（维护者）

MacBroom 通过 **PyPI Trusted Publisher（OIDC）** 自动发布：打 `vX.Y.Z` 标签即触发
`.github/workflows/release.yml` 完成「构建 → 校验 → 发 PyPI → 建 GitHub Release」，
**仓库里不存放任何 PyPI token**。

## 一、一次性配置（仅首次发布前做一次）

### 1. 在 PyPI 注册「待定可信发布者」（Pending Publisher）

包还没发布过，用 *pending* 方式预登记。登录 <https://pypi.org> → 账户 →
**Publishing** → *Add a new pending publisher*，填写：

| 字段 | 值 |
|------|-----|
| PyPI Project Name | `macbroom` |
| Owner | `mythkiven` |
| Repository name | `MacBroom` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

> 提交后，首次由该 workflow 触发的发布会自动「认领」`macbroom` 这个包名。
> 名字一旦被别人占用就用不了——尽早登记。

### 2.（可选，推荐）在 GitHub 配置 `pypi` 环境保护

仓库 → Settings → Environments → New environment → 命名 `pypi`，
可加「Required reviewers」或限制只允许 `v*` 标签部署，给发布加一道人工闸门。
workflow 已声明 `environment: pypi`，配不配保护都能跑，配了更稳。

## 二、每次发版步骤

1. 改版本号（两处必须一致，CI 会校验标签 == pyproject 版本）：
   - `pyproject.toml` 的 `version`
   - `macbroom/__init__.py` 的 `__version__`
2. 更新 `更新日志.md`（或 CHANGELOG），写清本次变化。
3. 提交并推送 `main`。
4. 打标签并推送（**这一步触发发布**）：
   ```bash
   git tag v1.1.0
   git push origin v1.1.0
   ```
5. 在 GitHub Actions 看 `Release` 工作流跑完（build → pypi-publish → github-release）。

## 三、发布后验证

```bash
pipx install macbroom        # 或 pip install macbroom
macbroom --version           # 应输出 macbroom 1.1.0
macbroom scan --category login_items --json   # 冒烟
```

## 四、本地预检（不发布，仅验证产物）

```bash
python -m build
python -m twine check dist/*
```

## 注意

- 标签格式必须 `vX.Y.Z`，且去掉 `v` 后要与 `pyproject.toml` 版本完全一致，否则 CI 直接失败（防止误发）。
- 不要把版本号写死在多处又忘了同步；`macbroom --version` 优先读已安装包的元数据，源码运行回退 `__init__.__version__`。
- 预发布可用 `v1.1.0-rc.1` 之类标签；如需标记为 pre-release，可在 GitHub Release 页调整。
