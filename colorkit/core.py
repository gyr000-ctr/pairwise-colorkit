"""colorkit 核心 API。

管线接收线性光 RGB（可含 HDR 超范围分量），把它转换到目标色彩空间。

- ``v2``（默认）：保留超色域分量，不做隐式裁剪，HDR 信息不丢失。
- ``v1``（兼容旧行为）：转换前把源颜色夹到 ``[0, 1]``，转换后再把结果夹到
  ``[0, 1]``，因此超范围像素会被静默裁剪。

实例之间不共享任何可变状态；每个实例自带缓存、计数器和线程锁。
"""

import math
import threading

__all__ = ["ColorPipeline"]

_VERSIONS = ("v1", "v2")
_SPACES = ("srgb", "linear", "oklab")


def _cbrt(x):
    """符号保持的立方根（负数也有实立方根）。"""
    return math.copysign(abs(x) ** (1.0 / 3.0), x)


def _linear_to_srgb(c):
    """把线性光分量编码为 sRGB。负值按同一线性段外推，不做裁剪。"""
    if c <= 0.0031308:
        return 12.92 * c
    return 1.055 * (c ** (1.0 / 2.4)) - 0.055


def _linear_to_oklab(rgb):
    """线性 sRGB -> Oklab（Björn Ottosson 的标准变换）。"""
    r, g, b = rgb

    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    l, m, s = _cbrt(l), _cbrt(m), _cbrt(s)

    return (
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    )


def _transform(rgb, space, clip):
    if clip:
        rgb = tuple(min(1.0, max(0.0, c)) for c in rgb)

    if space == "linear":
        out = rgb
    elif space == "srgb":
        out = tuple(_linear_to_srgb(c) for c in rgb)
    else:  # space == "oklab"
        out = _linear_to_oklab(rgb)

    if clip:
        out = tuple(min(1.0, max(0.0, c)) for c in out)

    return tuple(float(c) for c in out)


class ColorPipeline:
    """一个独立的颜色转换管线（带版本化缓存）。"""

    def __init__(self, version="v2"):
        """构造管线，version 取 v1 或 v2。"""
        if version not in _VERSIONS:
            raise ValueError("unknown pipeline version: %r" % (version,))

        self._version = version
        self._lock = threading.Lock()
        self._cache = {}
        self._hits = 0
        self._misses = 0

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------
    def convert(self, rgb, space):
        """单次转换，返回三元组。"""
        rgb = self._validate_rgb(rgb)
        self._validate_space(space)

        with self._lock:
            # 版本必须在锁内读取：否则并发的 set_version 可能在清空缓存之后
            # 用旧版本写回一条新条目，导致切换版本后缓存不归零。
            version = self._version
            # 缓存键包含管线版本：任何版本差异都不能复用同一条结果。
            key = (version, space, rgb)

            cached = self._cache.get(key)
            if cached is not None:
                self._hits += 1
                return cached

            self._misses += 1
            result = _transform(rgb, space, clip=version == "v1")
            self._cache[key] = result
            return result

    def convert_many(self, items, space):
        """批量转换，逐元素与 :meth:`convert` 一致（含缓存行为）。"""
        self._validate_space(space)
        # convert() 内部完成参数校验与缓存，保证单次/批量结果完全相同。
        return [self.convert(rgb, space) for rgb in items]

    def cache_stats(self):
        """返回 {'hits','misses'}。"""
        with self._lock:
            return {"hits": self._hits, "misses": self._misses}

    def clear_cache(self):
        """清空缓存并归零计数。"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def set_version(self, version):
        """切换版本，需清空缓存并归零计数。"""
        if version not in _VERSIONS:
            raise ValueError("unknown pipeline version: %r" % (version,))
        with self._lock:
            self._version = version
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    # ------------------------------------------------------------------
    # 校验
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_space(space):
        if not isinstance(space, str) or space not in _SPACES:
            raise ValueError("unknown color space: %r" % (space,))

    @staticmethod
    def _validate_rgb(rgb):
        if isinstance(rgb, (str, bytes)):
            raise ValueError("rgb must be a sequence of three numbers")

        try:
            values = tuple(float(c) for c in rgb)
        except (TypeError, ValueError):
            raise ValueError("rgb must be a sequence of three numbers") from None

        if len(values) != 3:
            raise ValueError("rgb must contain exactly three components")

        for c in values:
            if not math.isfinite(c):
                raise ValueError("rgb components must be finite")

        return values
