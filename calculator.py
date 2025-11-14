"""
裝備組合數值計算器
"""
from typing import List, Dict
from equipment import Equipment
from inventory import Inventory


class EquipmentCalculator:
    """裝備數值計算器"""
    
    def __init__(self, inventory: Inventory):
        self.inventory = inventory
        self.set_bonuses: Dict[str, Dict[str, float]] = {}  # 套裝效果定義
    
    def add_set_bonus(self, set_name: str, piece_count: int, bonus: Dict[str, float]):
        """添加套裝效果
        Args:
            set_name: 套裝名稱
            piece_count: 需要的件數
            bonus: 加成屬性
        """
        if set_name not in self.set_bonuses:
            self.set_bonuses[set_name] = {}
        self.set_bonuses[set_name][piece_count] = bonus
    
    def calculate_combination(self, equipment_ids: List[str]) -> Dict[str, float]:
        """計算裝備組合的總屬性
        
        Args:
            equipment_ids: 裝備ID列表
            
        Returns:
            包含總屬性和套裝效果的字典
        """
        total_attributes: Dict[str, float] = {}
        set_counts: Dict[str, int] = {}
        
        # 計算基礎屬性
        for eq_id in equipment_ids:
            equipment = self.inventory.get_equipment(eq_id)
            if equipment:
                # 累加屬性
                for attr_name, attr_value in equipment.attributes.items():
                    total_attributes[attr_name] = total_attributes.get(attr_name, 0) + attr_value
                
                # 統計套裝件數
                if equipment.set_name:
                    set_counts[equipment.set_name] = set_counts.get(equipment.set_name, 0) + 1
        
        # 計算套裝加成
        set_bonuses_applied: Dict[str, Dict[str, float]] = {}
        for set_name, count in set_counts.items():
            if set_name in self.set_bonuses:
                # 找到符合件數的套裝效果（取最大件數的效果）
                applicable_bonuses = [
                    (piece_count, bonus) 
                    for piece_count, bonus in self.set_bonuses[set_name].items()
                    if piece_count <= count
                ]
                if applicable_bonuses:
                    piece_count, bonus = max(applicable_bonuses, key=lambda x: x[0])
                    set_bonuses_applied[f"{set_name}({piece_count}件)"] = bonus
                    # 應用套裝加成
                    for attr_name, attr_value in bonus.items():
                        total_attributes[attr_name] = total_attributes.get(attr_name, 0) + attr_value
        
        return {
            "total_attributes": total_attributes,
            "set_bonuses": set_bonuses_applied,
            "equipment_count": len(equipment_ids)
        }
    
    def calculate_total_power(self, equipment_ids: List[str]) -> float:
        """計算組合總戰力"""
        result = self.calculate_combination(equipment_ids)
        return sum(result["total_attributes"].values())

