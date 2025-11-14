"""
裝備類別定義
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from classes import GuardianClass

# 裝備屬性列表（按順序）
EQUIPMENT_ATTRIBUTES = ["生命值", "近戰", "手榴彈", "超能力", "職業", "武器"]

# 裝備基本數值（每個裝備只有3個屬性有數值）
EQUIPMENT_BASE_VALUES = [30, 25, 20]

# 最大強化等級
MAX_UPGRADE_LEVEL = 5

# 詞條類型定義
STAT_TYPE_MAIN = "主詞條"      # 30
STAT_TYPE_SUB = "副詞條"      # 25
STAT_TYPE_RANDOM = "隨機詞條"  # 20
STAT_TYPE_SUPPLEMENT = "補充詞條"  # 0~5（升級後增加）

# 裝備標籤定義（標籤 -> (主詞條屬性, 副詞條屬性)）
EQUIPMENT_TAGS = {
    "堡壘": ("生命值", "職業"),
    "赤拳互鬥": ("近戰", "生命值"),
    "榴彈兵": ("手榴彈", "超能力"),
    "至高典範": ("超能力", "近戰"),
    "戰術家": ("職業", "武器"),
    "槍手": ("武器", "手榴彈")
}


@dataclass
class Equipment:
    """裝備基礎類別"""
    id: str
    name: str
    type: str  # 裝備類型：頭盔、臂鎧、胸鎧、護腿、職業物品
    rarity: str  # 稀有度：普通、稀有、史詩、傳說等
    tag: Optional[str] = None  # 裝備標籤：堡壘、赤拳互鬥、榴彈兵、至高典範、戰術家、槍手
    attributes: Dict[str, float] = field(default_factory=dict)  # 屬性數值：生命值、近戰、手榴彈、超能力、職業、武器
    stat_tags: Dict[str, str] = field(default_factory=dict)  # 屬性標籤：{屬性名: 詞條類型}
    class_restriction: Optional[List[GuardianClass]] = None  # 職業限制，None 表示所有職業可用
    set_name: Optional[str] = None  # 所屬套裝名稱
    level: int = 0  # 強化等級（0-5級，預設0級）
    locked_attr: Optional[str] = None  # 鎖定的屬性（+5）
    penalty_attr: Optional[str] = None  # 懲罰屬性（-5）
    
    def __post_init__(self):
        """初始化後驗證屬性"""
        self._normalize_attributes()
        # 如果有裝備標籤，根據標籤生成詞條標籤；否則根據數值自動生成
        if self.tag:
            self._generate_stat_tags_from_equipment_tag()
        elif not self.stat_tags:
            self._generate_stat_tags()
        # 注意：不在這裡應用鎖定效果，鎖定和懲罰效果只在計算時應用
        self._validate_attributes()
        self._validate_stat_tags()
    
    def _validate_attributes(self):
        """驗證屬性是否符合規則：只有3個屬性有數值（30、25、20），其他3個為0或升級值
        
        注意：此驗證在基礎屬性上進行，不考慮鎖定和懲罰效果（這些效果只在計算時應用）
        """
        non_zero_attrs = {k: v for k, v in self.attributes.items() if v != 0}
        
        # 檢查非零屬性數量（應該恰好是3個）
        if len(non_zero_attrs) != 3:
            raise ValueError(f"裝備 {self.name} 必須恰好有3個非零屬性，目前有 {len(non_zero_attrs)} 個")
        
        # 檢查非零屬性的基礎值是否為30、25、20
        values = sorted(non_zero_attrs.values(), reverse=True)
        expected_values = sorted(EQUIPMENT_BASE_VALUES, reverse=True)
        
        if len(values) != len(expected_values) or any(abs(val - expected) > 0.01 for val, expected in zip(values, expected_values)):
            raise ValueError(f"裝備 {self.name} 的基礎屬性數值必須為 {EQUIPMENT_BASE_VALUES}，目前為 {values}")
        
    def _validate_stat_tags(self):
        """驗證標籤是否符合規則"""
        # 檢查每個屬性都有標籤
        for attr in EQUIPMENT_ATTRIBUTES:
            if attr not in self.stat_tags:
                raise ValueError(f"裝備 {self.name} 的屬性 {attr} 缺少標籤")
        
        # 檢查標籤類型數量
        main_stats = [k for k, v in self.stat_tags.items() if v == STAT_TYPE_MAIN]
        sub_stats = [k for k, v in self.stat_tags.items() if v == STAT_TYPE_SUB]
        random_stats = [k for k, v in self.stat_tags.items() if v == STAT_TYPE_RANDOM]
        supplement_stats = [k for k, v in self.stat_tags.items() if v == STAT_TYPE_SUPPLEMENT]
        
        if len(main_stats) != 1:
            raise ValueError(f"裝備 {self.name} 必須恰好有1個主詞條，目前有 {len(main_stats)} 個")
        if len(sub_stats) != 1:
            raise ValueError(f"裝備 {self.name} 必須恰好有1個副詞條，目前有 {len(sub_stats)} 個")
        if len(random_stats) != 1:
            raise ValueError(f"裝備 {self.name} 必須恰好有1個隨機詞條，目前有 {len(random_stats)} 個")
        if len(supplement_stats) != 3:
            raise ValueError(f"裝備 {self.name} 必須恰好有3個補充詞條，目前有 {len(supplement_stats)} 個")
        
        # 檢查詞條數值是否正確（只驗證基礎值，不考慮鎖定和懲罰效果）
        main_attr = main_stats[0]
        sub_attr = sub_stats[0]
        random_attr = random_stats[0]
        
        # 基礎值（不考慮鎖定和懲罰效果）
        expected_main = 30.0
        expected_sub = 25.0
        expected_random = 20.0
        
        if abs(self.attributes[main_attr] - expected_main) > 0.01:
            raise ValueError(f"裝備 {self.name} 的主詞條 {main_attr} 數值應為{expected_main}，目前為 {self.attributes[main_attr]}")
        if abs(self.attributes[sub_attr] - expected_sub) > 0.01:
            raise ValueError(f"裝備 {self.name} 的副詞條 {sub_attr} 數值應為{expected_sub}，目前為 {self.attributes[sub_attr]}")
        if abs(self.attributes[random_attr] - expected_random) > 0.01:
            raise ValueError(f"裝備 {self.name} 的隨機詞條 {random_attr} 數值應為{expected_random}，目前為 {self.attributes[random_attr]}")
        
        # 如果有裝備標籤，檢查主詞條和副詞條是否符合標籤定義
        if self.tag:
            if self.tag not in EQUIPMENT_TAGS:
                raise ValueError(f"裝備 {self.name} 的標籤 {self.tag} 不在定義中")
            expected_main, expected_sub = EQUIPMENT_TAGS[self.tag]
            if main_attr != expected_main:
                raise ValueError(f"裝備 {self.name} 標籤 {self.tag} 的主詞條應為 {expected_main}，目前為 {main_attr}")
            if sub_attr != expected_sub:
                raise ValueError(f"裝備 {self.name} 標籤 {self.tag} 的副詞條應為 {expected_sub}，目前為 {sub_attr}")
        
        # 檢查補充詞條的數值（應該在0到level之間）
        for attr_name in supplement_stats:
            attr_value = self.attributes[attr_name]
            if attr_value < 0 or attr_value > self.level:
                raise ValueError(f"裝備 {self.name} 的補充詞條 {attr_name} 數值應在0到{self.level}之間，目前為 {attr_value}")
    
    def _normalize_attributes(self):
        """標準化屬性：確保所有6種屬性都存在，不存在的設為0"""
        for attr in EQUIPMENT_ATTRIBUTES:
            if attr not in self.attributes:
                self.attributes[attr] = 0.0
    
    def _generate_stat_tags_from_equipment_tag(self):
        """根據裝備標籤生成詞條標籤"""
        if self.tag not in EQUIPMENT_TAGS:
            raise ValueError(f"未知的裝備標籤: {self.tag}，可用標籤: {list(EQUIPMENT_TAGS.keys())}")
        
        self.stat_tags = {}
        main_attr, sub_attr = EQUIPMENT_TAGS[self.tag]
        
        # 設置主詞條和副詞條
        self.stat_tags[main_attr] = STAT_TYPE_MAIN
        self.stat_tags[sub_attr] = STAT_TYPE_SUB
        
        # 找出剩餘的4個屬性（用於隨機詞條和補充詞條）
        remaining_attrs = [attr for attr in EQUIPMENT_ATTRIBUTES if attr not in [main_attr, sub_attr]]
        
        # 找出當前有數值的屬性（應該是30、25、20）
        non_zero_attrs = {k: v for k, v in self.attributes.items() if v != 0}
        
        # 找出隨機詞條（數值為20的，或剩餘屬性中第一個有數值的）
        random_attr = next(
            (attr_name for attr_name, attr_value in non_zero_attrs.items()
             if attr_name not in [main_attr, sub_attr] and abs(attr_value - 20) < 0.01),
            next((attr_name for attr_name in remaining_attrs if attr_name in non_zero_attrs), None)
        )
        
        if random_attr:
            self.stat_tags[random_attr] = STAT_TYPE_RANDOM
        
        # 其餘屬性標記為補充詞條
        for attr in EQUIPMENT_ATTRIBUTES:
            if attr not in self.stat_tags:
                self.stat_tags[attr] = STAT_TYPE_SUPPLEMENT
    
    def _generate_stat_tags(self):
        """根據數值自動生成標籤（當沒有裝備標籤時使用）"""
        non_zero_attrs = {k: v for k, v in self.attributes.items() if v != 0}
        if len(non_zero_attrs) != 3:
            return
        
        sorted_attrs = sorted(non_zero_attrs.items(), key=lambda x: x[1], reverse=True)
        self.stat_tags = {
            sorted_attrs[0][0]: STAT_TYPE_MAIN,
            sorted_attrs[1][0]: STAT_TYPE_SUB,
            sorted_attrs[2][0]: STAT_TYPE_RANDOM
        }
        
        for attr in EQUIPMENT_ATTRIBUTES:
            if attr not in self.stat_tags:
                self.stat_tags[attr] = STAT_TYPE_SUPPLEMENT
    
    def _apply_lock_effect(self):
        """應用鎖定效果（只在有懲罰屬性時應用）"""
        if not (self.locked_attr and self.penalty_attr):
            return
        
        if self.locked_attr not in EQUIPMENT_ATTRIBUTES:
            raise ValueError(f"鎖定屬性 {self.locked_attr} 不存在")
        if self.penalty_attr not in EQUIPMENT_ATTRIBUTES:
            raise ValueError(f"懲罰屬性 {self.penalty_attr} 不存在")
        
        self.attributes[self.locked_attr] += 5
        self.attributes[self.penalty_attr] = max(0, self.attributes[self.penalty_attr] - 5)
    
    def get_stat_tag(self, attr_name: str) -> str:
        """獲取屬性的詞條類型"""
        return self.stat_tags.get(attr_name, STAT_TYPE_SUPPLEMENT)
    
    def get_max_level_attributes(self) -> Dict[str, float]:
        """獲取滿級時的屬性（不修改原始裝備）
        
        注意：此方法會考慮鎖定和懲罰屬性的效果
        - 鎖定屬性：+5
        - 懲罰屬性：-5（但不低於0）
        
        計算邏輯：
        1. 先計算滿級時的基礎屬性（補充詞條升級到5）
        2. 然後應用鎖定和懲罰效果
        """
        def get_base_value(attr_name: str) -> float:
            """獲取屬性的基礎值（不考慮鎖定和懲罰）"""
            stat_type = self.get_stat_tag(attr_name)
            if stat_type == STAT_TYPE_MAIN:
                return 30.0
            elif stat_type == STAT_TYPE_SUB:
                return 25.0
            elif stat_type == STAT_TYPE_RANDOM:
                return 20.0
            else:  # STAT_TYPE_SUPPLEMENT
                # 補充詞條的基礎值取決於裝備等級，滿級時為 MAX_UPGRADE_LEVEL
                return float(MAX_UPGRADE_LEVEL)
        
        # 構建滿級時的基礎屬性（所有補充詞條都升級到5）
        max_attrs = {}
        for attr_name in EQUIPMENT_ATTRIBUTES:
            stat_type = self.get_stat_tag(attr_name)
            if stat_type == STAT_TYPE_MAIN:
                max_attrs[attr_name] = 30.0
            elif stat_type == STAT_TYPE_SUB:
                max_attrs[attr_name] = 25.0
            elif stat_type == STAT_TYPE_RANDOM:
                max_attrs[attr_name] = 20.0
            else:  # STAT_TYPE_SUPPLEMENT
                max_attrs[attr_name] = float(MAX_UPGRADE_LEVEL)
        
        # 應用鎖定和懲罰效果
        if self.locked_attr and self.penalty_attr:
            # 鎖定屬性：基礎值 +5
            locked_base = get_base_value(self.locked_attr)
            max_attrs[self.locked_attr] = locked_base + 5
            
            # 懲罰屬性：基礎值 -5（但不低於0）
            penalty_base = get_base_value(self.penalty_attr)
            max_attrs[self.penalty_attr] = max(0, penalty_base - 5)
        
        return max_attrs
    
    def __str__(self):
        class_info = ""
        if self.class_restriction:
            class_names = [str(c) for c in self.class_restriction]
            class_info = f" [{', '.join(class_names)}]"
        level_info = f" +{self.level}" if self.level > 0 else ""
        return f"{self.name} ({self.type}){class_info}{level_info}"
    
