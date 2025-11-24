"""
套裝數據持久化存儲
"""
import json
import os
import tempfile
import shutil
from typing import Dict, List, Optional
from datetime import datetime


BUILD_STORAGE_FILE = 'build_storage.json'


def save_builds(builds: List[Dict]) -> None:
    """保存套裝列表到文件（使用原子寫入）"""
    data = {
        "builds": builds,
        "version": "1.0",
        "last_updated": datetime.now().isoformat()
    }

    # 獲取目標文件的目錄
    target_dir = os.path.dirname(os.path.abspath(BUILD_STORAGE_FILE))

    try:
        # 創建臨時文件，寫入數據
        fd, temp_path = tempfile.mkstemp(suffix='.json', dir=target_dir)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 原子性地替換目標文件
            if os.path.exists(BUILD_STORAGE_FILE):
                # 先備份原文件
                backup_path = BUILD_STORAGE_FILE + '.bak'
                shutil.copy2(BUILD_STORAGE_FILE, backup_path)
                try:
                    os.replace(temp_path, BUILD_STORAGE_FILE)
                    # 成功後刪除備份
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                except Exception:
                    # 失敗時恢復備份
                    if os.path.exists(backup_path):
                        shutil.copy2(backup_path, BUILD_STORAGE_FILE)
                    raise
            else:
                os.replace(temp_path, BUILD_STORAGE_FILE)
        except Exception:
            # 確保清理臨時文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
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

