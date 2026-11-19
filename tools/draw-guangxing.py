# -*- coding: utf-8 -*-
"""畫廣興國小的模組排列圖（估計版，位置照空拍實測）。

各棟的位置、方位、每一坡的長寬，都是從空拍照量出來的，不是目測擺的：
  重心用面板遮罩的質心，傾斜用「每一列最左／最右面板像素」做線性迴歸。
  量到的是 D/B 兩棟水平（0°）、C 棟 -4°、A 棟 -3°——都幾乎正南北／正東西，
  第一版畫成 -15° / -22° 是錯的。
  另外 C 棟其實是「上下兩段獨立屋頂」，正好對應報告裡它有四個坡
  （傾角 26°/25° 一段、2°/3° 另一段）。

各棟片數仍是估的：空拍是斜角的（近端模組約 19px、遠端更小，又有樹遮），
行列數量不到 ±1，所以用面板面積佔比把 957 片分下去。

畫法：每一坡的方框 = 它在空拍上量到的footprint（等比例搬過來），
再切成 rows × cols。所以各棟的格子大小略有不同——這是刻意的，
格子大小跟著實際屋頂走，位置才會對。

顏色一律 rgb()，不用 #rrggbb —— data URI 裡的 # 會把 SVG 截斷。
"""
import io, math

# 空拍實測：id, 重心(img x,y), 沿屋脊長 L, 橫向寬 W, 傾斜角(度), 行(cols), 列(rows), 坡向
# 「橫」的棟長邊是水平；「直」的棟長邊是垂直。
SLOPES = [
    ('D棟-北坡',     1278, 439, 496, 52,  0.0, 'h', 24,  5, '面北 4°'),
    ('D棟-南坡',     1278, 502, 497, 71,  0.0, 'h', 24,  7, '面南 184°'),
    ('B棟-北坡',     1311, 786, 736, 37,  0.0, 'h', 35,  3, '面北 34°'),
    ('B棟-南坡西段',  1104, 833, 329, 42,  0.0, 'h', 16,  4, '面南 160°'),
    ('B棟-南坡東段',  1514, 834, 321, 56,  0.0, 'h', 15,  5, '面南 160°'),
    ('C棟上段-西坡',   754, 730, 156, 40, 0.0, 'v',  4,  8, '面西 254°'),
    ('C棟上段-東坡',   821, 745, 187, 60, 0.0, 'v',  6,  9, '面東 80°'),
    ('C棟下段-西坡',   743,1055, 367, 56, 0.0, 'v',  5, 18, '面西 269°'),
    ('C棟下段-東坡',   800,1033, 391, 56, 0.0, 'v',  5, 19, '面東 85°'),
    ('A棟-西南坡',    1612,1085, 301, 64, 0.0, 'v',  6, 14, '面西南 45°'),
    ('A棟-東坡',     1686,1088, 301, 56, 0.0, 'v',  5, 14, '面東 94°'),
]

# 空拍 → 畫布：單一平移＋縮放，相對位置原封不動
IX0, IY0, IX1, IY1 = 700, 400, 1730, 1250
S = 1.18
OX, OY = 250 - IX0*S, 250 - IY0*S
W = int((IX1-IX0)*S) + 530
H = int((IY1-IY0)*S) + 400
def M(x, y): return (x*S+OX, y*S+OY)

def rot(px, py, cx, cy, deg):
    a = math.radians(deg); dx, dy = px-cx, py-cy
    return (cx + dx*math.cos(a) - dy*math.sin(a), cy + dx*math.sin(a) + dy*math.cos(a))

o = []; w = o.append
w('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">' % (W,H,W,H))
w('<rect width="%d" height="%d" fill="white"/>' % (W,H))
w('<style>text{font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;}'
  '.t{font-size:44px;font-weight:700;fill:rgb(20,20,20)}'
  '.s{font-size:21px;fill:rgb(90,90,90)}'
  '.warn{font-size:21px;fill:rgb(170,100,30)}'
  '.bl{font-size:25px;font-weight:700;fill:rgb(10,60,140)}'
  '.bs{font-size:16px;fill:rgb(70,110,170)}'
  '.n{font-size:18px;fill:rgb(120,120,120)}'
  '.pv{fill:rgb(214,226,242);stroke:rgb(45,80,140);stroke-width:1.1}</style>')

w('<text class="t" x="60" y="66">廣興國小　模組排列圖</text>')
w('<text class="s" x="60" y="106">URE D1K330H3A　330W × 957 片 ＝ 315.81 kWp　｜　DELTA M70A_262 × 7　｜　鐵皮屋頂</text>')
w('<text class="s" x="60" y="136">各坡的位置與長寬都是從空拍量出來的；各棟互相正交（空拍上的 3～4° 是機頭沒對正）。</text>')
w('<text class="warn" x="60" y="166">⚠ 行列數是用實測 footprint ÷ 模組尺寸推的，不是一片一片數的（斜角空拍數不準）。現場請對一次再用。</text>')
w('<line x1="60" y1="192" x2="%d" y2="192" stroke="rgb(215,215,215)" stroke-width="2"/>' % (W-60))

