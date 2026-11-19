# -*- coding: utf-8 -*-
"""重量廣興國小：遮罩定範圍，自相關求節距，相除得行列數。

第一版是「面板面積佔比 × 957」分下去的，±數片；這一版改成量測：

  1. 面板遮罩（深色 + 反光兩種都算）→ 每一坡的實際四邊
  2. 高通影像（原圖 − 高斯模糊）把鋁框線拉出來
  3. 沿兩個方向各做一維投影，自相關取主週期 = 模組節距
  4. 範圍 ÷ 節距 = 行／列數

比「找峰值」穩：少認一條線不會直接少一格，週期是整段訊號一起決定的。
屋脊收邊（ridge flashing）在遮罩上不是面板，所以不會被算成一列——
第一版 B棟南坡東段 多算一列就是這個原因。
"""
import json
import numpy as np
from PIL import Image, ImageFilter

im = Image.open('aerial.png')
g = im.convert('L')
A = np.asarray(g).astype(float)
B = np.asarray(g.filter(ImageFilter.GaussianBlur(6))).astype(float)
HP = A - B
rgb = np.asarray(im.convert('RGB')).astype(float)
RED = (rgb[:, :, 0] > 140) & (rgb[:, :, 0] - rgb[:, :, 1] > 60) & (rgb[:, :, 0] - rgb[:, :, 2] > 60)
MASK = np.load('pvmask.npy')


def extent(x0, x1, y0, y1, axis, frac=0.35, bridge=3):
    """遮罩在該方向上的實際範圍：逐行（列）看面板像素佔比，取連續達標的一段。

    bridge 是容忍的斷點寬度：沿屋脊方向要大一點（模組之間的走道、
    煙囪會讓某幾行掉下去），跨坡方向要小（屋脊本身就該把兩坡切開）。
    """
    sub = MASK[y0:y1, x0:x1]
    p = sub.mean(axis=1 if axis == 'y' else 0)
    th = max(frac * np.percentile(p, 90), 0.2)
    idx = np.where(p >= th)[0]
    if len(idx) == 0:
        return None
    runs, s = [], idx[0]
    for i in range(1, len(idx)):
        if idx[i] - idx[i - 1] > bridge:
            runs.append((s, idx[i - 1]))
            s = idx[i]
    runs.append((s, idx[-1]))
    a, b = max(runs, key=lambda r: r[1] - r[0])
    base = y0 if axis == 'y' else x0
    return base + a, base + b + 1


def pitch(x0, x1, y0, y1, axis, lo=7, hi=30):
    """自相關主週期：鋁框線是等間距亮線，投影後找最強的週期。"""
    sub = np.where(RED[y0:y1, x0:x1], np.nan, HP[y0:y1, x0:x1])
    p = np.nanmean(sub, axis=1 if axis == 'y' else 0)
    p = np.nan_to_num(p, nan=0.0)
    p = p - p.mean()
    n = len(p)
    ac = np.correlate(p, p, 'full')[n - 1:]
    ac = ac / (ac[0] + 1e-9)
    hi = min(hi, n - 2)
    best = max(range(lo, hi + 1), key=lambda k: ac[k])
    # 拋物線內插，取到小數
    if 0 < best < len(ac) - 1:
        y1_, y2_, y3_ = ac[best - 1], ac[best], ac[best + 1]
        d = (y1_ - y3_) / (2 * (y1_ - 2 * y2_ + y3_) + 1e-9)
        return best + d, ac[best]
    return float(best), ac[best]


def one(name, cx, cy, L, W, o):
    if o == 'h':
        bx = (cx - L // 2 - 20, cx + L // 2 + 20)
        by = (cy - W // 2 - 20, cy + W // 2 + 20)
    else:
        bx = (cx - W // 2 - 20, cx + W // 2 + 20)
        by = (cy - L // 2 - 20, cy + L // 2 + 20)
    # 先定跨坡的邊（屋脊／屋簷分得開），再在那一條帶裡定沿屋脊的邊
    ca, cb = ('y', 'x') if o == 'h' else ('x', 'y')
    e1 = extent(bx[0], bx[1], by[0], by[1], ca, bridge=2)
    if not e1:
        print('%-14s 遮罩抓不到' % name)
        return None
    if ca == 'y':
        by = e1
    else:
        bx = e1
    e2 = extent(bx[0], bx[1], by[0], by[1], cb, bridge=10)
    if not e2:
        print('%-14s 遮罩抓不到' % name)
        return None
    if cb == 'y':
        by = e2
    else:
        bx = e2
    ex, ey = bx, by
    px, cfx = pitch(ex[0], ex[1], ey[0], ey[1], 'x', hi=26)
    py, cfy = pitch(ex[0], ex[1], ey[0], ey[1], 'y', hi=26)
    nx, ny = (ex[1] - ex[0]) / px, (ey[1] - ey[0]) / py
    print('%-14s x %4d-%4d (%3d) 節距 %5.2f → %5.2f 格 | y %4d-%4d (%3d) 節距 %5.2f → %5.2f 格'
          % (name, ex[0], ex[1], ex[1] - ex[0], px, nx, ey[0], ey[1], ey[1] - ey[0], py, ny))
    return dict(name=name, x=ex, y=ey, px=px, py=py, nx=nx, ny=ny, o=o)


if __name__ == '__main__':
    S = json.load(open('slopes.json', encoding='utf-8'))
    out = [one(n, cx, cy, L, W, o) for n, cx, cy, L, W, o, _, _ in S]
    out=[{k:(float(v) if isinstance(v,(np.floating,)) else (list(map(int,v)) if isinstance(v,tuple) else v)) for k,v in o.items()} for o in out if o]
    json.dump(out, open('measured.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
