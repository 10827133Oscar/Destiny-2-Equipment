"""
應用配置
"""
import os

class Config:
    """應用配置類"""
    # Flask 配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # 服務器配置
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    
    # 數據文件
    EQUIPMENT_STORAGE_FILE = 'equipment_storage.json'
    BUILD_STORAGE_FILE = 'build_storage.json'
    
    # API 配置
    JSON_AS_ASCII = False  # 支持中文JSON響應
    
    # 裝備配置
    EQUIPMENT_TYPES = ["頭盔", "臂鎧", "胸鎧", "護腿", "職業物品"]
    MAX_UPGRADE_LEVEL = 5
    MAX_EQUIPMENTS_PER_TYPE = 999  # 每種類型最多裝備數量

