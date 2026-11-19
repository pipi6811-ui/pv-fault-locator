# -*- coding: utf-8 -*-
"""直接數模組：每一片在高通影像上是一塊被亮框線圍起來的暗塊。

前面兩種做法都不夠準：
  - 面積佔比分配 → ±數片
  - 範圍 ÷ 自相關節距 → 窄邊（只有 40~60 px）自相關抓不到正確週期

這一版改成數連通塊：高通影像取暗的部分，侵蝕一次把框線斷開，
連通塊的質心再依 x / y 分群，就得到行數與列數。
分群用的門檻是節距的一半，節距從質心兩兩間距的中位數取。
"""
import json
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

im = Image.open('aerial.png')
g = im.convert('L')
A = np.asarray(g).astype(float)
B = np.asarray(g.filter(ImageFilter.GaussianBlur(6))).astype(float)
HP = A - B
rgb = np.asarray(im.convert('RGB')).astype(float)
RED = (rgb[:, :, 0] > 140) & (rgb[:, :, 0] - rgb[:, :, 1] > 60) & (rgb[:, :, 0] - rgb[:, :, 2] > 60)


def cluster(vals, gap):
    """一維分群：排序後，間隔大於 gap 就切一群。回傳每群的中位數。"""
    v = sorted(vals)
    out, cur = [], [v[0]]
    for x in v[1:]:
        if x - cur[-1] > gap:
            out.append(cur)
            cur = []
        cur.append(x)
    out.append(cur)
    return [float(np.median(c)) for c in out], [len(c) for c in out]


def count(name, x0, x1, y0, y1, dark=-1.5, minpx=18):
    sub = HP[y0:y1, x0:x1]
    bad = RED[y0:y1, x0:x1]
    m = (sub < dark) & (~bad)
    m = ndi.binary_opening(m, np.ones((2, 2)))
    lab, n = ndi.label(m)
    if n == 0:
        print('%-14s 沒有暗塊' % name)
        return None
    sizes = ndi.sum(m, lab, range(1, n + 1))
    keep = [i + 1 for i, s in enumerate(sizes) if s >= minpx]
    cen = ndi.center_of_mass(m, lab, keep)
    cy = np.array([c[0] for c in cen]) + y0
    cx = np.array([c[1] for c in cen]) + x0
    # 節距：同一列裡相鄰質心的距離中位數
    def pitch(a, b):
        d = []
        for v in np.unique(np.round(b / 8)):
            s = np.sort(a[np.abs(b / 8 - v) < .5])
            d += list(np.diff(s))
        d = [x for x in d if x > 4]
        return float(np.median(d)) if d else 0.0
    px, py = pitch(cx, cy), pitch(cy, cx)
    colc, coln = cluster(cx, px * .6) if px else ([], [])
    rowc, rown = cluster(cy, py * .6) if py else ([], [])
    print('%-14s 暗塊 %3d 片 | 行(x) %2d 群 節距 %4.1f | 列(y) %2d 群 節距 %4.1f | %d×%d=%d'
          % (name, len(keep), len(colc), px, len(rowc), py, len(colc), len(rowc), len(colc) * len(rowc)))
    print('%-14s   每行片數 %s' % ('', coln))
    print('%-14s   每列片數 %s' % ('', rown))
    return dict(name=name, n=len(keep), cols=len(colc), rows=len(rowc),
                px=px, py=py, coln=coln, rown=rown)


if __name__ == '__main__':
    for j in json.load(open('boxes.json', encoding='utf-8')):
        count(j['name'], j['x0'], j['x1'], j['y0'], j['y1'])
