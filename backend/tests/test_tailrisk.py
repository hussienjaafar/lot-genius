import numpy as np

from backend.lotgenius.roi import _var_cvar


def test_var_cvar_monotone():
    vals = np.array([0.9, 1.0, 1.1, 1.2])
    q, c = _var_cvar(vals, 0.25)
    assert 0.9 <= q <= 1.0
    assert c <= q
