# -*- coding: utf-8 -*-
"""祥利一期：輸出底圖與描圖台用的區塊範本。

量到的結構（全部從 CAD 向量圖轉的 600dpi 點陣量出來，不是猜的）：

  條 B~F（5 條）  9 行 × 32 列，列是「每 4 列一組」，組間有維修走道
                  → 一組一個區塊，8 個區塊 × (9×4) = 288 片／條
  條 A（最左）    32 列均勻、中間有一條走道把行切成兩群，
                  而且第 9 列起整條往左多一行：
                    第 1~8 列    3 行 + 5 行 = 8 行
                    第 9~32 列   4 行 + 5 行 = 9 行
                  → 8×3 + 8×5 + 24×4 + 24×5 = 280 片

  合計 5×288 + 280 = 1720 片，與圖上標的、與規格表（8×192+184）相符。
"""
import json
import numpy as np
from PIL import Image
from build import row_cells, col_lines

Image.MAX_IMAGE_PIXELS = None
SRC = 'hi-rot.png'
CROP = (1020, 1560, 4400, 4660)        # 底圖裁切（600dpi 座標）
SCALE = 0.62                            # 底圖縮放


def cols_clean(x0, x1, y0, y1, want, pitch=52.4):
    """抓直線後，用主節距擬合出 want+1 條等距的行邊界。

    不能直接拿「最外面那兩條線」當邊界：條的外框線就在模組邊界外面一點
    （約 78px），把它當成第一條的話，跨距會從 472 變成 499、節距從 52.4
    變成 55.4，整排格子就往左偏並且逐行累積漂移。

    做法：只留彼此間距接近主節距的那一串（模組邊界），對「序號→位置」
    做最小平方擬合，再外推成 want+1 條。這樣外框線與雜線都不影響結果。
    """
    c = col_lines(y0, y1, x0 - 90, x1 + 90, frac=0.6)
    c = np.asarray(sorted(set(int(v) for v in c)), dtype=float)
    # 找出最長的一串「間距 ≈ pitch」
    best = []
    for i in range(len(c)):
        run = [c[i]]
        for v in c[i + 1:]:
            if abs(v - run[-1] - pitch) <= 3.0:
                run.append(v)
        if len(run) > len(best):
            best = run
    if len(best) < 3:
        best = list(c)
    idx = np.arange(len(best), dtype=float)
    k, b = np.polyfit(idx, np.array(best), 1)
    # 把這一串對到格子序號：以整個模組區的中心對齊
    lo = int(round((min(best) - (x0 - 10)) / k))
    start = min(best) - lo * k
    lines = [start + i * k for i in range(want + 1)]
    return lines


def quad(x0, y0, x1, y1):
    cx0, cy0, cx1, cy1 = CROP
    w, h = cx1 - cx0, cy1 - cy0
    f = lambda x, y: [round((x - cx0) / w, 4), round((y - cy0) / h, 4)]
    return [f(x0, y0), f(x1, y0), f(x1, y1), f(x0, y1)]


# 量到的「列」是模組的內部（約 60px），上下各還有一半的框線（約 12px）。
# 區塊要用完整的模組高度，不然一個 4 列的框會被切成 4 份 78.75 而不是 85，
# 往下累積就偏掉半格——疊圖看起來還好，但每一格的中心會跑掉。
FRAME = 12.5


def group_rows(rows, big=35):
    out, run = [], [rows[0]]
    for a, b in rows[1:]:
        if a - run[-1][1] > big:
            out.append(run); run = []
        run.append((a, b))
    out.append(run)
    return out


if __name__ == '__main__':
    blocks, total = [], 0

    # ── 條 A（最左）──
    rA = row_cells(1190, 1600)
    up, dn = rA[:8], rA[8:]
    for tag, rows, groups in [
            ('A上', up, [(1163, 1319, 3), (1351, 1611, 5)]),
            ('A下', dn, [(1111, 1319, 4), (1351, 1611, 5)])]:
        y0, y1 = rows[0][0], rows[-1][1]
        for gi, (gx0, gx1, nc) in enumerate(groups):
            blocks.append(dict(id='%s-%d' % (tag, gi + 1), rows=len(rows), cols=nc,
                               quad=quad(gx0, y0 - FRAME, gx1, y1 + FRAME)))
            total += len(rows) * nc

    # ── 條 B~F ──
    for bid, x0, x1 in [('B', 1690, 2100), ('C', 2210, 2625), ('D', 2755, 3172),
                        ('E', 3277, 3693), ('F', 3825, 4240)]:
        rows = row_cells(x0, x1)
        cl = cols_clean(x0, x1, rows[0][0], rows[-1][1], 9)
        gx0, gx1, nc = cl[0], cl[-1], len(cl) - 1
        for gi, run in enumerate(group_rows(rows)):
            blocks.append(dict(id='%s%d' % (bid, gi + 1), rows=len(run), cols=nc,
                               quad=quad(gx0, run[0][0] - FRAME, gx1, run[-1][1] + FRAME)))
            total += len(run) * nc

    print('區塊 %d 個，合計 %d 片  （圖上標 1720）%s'
          % (len(blocks), total, '✓' if total == 1720 else ' ← 不符！'))
    for b in blocks[:6]:
        print('   %-6s %d 行 × %2d 列 = %3d' % (b['id'], b['cols'], b['rows'], b['rows'] * b['cols']))
    json.dump(blocks, open('blocks.json', 'w'), ensure_ascii=False, indent=1)

    im = Image.open(SRC).crop(CROP)
    im = im.resize((int(im.width * SCALE), int(im.height * SCALE)), Image.LANCZOS)
    im.convert('L').save('祥利一期.png', optimize=True)
    print('底圖 %dx%d' % (im.width, im.height))
