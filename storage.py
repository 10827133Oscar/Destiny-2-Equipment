"""
裝備數據持久化存儲
"""
import json
import os
import logging
import tempfile
import shutil
from typing import Dict, List, Optional
from equipment import Equipment, EQUIPMENT_ATTRIBUTES
from classes import GuardianClass
from config import Config

logger = logging.getLogger(__name__)


STORAGE_FILE = Config.EQUIPMENT_STORAGE_FILE


def equipment_to_dict(equipment: Equipment) -> Dict:
    """將裝備對象轉換為字典"""
    return {
        "id": equipment.id,
        "name": equipment.name,
        "type": equipment.type,
        "rarity": equipment.rarity,
        "tag": equipment.tag,
        "attributes": equipment.attributes,
        "stat_tags": equipment.stat_tags,
        "class_restriction": [gc.value for gc in (equipment.class_restriction or [])],
        "set_name": equipment.set_name,
        "level": equipment.level,
        "locked_attr": equipment.locked_attr,
        "penalty_attr": equipment.penalty_attr
    }


def dict_to_equipment(data: Dict) -> Equipment:
    """將字典轉換為裝備對象"""
    # 處理職業限制
    class_restriction = None
    if data.get("class_restriction"):
        class_restriction = [GuardianClass(c) for c in data["class_restriction"]]
    
    # 創建設備
    equipment = Equipment(
        id=data["id"],
        name=data["name"],
        type=data["type"],
        rarity=data.get("rarity", "傳說"),
        tag=data.get("tag"),
        attributes=data.get("attributes", {}),
        stat_tags=data.get("stat_tags", {}),
        class_restriction=class_restriction,
        set_name=data.get("set_name"),
        level=data.get("level", 0),
        locked_attr=data.get("locked_attr"),
        penalty_attr=data.get("penalty_attr")
    )
    
    return equipment


def save_equipments(equipments: List[Equipment]) -> None:
    """保存裝備列表到文件（使用原子寫入）"""
    data = {
        "equipments": [equipment_to_dict(eq) for eq in equipments],
        "version": "1.0"
    }

    # 獲取目標文件的目錄
    target_dir = os.path.dirname(os.path.abspath(STORAGE_FILE))

    try:
        # 創建臨時文件，寫入數據
        fd, temp_path = tempfile.mkstemp(suffix='.json', dir=target_dir)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 原子性地替換目標文件
            # Windows 需要先刪除目標文件
            if os.path.exists(STORAGE_FILE):
                # 先備份原文件
                backup_path = STORAGE_FILE + '.bak'
                shutil.copy2(STORAGE_FILE, backup_path)
                try:
                    os.replace(temp_path, STORAGE_FILE)
                    # 成功後刪除備份
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                except Exception:
                    # 失敗時恢復備份
                    if os.path.exists(backup_path):
                        shutil.copy2(backup_path, STORAGE_FILE)
                    raise
            else:
                os.replace(temp_path, STORAGE_FILE)
        except Exception:
            # 確保清理臨時文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
    except Exception as e:
        raise IOError(f"保存裝備數據失敗: {e}")


def load_equipments() -> List[Equipment]:
    """從文件加載裝備列表"""
    if not os.path.exists(STORAGE_FILE):
        return []
    
    try:
        with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        equipments = []
        for eq_data in data.get("equipments", []):
            try:
                equipment = dict_to_equipment(eq_data)
                equipments.append(equipment)
            except Exception as e:
                logger.warning(f"加載裝備 {eq_data.get('id', 'unknown')} 失敗: {e}")
                continue
        
        return equipments
    except json.JSONDecodeError as e:
        raise IOError(f"讀取裝備數據失敗：JSON 格式錯誤: {e}")
    except Exception as e:
        raise IOError(f"讀取裝備數據失敗: {e}")

