# -*- coding: utf-8 -*-
"""把祥利一期的模組格子抽出來，輸出描圖台用的區塊。

來源是 CAD 匯出的向量圖轉成的點陣（600dpi），量的是「模組格線」本身，
不是猜的。每一列模組在圖上是「25px 邊框 + 60px 內部」的重複單元。

三個獨立來源互相對帳：
  1. 格線幾何     5 條 ×(9行×32列) + 左條(8行×8列 + 9行×24列) = 1720
  2. 圖上的串號   左條有 DC8-1~4（4串×24=96）與 DC9-1~8（8串×23=184）= 280
  3. 規格表       INV01~08 各 24串8併=192、INV09 23串8併=184，合計 1720

條 3~7 的列是「每 4 列一組」，組間有維修走道；一個區塊只能是等分的矩形，
所以一組一個區塊，不要用一個 32 列的大框硬切（走道會讓格子對不準）。
"""
import json
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
A = np.asarray(Image.open('hi-rot.png').convert('L')) < 160
IMG_H, IMG_W = A.shape


def merge(idx, tol=3):
    m, cur = [], [idx[0]]
    for v in idx[1:]:
        if v - cur[-1] <= tol:
            cur.append(v)
        else:
            m.append(int(np.mean(cur))); cur = [v]
    m.append(int(np.mean(cur)))
    return np.array(m)


def row_cells(x0, x1, frac=0.55):
    """回傳每一列模組的 (上緣, 下緣)。"""
    r = A[:, x0:x1].sum(axis=1)
    idx = np.where(r > (x1 - x0) * frac)[0]
    idx = idx[(idx > 1500) & (idx < 5000)]
    m = merge(idx)
    d = np.diff(m)
    return [(int(m[i]), int(m[i + 1])) for i in range(len(d)) if 52 <= d[i] <= 68]


def col_lines(y0, y1, x0, x1, frac=0.45):
    c = A[y0:y1, x0:x1].sum(axis=0)
    idx = np.where(c > (y1 - y0) * frac)[0]
    return merge(idx, 4) + x0


def blocks_of(rows, cols, bid, gap=1.4):
    """把連續、等距的列併成一個區塊；走道處切開。"""
    out, run = [], [rows[0]]
    base = rows[0][1] - rows[0][0]
    for a, b in rows[1:]:
        if (a - run[-1][0]) <= (run[-1][1] - run[-1][0] + base) * gap * 0.6 + base:
            run.append((a, b))
        else:
            out.append(run); run = [(a, b)]
    out.append(run)
    res = []
    for i, run in enumerate(out):
        top, bot = run[0][0], run[-1][1]
        res.append(dict(id='%s-%d' % (bid, i + 1), rows=len(run), cols=len(cols) - 1,
                        x0=float(cols[0]), x1=float(cols[-1]), y0=float(top), y1=float(bot)))
    return res


if __name__ == '__main__':
    STRIPS = [('B', 1690, 2100), ('C', 2210, 2625), ('D', 2755, 3172),
              ('E', 3277, 3693), ('F', 3825, 4240)]
    out = []
    for bid, x0, x1 in STRIPS:
        rows = row_cells(x0, x1)
        cols = col_lines(rows[0][0], rows[-1][1], x0 - 20, x1 + 20)
        cols = cols[(cols >= x0 - 15) & (cols <= x1 + 15)]
        bs = blocks_of(rows, cols, bid)
        n = sum(b['rows'] * b['cols'] for b in bs)
        print('%s  %d 區塊  %d 行 × 共 %d 列 = %d 片' %
              (bid, len(bs), len(cols) - 1, sum(b['rows'] for b in bs), n))
        out += bs
    # 左條：上段 8 行、下段 9 行，交界在 y≈2475
    rowsL = row_cells(1190, 1600)
    CUT = 2475
    up = [r for r in rowsL if r[1] <= CUT]
    dn = [r for r in rowsL if r[0] > CUT]
    colsU = col_lines(up[0][0], up[-1][1], 1100, 1700)
    colsU = colsU[(colsU >= 1150) & (colsU <= 1625)]
    colsD = col_lines(dn[0][0], dn[-1][1], 1080, 1700)
    colsD = colsD[(colsD >= 1100) & (colsD <= 1625)]
    print('左條上段 %d 列、直線 %s' % (len(up), colsU))
    print('左條下段 %d 列、直線 %s' % (len(dn), colsD))
    json.dump(dict(strips=out, rowsL=[list(map(int, r)) for r in rowsL],
                   colsU=[int(c) for c in colsU], colsD=[int(c) for c in colsD],
                   cut=CUT, img=[int(IMG_W), int(IMG_H)]),
              open('geom.json', 'w'), ensure_ascii=False, indent=1)
    print('條 3~7 合計 %d 片' % sum(b['rows'] * b['cols'] for b in out))
