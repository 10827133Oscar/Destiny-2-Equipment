"""
倉庫系統
"""
from typing import List, Dict, Optional
from equipment import Equipment
from classes import GuardianClass


class Inventory:
    """單一職業的裝備倉庫管理系統"""
    
    def __init__(self, guardian_class: GuardianClass):
        """
        初始化倉庫
        Args:
            guardian_class: 此倉庫所屬的職業
        """
        self.guardian_class = guardian_class
        self.equipments: Dict[str, Equipment] = {}
    
    def add_equipment(self, equipment: Equipment):
        """添加裝備到倉庫（會檢查職業相容性）"""
        if equipment.class_restriction is None or self.guardian_class in equipment.class_restriction:
            self.equipments[equipment.id] = equipment
        else:
            raise ValueError(f"裝備 {equipment.name} 與職業 {self.guardian_class.value} 不相容")
    
    def remove_equipment(self, equipment_id: str):
        """從倉庫移除裝備"""
        if equipment_id in self.equipments:
            del self.equipments[equipment_id]
    
    def get_equipment(self, equipment_id: str) -> Optional[Equipment]:
        """根據ID獲取裝備"""
        return self.equipments.get(equipment_id)
    
    def get_all_equipments(self) -> List[Equipment]:
        """獲取所有裝備"""
        return list(self.equipments.values())


class ClassInventoryManager:
    """管理三個職業的裝備倉庫"""
    
    def __init__(self):
        """初始化三個職業的倉庫"""
        self.inventories: Dict[GuardianClass, Inventory] = {
            GuardianClass.TITAN: Inventory(GuardianClass.TITAN),
            GuardianClass.HUNTER: Inventory(GuardianClass.HUNTER),
            GuardianClass.WARLOCK: Inventory(GuardianClass.WARLOCK)
        }
    
    def get_inventory(self, guardian_class: GuardianClass) -> Inventory:
        """獲取指定職業的倉庫"""
        return self.inventories[guardian_class]
    
    def add_equipment(self, equipment: Equipment):
        """添加裝備到對應職業的倉庫
        如果裝備是通用裝備（class_restriction 為 None），則添加到所有職業的倉庫
        如果裝備有職業限制，則只添加到對應職業的倉庫
        """
        if equipment.class_restriction is None:
            # 通用裝備，添加到所有職業的倉庫
            for inventory in self.inventories.values():
                inventory.add_equipment(equipment)
        else:
            # 有職業限制的裝備，只添加到對應職業的倉庫
            for guardian_class in equipment.class_restriction:
                self.inventories[guardian_class].add_equipment(equipment)
    
    def remove_equipment(self, equipment_id: str, guardian_class: Optional[GuardianClass] = None):
        """從倉庫移除裝備
        Args:
            equipment_id: 裝備ID
            guardian_class: 如果指定職業，只從該職業的倉庫移除；否則從所有職業的倉庫移除
        """
        if guardian_class:
            self.inventories[guardian_class].remove_equipment(equipment_id)
        else:
            for inventory in self.inventories.values():
                inventory.remove_equipment(equipment_id)
