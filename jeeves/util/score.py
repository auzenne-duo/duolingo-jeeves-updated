import numpy as np
import pandas as pd


def pearsons_coefficient(a, b):
    if not isinstance(a, pd.Series):
        a = pd.Series(a)
    if not isinstance(b, pd.Series):
        b = pd.Series(b)
    unified_index = set(a.index).union(b.index)

    def reidx(x):
        return x.reindex(unified_index, fill_value=0)

    def center(x):
        return x - np.average(x)

    return cosine_similarity(center(reidx(a)), center(reidx(b)))


def cosine_similarity(a, b):
    if not isinstance(a, pd.Series):
        a = pd.Series(a)
    if not isinstance(b, pd.Series):
        b = pd.Series(b)
    unified_index = set(a.index).union(b.index)
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)

    def reidx(x):
        return x.reindex(unified_index, fill_value=0)

    a_re = reidx(a)
    b_re = reidx(b)
    a_dot_b = a_re.dot(b_re)
    return a_dot_b / (a_norm * b_norm)
