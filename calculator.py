"""
裝備組合數值計算器
"""
from typing import List, Dict, Optional
from itertools import combinations, product
from equipment import (
    Equipment, EQUIPMENT_ATTRIBUTES, EQUIPMENT_TAGS, MAX_UPGRADE_LEVEL,
    STAT_TYPE_MAIN, STAT_TYPE_SUB, STAT_TYPE_RANDOM, STAT_TYPE_SUPPLEMENT
)
from inventory import ClassInventoryManager
from classes import GuardianClass


class EquipmentCalculator:
    """裝備數值計算器"""
    
    def __init__(self, inventory_manager: ClassInventoryManager):
        """
        初始化計算器
        Args:
            inventory_manager: 職業倉庫管理器
        """
        self.inventory_manager = inventory_manager
        self.set_bonuses: Dict[str, Dict[int, Dict[str, float]]] = {}  # 套裝效果定義 {套裝名: {件數: {屬性: 數值}}}
    
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
    
    def calculate_combination(self, equipment_ids: List[str], guardian_class: GuardianClass, 
                             exotic_equipment: Optional[Dict] = None) -> Dict:
        """計算裝備組合的總屬性
        
        Args:
            equipment_ids: 裝備ID列表
            guardian_class: 守護者職業（必須指定，用於從對應職業的倉庫獲取裝備）
            exotic_equipment: 可選的異域裝備字典，格式：{
                "name": str,
                "type": str,
                "attributes": Dict[str, float],  # 滿級屬性（補充詞條已升級到5）
                "level": int  # 原始等級（用於顯示）
            }
            
        Returns:
            包含詳細計算結果的字典
        """
        if guardian_class is None:
            raise ValueError("必須指定職業才能計算裝備組合")
        
        inventory = self.inventory_manager.get_inventory(guardian_class)
        total_attributes: Dict[str, float] = {}
        equipment_details: List[Dict] = []
        set_counts: Dict[str, int] = {}
        missing_equipments: List[str] = []
        
        # 統計各詞條類型的總數值
        stat_type_totals: Dict[str, Dict[str, float]] = {
            STAT_TYPE_MAIN: {},
            STAT_TYPE_SUB: {},
            STAT_TYPE_RANDOM: {},
            STAT_TYPE_SUPPLEMENT: {}
        }
        
        # 計算基礎屬性（使用滿級屬性進行計算）
        for eq_id in equipment_ids:
            equipment = inventory.get_equipment(eq_id)
            if equipment:
                # 獲取滿級時的屬性（不修改原始裝備）
                max_level_attrs = equipment.get_max_level_attributes()
                eq_attrs = {}
                eq_stat_types = {}
                
                # 累加屬性並記錄詞條類型（使用滿級屬性）
                for attr_name, attr_value in max_level_attrs.items():
                    total_attributes[attr_name] = total_attributes.get(attr_name, 0) + attr_value
                    eq_attrs[attr_name] = attr_value
                    stat_type = equipment.get_stat_tag(attr_name)
                    eq_stat_types[attr_name] = stat_type
                    if stat_type in stat_type_totals:
                        stat_type_totals[stat_type][attr_name] = stat_type_totals[stat_type].get(attr_name, 0) + attr_value
                
                # 記錄裝備詳情（顯示滿級屬性）
                equipment_details.append({
                    "id": eq_id,
                    "name": equipment.name,
                    "type": equipment.type,
                    "tag": equipment.tag,
                    "attributes": eq_attrs,  # 滿級屬性
                    "stat_types": eq_stat_types,
                    "locked_attr": equipment.locked_attr,
                    "penalty_attr": equipment.penalty_attr,
                    "level": MAX_UPGRADE_LEVEL,  # 顯示為滿級
                    "original_level": equipment.level,  # 原始等級
                    "set_name": equipment.set_name
                })
                
                # 統計套裝件數
                if equipment.set_name:
                    set_counts[equipment.set_name] = set_counts.get(equipment.set_name, 0) + 1
            else:
                missing_equipments.append(eq_id)
        
        # 處理異域裝備（如果有的話）
        if exotic_equipment:
            # 異域裝備的屬性已經是滿級屬性（補充詞條已升級到5）
            exotic_attrs = exotic_equipment.get("attributes", {})
            eq_attrs = {}
            
            # 累加屬性
            for attr_name, attr_value in exotic_attrs.items():
                total_attributes[attr_name] = total_attributes.get(attr_name, 0) + attr_value
                eq_attrs[attr_name] = attr_value
            
            # 記錄異域裝備詳情
            equipment_details.append({
                "id": "exotic_temp",
                "name": exotic_equipment.get("name", "異域裝備"),
                "type": exotic_equipment.get("type", "未知"),
                "tag": exotic_equipment.get("tag"),
                "attributes": eq_attrs,  # 滿級屬性
                "stat_types": {},  # 異域裝備不需要詞條類型
                "locked_attr": None,  # 異域裝備沒有鎖定特性
                "penalty_attr": None,  # 異域裝備沒有鎖定特性
                "level": MAX_UPGRADE_LEVEL,  # 顯示為滿級
                "original_level": exotic_equipment.get("level", 0),  # 原始等級
                "set_name": None,
                "is_exotic": True  # 標記為異域裝備
            })
        
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
        
        # 確保所有屬性都存在（如果沒有則設為0）
        for attr in EQUIPMENT_ATTRIBUTES:
            if attr not in total_attributes:
                total_attributes[attr] = 0.0
        
        # 計算總和
        total_sum = sum(total_attributes.values())
        
        # 計算總裝備數量（包括異域裝備）
        equipment_count = len(equipment_ids) - len(missing_equipments)
        if exotic_equipment:
            equipment_count += 1
        
        result = {
            "guardian_class": guardian_class.value,
            "equipment_ids": equipment_ids,
            "equipment_count": equipment_count,
            "equipment_details": equipment_details,
            "total_attributes": total_attributes,
            "stat_type_totals": stat_type_totals,
            "set_bonuses": set_bonuses_applied,
            "set_counts": set_counts,
            "total_sum": total_sum,
            "warnings": []
        }
        
        if missing_equipments:
            result["warnings"].append(f"以下裝備在 {guardian_class.value} 的倉庫中不存在: {', '.join(missing_equipments)}")
        
        return result
    
    def format_result(self, result: Dict) -> str:
        """格式化計算結果為可讀字符串"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"職業: {result['guardian_class']}")
        lines.append(f"裝備數量: {result['equipment_count']}")
        lines.append("=" * 60)
        
        # 顯示裝備詳情
        if result.get("equipment_details"):
            # 定義裝備類型順序
            equipment_type_order = ["頭盔", "臂鎧", "胸鎧", "護腿", "職業物品"]
            type_order_map = {eq_type: i for i, eq_type in enumerate(equipment_type_order)}
            
            # 按照裝備類型順序排序
            sorted_equipments = sorted(
                result["equipment_details"],
                key=lambda eq: (type_order_map.get(eq['type'], 999), eq.get('is_exotic', False))
            )
            
            for eq in sorted_equipments:
                # 異域裝備標題格式：【部位-異域裝備】
                if eq.get('is_exotic'):
                    lines.append(f"\n【{eq['type']}-異域裝備】")
                else:
                    lines.append(f"\n【{eq['type']}】")
                lines.append(f"  {eq['name']}")
                if eq.get('tag'):
                    lines.append(f"    標籤: {eq['tag']}")
                # 異域裝備沒有鎖定特性，只有普通裝備顯示鎖定信息
                if eq.get('locked_attr') and not eq.get('is_exotic'):
                    lines.append(f"    鎖定: {eq['locked_attr']} (+5), 懲罰: {eq.get('penalty_attr', '無')} (-5)")
                if eq.get('original_level') is not None and eq.get('original_level') != MAX_UPGRADE_LEVEL:
                    lines.append(f"    等級: +{eq['level']} (原始等級: +{eq['original_level']})")
                else:
                    lines.append(f"    等級: +{eq['level']}")
                for attr, value in eq['attributes'].items():
                    if value > 0:
                        lines.append(f"      {attr}: {value:.0f}")
        
        # 顯示總屬性
        lines.append("\n【總屬性數值】")
        for attr in EQUIPMENT_ATTRIBUTES:
            value = result["total_attributes"].get(attr, 0)
            lines.append(f"  {attr}: {value:.0f}")
        
        # 顯示詞條類型統計
        lines.append("\n【詞條類型統計】")
        for stat_type, attrs in result["stat_type_totals"].items():
            if attrs:
                lines.append(f"  {stat_type}:")
                for attr, value in attrs.items():
                    lines.append(f"    {attr}: {value:.0f}")
        
        # 顯示套裝效果
        if result.get("set_bonuses"):
            lines.append("\n【套裝效果】")
            for set_name, bonus in result["set_bonuses"].items():
                lines.append(f"  {set_name}:")
                for attr, value in bonus.items():
                    lines.append(f"    {attr}: +{value:.0f}")
        
        # 顯示總和
        lines.append(f"\n【總和】: {result['total_sum']:.0f}")
        
        # 顯示警告
        if result.get("warnings"):
            lines.append("\n【警告】")
            for warning in result["warnings"]:
                lines.append(f"  ⚠ {warning}")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def find_combination_by_target(self, target_attributes: Dict[str, float], 
                                   guardian_class: GuardianClass,
                                   max_equipments: int = 5,
                                   exotic_equipment: Optional[Dict] = None,
                                   preferred_attr: Optional[str] = None) -> Dict:
        """根據目標屬性值尋找裝備組合"""
        inventory = self.inventory_manager.get_inventory(guardian_class)
        all_equipments = inventory.get_all_equipments()
        
        if len(all_equipments) == 0 and not exotic_equipment:
            return {
                "found": False,
                "message": "倉庫中沒有裝備",
                "required_equipments": []
            }
        
        # 過濾出有目標屬性的裝備（使用滿級屬性）
        relevant_equipments = []
        for eq in all_equipments:
            max_level_attrs = eq.get_max_level_attributes()
            for target_attr in target_attributes.keys():
                if max_level_attrs.get(target_attr, 0) > 0:
                    relevant_equipments.append(eq)
                    break
        
        if len(relevant_equipments) == 0:
            return {
                "found": False,
                "message": "倉庫中沒有包含目標屬性的裝備",
                "required_equipments": []
            }
        
        # 嘗試不同數量的裝備組合（從1個到max_equipments個）
        best_combination = None
        best_score = float('inf')
        best_result = None
        best_penalty_configs = {}  # 記錄最佳組合的懲罰屬性配置
        best_preferred_value = -1  # 記錄最佳組合的偏好屬性值（用於在滿足目標後優化）
        
        for num_equipments in range(1, min(max_equipments + 1, len(relevant_equipments) + 1)):
            for combo in combinations(relevant_equipments, num_equipments):
                # 找出有鎖定但沒有懲罰屬性的裝備
                locked_equipments = [eq for eq in combo if eq.locked_attr and not eq.penalty_attr]
                
                # 如果有需要選擇懲罰屬性的裝備，嘗試不同的懲罰屬性組合
                if locked_equipments:
                    penalty_combinations = self._generate_penalty_combinations(locked_equipments)
                    
                    # 嘗試每種懲罰屬性組合
                    for penalty_config in penalty_combinations:
                        # 臨時設置懲罰屬性
                        original_penalties = {}
                        for eq in locked_equipments:
                            if eq.id in penalty_config:
                                original_penalties[eq.id] = eq.penalty_attr
                                eq.penalty_attr = penalty_config[eq.id]
                                # 重新應用鎖定效果
                                self._reapply_lock_effect(eq)
                        
                        try:
                            eq_ids = [eq.id for eq in combo]
                            result = self.calculate_combination(eq_ids, guardian_class, exotic_equipment)
                            
                            # 計算最佳加成分配
                            bonus_allocation = self._calculate_optimal_bonuses(
                                result["total_attributes"], target_attributes, preferred_attr
                            )
                            
                            # 應用加成到總屬性
                            final_attributes = result["total_attributes"].copy()
                            for attr, bonus_count in bonus_allocation.items():
                                final_attributes[attr] = final_attributes.get(attr, 0) + bonus_count * 10
                            
                            # 計算與目標的差距（只計算目標屬性，使用應用加成後的屬性）
                            score = 0
                            all_met = True
                            for target_attr, target_value in target_attributes.items():
                                actual_value = final_attributes.get(target_attr, 0)
                                if actual_value < target_value:
                                    all_met = False
                                    score += (target_value - actual_value) ** 2  # 使用平方差
                                else:
                                    # 如果超過目標，也計算超出的部分（但權重較小）
                                    score += (actual_value - target_value) * 0.1
                            
                            # 獲取偏好屬性值（如果指定了偏好）
                            preferred_value = final_attributes.get(preferred_attr, 0) if preferred_attr else 0
                            
                            # 選擇最佳組合：優先滿足目標，然後優化偏好屬性
                            is_better = False
                            if all_met:
                                # 如果都滿足目標
                                if best_score == float('inf'):
                                    # 之前沒有滿足目標的組合
                                    is_better = True
                                elif best_score > 0:
                                    # 之前沒有滿足目標，現在滿足了
                                    is_better = True
                                elif best_score == 0:
                                    # 都滿足了目標，比較偏好屬性值
                                    if preferred_attr:
                                        if preferred_value > best_preferred_value:
                                            is_better = True
                                    else:
                                        # 沒有偏好屬性，選擇分數更小的（更接近目標）
                                        if score < best_score:
                                            is_better = True
                            else:
                                # 如果沒滿足目標，只比較分數
                                if score < best_score:
                                    is_better = True
                            
                            if is_better:
                                best_score = score if not all_met else 0
                                best_combination = eq_ids
                                best_result = result
                                best_penalty_configs = penalty_config.copy()
                                best_bonus_allocation = bonus_allocation.copy()
                                best_preferred_value = preferred_value
                                
                                # 如果完全匹配，立即返回
                                if all_met and score == 0:
                                    # 還原懲罰屬性
                                    for eq in locked_equipments:
                                        if eq.id in original_penalties:
                                            eq.penalty_attr = original_penalties[eq.id]
                                            self._reapply_lock_effect(eq)
                                    
                                    # 更新結果中的總屬性（包含加成）
                                    best_result["total_attributes"] = final_attributes
                                    best_result["bonus_allocation"] = bonus_allocation
                                    
                                    return {
                                        "found": True,
                                        "combination": best_combination,
                                        "result": best_result,
                                        "penalty_configs": best_penalty_configs,
                                        "bonus_allocation": bonus_allocation,
                                        "target_attributes": target_attributes,
                                        "message": "找到完全匹配的裝備組合"
                                    }
                        finally:
                            # 還原懲罰屬性
                            for eq in locked_equipments:
                                if eq.id in original_penalties:
                                    eq.penalty_attr = original_penalties[eq.id]
                                    self._reapply_lock_effect(eq)
                else:
                    # 沒有需要選擇懲罰屬性的裝備，直接計算
                    eq_ids = [eq.id for eq in combo]
                    result = self.calculate_combination(eq_ids, guardian_class, exotic_equipment)
                    
                    # 計算最佳加成分配
                    bonus_allocation = self._calculate_optimal_bonuses(
                        result["total_attributes"], target_attributes, preferred_attr
                    )
                    
                    # 應用加成到總屬性
                    final_attributes = result["total_attributes"].copy()
                    for attr, bonus_count in bonus_allocation.items():
                        final_attributes[attr] = final_attributes.get(attr, 0) + bonus_count * 10
                    
                    # 計算與目標的差距（使用應用加成後的屬性）
                    score = 0
                    all_met = True
                    for target_attr, target_value in target_attributes.items():
                        actual_value = final_attributes.get(target_attr, 0)
                        if actual_value < target_value:
                            all_met = False
                            score += (target_value - actual_value) ** 2
                        else:
                            score += (actual_value - target_value) * 0.1
                    
                    # 獲取偏好屬性值（如果指定了偏好）
                    preferred_value = final_attributes.get(preferred_attr, 0) if preferred_attr else 0
                    
                    # 選擇最佳組合：優先滿足目標，然後優化偏好屬性
                    is_better = False
                    if all_met:
                        # 如果都滿足目標
                        if best_score == float('inf'):
                            # 之前沒有滿足目標的組合
                            is_better = True
                        elif best_score > 0:
                            # 之前沒有滿足目標，現在滿足了
                            is_better = True
                        elif best_score == 0:
                            # 都滿足了目標，比較偏好屬性值
                            if preferred_attr:
                                if preferred_value > best_preferred_value:
                                    is_better = True
                            else:
                                # 沒有偏好屬性，選擇分數更小的（更接近目標）
                                if score < best_score:
                                    is_better = True
                    else:
                        # 如果沒滿足目標，只比較分數
                        if score < best_score:
                            is_better = True
                    
                    if is_better:
                        best_score = score if not all_met else 0
                        best_combination = eq_ids
                        best_result = result
                        best_penalty_configs = {}  # 沒有懲罰配置
                        best_bonus_allocation = bonus_allocation.copy()
                        best_preferred_value = preferred_value
                        
                        if all_met and score == 0:
                            # 更新結果中的總屬性（包含加成）
                            best_result["total_attributes"] = final_attributes
                            best_result["bonus_allocation"] = bonus_allocation
                            
                            return {
                                "found": True,
                                "combination": best_combination,
                                "result": best_result,
                                "bonus_allocation": bonus_allocation,
                                "target_attributes": target_attributes,
                                "message": "找到完全匹配的裝備組合"
                            }
        
        # 如果找到接近的組合
        if best_combination:
            # 應用最佳加成分配到結果
            final_attributes = best_result["total_attributes"].copy()
            for attr, bonus_count in best_bonus_allocation.items():
                final_attributes[attr] = final_attributes.get(attr, 0) + bonus_count * 10
            best_result["total_attributes"] = final_attributes
            best_result["bonus_allocation"] = best_bonus_allocation
            
            # 檢查是否所有目標都達到（使用應用加成後的屬性）
            all_targets_met = True
            missing_attrs = {}
            for target_attr, target_value in target_attributes.items():
                actual_value = final_attributes.get(target_attr, 0)
                if actual_value < target_value:
                    all_targets_met = False
                    missing_attrs[target_attr] = target_value - actual_value
            
            if all_targets_met:
                return {
                    "found": True,
                    "combination": best_combination,
                    "result": best_result,
                    "penalty_configs": best_penalty_configs,
                    "bonus_allocation": best_bonus_allocation,
                    "target_attributes": target_attributes,
                    "message": "找到達到目標的裝備組合（部分屬性超出）"
                }
            else:
                # 如果配不出來，分析需要的裝備（考慮加成後的屬性）
                # 在分析時，需要從缺少的屬性中減去加成提供的屬性
                adjusted_missing = missing_attrs.copy()
                for attr, bonus_count in best_bonus_allocation.items():
                    if attr in adjusted_missing:
                        adjusted_missing[attr] = max(0, adjusted_missing[attr] - bonus_count * 10)
                
                exotic_type = exotic_equipment.get("type") if exotic_equipment else None
                required_equipments = self._analyze_required_equipments(
                    target_attributes, best_result, guardian_class, adjusted_missing, exotic_type
                )
                return {
                    "found": False,
                    "best_combination": best_combination,
                    "best_result": best_result,
                    "penalty_configs": best_penalty_configs,
                    "bonus_allocation": best_bonus_allocation,
                    "target_attributes": target_attributes,
                    "missing_attributes": missing_attrs,
                    "required_equipments": required_equipments,
                    "message": f"無法完全達到目標，缺少屬性：{missing_attrs}"
                }
        
        # 如果完全找不到
        exotic_type = exotic_equipment.get("type") if exotic_equipment else None
        required_equipments = self._analyze_required_equipments(
            target_attributes, None, guardian_class, target_attributes, exotic_type
        )
        return {
            "found": False,
            "target_attributes": target_attributes,
            "required_equipments": required_equipments,
            "message": "無法找到接近目標的裝備組合"
        }
    
    def _analyze_required_equipments(self, target_attributes: Dict[str, float],
                                     current_result: Optional[Dict],
                                     guardian_class: GuardianClass,
                                     missing_attrs: Dict[str, float],
                                     exotic_type: Optional[str] = None) -> List[Dict]:
        """分析達到目標所需的裝備（推薦倉庫中沒有的裝備）"""
        
        inventory = self.inventory_manager.get_inventory(guardian_class)
        all_equipments = inventory.get_all_equipments()
        existing_types = set()  # 用於追蹤已推薦的裝備類型，避免重複
        
        # 計算當前已有的屬性值
        current_attrs = {}
        if current_result:
            current_attrs = current_result["total_attributes"]
        else:
            for attr in EQUIPMENT_ATTRIBUTES:
                current_attrs[attr] = 0
        
        # 計算還需要的屬性值
        needed_attrs = {}
        for attr, target_value in target_attributes.items():
            current_value = current_attrs.get(attr, 0)
            needed = target_value - current_value
            if needed > 0:
                needed_attrs[attr] = needed
        
        if not needed_attrs:
            return []
        
        # 生成推薦裝備配置（倉庫中沒有的）
        equipment_types = ["頭盔", "臂鎧", "胸鎧", "護腿", "職業物品"]
        # 排除異域裝備的部位
        if exotic_type and exotic_type in equipment_types:
            equipment_types = [t for t in equipment_types if t != exotic_type]
        recommended = []
        
        # 為每個需要的屬性生成推薦裝備
        for attr, needed_value in needed_attrs.items():
            if len(recommended) >= 3:
                break
            
            # 找出能提供該屬性的最佳標籤配置
            best_config = None
            best_score = 0
            
            for tag, (main_attr, sub_attr) in EQUIPMENT_TAGS.items():
                # 檢查這個標籤是否能提供需要的屬性
                contribution = 0
                if main_attr == attr:
                    contribution += 30  # 主詞條
                elif sub_attr == attr:
                    contribution += 25  # 副詞條
                
                # 如果主詞條或副詞條是目標屬性，可以考慮鎖定
                if main_attr == attr:
                    contribution += 5  # 鎖定可以額外+5
                
                if contribution > best_score:
                    # 選擇一個未推薦過的裝備類型
                    for eq_type in equipment_types:
                        if eq_type not in existing_types:
                            # 選擇隨機詞條（不能與主詞條、副詞條重複）
                            available_random = [a for a in EQUIPMENT_ATTRIBUTES 
                                              if a not in [main_attr, sub_attr]]
                            if available_random:
                                random_stat = available_random[0]
                                
                                # 計算滿級屬性
                                max_attrs = {}
                                max_attrs[main_attr] = 35 if main_attr == attr else 30  # 如果鎖定目標屬性則+5
                                max_attrs[sub_attr] = 25
                                max_attrs[random_stat] = 20
                                
                                # 補充詞條（滿級時為5）
                                for supplement_attr in EQUIPMENT_ATTRIBUTES:
                                    if supplement_attr not in [main_attr, sub_attr, random_stat]:
                                        max_attrs[supplement_attr] = MAX_UPGRADE_LEVEL
                                
                                # 計算對所需屬性的貢獻
                                total_contribution = max_attrs.get(attr, 0)
                                
                                if total_contribution > 0 and total_contribution >= best_score:
                                    best_score = total_contribution
                                    best_config = {
                                        "type": eq_type,
                                        "tag": tag,
                                        "random_stat": random_stat,
                                        "locked_attr": attr if main_attr == attr else None,
                                        "attributes": max_attrs,
                                        "contribution": total_contribution
                                    }
                            break
            
            if best_config:
                # 計算對所有所需屬性的貢獻
                contributions = {}
                for needed_attr, needed_val in needed_attrs.items():
                    attr_value = best_config["attributes"].get(needed_attr, 0)
                    contributions[needed_attr] = min(attr_value, needed_val)
                
                recommended.append({
                    "name": f"{best_config['tag']}_{best_config['type']}",
                    "type": best_config["type"],
                    "tag": best_config["tag"],
                    "random_stat": best_config["random_stat"],
                    "locked_attr": best_config["locked_attr"],
                    "attributes": {k: v for k, v in best_config["attributes"].items() if v > 0},
                    "contributions": contributions,
                    "score": sum(contributions.values())
                })
                # 標記這個裝備類型已被使用
                existing_types.add(best_config["type"])
        
        # 如果還需要更多裝備，生成通用的高屬性裝備
        while len(recommended) < 3 and len(recommended) < len(equipment_types):
            # 找出還需要的屬性
            remaining_needs = {}
            for attr, needed_value in needed_attrs.items():
                provided = sum(r["contributions"].get(attr, 0) for r in recommended)
                remaining = needed_value - provided
                if remaining > 0:
                    remaining_needs[attr] = remaining
            
            if not remaining_needs:
                break
            
            # 找出能提供最多剩餘需求的標籤
            best_tag = None
            best_attr = max(remaining_needs.items(), key=lambda x: x[1])[0]
            
            for tag, (main_attr, sub_attr) in EQUIPMENT_TAGS.items():
                if main_attr == best_attr or sub_attr == best_attr:
                    best_tag = tag
                    break
            
            if not best_tag:
                # 如果沒有匹配的標籤，選擇第一個
                best_tag = list(EQUIPMENT_TAGS.keys())[0]
                main_attr, sub_attr = EQUIPMENT_TAGS[best_tag]
            
            # 選擇一個未使用的裝備類型
            for eq_type in equipment_types:
                if eq_type not in existing_types:
                    available_random = [a for a in EQUIPMENT_ATTRIBUTES 
                                      if a not in [main_attr, sub_attr]]
                    if available_random:
                        random_stat = available_random[0]
                        
                        # 計算滿級屬性
                        max_attrs = {}
                        max_attrs[main_attr] = 30
                        max_attrs[sub_attr] = 25
                        max_attrs[random_stat] = 20
                        
                        # 補充詞條
                        for supplement_attr in EQUIPMENT_ATTRIBUTES:
                            if supplement_attr not in [main_attr, sub_attr, random_stat]:
                                max_attrs[supplement_attr] = MAX_UPGRADE_LEVEL
                        
                        # 計算貢獻
                        contributions = {}
                        for needed_attr, needed_val in needed_attrs.items():
                            attr_value = max_attrs.get(needed_attr, 0)
                            contributions[needed_attr] = min(attr_value, needed_val)
                        
                        recommended.append({
                            "name": f"{best_tag}_{eq_type}",
                            "type": eq_type,
                            "tag": best_tag,
                            "random_stat": random_stat,
                            "locked_attr": None,
                            "attributes": {k: v for k, v in max_attrs.items() if v > 0},
                            "contributions": contributions,
                            "score": sum(contributions.values())
                        })
                        existing_types.add(eq_type)
                        break
        
        # 按分數排序，取前3個
        recommended.sort(key=lambda x: x["score"], reverse=True)
        return recommended[:3]
    
    def _calculate_optimal_bonuses(self, base_attributes: Dict[str, float], 
                                   target_attributes: Dict[str, float],
                                   preferred_attr: Optional[str] = None) -> Dict[str, int]:
        """計算最佳的5個數值加成分配（每個+10，總共5個）
        
        Args:
            base_attributes: 基礎屬性（裝備提供的屬性）
            target_attributes: 目標屬性
            
        Returns:
            加成分配字典，例如 {"近戰": 3, "超能力": 2} 表示3個近戰加成，2個超能力加成
        """
        # 計算每個目標屬性還需要多少
        needed = {}
        for attr, target_value in target_attributes.items():
            base_value = base_attributes.get(attr, 0)
            need = max(0, target_value - base_value)
            if need > 0:
                needed[attr] = need
        
        if not needed:
            # 如果所有目標都已達成，將加成分配給偏好屬性（如果指定），否則平均分配
            bonus_allocation = {}
            for attr in target_attributes.keys():
                bonus_allocation[attr] = 0
            
            total_bonuses = 5
            if preferred_attr and preferred_attr in EQUIPMENT_ATTRIBUTES:
                # 如果有偏好屬性，將所有加成分配給偏好屬性
                bonus_allocation[preferred_attr] = total_bonuses
            else:
                # 否則平均分配給目標屬性
                for attr in target_attributes.keys():
                    bonus_allocation[attr] = total_bonuses // len(target_attributes)
                remaining = total_bonuses % len(target_attributes)
                for i, attr in enumerate(target_attributes.keys()):
                    if i < remaining:
                        bonus_allocation[attr] += 1
            return bonus_allocation
        
        # 計算每個屬性需要多少個加成（向上取整）
        bonus_allocation = {}
        total_bonuses = 5
        
        # 初始化所有目標屬性的加成為0
        for attr in target_attributes.keys():
            bonus_allocation[attr] = 0
        
        # 如果偏好屬性不在目標屬性中，也初始化它
        if preferred_attr and preferred_attr not in target_attributes:
            bonus_allocation[preferred_attr] = 0
        
        # 按需求比例分配（只分配給有需求的目標屬性）
        total_need = sum(needed.values())
        if total_need > 0:
            # 先計算需要多少加成才能滿足所有目標
            total_bonuses_needed = 0
            for attr, need_value in needed.items():
                # 每個加成+10，所以需要的加成數 = ceil(need_value / 10)
                bonuses_needed = int((need_value + 9) // 10)  # 向上取整
                bonus_allocation[attr] = bonuses_needed
                total_bonuses_needed += bonuses_needed
            
            # 如果需要的加成超過5個，按比例縮減
            if total_bonuses_needed > total_bonuses:
                # 按比例縮減，但確保至少每個有需求的屬性都有1個（如果可能）
                # 先嘗試給每個有需求的屬性分配1個
                for attr in needed.keys():
                    bonus_allocation[attr] = 1
                current_total = len(needed)
                
                # 如果還是超過，按比例縮減
                if current_total > total_bonuses:
                    scale = total_bonuses / current_total
                    for attr in needed.keys():
                        bonus_allocation[attr] = max(0, int(bonus_allocation[attr] * scale))
                    current_total = sum(bonus_allocation.values())
                
                # 如果還有剩餘，按需求比例分配
                remaining = total_bonuses - current_total
                if remaining > 0:
                    sorted_needs = sorted(needed.items(), key=lambda x: x[1], reverse=True)
                    for attr, need_value in sorted_needs:
                        if remaining <= 0:
                            break
                        bonus_allocation[attr] = bonus_allocation.get(attr, 0) + 1
                        remaining -= 1
            else:
                # 如果需要的加成不超過5個，剩餘的給偏好屬性
                current_total = sum(bonus_allocation.values())
                remaining = total_bonuses - current_total
                if remaining > 0:
                    if preferred_attr and preferred_attr in EQUIPMENT_ATTRIBUTES:
                        # 將剩餘加成全部給偏好屬性
                        bonus_allocation[preferred_attr] = bonus_allocation.get(preferred_attr, 0) + remaining
                    elif needed:
                        # 沒有偏好屬性，按需求比例分配剩餘的加成
                        sorted_needs = sorted(needed.items(), key=lambda x: x[1], reverse=True)
                        for attr, need_value in sorted_needs:
                            if remaining <= 0:
                                break
                            bonus_allocation[attr] = bonus_allocation.get(attr, 0) + 1
                            remaining -= 1
        else:
            # 如果所有目標都已達成，將所有加成給偏好屬性
            if preferred_attr and preferred_attr in EQUIPMENT_ATTRIBUTES:
                bonus_allocation[preferred_attr] = total_bonuses
            else:
                # 沒有偏好屬性，平均分配給目標屬性
                for attr in target_attributes.keys():
                    bonus_allocation[attr] = total_bonuses // len(target_attributes)
                remaining = total_bonuses % len(target_attributes)
                for i, attr in enumerate(target_attributes.keys()):
                    if i < remaining:
                        bonus_allocation[attr] += 1
        
        # 確保所有目標屬性都在分配中（即使為0）
        for attr in target_attributes.keys():
            if attr not in bonus_allocation:
                bonus_allocation[attr] = 0
        
        return bonus_allocation
    
    def _generate_penalty_combinations(self, locked_equipments: List[Equipment]) -> List[Dict[str, str]]:
        """為有鎖定屬性的裝備生成懲罰屬性組合"""
        if not locked_equipments:
            return [{}]
        
        # 為每個裝備生成可選的懲罰屬性（排除鎖定屬性本身）
        equipment_options = []
        for eq in locked_equipments:
            options = [attr for attr in EQUIPMENT_ATTRIBUTES if attr != eq.locked_attr]
            equipment_options.append((eq.id, options))
        
        # 生成所有可能的組合（使用笛卡爾積）
        configs = []
        for combo in product(*[options for _, options in equipment_options]):
            config = {eq_id: combo[i] for i, (eq_id, _) in enumerate(equipment_options)}
            configs.append(config)
        
        return configs
    
    def _reapply_lock_effect(self, equipment: Equipment):
        """臨時應用鎖定效果（當懲罰屬性改變時）
        
        注意：此方法會臨時修改裝備的屬性，但由於我們現在不在創建時應用效果，
        裝備的基礎屬性已經是正確的，所以這裡只需要臨時設置懲罰屬性即可。
        實際的鎖定和懲罰效果會在 get_max_level_attributes() 中正確計算。
        
        此方法現在只是一個佔位符，實際效果由 get_max_level_attributes() 處理。
        """
        # 不再需要修改裝備屬性，因為鎖定和懲罰效果只在計算時應用
        # 只需要確保 penalty_attr 被設置即可
        pass
    
    def format_target_result(self, result: Dict) -> str:
        """格式化目標匹配結果為可讀字符串"""
        lines = []
        lines.append("=" * 60)
        lines.append("【目標屬性匹配結果】")
        lines.append("=" * 60)
        
        # 顯示目標屬性
        lines.append("\n【目標屬性】")
        for attr, value in result.get("target_attributes", {}).items():
            lines.append(f"  {attr}: {value:.0f}")
        
        if result.get("found"):
            # 找到組合
            lines.append(f"\n✓ {result.get('message', '找到裝備組合')}")
            
            # 顯示數值加成分配（如果有）
            if "bonus_allocation" in result and result["bonus_allocation"]:
                lines.append("\n【數值加成分配（5個加成，每個+10）】")
                total_bonuses = 0
                for attr, bonus_count in result["bonus_allocation"].items():
                    if bonus_count > 0:
                        lines.append(f"  {attr}: {bonus_count}個加成 = +{bonus_count * 10}")
                        total_bonuses += bonus_count
                if total_bonuses < 5:
                    lines.append(f"  剩餘 {5 - total_bonuses} 個加成未分配")
            
            # 顯示懲罰屬性配置（如果有）
            if "penalty_configs" in result and result["penalty_configs"]:
                lines.append("\n【懲罰屬性配置】")
                for eq_id, penalty_attr in result["penalty_configs"].items():
                    lines.append(f"  裝備 {eq_id}: 懲罰屬性 = {penalty_attr} (-5)")
            
            lines.append("\n【推薦裝備組合】")
            if "result" in result:
                formatted = self.format_result(result["result"])
                lines.append(formatted)
        else:
            # 未找到組合
            lines.append(f"\n✗ {result.get('message', '無法找到裝備組合')}")
            
            # 顯示最佳組合（如果有的話）
            if "best_result" in result:
                lines.append("\n【最接近的組合】")
                formatted = self.format_result(result["best_result"])
                lines.append(formatted)
                
                # 顯示數值加成分配（如果有）
                if "bonus_allocation" in result and result["bonus_allocation"]:
                    lines.append("\n【數值加成分配（5個加成，每個+10）】")
                    total_bonuses = 0
                    for attr, bonus_count in result["bonus_allocation"].items():
                        if bonus_count > 0:
                            lines.append(f"  {attr}: {bonus_count}個加成 = +{bonus_count * 10}")
                            total_bonuses += bonus_count
                    if total_bonuses < 5:
                        lines.append(f"  剩餘 {5 - total_bonuses} 個加成未分配")
                
                # 顯示缺少的屬性（已考慮加成）
                if "missing_attributes" in result:
                    lines.append("\n【缺少的屬性（已考慮加成）】")
                    for attr, value in result["missing_attributes"].items():
                        lines.append(f"  {attr}: 還需要 {value:.0f}")
            
            # 顯示所需裝備（倉庫中沒有的推薦裝備）
            if "required_equipments" in result and result["required_equipments"]:
                lines.append("\n【推薦裝備（倉庫中沒有的，最多3個）】")
                for i, req_eq in enumerate(result["required_equipments"], 1):
                    lines.append(f"\n  {i}. {req_eq['name']} ({req_eq['type']})")
                    if req_eq.get('tag'):
                        main_attr, sub_attr = EQUIPMENT_TAGS[req_eq['tag']]
                        lines.append(f"     標籤: {req_eq['tag']} (主詞條: {main_attr}, 副詞條: {sub_attr})")
                    if req_eq.get('random_stat'):
                        lines.append(f"     隨機詞條: {req_eq['random_stat']}")
                    if req_eq.get('locked_attr'):
                        lines.append(f"     鎖定屬性: {req_eq['locked_attr']} (+5)")
                    lines.append(f"     滿級屬性:")
                    for attr, value in sorted(req_eq.get('attributes', {}).items(), 
                                            key=lambda x: x[1], reverse=True):
                        if value > 0:
                            lines.append(f"       {attr}: {value:.0f}")
                    lines.append(f"     對目標屬性的貢獻:")
                    for attr, value in req_eq.get('contributions', {}).items():
                        if value > 0:
                            lines.append(f"       {attr}: +{value:.0f}")
                    lines.append(f"     總分: {req_eq.get('score', 0):.0f}")
        
        lines.append("=" * 60)
        return "\n".join(lines)
