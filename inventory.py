"""
倉庫系統
"""
from typing import List, Dict, Optional
from equipment import Equipment


class Inventory:
    """裝備倉庫管理系統"""
    
    def __init__(self):
        self.equipments: Dict[str, Equipment] = {}
    
    def add_equipment(self, equipment: Equipment):
        """添加裝備到倉庫"""
        self.equipments[equipment.id] = equipment
    
    def remove_equipment(self, equipment_id: str):
        """從倉庫移除裝備"""
        if equipment_id in self.equipments:
            del self.equipments[equipment_id]
    
    def get_equipment(self, equipment_id: str) -> Optional[Equipment]:
        """根據ID獲取裝備"""
        return self.equipments.get(equipment_id)
    
    def get_equipments_by_type(self, equipment_type: str) -> List[Equipment]:
        """根據類型獲取裝備列表"""
        return [eq for eq in self.equipments.values() if eq.type == equipment_type]
    
    def get_equipments_by_set(self, set_name: str) -> List[Equipment]:
        """根據套裝名稱獲取裝備列表"""
        return [eq for eq in self.equipments.values() if eq.set_name == set_name]
    
    def get_all_equipments(self) -> List[Equipment]:
        """獲取所有裝備"""
        return list(self.equipments.values())
    
    def search_equipments(self, keyword: str) -> List[Equipment]:
        """搜尋裝備（根據名稱）"""
        keyword = keyword.lower()
        return [eq for eq in self.equipments.values() if keyword in eq.name.lower()]

