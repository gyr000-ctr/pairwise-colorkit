"""colorkit 核心 API（初始未实现）。"""


class ColorPipeline:
    def __init__(self, version='v2'):
        """构造管线，version 取 v1 或 v2"""
        raise NotImplementedError

    def convert(self, rgb, space):
        """单次转换，返回三元组"""
        raise NotImplementedError

    def convert_many(self, items, space):
        """批量转换"""
        raise NotImplementedError

    def cache_stats(self):
        """返回 {'hits','misses'}"""
        raise NotImplementedError

    def clear_cache(self):
        """清空缓存并归零计数"""
        raise NotImplementedError

    def set_version(self, version):
        """切换版本，需清空缓存"""
        raise NotImplementedError
