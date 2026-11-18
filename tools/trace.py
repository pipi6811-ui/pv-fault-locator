#!/usr/bin/env python3
"""把掃描的串併圖描成向量 SVG。

沙箱沒有 potrace／autotrace，所以自己做：
  1. 轉灰階，用局部門檻二值化（掃描紙張明暗不均，固定門檻會把淡線吃掉）
  2. 去雜點（掃描的髒污、JPEG 雜訊）
  3. marching squares 取出所有輪廓（含內孔）
  4. Douglas-Peucker 簡化，控制檔案大小
  5. 一條 path 全部裝起來，fill-rule evenodd 讓內孔自動鏤空

輸出是純圖形輪廓：線條與文字都變成填滿的外框，放多大都不會糊。
"""
import sys, io, json
from PIL import Image
import numpy as np

SRC = sys.argv[1]
OUT = sys.argv[2]
SCALE = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0   # 先放大再二值化，輪廓較平滑
EPS = float(sys.argv[4]) if len(sys.argv) > 4 else 0.9     # 簡化容忍度（放大後的像素）
MIN_AREA = float(sys.argv[5]) if len(sys.argv) > 5 else 12 # 小於這個面積的連通塊當雜點丟掉

im = Image.open(SRC).convert("L")
W0, H0 = im.size
if SCALE != 1.0:
    im = im.resize((int(W0 * SCALE), int(H0 * SCALE)), Image.LANCZOS)
g = np.asarray(im, dtype=np.float32)
H, W = g.shape

# ── 局部門檻 ──
# 紙張有明暗漸層、邊角偏灰，整張用一個門檻會把淡的線丟掉或把灰底吃進來。
# 用大半徑的盒狀模糊當「背景亮度」，比背景暗一截的才算墨。
def boxblur(a, r):
    # 積分圖，O(1) 取任意矩形平均
    p = np.pad(a, r, mode="edge")
    s = p.cumsum(0).cumsum(1)
    s = np.pad(s, ((1, 0), (1, 0)))
    y, x = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    y0, x0 = y, x
    y1, x1 = y + 2 * r + 1, x + 2 * r + 1
    tot = s[y1, x1] - s[y0, x1] - s[y1, x0] + s[y0, x0]
    return tot / ((2 * r + 1) ** 2)

R = max(8, int(min(H, W) * 0.02))
bg = boxblur(g, R)
ink = (g < bg - 18) | (g < 110)        # 比背景暗一截，或本來就很黑
ink = ink.astype(np.uint8)

# ── 去雜點：丟掉面積太小的連通塊（4 連通，用氾濫填充的疊代版避免遞迴爆掉）──
def despeckle(mask, min_area):
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out = np.zeros_like(mask)
    idx = np.argwhere(mask > 0)
    for sy, sx in idx:
        if seen[sy, sx]:
            continue
        stack = [(sy, sx)]
        seen[sy, sx] = True
        comp = []
        while stack:
            y, x = stack.pop()
            comp.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(comp) >= min_area:
            for y, x in comp:
                out[y, x] = 1
    return out

ink = despeckle(ink, int(MIN_AREA * SCALE * SCALE / 4))
print(f"墨點比例 {ink.mean()*100:.2f}%  尺寸 {W}x{H}", file=sys.stderr)

# ── crack following：沿著墨與紙的交界走 ──
# 先前用 marching squares，鞍點與 visited 的判斷有漏，輪廓會中途斷掉，
# 再被 Z 硬接起來，就在圖上填出一塊不存在的黑色三角形。
# 改成走「裂縫」：每個墨像素凡是鄰居是紙的那一邊，就放一條有向邊，
# 方向統一讓墨在右手邊。這樣每條輪廓在數學上保證閉合，不會有斷頭。
pad = np.pad(ink, 1).astype(bool)
core = pad[1:-1, 1:-1]
up    = core & ~pad[:-2, 1:-1]
down  = core & ~pad[2:,  1:-1]
left  = core & ~pad[1:-1, :-2]
right = core & ~pad[1:-1, 2:]

edges = {}          # (x,y) -> [(x2,y2), ...]
def add(a, b):
    edges.setdefault(a, []).append(b)

for mask, mk in ((up, 0), (right, 1), (down, 2), (left, 3)):
    ys_, xs_ = np.nonzero(mask)
    for k in range(len(ys_)):
        y = int(ys_[k]); x = int(xs_[k])
        if mk == 0:   add((x, y),     (x + 1, y))
        elif mk == 1: add((x + 1, y), (x + 1, y + 1))
        elif mk == 2: add((x + 1, y + 1), (x, y + 1))
        else:         add((x, y + 1), (x, y))

print(f"交界邊 {sum(len(v) for v in edges.values())}", file=sys.stderr)

# 對角相接的地方一個頂點會有兩條出邊；挑轉得最右（順時針）的那條，
# 兩個區塊才會各自成為獨立的輪廓，不會纏在一起。

contours = []
for start_v in list(edges.keys()):
    while edges.get(start_v):
        pts = [start_v]
        v = start_v
        prev_d = None
        guard = 0
        while True:
            guard += 1
            if guard > 2_000_000:
                break
            outs = edges.get(v)
            if not outs:
                break
            if len(outs) == 1:
                nxt = outs.pop(0)
            else:
                # 依上一步方向挑最右轉的那條
                def dirof(a, b):
                    dx, dy = b[0] - a[0], b[1] - a[1]
                    return 0 if dx > 0 else 2 if dx < 0 else 1 if dy > 0 else 3
                best_i, best_r = 0, 99
                for i, cand in enumerate(outs):
                    d = dirof(v, cand)
                    r = 0 if prev_d is None else (d - prev_d) % 4
                    rank = {3: 0, 0: 1, 1: 2, 2: 3}[r] if prev_d is not None else 1
                    if rank < best_r:
                        best_r, best_i = rank, i
                nxt = outs.pop(best_i)
            if not edges[v]:
                del edges[v]
            prev_d = (0 if nxt[0] > v[0] else 2 if nxt[0] < v[0] else
                      1 if nxt[1] > v[1] else 3)
            v = nxt
            if v == start_v:
                break
            pts.append(v)
        if len(pts) >= 4:
            contours.append(pts)

print(f"輪廓 {len(contours)} 條，點數 {sum(len(c) for c in contours)}", file=sys.stderr)

# ── Douglas-Peucker ──
def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        ax, ay = pts[a]; bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        n = (dx * dx + dy * dy) ** 0.5
        best, bi = -1.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            if n == 0:
                d = ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
            else:
                d = abs(dy * px - dx * py + bx * ay - by * ax) / n
            if d > best:
                best, bi = d, i
        if best > eps:
            keep[bi] = True
            stack.append((a, bi)); stack.append((bi, b))
    return [p for p, k in zip(pts, keep) if k]

paths = []
total = 0
for c in contours:
    s = rdp(c, EPS)
    if len(s) < 3:
        continue
    total += len(s)
    d = "M" + " ".join(f"{x/SCALE:.1f},{y/SCALE:.1f}" for x, y in s) + "Z"
    paths.append(d)

print(f"簡化後點數 {total}", file=sys.stderr)

svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W0} {H0}" '
    f'width="{W0}" height="{H0}">'
    f'<rect width="{W0}" height="{H0}" fill="white"/>'
    f'<path fill="rgb(17,17,17)" fill-rule="evenodd" d="{"".join(paths)}"/></svg>'
)
io.open(OUT, "w", encoding="utf-8").write(svg)
print(f"寫出 {OUT}  {len(svg)/1024:.0f} KB", file=sys.stderr)