cx0, cy0 = W-120, 300
w('<circle cx="%d" cy="%d" r="46" fill="none" stroke="rgb(150,150,150)" stroke-width="2"/>' % (cx0,cy0))
w('<path d="M%d,%d L%d,%d L%d,%d Z" fill="rgb(60,60,60)"/>' % (cx0,cy0-42,cx0-11,cy0+6,cx0+11,cy0+6))
for lab,dx,dy in [('N',0,-56),('S',0,70),('E',60,8),('W',-60,8)]:
    w('<text class="n" x="%d" y="%d" text-anchor="middle">%s</text>' % (cx0+dx,cy0+dy,lab))

quads = {}; boxes = {}
for bid, ix, iy, L, Wd, deg, ori, cols, rows, face in SLOPES:
    bx, by = M(ix, iy)
    bw, bh = (L*S, Wd*S) if ori == 'h' else (Wd*S, L*S)
    x0, y0 = bx-bw/2, by-bh/2
    cw, ch = bw/cols, bh/rows
    w('<g transform="rotate(%g %g %g)">' % (deg, bx, by))
    for r in range(rows):
        for c in range(cols):
            w('<rect class="pv" x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="1"/>'
              % (x0+c*cw+0.8, y0+r*ch+0.8, cw-1.6, ch-1.6))
    w('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" '
      'stroke="rgb(20,20,20)" stroke-width="2"/>' % (x0-1.2, y0-1.2, bw+2.4, bh+2.4))
    w('</g>')
    q = [rot(px,py,bx,by,deg) for px,py in [(x0,y0),(x0+bw,y0),(x0+bw,y0+bh),(x0,y0+bh)]]
    quads[bid] = q; boxes[bid] = (q, cols, rows, face)

SIDE = {'D棟-北坡':'top','D棟-南坡':'bottom','B棟-北坡':'top',
        'B棟-南坡西段':'bottom','B棟-南坡東段':'bottom',
        'C棟上段-西坡':'left','C棟上段-東坡':'top','C棟下段-西坡':'left',
        'C棟下段-東坡':'right','A棟-西南坡':'left','A棟-東坡':'right'}
for bid,(q,cols,rows,face) in boxes.items():
    xs=[p[0] for p in q]; ys=[p[1] for p in q]
    x0,x1,y0,y1 = min(xs),max(xs),min(ys),max(ys)
    sd = SIDE[bid]
    if sd=='top':      lx,ly,anc = (x0+x1)/2, y0-32, 'middle'
    elif sd=='bottom': lx,ly,anc = (x0+x1)/2, y1+34, 'middle'
    elif sd=='left':   lx,ly,anc = x0-16, (y0+y1)/2, 'end'
    else:              lx,ly,anc = x1+16, (y0+y1)/2, 'start'
    w('<text class="bl" x="%.0f" y="%.0f" text-anchor="%s">%s</text>' % (lx,ly,anc,bid))
    w('<text class="bs" x="%.0f" y="%.0f" text-anchor="%s">%d 行 × %d 列 ＝ %d 片　%s</text>'
      % (lx,ly+20,anc,cols,rows,cols*rows,face))

per = {}
for bid,_,_,_,_,_,_,c,r,_ in SLOPES:
    k = bid.split('棟')[0]+'棟'; per[k] = per.get(k,0)+c*r
tot = sum(per.values())
w('<text class="s" x="60" y="%d">%s　＝ 合計 %d 片</text>'
  % (H-36, '　'.join('%s %d 片' % (k,per[k]) for k in ['A棟','B棟','C棟','D棟']), tot))
w('</svg>')

svg = ''.join(o)
io.open('gx/廣興國小.svg','w',encoding='utf-8').write(svg)
print('寫出 %.0f KB  畫布 %dx%d' % (len(svg.encode('utf-8'))/1024, W, H))
for k in ['A棟','B棟','C棟','D棟']: print(' ', k, per[k], '片')
print('合計', tot); assert tot == 957, tot
print()
RC = dict((s[0],(s[8],s[7])) for s in SLOPES)
for bid,q in quads.items():
    r,c = RC[bid]
    print('    {id:"%s",rows:%d,cols:%d,major:"row",snake:false,' % (bid,r,c))
    print('     quad:[[%.4f,%.4f],[%.4f,%.4f],[%.4f,%.4f],[%.4f,%.4f]],strings:[]},'
          % tuple(v for p in q for v in (p[0]/W, p[1]/H)))
