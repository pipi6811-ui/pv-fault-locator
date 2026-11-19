# -*- coding: utf-8 -*-
"""畫廣興國小的模組排列圖（估計版）。

這個案場沒有串併圖，空拍是斜角的（近端模組約 19px、遠端更小，又有樹遮），
所以各棟的行列數量不到 ±1。改用「面板面積佔比」分配 957 片——面積量得準，
而且所有模組一樣大。佐證：C 棟分到 294 片，剛好等於 INV03+INV06 = 293。

棟的相對位置照空拍擺（羅盤 N 朝上）：
  D 棟最北，東西向；B 棟在中間，東西向；
  C 棟在西側，南北向偏東 15°；A 棟在東南，南北向偏東 22°。
坡面依維運評估報告的傾角／面向，不是用猜的。

顏色一律 rgb()，不用 #rrggbb —— data URI 裡的 # 會把 SVG 截斷。
"""
import io, math

CW, CH = 22.0, 14.0     # 一片模組的格子
PAD = 2.0
W, H = 1480, 1230

# id, 行(cols), 列(rows), 中心 x, 中心 y, 旋轉角(度, 順時針), 標題
BLOCKS = [
    ('D棟-北坡', 25, 5,  860, 300,   0, '面北 4°',      'top'),
    ('D棟-南坡', 25, 5,  860, 392,   0, '面南 184°',    'bottom'),
    ('B棟-北坡', 36, 3,  838, 596,   0, '面北 34°',      'top'),
    ('B棟-南坡', 36, 3,  838, 662,   0, '面南 160°',    'bottom'),
    ('C棟-西坡',  7, 21, 280, 905, -15, '面西 254°／269°','bottom'),
    ('C棟-東坡',  7, 21, 450, 860, -15, '面東 80°／85°',  'right'),
    ('A棟-西南坡', 9, 11,  972, 960, -22, '面西南 45°',   'bottom'),
    ('A棟-東坡',  7, 14, 1150, 915, -22, '面東 94°',      'top'),
]

def rot(px, py, cx, cy, deg):
    a = math.radians(deg)
    dx, dy = px - cx, py - cy
    return (cx + dx*math.cos(a) - dy*math.sin(a),
            cy + dx*math.sin(a) + dy*math.cos(a))

o = []; w = o.append
w('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">' % (W,H,W,H))
w('<rect width="%d" height="%d" fill="white"/>' % (W,H))
w('<style>'
  'text{font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;}'
  '.t{font-size:44px;font-weight:700;fill:rgb(20,20,20)}'
  '.s{font-size:21px;fill:rgb(90,90,90)}'
  '.warn{font-size:21px;fill:rgb(170,100,30)}'
  '.bl{font-size:27px;font-weight:700;fill:rgb(10,60,140)}'
  '.bs{font-size:16px;fill:rgb(70,110,170)}'
  '.n{font-size:13px;fill:rgb(120,120,120)}'
  '.pv{fill:rgb(214,226,242);stroke:rgb(45,80,140);stroke-width:1.2}'
  '</style>')

w('<text class="t" x="60" y="66">廣興國小　模組排列圖</text>')
w('<text class="s" x="60" y="106">URE D1K330H3A　330W × 957 片 ＝ 315.81 kWp　｜　DELTA M70A_262 × 7</text>')
w('<text class="s" x="60" y="136">鐵皮屋頂　｜　四棟，坡面依維運評估報告的傾角／面向　｜　不標串號，只記位置</text>')
w('<text class="warn" x="60" y="166">⚠ 各棟片數是按空拍的面板面積比例估的（斜角空拍量不到 ±1 片），現場請對一次再用。</text>')
w('<line x1="60" y1="190" x2="%d" y2="190" stroke="rgb(215,215,215)" stroke-width="2"/>' % (W-60))

