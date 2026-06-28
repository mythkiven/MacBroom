## 改动说明 / What does this PR do?
简要描述本次改动及动机。

## 关联 issue / Related issue
Closes #

## 类型 / Type
- [ ] Bug 修复
- [ ] 新功能 / 新扫描器
- [ ] 重构 / 性能
- [ ] 文档

## 自检清单 / Checklist
- [ ] `MACBROOM_LOG_DIR=/tmp/macbroom-test python -m unittest discover -s tests` 通过
- [ ] `python -m compileall macbroom` 无报错
- [ ] 新增 `ScanItem` 均显式设置了 `risk`（safe / moderate / risky）
- [ ] 新增/改动的文案已同时补 `zh` 与 `en`
- [ ] 未触碰 `core/fsutil.PROTECTED_PREFIXES` 的安全约束；删除一律走废纸篓或固定安全命令
- [ ] 自测使用 `MACBROOM_LOG_DIR` 指向 /tmp，未污染真实数据
