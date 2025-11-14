"""
裝備類別定義
"""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Equipment:
    """裝備基礎類別"""
    id: str
    name: str
    type: str  # 裝備類型：武器、頭盔、護甲、鞋子等
    rarity: str  # 稀有度：普通、稀有、史詩、傳說等
    attributes: Dict[str, float]  # 屬性數值：攻擊、防禦、生命值等
    set_name: Optional[str] = None  # 所屬套裝名稱
    
    def __str__(self):
        return f"{self.name} ({self.type})"
    
    def get_total_power(self) -> float:
        """計算裝備總戰力（可自定義計算公式）"""
        return sum(self.attributes.values())


