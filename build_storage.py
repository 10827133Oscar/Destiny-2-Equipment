"""
套裝數據持久化存儲
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime


BUILD_STORAGE_FILE = 'build_storage.json'


def save_builds(builds: List[Dict]) -> None:
    """保存套裝列表到文件"""
    data = {
        "builds": builds,
        "version": "1.0",
        "last_updated": datetime.now().isoformat()
    }
    
    try:
        with open(BUILD_STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise IOError(f"保存套裝數據失敗: {e}")


def load_builds() -> List[Dict]:
    """從文件加載套裝列表"""
    if not os.path.exists(BUILD_STORAGE_FILE):
        return []
    
    try:
        with open(BUILD_STORAGE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data.get("builds", [])
    except json.JSONDecodeError as e:
        raise IOError(f"讀取套裝數據失敗：JSON 格式錯誤: {e}")
    except Exception as e:
        raise IOError(f"讀取套裝數據失敗: {e}")


def clear_build_storage() -> None:
    """清空存儲文件"""
    if os.path.exists(BUILD_STORAGE_FILE):
        os.remove(BUILD_STORAGE_FILE)

