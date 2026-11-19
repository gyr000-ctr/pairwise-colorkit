import threading

import pytest

import colorkit

import math

PIPE = None


def _pipeline():
    global PIPE
    if PIPE is None:
        PIPE = colorkit.ColorPipeline(version="v2")
    return PIPE


def _one_vs_many():
    p = _pipeline()
    items = [(0.1, 0.2, 0.3), (0.5, 0.5, 0.5), (0.9, 0.1, 0.0)]
    many = p.convert_many(items, "oklab")
    single = [p.convert(rgb, "oklab") for rgb in items]
    return many == single


def _concurrent_equals_serial():
    p = _pipeline()
    items = [(i / 20.0, 0.5, 1.0 - i / 20.0) for i in range(20)]
    serial = [p.convert(rgb, "oklab") for rgb in items]
    out = {}
    def work(idx):
        out[idx] = p.convert(items[idx], "oklab")
    threads = [threading.Thread(target=work, args=(i,)) for i in range(len(items))]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return [out[i] for i in range(len(items))] == serial


def _cache_hits_grow():
    p = _pipeline()
    p.clear_cache()
    p.convert((0.2, 0.3, 0.4), "oklab")
    before = p.cache_stats()["hits"]
    p.convert((0.2, 0.3, 0.4), "oklab")
    return p.cache_stats()["hits"] == before + 1


def _clear_resets():
    p = _pipeline()
    p.convert((0.2, 0.3, 0.4), "oklab")
    p.clear_cache()
    return p.cache_stats() == {"hits": 0, "misses": 0}


def _unknown_space():
    try:
        _pipeline().convert((0.1, 0.1, 0.1), "cmyk")
    except ValueError:
        return True
    return False


def _bad_rgb():
    try:
        _pipeline().convert((0.1, 0.1), "oklab")
    except ValueError:
        return True
    return False


def _version_differ_out_of_gamut():
    v1 = colorkit.ColorPipeline(version="v1")
    v2 = colorkit.ColorPipeline(version="v2")
    rgb = (1.2, 0.5, 0.5)
    return v1.convert(rgb, "oklab") != v2.convert(rgb, "oklab")


def _v1_clips():
    out = colorkit.ColorPipeline(version="v1").convert((1.2, -0.2, 0.5), "oklab")
    return all(0.0 <= v <= 1.0 for v in out)


def _v2_preserves():
    out = colorkit.ColorPipeline(version="v2").convert((1.2, -0.2, 0.5), "oklab")
    return any(v < 0.0 or v > 1.0 for v in out)


def _bad_version():
    try:
        colorkit.ColorPipeline(version="v3")
    except ValueError:
        return True
    return False


def _tuple_len():
    return len(_pipeline().convert((0.1, 0.2, 0.3), "srgb")) == 3


def _nan_rejected():
    try:
        _pipeline().convert((float("nan"), 0.0, 0.0), "oklab")
    except ValueError:
        return True
    return False


def _set_version_clears():
    p = _pipeline()
    p.convert((0.2, 0.3, 0.4), "oklab")
    p.set_version("v1")
    return p.cache_stats() == {"hits": 0, "misses": 0}


def _empty_many():
    return _pipeline().convert_many([], "oklab") == []


def _two_instances_independent():
    a = colorkit.ColorPipeline(version="v1")
    b = colorkit.ColorPipeline(version="v2")
    rgb = (1.2, 0.5, 0.5)
    return a.convert(rgb, "oklab") != b.convert(rgb, "oklab") and a.cache_stats()["misses"] >= 1

CASES = [
        ("one_vs_many", "_one_vs_many"),
        ("concurrent", "_concurrent_equals_serial"),
        ("cache_hits", "_cache_hits_grow"),
        ("clear_resets", "_clear_resets"),
        ("unknown_space", "_unknown_space"),
        ("bad_rgb", "_bad_rgb"),
        ("version_differ", "_version_differ_out_of_gamut"),
        ("v1_clips", "_v1_clips"),
        ("v2_preserves", "_v2_preserves"),
        ("bad_version", "_bad_version"),
        ("tuple_len", "_tuple_len"),
        ("nan", "_nan_rejected"),
        ("set_version", "_set_version_clears"),
        ("empty_many", "_empty_many"),
        ("two_instances", "_two_instances_independent"),
    ]


@pytest.mark.parametrize("name,check", CASES, ids=[c[0] for c in CASES])
def test_spec(name, check):
    assert check() is True
