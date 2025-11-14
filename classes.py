"""
Destiny 2 職業定義
"""
from enum import Enum


class GuardianClass(Enum):
    """守護者職業"""
    TITAN = "泰坦"
    HUNTER = "獵人"
    WARLOCK = "術士"
    
    def __str__(self):
        return self.value
    
    @classmethod
    def get_all_classes(cls):
        """獲取所有職業列表"""
        return [cls.TITAN, cls.HUNTER, cls.WARLOCK]

