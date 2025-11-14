"""
裝備管理工具
提供簡化的裝備添加和套裝配置功能

主要功能：
- 添加裝備到倉庫
- 配置套裝組合
- 列出和管理裝備
- 刪除裝備
"""
from typing import Dict, Optional, List
from equipment import Equipment, EQUIPMENT_TAGS, EQUIPMENT_ATTRIBUTES, STAT_TYPE_RANDOM
from inventory import ClassInventoryManager
from calculator import EquipmentCalculator
from classes import GuardianClass
from storage import save_equipments, load_equipments


class EquipmentManager:
    """裝備管理器 - 提供簡化的裝備操作接口"""
    
    def __init__(self):
        """初始化管理器"""
        self.inventory_manager = ClassInventoryManager()
        self.calculator = EquipmentCalculator(self.inventory_manager)
        self.equipment_counter = {}  # 用於生成唯一ID
        
        # 從文件加載已保存的裝備
        self._load_from_storage()
    
    def add_equipment_simple(self, 
                            guardian_class: GuardianClass,
                            equipment_type: str,
                            tag: str,
                            random_stat: str,
                            locked_attr: Optional[str] = None,
                            set_name: Optional[str] = None) -> Equipment:
        """簡化添加裝備
        
        Args:
            guardian_class: 職業
            equipment_type: 裝備類型（頭盔、臂鎧、胸鎧、護腿、職業物品）
            tag: 裝備標籤（堡壘、赤拳互鬥、榴彈兵、至高典範、戰術家、槍手）
            random_stat: 隨機詞條屬性名稱
            locked_attr: 鎖定的屬性（可選，懲罰屬性在配置套裝時才選擇）
            set_name: 套裝名稱（可選）
            
        Returns:
            創建的裝備對象
        """
        # 驗證標籤
        if tag not in EQUIPMENT_TAGS:
            raise ValueError(f"未知的裝備標籤: {tag}，可用標籤: {list(EQUIPMENT_TAGS.keys())}")
        
        # 驗證裝備類型
        valid_types = ["頭盔", "臂鎧", "胸鎧", "護腿", "職業物品"]
        if equipment_type not in valid_types:
            raise ValueError(f"未知的裝備類型: {equipment_type}，可用類型: {valid_types}")
        
        # 驗證隨機詞條屬性
        if random_stat not in EQUIPMENT_ATTRIBUTES:
            raise ValueError(f"未知的屬性: {random_stat}，可用屬性: {EQUIPMENT_ATTRIBUTES}")
        
        # 獲取標籤對應的主詞條和副詞條
        main_attr, sub_attr = EQUIPMENT_TAGS[tag]
        
        # 驗證隨機詞條不能與主詞條或副詞條重複
        if random_stat == main_attr or random_stat == sub_attr:
            raise ValueError(f"隨機詞條不能與主詞條({main_attr})或副詞條({sub_attr})重複")
        
        # 檢查是否已存在相同裝備（類型、標籤、隨機詞條、鎖定屬性都相同）
        inventory = self.inventory_manager.get_inventory(guardian_class)
        existing_equipments = inventory.get_all_equipments()
        
        for existing_eq in existing_equipments:
            # 獲取現有裝備的隨機詞條屬性
            existing_random_stat = None
            for attr, stat_type in existing_eq.stat_tags.items():
                if stat_type == STAT_TYPE_RANDOM:
                    existing_random_stat = attr
                    break
            
            if (existing_eq.type == equipment_type and
                existing_eq.tag == tag and
                existing_random_stat == random_stat and
                existing_eq.locked_attr == locked_attr):
                raise ValueError("倉庫中已存在相同裝備")
        
        # 生成唯一ID
        class_key = guardian_class.value
        if class_key not in self.equipment_counter:
            self.equipment_counter[class_key] = {}
        if equipment_type not in self.equipment_counter[class_key]:
            self.equipment_counter[class_key][equipment_type] = 0
        
        self.equipment_counter[class_key][equipment_type] += 1
        equipment_id = f"{class_key}_{equipment_type}_{self.equipment_counter[class_key][equipment_type]:03d}"
        
        # 構建屬性字典（基礎值：主詞條30，副詞條25，隨機詞條20）
        attributes = {
            main_attr: 30,
            sub_attr: 25,
            random_stat: 20
        }
        
        # 創建裝備（如果鎖定但沒有懲罰屬性，先不設置懲罰屬性，在配置套裝時再選擇）
        # level 默認為 0（未升級），補充詞條為 0
        equipment = Equipment(
            id=equipment_id,
            name=f"{tag}_{equipment_type}",
            type=equipment_type,
            rarity="傳說",
            tag=tag,
            attributes=attributes,
            class_restriction=[guardian_class],
            set_name=set_name,
            level=0,  # 默認未升級
            locked_attr=locked_attr,
            penalty_attr=None  # 懲罰屬性在配置套裝時才選擇
        )
        
        # 添加到倉庫
        self.inventory_manager.add_equipment(equipment)
        
        # 保存到文件
        self._save_to_storage()
        
        return equipment
    
    def configure_build(self, 
                       guardian_class: GuardianClass,
                       target_attributes: Dict[str, float],
                       exotic_equipment: Optional[Dict] = None,
                       preferred_attr: Optional[str] = None) -> Dict:
        """配置套裝"""
        return self.calculator.find_combination_by_target(
            target_attributes, guardian_class, exotic_equipment=exotic_equipment, preferred_attr=preferred_attr
        )
    
    def get_inventory_manager(self) -> ClassInventoryManager:
        """獲取倉庫管理器"""
        return self.inventory_manager
    
    def get_calculator(self) -> EquipmentCalculator:
        """獲取計算器"""
        return self.calculator
    
    def list_equipments(self, guardian_class: GuardianClass) -> List[Dict]:
        """列出指定職業的所有裝備"""
        equipments = self.inventory_manager.get_inventory(guardian_class).get_all_equipments()
        return [{
            "id": eq.id,
            "name": eq.name,
            "type": eq.type,
            "tag": eq.tag,
            "attributes": {k: v for k, v in eq.attributes.items() if v > 0},
            "locked_attr": eq.locked_attr,
            "penalty_attr": eq.penalty_attr,
            "level": eq.level,
            "set_name": eq.set_name
        } for eq in equipments]
    
    def remove_equipment(self, equipment_id: str, guardian_class: GuardianClass) -> bool:
        """刪除指定職業的裝備
        
        Args:
            equipment_id: 裝備ID
            guardian_class: 職業
            
        Returns:
            是否成功刪除
        """
        inventory = self.inventory_manager.get_inventory(guardian_class)
        equipment = inventory.get_equipment(equipment_id)
        
        if equipment is None:
            return False
        
        # 從倉庫移除裝備
        self.inventory_manager.remove_equipment(equipment_id, guardian_class)
        
        # 保存到文件
        self._save_to_storage()
        
        return True
    
    def _load_from_storage(self) -> None:
        """從存儲文件加載裝備"""
        try:
            equipments = load_equipments()
            for equipment in equipments:
                # 添加到倉庫
                self.inventory_manager.add_equipment(equipment)
                
                # 更新計數器（確保新添加的裝備ID不會重複）
                if equipment.class_restriction:
                    for gc in equipment.class_restriction:
                        class_key = gc.value
                        if class_key not in self.equipment_counter:
                            self.equipment_counter[class_key] = {}
                        if equipment.type not in self.equipment_counter[class_key]:
                            self.equipment_counter[class_key][equipment.type] = 0
                        
                        # 從ID中提取編號
                        try:
                            parts = equipment.id.split('_')
                            if len(parts) >= 3:
                                num_str = parts[-1]
                                num = int(num_str)
                                # 更新計數器為已使用的最大編號
                                if num > self.equipment_counter[class_key][equipment.type]:
                                    self.equipment_counter[class_key][equipment.type] = num
                        except (ValueError, IndexError):
                            pass
        except Exception as e:
            print(f"警告：加載裝備數據失敗: {e}")
    
    def _save_to_storage(self) -> None:
        """保存所有裝備到存儲文件"""
        try:
            # 收集所有職業的所有裝備（使用ID避免重複）
            all_equipments = []
            seen_ids = set()
            for gc in GuardianClass.get_all_classes():
                equipments = self.inventory_manager.get_inventory(gc).get_all_equipments()
                for eq in equipments:
                    if eq.id not in seen_ids:
                        all_equipments.append(eq)
                        seen_ids.add(eq.id)
            
            save_equipments(all_equipments)
        except Exception as e:
            print(f"警告：保存裝備數據失敗: {e}")