# 羅盤
cx, cy = W-110, 268
w('<circle cx="%d" cy="%d" r="46" fill="none" stroke="rgb(150,150,150)" stroke-width="2"/>' % (cx,cy))
w('<path d="M%d,%d L%d,%d L%d,%d Z" fill="rgb(60,60,60)"/>' % (cx,cy-42,cx-11,cy+6,cx+11,cy+6))
for lab,dx,dy in [('N',0,-56),('S',0,66),('E',58,8),('W',-58,8)]:
    w('<text class="n" x="%d" y="%d" text-anchor="middle" font-size="18">%s</text>' % (cx+dx,cy+dy,lab))

quads = {}
for bid, cols, rows, bx, by, deg, sub, side in BLOCKS:
    bw, bh = cols*CW, rows*CH
    x0, y0 = bx-bw/2, by-bh/2
    g = '<g transform="rotate(%g %g %g)">' % (deg, bx, by)
    w(g)
    for r in range(rows):
        for c in range(cols):
            w('<rect class="pv" x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1.5"/>'
              % (x0+c*CW+PAD/2, y0+r*CH+PAD/2, CW-PAD, CH-PAD))
    w('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" '
      'stroke="rgb(20,20,20)" stroke-width="2.2"/>' % (x0-1.5, y0-1.5, bw+3, bh+3))
    w('</g>')
    quads[bid] = [rot(px,py,bx,by,deg) for px,py in
                  [(x0,y0),(x0+bw,y0),(x0+bw,y0+bh),(x0,y0+bh)]]

# 標籤擺在區塊的外框之外，不壓到面板
for bid, cols, rows, bx, by, deg, sub, side in BLOCKS:
    xs = [p[0] for p in quads[bid]]; ys = [p[1] for p in quads[bid]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    if side == 'top':      lx, ly, anc = (x0+x1)/2, y0-34, 'middle'
    elif side == 'bottom': lx, ly, anc = (x0+x1)/2, y1+36, 'middle'
    elif side == 'left':   lx, ly, anc = x0-18, (y0+y1)/2, 'end'
    else:                  lx, ly, anc = x1+18, (y0+y1)/2, 'start'
    w('<text class="bl" x="%.0f" y="%.0f" text-anchor="%s">%s</text>' % (lx, ly, anc, bid))
    w('<text class="bs" x="%.0f" y="%.0f" text-anchor="%s">%d 行 × %d 列 ＝ %d 片　%s</text>'
      % (lx, ly+21, anc, cols, rows, cols*rows, sub))

tot = sum(b[1]*b[2] for b in BLOCKS)
per = {}
for b in BLOCKS:
    bid, c, r = b[0], b[1], b[2]
    k = bid.split('-')[0]; per[k] = per.get(k,0)+c*r
w('<text class="s" x="60" y="%d">%s　＝ 合計 %d 片</text>'
  % (H-34, '　'.join('%s %d 片' % (k, per[k]) for k in ['A棟','B棟','C棟','D棟']), tot))
w('</svg>')

svg = ''.join(o)
io.open('gx/廣興國小.svg','w',encoding='utf-8').write(svg)
print('寫出 %.0f KB  畫布 %dx%d' % (len(svg.encode('utf-8'))/1024, W, H))
for k in ['A棟','B棟','C棟','D棟']: print(' ', k, per[k], '片')
print('合計', tot)
assert tot == 957, tot
print()
RC = dict((x[0],(x[2],x[1])) for x in BLOCKS)
for bid,(a,b,c,d) in quads.items():
    r,cc = RC[bid]
    print('    {id:"%s",rows:%d,cols:%d,major:"row",snake:false,' % (bid,r,cc))
    print('     quad:[[%.4f,%.4f],[%.4f,%.4f],[%.4f,%.4f],[%.4f,%.4f]],strings:[]},'
          % (a[0]/W,a[1]/H, b[0]/W,b[1]/H, c[0]/W,c[1]/H, d[0]/W,d[1]/H))
