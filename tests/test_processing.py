# 简单滤波函数
from mst.core.processing import moving_average
from pytest import approx


def test_moving_average_basic():
    out = moving_average([1, 2, 3, 4, 5], window=3)
    assert out.y == approx([2.0, 3.0, 4.0])

