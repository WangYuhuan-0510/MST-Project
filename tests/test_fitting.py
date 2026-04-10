# 曲线拟合能跑通、结果在合理范围
import numpy as np

from mst.core.fitting import fit_4pl_curve, sigmoid_4pl


def test_fit_4pl_curve_runs():
    x = np.logspace(-2, 1, 24)
    y = sigmoid_4pl(x, bottom=0.2, top=1.0, ec50=2.0, hill=1.2)
    res = fit_4pl_curve(x, y)
    assert 0.0 < res.ec50 < 10.0
    assert 0.1 < res.hill < 5.0
