"""数据模型：扫描项与分类。

ScanItem 是整个工具的统一数据单元，扫描器产出它、Web 展示它、删除接口消费它。
保持纯数据 + 少量序列化逻辑，不放业务规则。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional


# 删除动作类型
ACTION_TRASH = "trash"      # 移动到「废纸篓」，可恢复
ACTION_RUN = "run"          # 服务端执行我们生成的安全命令（如 simctl / brew cleanup）
ACTION_MANUAL = "manual"    # 需要 sudo 或有风险，仅展示命令让用户自行执行

# 风险等级：决定默认是否展示 / 是否默认勾选 / UI 配色。
RISK_SAFE = "safe"          # 可放心删，删了会自动重建，不丢数据
RISK_MODERATE = "moderate"  # 一般安全，但属于个人数据 / 需复核
RISK_RISKY = "risky"        # 高风险：不可逆 / 可能丢重要数据，默认隐藏

RISK_LEVELS = (RISK_SAFE, RISK_MODERATE, RISK_RISKY)


@dataclass
class ScanItem:
    """一个可清理项。"""

    category: str                       # 所属分类 key
    name: str                           # 展示名称
    size: int = 0                       # 占用字节数
    path: Optional[str] = None          # 绝对路径（trash 动作必填）
    group: str = "其它"                 # 分组（通常是 App 名 / 子类）
    action: str = ACTION_TRASH          # 删除动作类型
    command: Optional[str] = None       # run / manual 动作的命令
    note: str = ""                      # 说明：为什么可删 / 风险提示
    recommend: bool = False             # 是否默认勾选（仅明确安全项为 True）
    needs_sudo: bool = False            # 是否已知需要管理员权限
    risk: str = RISK_MODERATE           # 风险等级，见 RISK_*
    mtime: float = 0.0                  # 最近修改时间（秒）
    reason: str = ""                      # 判定理由（为何出现在结果里）
    children: list[dict] = field(default_factory=list)  # 可展开子项 [{path, size, name}]
    id: str = field(default="")

    def __post_init__(self) -> None:
        if self.risk not in RISK_LEVELS:
            self.risk = RISK_MODERATE
        if not self.id:
            # 以「分类 + 路径/命令」为种子，保证同一项跨多次扫描得到稳定 ID，
            # 重扫后前端可据此保留用户已勾选的项。
            seed = f"{self.category}|{self.path or self.command or self.name}"
            self.id = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Category:
    """一个扫描分类的元信息。"""

    key: str
    title: str
    description: str
    icon: str = "📦"
    danger: bool = False   # True 表示该分类整体偏「需人工确认」，UI 标橙色
