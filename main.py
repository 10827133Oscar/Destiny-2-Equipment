"""
主程式 - 遊戲裝備系統範例
"""
from equipment import Equipment
from inventory import Inventory
from calculator import EquipmentCalculator


def main():
    """主程式範例"""
    # 初始化系統
    inventory = Inventory()
    calculator = EquipmentCalculator(inventory)
    
    # 創建範例裝備（Destiny 2 風格）
    # 護甲裝備使用 Destiny 2 的屬性系統
    helmet = Equipment(
        id="armor001",
        name="異域頭盔 - 聖人14號",
        type="頭盔",
        rarity="異域",
        attributes={
            "移動": 10,
            "韌性": 20,
            "恢復": 15,
            "紀律": 12,
            "智力": 8,
            "力量": 10
        },
        set_name="泰坦套裝"
    )
    
    chest = Equipment(
        id="armor002",
        name="傳說護甲 - 泰坦胸甲",
        type="胸甲",
        rarity="傳說",
        attributes={
            "移動": 8,
            "韌性": 18,
            "恢復": 12,
            "紀律": 15,
            "智力": 10,
            "力量": 12
        },
        set_name="泰坦套裝"
    )
    
    legs = Equipment(
        id="armor003",
        name="傳說護甲 - 泰坦腿甲",
        type="腿甲",
        rarity="傳說",
        attributes={
            "移動": 15,
            "韌性": 10,
            "恢復": 18,
            "紀律": 10,
            "智力": 12,
            "力量": 15
        },
        set_name="泰坦套裝"
    )
    
    # 添加到倉庫
    inventory.add_equipment(helmet)
    inventory.add_equipment(chest)
    inventory.add_equipment(legs)
    
    # 設定套裝效果（Destiny 2 風格）
    calculator.add_set_bonus("泰坦套裝", 2, {"韌性": 5, "恢復": 5})
    calculator.add_set_bonus("泰坦套裝", 3, {"韌性": 10, "恢復": 10, "移動": 5})
    
    # 計算組合數值
    combination = ["armor001", "armor002", "armor003"]
    result = calculator.calculate_combination(combination)
    
    print("=== Destiny 2 裝備組合計算結果 ===")
    print(f"裝備數量: {result['equipment_count']}")
    print("\n總屬性數值:")
    # 按照 Destiny 2 的屬性順序顯示
    destiny_attributes = ["移動", "韌性", "恢復", "紀律", "智力", "力量"]
    for attr in destiny_attributes:
        if attr in result["total_attributes"]:
            value = result["total_attributes"][attr]
            print(f"  {attr}: {value:.0f}")
    
    print("\n套裝效果:")
    for set_name, bonus in result["set_bonuses"].items():
        print(f"  {set_name}:")
        for attr, value in bonus.items():
            print(f"    {attr}: +{value:.0f}")
    
    print(f"\n總屬性點數: {calculator.calculate_total_power(combination):.0f}")


if __name__ == "__main__":
    main()

