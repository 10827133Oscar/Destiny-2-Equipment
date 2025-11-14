"""
Flask 後端 API 服務器
"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from equipment_manager import EquipmentManager
from classes import GuardianClass
from equipment import EQUIPMENT_TAGS, EQUIPMENT_ATTRIBUTES
from config import Config
from build_storage import save_builds, load_builds
import logging
import uuid
from datetime import datetime

# 配置日誌
logging.basicConfig(
    level=logging.INFO if not Config.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# 全局裝備管理器
manager = EquipmentManager()

# 裝備類型常量（從配置讀取）
EQUIPMENT_TYPES = Config.EQUIPMENT_TYPES


def validate_guardian_class(class_str: str) -> GuardianClass:
    """驗證並轉換職業字符串"""
    try:
        return GuardianClass(class_str)
    except ValueError:
        raise ValueError(f"無效的職業: {class_str}")


def validate_equipment_type(equipment_type: str) -> None:
    """驗證裝備類型"""
    if equipment_type not in EQUIPMENT_TYPES:
        raise ValueError(f"無效的裝備類型: {equipment_type}")


@app.route('/')
def index():
    """主頁"""
    return render_template('index.html')


@app.route('/api/classes', methods=['GET'])
def get_classes():
    """獲取所有職業"""
    classes = [{"value": gc.value, "name": str(gc)} for gc in GuardianClass.get_all_classes()]
    return jsonify(classes)


@app.route('/api/equipment-types', methods=['GET'])
def get_equipment_types():
    """獲取裝備類型"""
    return jsonify(EQUIPMENT_TYPES)


@app.route('/api/equipment-tags', methods=['GET'])
def get_equipment_tags():
    """獲取裝備標籤"""
    tags = [
        {
            "tag": tag,
            "main_attr": main_attr,
            "sub_attr": sub_attr
        }
        for tag, (main_attr, sub_attr) in EQUIPMENT_TAGS.items()
    ]
    return jsonify(tags)


@app.route('/api/attributes', methods=['GET'])
def get_attributes():
    """獲取所有屬性"""
    return jsonify(EQUIPMENT_ATTRIBUTES)


@app.route('/api/equipment/add', methods=['POST'])
def add_equipment():
    """添加裝備"""
    if not request.is_json:
        return jsonify({"success": False, "error": "請求必須是 JSON 格式"}), 400
    
    try:
        data = request.json
        
        # 驗證必需字段
        required_fields = ['guardian_class', 'equipment_type', 'tag', 'random_stat']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"success": False, "error": f"缺少必需字段: {field}"}), 400
        
        # 驗證並轉換數據
        guardian_class = validate_guardian_class(data['guardian_class'])
        validate_equipment_type(data['equipment_type'])
        
        if data['tag'] not in EQUIPMENT_TAGS:
            return jsonify({"success": False, "error": f"無效的裝備標籤: {data['tag']}"}), 400
        
        if data['random_stat'] not in EQUIPMENT_ATTRIBUTES:
            return jsonify({"success": False, "error": f"無效的屬性: {data['random_stat']}"}), 400
        
        # 添加裝備
        equipment = manager.add_equipment_simple(
            guardian_class=guardian_class,
            equipment_type=data['equipment_type'],
            tag=data['tag'],
            random_stat=data['random_stat'],
            locked_attr=data.get('locked_attr') or None,
            set_name=data.get('set_name') or None
        )
        
        return jsonify({
            "success": True,
            "equipment": {
                "id": equipment.id,
                "name": equipment.name,
                "type": equipment.type,
                "attributes": {k: v for k, v in equipment.attributes.items() if v > 0},
                "level": equipment.level,
                "locked_attr": equipment.locked_attr
            }
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"添加裝備錯誤: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"服務器錯誤: {str(e)}"}), 500


@app.route('/api/equipment/list', methods=['GET'])
def list_equipments():
    """列出裝備"""
    try:
        guardian_class_str = request.args.get('guardian_class')
        if guardian_class_str:
            guardian_class = validate_guardian_class(guardian_class_str)
            equipments = manager.list_equipments(guardian_class)
            return jsonify({"success": True, "equipments": equipments})
        else:
            # 返回所有職業的裝備
            all_equipments = {
                gc.value: manager.list_equipments(gc)
                for gc in GuardianClass.get_all_classes()
            }
            return jsonify({"success": True, "equipments": all_equipments})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"列出裝備錯誤: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"服務器錯誤: {str(e)}"}), 500


@app.route('/api/equipment/delete', methods=['POST'])
def delete_equipment():
    """刪除裝備"""
    if not request.is_json:
        return jsonify({"success": False, "error": "請求必須是 JSON 格式"}), 400
    
    try:
        data = request.json
        
        # 驗證必需字段
        if 'guardian_class' not in data:
            return jsonify({"success": False, "error": "缺少必需字段: guardian_class"}), 400
        if 'equipment_id' not in data:
            return jsonify({"success": False, "error": "缺少必需字段: equipment_id"}), 400
        
        guardian_class = validate_guardian_class(data['guardian_class'])
        equipment_id = data['equipment_id']
        
        # 刪除裝備
        success = manager.remove_equipment(equipment_id, guardian_class)
        
        if success:
            return jsonify({"success": True, "message": "裝備已刪除"})
        else:
            return jsonify({"success": False, "error": "裝備不存在"}), 404
            
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"刪除裝備錯誤: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"服務器錯誤: {str(e)}"}), 500


@app.route('/api/build/configure', methods=['POST'])
def configure_build():
    """配置套裝"""
    if not request.is_json:
        return jsonify({"success": False, "error": "請求必須是 JSON 格式"}), 400
    
    try:
        data = request.json
        
        # 驗證必需字段
        if 'guardian_class' not in data:
            return jsonify({"success": False, "error": "缺少必需字段: guardian_class"}), 400
        
        guardian_class = validate_guardian_class(data['guardian_class'])
        target_attributes = data.get('target_attributes', {})
        
        # 驗證目標屬性
        if not target_attributes:
            return jsonify({"success": False, "error": "至少需要一個目標屬性"}), 400
        
        for attr, value in target_attributes.items():
            if attr not in EQUIPMENT_ATTRIBUTES:
                return jsonify({"success": False, "error": f"無效的屬性: {attr}"}), 400
            if not isinstance(value, (int, float)) or value < 0:
                return jsonify({"success": False, "error": f"屬性值必須是非負數: {attr}"}), 400
        
        # 處理異域裝備
        exotic_equipment = None
        if data.get('use_exotic'):
            exotic_data = data.get('exotic_equipment', {})
            
            if 'type' not in exotic_data or exotic_data['type'] not in EQUIPMENT_TYPES:
                return jsonify({"success": False, "error": "異域裝備必須指定有效的裝備類型"}), 400
            
            exotic_attrs = exotic_data.get('attributes', {})
            # 如果屬性值為0或未定義，使用5作為預設值（滿等補充詞條）
            processed_attrs = {}
            for attr in EQUIPMENT_ATTRIBUTES:
                value = exotic_attrs.get(attr, 0)
                processed_attrs[attr] = value if value > 0 else 5
            
            non_zero_count = sum(1 for v in processed_attrs.values() if v > 0)
            if non_zero_count < 3:
                return jsonify({"success": False, "error": "異域裝備必須至少有3個非零屬性"}), 400
            
            exotic_equipment = {
                "name": exotic_data.get('name', '異域裝備').strip() or '異域裝備',
                "type": exotic_data['type'],
                "attributes": processed_attrs,
                "level": max(0, min(5, int(exotic_data.get('level', 0)))),
                "tag": exotic_data.get('tag') or None
            }
        
        # 獲取偏好屬性（可選）
        preferred_attr = data.get('preferred_attr')
        if preferred_attr and preferred_attr not in EQUIPMENT_ATTRIBUTES:
            return jsonify({"success": False, "error": f"無效的偏好屬性: {preferred_attr}"}), 400
        
        # 配置套裝
        result = manager.configure_build(guardian_class, target_attributes, exotic_equipment, preferred_attr)
        
        # 格式化結果
        formatted_result = manager.get_calculator().format_target_result(result)
        
        return jsonify({
            "success": True,
            "result": result,
            "formatted": formatted_result
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"配置套裝錯誤: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"服務器錯誤: {str(e)}"}), 500


@app.route('/api/build/save', methods=['POST'])
def save_build():
    """保存套裝"""
    if not request.is_json:
        return jsonify({"success": False, "error": "請求必須是 JSON 格式"}), 400
    
    try:
        data = request.json
        
        # 驗證必需字段
        required_fields = ['name', 'guardian_class', 'result']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"缺少必需字段: {field}"}), 400
        
        # 驗證名稱
        build_name = data['name'].strip()
        if not build_name:
            return jsonify({"success": False, "error": "套裝名稱不能為空"}), 400
        
        # 加載現有套裝
        builds = load_builds()
        
        # 檢查名稱是否重複
        existing_names = [b['name'] for b in builds if b.get('guardian_class') == data['guardian_class']]
        if build_name in existing_names:
            return jsonify({"success": False, "error": "該職業下已存在相同名稱的套裝"}), 400
        
        # 創建新套裝
        new_build = {
            "id": str(uuid.uuid4()),
            "name": build_name,
            "guardian_class": data['guardian_class'],
            "target_attributes": data.get('target_attributes', {}),
            "preferred_attr": data.get('preferred_attr'),
            "exotic_equipment": data.get('exotic_equipment'),
            "result": data['result'],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        builds.append(new_build)
        save_builds(builds)
        
        return jsonify({
            "success": True,
            "build": new_build,
            "message": "套裝已成功保存"
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"保存套裝錯誤: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"服務器錯誤: {str(e)}"}), 500


@app.route('/api/build/list', methods=['GET'])
def list_builds():
    """列出套裝"""
    try:
        guardian_class_str = request.args.get('guardian_class')
        builds = load_builds()
        
        if guardian_class_str:
            guardian_class = validate_guardian_class(guardian_class_str)
            filtered_builds = [b for b in builds if b.get('guardian_class') == guardian_class.value]
            return jsonify({"success": True, "builds": filtered_builds})
        else:
            return jsonify({"success": True, "builds": builds})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"列出套裝錯誤: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"服務器錯誤: {str(e)}"}), 500


@app.route('/api/build/delete', methods=['POST'])
def delete_build():
    """刪除套裝"""
    if not request.is_json:
        return jsonify({"success": False, "error": "請求必須是 JSON 格式"}), 400
    
    try:
        data = request.json
        
        if 'build_id' not in data:
            return jsonify({"success": False, "error": "缺少必需字段: build_id"}), 400
        
        build_id = data['build_id']
        builds = load_builds()
        
        # 查找並刪除套裝
        original_count = len(builds)
        builds = [b for b in builds if b.get('id') != build_id]
        
        if len(builds) == original_count:
            return jsonify({"success": False, "error": "套裝不存在"}), 404
        
        save_builds(builds)
        
        return jsonify({"success": True, "message": "套裝已刪除"})
    except Exception as e:
        app.logger.error(f"刪除套裝錯誤: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"服務器錯誤: {str(e)}"}), 500


@app.errorhandler(404)
def not_found(error):
    """處理 404 錯誤"""
    return jsonify({"success": False, "error": "接口不存在"}), 404


@app.errorhandler(500)
def internal_error(error):
    """處理 500 錯誤"""
    return jsonify({"success": False, "error": "服務器內部錯誤"}), 500


if __name__ == '__main__':
    app.run(
        debug=Config.DEBUG,
        port=Config.PORT,
        host=Config.HOST
    )

