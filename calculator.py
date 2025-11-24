"""
裝備組合數值計算器
"""
from typing import List, Dict, Optional
from itertools import product
from equipment import (
    Equipment, EQUIPMENT_ATTRIBUTES, EQUIPMENT_TAGS, MAX_UPGRADE_LEVEL,
    STAT_TYPE_MAIN, STAT_TYPE_SUB, STAT_TYPE_RANDOM, STAT_TYPE_SUPPLEMENT
)
from inventory import ClassInventoryManager
from classes import GuardianClass
from config import Config


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
        self._config_cache: Dict[str, List[Dict]] = {}  # 配置緩存

    def _calculate_base_after_replacement(self, base_total: Dict, old_attrs: Dict, new_attrs: Dict) -> Dict:
        """計算替換裝備後的基礎屬性

        Args:
            base_total: 當前總基礎屬性
            old_attrs: 被替換裝備的屬性
            new_attrs: 新裝備的屬性

        Returns:
            替換後的基礎屬性
        """
        new_base = {}
        for attr in EQUIPMENT_ATTRIBUTES:
            old_val = old_attrs.get(attr, 0)
            new_val = new_attrs.get(attr, 0)
            new_base[attr] = base_total.get(attr, 0) - old_val + new_val
        return new_base

    def _apply_bonuses_and_corrections(self, base_attrs: Dict, bonus_allocation: Dict) -> Dict:
        """應用加成和碎片修正到基礎屬性

        Args:
            base_attrs: 基礎屬性
            bonus_allocation: 加成分配

        Returns:
            最終屬性
        """
        final_total = base_attrs.copy()

        # 應用加成
        for attr, bonus_count in bonus_allocation.items():
            final_total[attr] = final_total.get(attr, 0) + bonus_count * 10

        # 應用碎片修正
        if hasattr(self, '_fragment_corrections') and self._fragment_corrections:
            for attr, correction in self._fragment_corrections.items():
                final_total[attr] = final_total.get(attr, 0) + correction

        return final_total

    def _check_targets_met(self, final_total: Dict, target_attributes: Dict) -> tuple:
        """檢查是否達成所有目標

        Args:
            final_total: 最終屬性
            target_attributes: 目標屬性

        Returns:
            (all_met: bool, remaining: float) - 是否全部達成，剩餘點數
        """
        all_met = True
        remaining = 0

        for attr, target_val in target_attributes.items():
            actual_val = final_total.get(attr, 0)
            if actual_val < target_val:
                all_met = False
                remaining -= (target_val - actual_val)
            else:
                remaining += actual_val - target_val

        return all_met, remaining
    
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
                                   preferred_attr: Optional[str] = None,
                                   fragment_corrections: Optional[Dict[str, float]] = None) -> Dict:
        """根據目標屬性值尋找裝備組合"""
        inventory = self.inventory_manager.get_inventory(guardian_class)
        all_equipments = inventory.get_all_equipments()

        # 保存碎片修正以便後續使用
        self._fragment_corrections = fragment_corrections or {}

        if len(all_equipments) == 0 and not exotic_equipment:
            return {
                "found": False,
                "message": "倉庫中沒有裝備",
                "required_equipments": []
            }

        # 按部位分組裝備
        equipments_by_type: Dict[str, List[Equipment]] = {eq_type: [] for eq_type in Config.EQUIPMENT_TYPES}
        for eq in all_equipments:
            if eq.type in equipments_by_type:
                equipments_by_type[eq.type].append(eq)

        # 確定需要填充的部位
        if exotic_equipment:
            exotic_type = exotic_equipment.get("type")
            required_types = [t for t in Config.EQUIPMENT_TYPES if t != exotic_type]
        else:
            required_types = Config.EQUIPMENT_TYPES.copy()

        # 檢查是否每個需要的部位都有裝備
        missing_types = [t for t in required_types if len(equipments_by_type[t]) == 0]
        if missing_types:
            return {
                "found": False,
                "message": f"缺少以下部位的裝備: {', '.join(missing_types)}",
                "required_equipments": [],
                "missing_types": missing_types
            }

        # 對每個部位的裝備按效益排序，並限制數量
        MAX_PER_TYPE = 10  # 每個部位最多考慮10件裝備（增加搜索廣度）
        target_attr_set = set(target_attributes.keys())

        for eq_type in required_types:
            # 計算裝備的效益分數：目標貢獻 - 浪費懲罰
            def calculate_efficiency(eq, targets=target_attr_set):
                max_level_attrs = eq.get_max_level_attributes()
                # 對目標屬性的貢獻
                contribution = sum(max_level_attrs.get(attr, 0) for attr in targets)
                # 在非目標屬性上的浪費（只計算主副詞條的浪費，補充詞條不算）
                waste = 0
                if eq.tag and eq.tag in EQUIPMENT_TAGS:
                    main_attr, sub_attr = EQUIPMENT_TAGS[eq.tag]
                    if main_attr not in targets:
                        waste += max_level_attrs.get(main_attr, 0)
                    if sub_attr not in targets:
                        waste += max_level_attrs.get(sub_attr, 0)
                # 效益 = 貢獻 - 浪費
                return contribution - waste

            # 總是排序，確保最佳裝備在前
            equipments_by_type[eq_type].sort(key=calculate_efficiency, reverse=True)
            # 限制數量
            if len(equipments_by_type[eq_type]) > MAX_PER_TYPE:
                equipments_by_type[eq_type] = equipments_by_type[eq_type][:MAX_PER_TYPE]

        # 初始化最佳結果
        best_combination = None
        best_score = float('inf')
        best_result = None
        best_penalty_configs = {}
        best_preferred_value = -1
        best_bonus_allocation = {}

        # 使用笛卡爾積生成所有可能的組合（每個部位選一件）
        type_equipment_lists = [equipments_by_type[t] for t in required_types]

        # 添加搜索計數限制
        MAX_COMBINATIONS_TO_CHECK = 20000  # 增加搜索上限以找到更多可能的組合
        combinations_checked = 0

        for combo in product(*type_equipment_lists):
            # 檢查組合數量限制
            if combinations_checked >= MAX_COMBINATIONS_TO_CHECK:
                break

            # 找出有鎖定但沒有懲罰屬性的裝備
            locked_equipments = [eq for eq in combo if eq.locked_attr and not eq.penalty_attr]

            # 如果有需要選擇懲罰屬性的裝備，嘗試不同的懲罰屬性組合
            if locked_equipments:
                penalty_combinations = self._generate_penalty_combinations(locked_equipments, target_attributes)

                # 限制懲罰屬性組合數量，避免過多計算
                MAX_PENALTY_COMBINATIONS = 50  # 增加懲罰屬性組合上限
                if len(penalty_combinations) > MAX_PENALTY_COMBINATIONS:
                    penalty_combinations = penalty_combinations[:MAX_PENALTY_COMBINATIONS]

                # 嘗試每種懲罰屬性組合
                for penalty_config in penalty_combinations:
                    # 檢查組合數量限制
                    if combinations_checked >= MAX_COMBINATIONS_TO_CHECK:
                        break

                    combinations_checked += 1
                    # 臨時設置懲罰屬性
                    original_penalties = {}
                    for eq in locked_equipments:
                        if eq.id in penalty_config:
                            original_penalties[eq.id] = eq.penalty_attr
                            eq.penalty_attr = penalty_config[eq.id]

                    try:
                        eq_ids = [eq.id for eq in combo]
                        result = self.calculate_combination(eq_ids, guardian_class, exotic_equipment)

                        # 計算當前最佳裝備數量
                        current_best_count = best_result["equipment_count"] if best_result else 0

                        # 使用統一的評估方法
                        eval_result = self._evaluate_combination(
                            result, target_attributes, preferred_attr, best_score,
                            current_best_count, best_preferred_value, exotic_equipment
                        )

                        if eval_result["is_better"]:
                            best_score = eval_result["score"]
                            best_combination = eq_ids
                            best_result = result
                            best_penalty_configs = penalty_config.copy()
                            best_bonus_allocation = eval_result["bonus_allocation"].copy()
                            best_preferred_value = eval_result["preferred_value"]

                            # 如果完全匹配，立即返回
                            if eval_result["all_met"] and eval_result["score"] == 0:
                                # 還原懲罰屬性
                                for eq in locked_equipments:
                                    if eq.id in original_penalties:
                                        eq.penalty_attr = original_penalties[eq.id]

                                # 更新結果中的總屬性（包含加成）
                                best_result["total_attributes"] = eval_result["final_attributes"]
                                best_result["bonus_allocation"] = eval_result["bonus_allocation"]

                                return {
                                    "found": True,
                                    "combination": best_combination,
                                    "result": best_result,
                                    "penalty_configs": best_penalty_configs,
                                    "bonus_allocation": eval_result["bonus_allocation"],
                                    "target_attributes": target_attributes,
                                    "fragment_corrections": self._fragment_corrections,
                                    "message": "找到完全匹配的裝備組合"
                                }
                    finally:
                        # 還原懲罰屬性
                        for eq in locked_equipments:
                            if eq.id in original_penalties:
                                eq.penalty_attr = original_penalties[eq.id]
            else:
                # 沒有需要選擇懲罰屬性的裝備，直接計算
                combinations_checked += 1
                eq_ids = [eq.id for eq in combo]
                result = self.calculate_combination(eq_ids, guardian_class, exotic_equipment)

                # 計算當前最佳裝備數量
                current_best_count = best_result["equipment_count"] if best_result else 0

                # 使用統一的評估方法
                eval_result = self._evaluate_combination(
                    result, target_attributes, preferred_attr, best_score,
                    current_best_count, best_preferred_value, exotic_equipment
                )

                if eval_result["is_better"]:
                    best_score = eval_result["score"]
                    best_combination = eq_ids
                    best_result = result
                    best_penalty_configs = {}  # 沒有懲罰配置
                    best_bonus_allocation = eval_result["bonus_allocation"].copy()
                    best_preferred_value = eval_result["preferred_value"]

                    # 早期終止：如果找到完全匹配的結果，立即返回
                    if eval_result["all_met"] and eval_result["score"] == 0:
                        # 更新結果中的總屬性（包含加成）
                        best_result["total_attributes"] = eval_result["final_attributes"]
                        best_result["bonus_allocation"] = eval_result["bonus_allocation"]

                        return {
                            "found": True,
                            "combination": best_combination,
                            "result": best_result,
                            "bonus_allocation": eval_result["bonus_allocation"],
                            "target_attributes": target_attributes,
                            "fragment_corrections": self._fragment_corrections,
                            "message": "找到完全匹配的裝備組合"
                        }
                        
        
        # 如果找到接近的組合
        if best_combination:
            # 應用最佳加成分配到結果
            final_attributes = best_result["total_attributes"].copy()
            for attr, bonus_count in best_bonus_allocation.items():
                final_attributes[attr] = final_attributes.get(attr, 0) + bonus_count * 10

            # 應用碎片修正
            if self._fragment_corrections:
                for attr, correction in self._fragment_corrections.items():
                    final_attributes[attr] = final_attributes.get(attr, 0) + correction

            best_result["total_attributes"] = final_attributes
            best_result["bonus_allocation"] = best_bonus_allocation

            # 檢查是否所有目標都達到（使用應用加成和碎片修正後的屬性）
            all_targets_met = True
            missing_attrs = {}
            for target_attr, target_value in target_attributes.items():
                actual_value = final_attributes.get(target_attr, 0)
                if actual_value < target_value:
                    all_targets_met = False
                    missing_attrs[target_attr] = target_value - actual_value
            
            if all_targets_met:
                message = "找到達到目標的裝備組合（部分屬性超出）"
                if combinations_checked >= MAX_COMBINATIONS_TO_CHECK:
                    message += "（已達搜索上限，結果可能不是最優）"
                return {
                    "found": True,
                    "combination": best_combination,
                    "result": best_result,
                    "penalty_configs": best_penalty_configs,
                    "bonus_allocation": best_bonus_allocation,
                    "target_attributes": target_attributes,
                    "fragment_corrections": self._fragment_corrections,
                    "message": message
                }
            else:
                # 如果配不出來，分析需要的裝備
                exotic_type = exotic_equipment.get("type") if exotic_equipment else None
                required_equipments = self._analyze_required_equipments(
                    target_attributes, best_result, guardian_class, missing_attrs, exotic_type, preferred_attr
                )
                message = f"無法完全達到目標，缺少屬性：{missing_attrs}"
                if combinations_checked >= MAX_COMBINATIONS_TO_CHECK:
                    message += "（已達搜索上限，可能還有更好的組合）"
                return {
                    "found": False,
                    "best_combination": best_combination,
                    "best_result": best_result,
                    "penalty_configs": best_penalty_configs,
                    "bonus_allocation": best_bonus_allocation,
                    "target_attributes": target_attributes,
                    "fragment_corrections": self._fragment_corrections,
                    "missing_attributes": missing_attrs,
                    "required_equipments": required_equipments,
                    "message": message
                }
        
        # 如果完全找不到
        exotic_type = exotic_equipment.get("type") if exotic_equipment else None
        required_equipments = self._analyze_required_equipments(
            target_attributes, None, guardian_class, target_attributes, exotic_type, preferred_attr
        )
        return {
            "found": False,
            "target_attributes": target_attributes,
            "fragment_corrections": self._fragment_corrections,
            "required_equipments": required_equipments,
            "message": "無法找到接近目標的裝備組合"
        }
    
    def _analyze_required_equipments(self, target_attributes: Dict[str, float],
                                     current_result: Optional[Dict],
                                     guardian_class: GuardianClass,
                                     missing_attrs: Dict[str, float],
                                     exotic_type: Optional[str] = None,
                                     preferred_attr: Optional[str] = None) -> List[Dict]:
        """分析達到目標所需的裝備替換建議

        邏輯：
        1. 先嘗試替換 1 件裝備能否達成目標
        2. 如果不行，嘗試替換 2 件
        3. 找到能達成目標的最少替換方案
        4. 不能替換異域裝備
        """
        if not current_result or not missing_attrs:
            return []

        # 獲取當前組合的裝備詳情
        current_equipments = current_result.get("equipment_details", [])
        if not current_equipments:
            return []

        # 計算基礎屬性（不含加成）- 從裝備詳情直接加總
        base_total = {}
        for attr in EQUIPMENT_ATTRIBUTES:
            base_total[attr] = 0
        for eq in current_equipments:
            for attr, value in eq.get("attributes", {}).items():
                base_total[attr] = base_total.get(attr, 0) + value

        # 過濾可替換的裝備（排除異域）
        replaceable = [eq for eq in current_equipments if not eq.get("is_exotic")]

        # 嘗試替換 1 件
        one_replace_solutions = []
        one_replace_improvements = []  # 不能達成但有改善的方案
        for eq in replaceable:
            solution = self._try_single_replacement(
                eq, base_total, target_attributes, missing_attrs, preferred_attr
            )
            if solution:
                if solution.get("can_achieve"):
                    one_replace_solutions.append(solution)
                else:
                    one_replace_improvements.append(solution)

        # 如果有能達成目標的單件替換方案
        if one_replace_solutions:
            # 按剩餘點數排序（越多越好，代表浪費越少）
            one_replace_solutions.sort(key=lambda x: x.get("remaining_points", 0), reverse=True)
            return [{
                "num_replacements": 1,
                "message": "需替換 1 件裝備達成目標",
                "replacements": [one_replace_solutions[0]]
            }]

        # 嘗試替換 2 件
        from itertools import combinations as iter_combinations
        two_replace_solutions = []

        for eq_pair in iter_combinations(replaceable, 2):
            solution = self._try_multi_replacement(
                eq_pair, base_total, target_attributes, missing_attrs, preferred_attr
            )
            if solution:
                two_replace_solutions.append(solution)

        if two_replace_solutions:
            # 按剩餘點數排序
            two_replace_solutions.sort(key=lambda x: x.get("remaining_points", 0), reverse=True)
            return [{
                "num_replacements": 2,
                "message": "需替換 2 件裝備達成目標",
                "replacements": two_replace_solutions[0]["replacements"],
                "new_total": two_replace_solutions[0].get("new_total", {})
            }]

        # 嘗試替換 3 件
        three_replace_solutions = []
        for eq_triple in iter_combinations(replaceable, 3):
            solution = self._try_multi_replacement(
                eq_triple, base_total, target_attributes, missing_attrs, preferred_attr
            )
            if solution:
                three_replace_solutions.append(solution)

        if three_replace_solutions:
            three_replace_solutions.sort(key=lambda x: x.get("remaining_points", 0), reverse=True)
            return [{
                "num_replacements": 3,
                "message": "需替換 3 件裝備達成目標",
                "replacements": three_replace_solutions[0]["replacements"],
                "new_total": three_replace_solutions[0].get("new_total", {})
            }]

        # 嘗試替換 4 件
        four_replace_solutions = []
        for eq_quad in iter_combinations(replaceable, 4):
            solution = self._try_multi_replacement(
                eq_quad, base_total, target_attributes, missing_attrs, preferred_attr
            )
            if solution:
                four_replace_solutions.append(solution)

        if four_replace_solutions:
            four_replace_solutions.sort(key=lambda x: x.get("remaining_points", 0), reverse=True)
            return [{
                "num_replacements": 4,
                "message": "需替換 4 件裝備達成目標",
                "replacements": four_replace_solutions[0]["replacements"],
                "new_total": four_replace_solutions[0].get("new_total", {})
            }]

        # 嘗試替換全部 5 件
        if len(replaceable) == 5:
            solution = self._try_multi_replacement(
                tuple(replaceable), base_total, target_attributes, missing_attrs, preferred_attr
            )
            if solution:
                return [{
                    "num_replacements": 5,
                    "message": "需替換 5 件裝備達成目標",
                    "replacements": solution["replacements"],
                    "new_total": solution.get("new_total", {})
                }]

        # 如果全部替換都無法達成，返回空（表示需要入手新裝備）
        return []

    def _try_single_replacement(self, eq: Dict, base_total: Dict,
                                 target_attributes: Dict, missing_attrs: Dict,
                                 preferred_attr: Optional[str] = None) -> Optional[Dict]:
        """嘗試替換單件裝備，返回能達成目標的方案

        Args:
            eq: 要被替換的裝備
            base_total: 當前組合的基礎屬性（不含加成）
            target_attributes: 目標屬性
            missing_attrs: 缺少的屬性
            preferred_attr: 偏好屬性
        """
        eq_type = eq["type"]
        eq_attrs = eq.get("attributes", {})

        # 獲取所有候選替換配置
        candidate_configs = self._find_replacement_configs(
            eq_type, target_attributes
        )

        if not candidate_configs:
            return None

        # 嘗試每個配置，找到能達成目標的
        best_result = None
        best_remaining = float('-inf')

        for config in candidate_configs:
            # 使用輔助函數計算替換後的基礎屬性
            new_base = self._calculate_base_after_replacement(base_total, eq_attrs, config["attributes"])

            # 計算最佳加成分配（考慮偏好屬性）
            bonus_allocation = self._calculate_optimal_bonuses(new_base, target_attributes, preferred_attr)

            # 使用輔助函數應用加成和碎片修正
            final_total = self._apply_bonuses_and_corrections(new_base, bonus_allocation)

            # 使用輔助函數檢查是否達成所有目標
            all_met, _ = self._check_targets_met(final_total, target_attributes)

            if all_met:
                # 計算剩餘點數（目標達成後的溢出）
                remaining = 0
                for attr, target_val in target_attributes.items():
                    remaining += final_total.get(attr, 0) - target_val

                if remaining > best_remaining:
                    best_remaining = remaining
                    best_result = {
                        "replace_type": eq_type,
                        "original_name": eq.get("name", "未知"),
                        "name": f"{config['tag']}_{eq_type}",
                        "type": eq_type,
                        "tag": config["tag"],
                        "random_stat": config["random_stat"],
                        "locked_attr": config["locked_attr"],
                        "attributes": config["attributes"],
                        "new_total": final_total,
                        "can_achieve": True,
                        "remaining_points": remaining
                    }

        if best_result:
            return best_result

        # 如果沒有找到能達成目標的配置，返回改善最多的
        # 使用第一個配置作為默認
        best_replacement = candidate_configs[0]

        # 使用輔助函數計算替換後的基礎屬性
        new_base = self._calculate_base_after_replacement(base_total, eq_attrs, best_replacement["attributes"])

        # 計算最佳加成分配（考慮偏好屬性）
        bonus_allocation = self._calculate_optimal_bonuses(new_base, target_attributes, preferred_attr)

        # 使用輔助函數應用加成和碎片修正
        final_total = self._apply_bonuses_and_corrections(new_base, bonus_allocation)

        # 使用輔助函數檢查是否達成所有目標
        all_met, _ = self._check_targets_met(final_total, target_attributes)

        if not all_met:
            # 計算改善程度（用於排序）
            # 計算原本加成後的屬性
            old_bonus = self._calculate_optimal_bonuses(base_total, target_attributes, preferred_attr)
            old_final = base_total.copy()
            for attr, bonus_count in old_bonus.items():
                old_final[attr] = old_final.get(attr, 0) + bonus_count * 10

            improvement = 0
            for attr, missing in missing_attrs.items():
                old_val = old_final.get(attr, 0)
                new_val = final_total.get(attr, 0)
                improvement += (new_val - old_val)

            return {
                "replace_type": eq_type,
                "original_name": eq.get("name", "未知"),
                "name": f"{best_replacement['tag']}_{eq_type}",
                "type": eq_type,
                "tag": best_replacement["tag"],
                "random_stat": best_replacement["random_stat"],
                "locked_attr": best_replacement["locked_attr"],
                "attributes": best_replacement["attributes"],
                "new_total": final_total,
                "can_achieve": False,
                "remaining_points": improvement
            }

        # 計算剩餘點數（目標達成後的溢出）
        remaining = 0
        for attr, target_val in target_attributes.items():
            remaining += final_total.get(attr, 0) - target_val

        return {
            "replace_type": eq_type,
            "original_name": eq.get("name", "未知"),
            "name": f"{best_replacement['tag']}_{eq_type}",
            "type": eq_type,
            "tag": best_replacement["tag"],
            "random_stat": best_replacement["random_stat"],
            "locked_attr": best_replacement["locked_attr"],
            "attributes": best_replacement["attributes"],
            "new_total": final_total,
            "can_achieve": True,
            "remaining_points": remaining
        }

    def _try_multi_replacement(self, eq_list: tuple, base_total: Dict,
                                target_attributes: Dict, missing_attrs: Dict,
                                preferred_attr: Optional[str] = None) -> Optional[Dict]:
        """嘗試替換多件裝備，返回能達成目標的方案

        Args:
            eq_list: 要被替換的裝備列表
            base_total: 當前組合的基礎屬性（不含加成）
            target_attributes: 目標屬性
            missing_attrs: 缺少的屬性
            preferred_attr: 偏好屬性
        """
        # 計算移除所有裝備後的基礎屬性
        total_after_removal = {}
        for attr in EQUIPMENT_ATTRIBUTES:
            val = base_total.get(attr, 0)
            for eq in eq_list:
                val -= eq.get("attributes", {}).get(attr, 0)
            total_after_removal[attr] = val

        # 獲取每個部位的所有可能配置
        all_configs = []
        for eq in eq_list:
            configs = self._find_replacement_configs(eq["type"], target_attributes)
            if not configs:
                return None
            all_configs.append((eq, configs))

        # 限制每個部位的配置數量以避免組合爆炸
        # 對於3件以上，使用更少的配置
        num_slots = len(eq_list)
        if num_slots <= 3:
            MAX_CONFIGS_PER_SLOT = 15
        elif num_slots == 4:
            MAX_CONFIGS_PER_SLOT = 8
        else:
            MAX_CONFIGS_PER_SLOT = 5

        limited_configs = []
        for eq, configs in all_configs:
            limited_configs.append((eq, configs[:MAX_CONFIGS_PER_SLOT]))

        # 使用笛卡爾積嘗試所有配置組合
        config_lists = [configs for _, configs in limited_configs]

        best_result = None
        best_remaining = float('-inf')

        for combo in product(*config_lists):
            # 計算替換後的總屬性
            new_total = total_after_removal.copy()
            for replacement in combo:
                for attr in EQUIPMENT_ATTRIBUTES:
                    new_total[attr] = new_total.get(attr, 0) + replacement["attributes"].get(attr, 0)

            # 計算最佳加成分配（考慮偏好屬性）
            bonus_allocation = self._calculate_optimal_bonuses(new_total, target_attributes, preferred_attr)

            # 使用輔助函數應用加成和碎片修正
            final_total = self._apply_bonuses_and_corrections(new_total, bonus_allocation)

            # 使用輔助函數檢查是否達成所有目標
            all_met, _ = self._check_targets_met(final_total, target_attributes)

            if all_met:
                # 計算剩餘點數
                remaining = 0
                for attr, target_val in target_attributes.items():
                    remaining += final_total.get(attr, 0) - target_val

                if remaining > best_remaining:
                    best_remaining = remaining
                    # 構建替換列表
                    replacements = []
                    for i, replacement in enumerate(combo):
                        eq = limited_configs[i][0]
                        replacements.append({
                            "replace_type": eq["type"],
                            "original_name": eq.get("name", "未知"),
                            "name": f"{replacement['tag']}_{eq['type']}",
                            "type": eq["type"],
                            "tag": replacement["tag"],
                            "random_stat": replacement["random_stat"],
                            "locked_attr": replacement["locked_attr"],
                            "attributes": replacement["attributes"]
                        })

                    best_result = {
                        "replacements": replacements,
                        "new_total": final_total,
                        "remaining_points": remaining
                    }

        return best_result

    def _find_replacement_configs(self, eq_type: str,
                                   target_attributes: Dict[str, float]) -> List[Dict]:
        """為指定部位找出所有可能的裝備配置

        Args:
            eq_type: 裝備類型
            target_attributes: 目標屬性

        Returns:
            配置列表，每個配置包含 tag, random_stat, locked_attr, attributes
        """
        # 使用緩存鍵
        cache_key = f"{eq_type}_{tuple(sorted(target_attributes.keys()))}"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]

        configs = []

        # 嘗試所有標籤和隨機詞條的組合
        for tag, (main_attr, sub_attr) in EQUIPMENT_TAGS.items():
            # 可用的隨機詞條（不能與主副詞條重複）
            available_random = [a for a in EQUIPMENT_ATTRIBUTES if a not in [main_attr, sub_attr]]

            # 嘗試每個可能的隨機詞條
            for random_stat in available_random:
                # 嘗試每個可能的鎖定屬性（包括不鎖定）
                lock_options = [None] + list(target_attributes.keys())

                for locked_attr in lock_options:
                    # 決定懲罰屬性
                    penalty_attr = None
                    if locked_attr:
                        # 優先選擇不在目標屬性中的屬性作為懲罰
                        for attr in EQUIPMENT_ATTRIBUTES:
                            if attr != locked_attr and attr not in target_attributes:
                                penalty_attr = attr
                                break
                        # 如果找不到，選擇任意非鎖定屬性
                        if not penalty_attr:
                            for attr in EQUIPMENT_ATTRIBUTES:
                                if attr != locked_attr:
                                    penalty_attr = attr
                                    break

                    # 計算滿級屬性
                    max_attrs = {}
                    for attr in EQUIPMENT_ATTRIBUTES:
                        if attr == main_attr:
                            base_val = 35.0 if attr == locked_attr else 30.0
                        elif attr == sub_attr:
                            base_val = 30.0 if attr == locked_attr else 25.0
                        elif attr == random_stat:
                            base_val = 25.0 if attr == locked_attr else 20.0
                        else:
                            base_val = 10.0 if attr == locked_attr else 5.0

                        # 應用懲罰
                        if attr == penalty_attr:
                            base_val -= 5.0

                        max_attrs[attr] = base_val

                    configs.append({
                        "tag": tag,
                        "random_stat": random_stat,
                        "locked_attr": locked_attr,
                        "attributes": max_attrs
                    })

        # 按對目標屬性的貢獻排序
        def calc_score(config):
            return sum(config["attributes"].get(attr, 0) for attr in target_attributes.keys())

        configs.sort(key=calc_score, reverse=True)

        # 存入緩存
        self._config_cache[cache_key] = configs
        return configs

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
    
    def _generate_penalty_combinations(self, locked_equipments: List[Equipment],
                                        target_attributes: Dict[str, float] = None) -> List[Dict[str, str]]:
        """為有鎖定屬性的裝備生成懲罰屬性組合

        Args:
            locked_equipments: 有鎖定屬性但沒有懲罰屬性的裝備列表
            target_attributes: 目標屬性，用於優先選擇非目標屬性作為懲罰
        """
        if not locked_equipments:
            return [{}]

        target_attrs = set(target_attributes.keys()) if target_attributes else set()

        # 為每個裝備生成可選的懲罰屬性
        # 優先選擇非目標屬性，排除鎖定屬性本身
        equipment_options = []
        for eq in locked_equipments:
            # 非目標屬性優先
            preferred = [attr for attr in EQUIPMENT_ATTRIBUTES
                        if attr != eq.locked_attr and attr not in target_attrs]
            # 目標屬性作為備選（不推薦）
            fallback = [attr for attr in EQUIPMENT_ATTRIBUTES
                       if attr != eq.locked_attr and attr in target_attrs]
            # 優先選項在前
            options = preferred + fallback
            equipment_options.append((eq.id, options))

        # 生成所有可能的組合（使用笛卡爾積）
        configs = []
        for combo in product(*[options for _, options in equipment_options]):
            config = {eq_id: combo[i] for i, (eq_id, _) in enumerate(equipment_options)}
            configs.append(config)

        # 按照懲罰目標屬性的數量排序（越少越好）
        def count_target_penalties(config):
            return sum(1 for penalty in config.values() if penalty in target_attrs)

        configs.sort(key=count_target_penalties)

        return configs

    def _evaluate_combination(self, result: Dict, target_attributes: Dict[str, float],
                              preferred_attr: Optional[str], best_score: float,
                              best_equipment_count: int, best_preferred_value: float,
                              exotic_equipment: Optional[Dict]) -> Dict:
        """評估組合是否比當前最佳更好

        Args:
            result: calculate_combination 的結果
            target_attributes: 目標屬性
            preferred_attr: 偏好屬性
            best_score: 當前最佳分數
            best_equipment_count: 當前最佳裝備數量
            best_preferred_value: 當前最佳偏好屬性值
            exotic_equipment: 異域裝備

        Returns:
            評估結果字典，包含 is_better, score, all_met, preferred_value,
            equipment_count, final_attributes, bonus_allocation
        """
        # 計算最佳加成分配
        bonus_allocation = self._calculate_optimal_bonuses(
            result["total_attributes"], target_attributes, preferred_attr
        )

        # 應用加成到總屬性
        final_attributes = result["total_attributes"].copy()
        for attr, bonus_count in bonus_allocation.items():
            final_attributes[attr] = final_attributes.get(attr, 0) + bonus_count * 10

        # 應用碎片修正
        if hasattr(self, '_fragment_corrections') and self._fragment_corrections:
            for attr, correction in self._fragment_corrections.items():
                final_attributes[attr] = final_attributes.get(attr, 0) + correction

        # 計算與目標的差距
        score = 0
        all_met = True
        target_attr_set = set(target_attributes.keys())

        for target_attr, target_value in target_attributes.items():
            actual_value = final_attributes.get(target_attr, 0)
            if actual_value < target_value:
                all_met = False
                score += (target_value - actual_value) ** 2
            else:
                score += (actual_value - target_value) * 0.1

        # 懲罰在非目標屬性上的浪費
        # 非目標屬性的數值都是浪費，因為總點數有限
        waste_penalty = 0
        for attr in EQUIPMENT_ATTRIBUTES:
            if attr not in target_attr_set:
                value = final_attributes.get(attr, 0)
                # 基礎補充詞條(每件5點，5件=25點)是不可避免的，超過的部分才是浪費
                base_supplement = 25  # 5件裝備的補充詞條總和
                if value > base_supplement:
                    waste_penalty += (value - base_supplement) * 1.5

        score += waste_penalty

        # 獲取偏好屬性值
        preferred_value = final_attributes.get(preferred_attr, 0) if preferred_attr else 0

        # 獲取當前組合的裝備數量
        current_equipment_count = result["equipment_count"]

        # 選擇最佳組合
        is_better = False
        if all_met:
            if best_score == float('inf'):
                is_better = True
            elif best_score > 0:
                is_better = True
            elif best_score == 0:
                if current_equipment_count > best_equipment_count:
                    is_better = True
                elif current_equipment_count == best_equipment_count:
                    if preferred_attr:
                        if preferred_value > best_preferred_value:
                            is_better = True
                    else:
                        if score < best_score:
                            is_better = True
        else:
            if score < best_score:
                is_better = True
            elif best_score != float('inf') and abs(score - best_score) < 10:
                if current_equipment_count > best_equipment_count:
                    is_better = True

        return {
            "is_better": is_better,
            "score": score if not all_met else 0,
            "all_met": all_met,
            "preferred_value": preferred_value,
            "equipment_count": current_equipment_count,
            "final_attributes": final_attributes,
            "bonus_allocation": bonus_allocation
        }

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

        # 顯示碎片修正（如果有）
        fragment_corrections = result.get("fragment_corrections", {})
        if fragment_corrections:
            lines.append("\n【碎片修正】")
            for attr, correction in fragment_corrections.items():
                sign = "+" if correction > 0 else ""
                lines.append(f"  {attr}: {sign}{correction:.0f}")

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

            # 先顯示當前總屬性（在訊息下方）
            if "best_result" in result:
                best_result = result["best_result"]
                total_attrs = best_result.get("total_attributes", {})
                if total_attrs:
                    lines.append("\n【當前總屬性】")
                    for attr in EQUIPMENT_ATTRIBUTES:
                        value = total_attrs.get(attr, 0)
                        if value > 0:
                            lines.append(f"  {attr}: {value:.0f}")

                # 顯示缺少的屬性（已考慮加成）
                if "missing_attributes" in result:
                    lines.append("\n【缺少的屬性（已考慮加成）】")
                    for attr, value in result["missing_attributes"].items():
                        lines.append(f"  {attr}: 還需要 {value:.0f}")

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

                # 顯示最接近的組合
                lines.append("\n【最接近的組合】")
                formatted = self.format_result(best_result)
                lines.append(formatted)

            # 顯示替換建議
            if "required_equipments" in result and result["required_equipments"]:
                for suggestion in result["required_equipments"]:
                    message = suggestion.get("message", "替換建議")
                    lines.append(f"\n【{message}】")

                    replacements = suggestion.get("replacements", [])
                    for i, req_eq in enumerate(replacements, 1):
                        # 顯示替換信息
                        lines.append(f"\n  {i}. 替換 {req_eq['replace_type']}: {req_eq['original_name']} → {req_eq['name']}")

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

                    # 顯示替換後的總屬性（在所有替換裝備之後顯示一次）
                    # 優先從 suggestion 取，如果沒有則從第一個替換裝備取
                    new_total = suggestion.get("new_total")
                    if not new_total and replacements:
                        new_total = replacements[0].get("new_total")

                    if new_total:
                        target_attrs = result.get("target_attributes", {})
                        lines.append(f"\n  【替換後總屬性】")
                        for attr in EQUIPMENT_ATTRIBUTES:
                            value = new_total.get(attr, 0)
                            if value > 0:
                                if attr in target_attrs:
                                    target_val = target_attrs[attr]
                                    status = "✓" if value >= target_val else f"差{target_val - value:.0f}"
                                    lines.append(f"    {attr}: {value:.0f} ({status})")
                                else:
                                    lines.append(f"    {attr}: {value:.0f}")
            elif "required_equipments" in result:
                # required_equipments 存在但為空，表示無法通過替換達成目標
                lines.append("\n【替換建議】")
                lines.append("  無法通過替換現有裝備達成目標。")
                lines.append("  可能需要：")
                lines.append("    - 增加碎片修正數值")
                lines.append("    - 降低目標屬性要求")
                lines.append("    - 入手具有更優詞條的裝備")

        lines.append("=" * 60)
        return "\n".join(lines)
