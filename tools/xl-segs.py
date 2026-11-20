# -*- coding: utf-8 -*-
"""從 CAD 匯出的 SVG 把線段撈出來。

祥利一期跟廣興國小最大的差別：這張是向量的迴路配置圖，模組的格線是
真的線段，座標是 CAD 畫的，不是從照片猜的。所以行列數不必「量」，
數線條就好——數錯了會對不上圖上標的 1720 片，馬上就知道。
"""
import io, re
import numpy as np

NUM = r'-?\d+(?:\.\d+)?'


def segments(path='p6.svg'):
    s = io.open(path, encoding='utf-8').read()
    body = s[s.index('</defs>'):]
    out = []
    for d in re.findall(r'<path[^>]*?d="([^"]+)"', body):
        if re.search(r'[CQAScqas]', d):
            continue
        # M x y L x y L x y ... 可能有好幾段
        toks = re.findall(r'([MLZz])\s*(' + NUM + r')?\s*(' + NUM + r')?', d)
        cur = None
        for op, a, b in toks:
            if op in 'Zz':
                cur = None
                continue
            if a is None or b is None or a == '' or b == '':
                continue
            p = (float(a), float(b))
            if op == 'M':
                cur = p
            else:
                if cur is not None:
                    out.append((cur[0], cur[1], p[0], p[1]))
                cur = p
    return np.array(out, dtype=float)


def split_hv(seg, tol=0.35):
    """分成水平、垂直兩組。CAD 線不會剛好完全水平，留一點容差。"""
    dx = np.abs(seg[:, 2] - seg[:, 0])
    dy = np.abs(seg[:, 3] - seg[:, 1])
    h = seg[(dy <= tol) & (dx > tol)]
    v = seg[(dx <= tol) & (dy > tol)]
    return h, v


if __name__ == '__main__':
    seg = segments()
    print('線段', len(seg))
    h, v = split_hv(seg)
    print('水平', len(h), '垂直', len(v))
    print('X 範圍 %.1f ~ %.1f   Y 範圍 %.1f ~ %.1f'
          % (seg[:, [0, 2]].min(), seg[:, [0, 2]].max(),
             seg[:, [1, 3]].min(), seg[:, [1, 3]].max()))
    for name, a in (('水平線長度', np.abs(h[:, 2] - h[:, 0])),
                    ('垂直線長度', np.abs(v[:, 3] - v[:, 1]))):
        q = np.percentile(a, [50, 75, 90, 95, 99])
        print('%s 中位數 %.2f  75%% %.2f  90%% %.2f  95%% %.2f  99%% %.2f  最長 %.1f'
              % (name, q[0], q[1], q[2], q[3], q[4], a.max()))
