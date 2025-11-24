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

    # 安全配置
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000').split(',')
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 最大請求大小 1MB
    MAX_BUILD_NAME_LENGTH = 50  # 套裝名稱最大長度
    MAX_EQUIPMENT_NAME_LENGTH = 100  # 裝備名稱最大長度

    # 裝備配置
    EQUIPMENT_TYPES = ["頭盔", "臂鎧", "胸鎧", "護腿", "職業物品"]
    MAX_UPGRADE_LEVEL = 5

