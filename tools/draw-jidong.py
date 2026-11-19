# -*- coding: utf-8 -*-
"""畫吉東國小的模組排列圖。

這個案場沒有現成的串併圖，是照空拍照量出來的排列直接畫的：
  A 棟 6 行 × 30 列 = 180 片（INV02 20串2併… 實為 20串9併）
  B 棟 4 行 ×  9 列 =  36 片（INV01 18串2併）
  合計 216 片 × 330W = 71.28 kWp，與維運評估報告相符。

不畫串線：這個案場不需要，工作人員只要點到哪一片。
顏色一律用 rgb()，不用 #rrggbb —— data URI 裡的 # 是片段起點，會把 SVG 截斷。
"""
import io

CW, CH = 62, 40          # 一片模組的格子大小（1.55:1，與空拍量到的比例一致）
PAD = 4                  # 模組與格線之間的留白
L, T = 96, 268           # 左、上邊界（留給行列號與標題）
GAPX = 150               # 兩棟之間的水平間距

A_C, A_R = 6, 30
B_C, B_R = 4, 9

bw, bh = B_C*CW, B_R*CH
aw, ah = A_C*CW, A_R*CH
W = max(1120, L + bw + GAPX + aw + 150)
H = T + ah + 90

o = []
w = o.append
w('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">' % (W, H, W, H))
w('<rect width="%d" height="%d" fill="white"/>' % (W, H))
w('<style>'
  'text{font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;}'
  '.t{font-size:46px;font-weight:700;fill:rgb(20,20,20)}'
  '.s{font-size:22px;fill:rgb(90,90,90)}'
  '.bl{font-size:34px;font-weight:700;fill:rgb(10,60,140)}'
  '.bs{font-size:20px;fill:rgb(70,110,170)}'
  '.n{font-size:17px;fill:rgb(110,110,110)}'
  '.pv{fill:rgb(214,226,242);stroke:rgb(45,80,140);stroke-width:2}'
  '</style>')

w('<text class="t" x="%d" y="70">吉東國小　模組排列圖</text>' % L)
w('<text class="s" x="%d" y="112">URE D1K330H3A　330W × 216 片 ＝ 71.28 kWp</text>' % L)
w('<text class="s" x="%d" y="144">A 棟 傾角 11°／面西 287°　　B 棟 傾角 10°／面東南 123°</text>' % L)
w('<text class="s" x="%d" y="176" fill="rgb(150,110,60)">'
  '依空拍實際排列繪製，不是廠商的串併圖；這個案場不標串號，只記位置。</text>' % L)
w('<line x1="%d" y1="200" x2="%d" y2="200" stroke="rgb(210,210,210)" stroke-width="2"/>'
  % (L, W-60))

def block(x0, y0, cols, rows, name, sub):
    w('<text class="bl" x="%d" y="%d">%s</text>' % (x0, y0-46, name))
    w('<text class="bs" x="%d" y="%d">%s</text>' % (x0, y0-20, sub))
    for c in range(cols):                                  # 行號
        w('<text class="n" x="%.1f" y="%.1f" text-anchor="middle">%d</text>'
          % (x0+c*CW+CW/2, y0-4, c+1))
    for r in range(rows):                                  # 列號：每列都標
        w('<text class="n" x="%.1f" y="%.1f" text-anchor="end">%d</text>'
          % (x0-10, y0+r*CH+CH/2+6, r+1))
    for r in range(rows):
        for c in range(cols):
            w('<rect class="pv" x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3"/>'
              % (x0+c*CW+PAD/2, y0+r*CH+PAD/2, CW-PAD, CH-PAD))
    w('<rect x="%.1f" y="%.1f" width="%d" height="%d" fill="none" '
      'stroke="rgb(20,20,20)" stroke-width="3"/>' % (x0-2, y0-2, cols*CW+4, rows*CH+4))

bx, by = L, T
block(bx, by, B_C, B_R, 'B 棟', '4 行 × 9 列 ＝ 36 片　INV01（18 串 2 併）')
ax, ay = L + bw + GAPX, T
block(ax, ay, A_C, A_R, 'A 棟', '6 行 × 30 列 ＝ 180 片　INV02（20 串 9 併）')
# A 棟中央的維修走道：畫虛線，不留空隙——留了空隙格子就不等寬，點選會算錯
w('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="rgb(190,90,40)" '
  'stroke-width="3" stroke-dasharray="10 8"/>' % (ax+3*CW, ay, ax+3*CW, ay+A_R*CH))
w('<text class="bs" x="%.1f" y="%.1f" text-anchor="middle" fill="rgb(190,90,40)">'
  '↑ 中央走道</text>' % (ax+3*CW, ay+A_R*CH+28))

w('<text class="s" x="%d" y="%d">一格 ＝ 一片模組。點到哪一格，記的就是「A 棟 R12-C4」這樣的位置。</text>'
  % (L, T+ah+54))
w('</svg>')

svg = ''.join(o)
io.open('jd/吉東國小.svg', 'w', encoding='utf-8').write(svg)
print('寫出 %.0f KB  畫布 %dx%d' % (len(svg.encode('utf-8'))/1024, W, H))
print('A 棟', A_C*A_R, '片   B 棟', B_C*B_R, '片   合計', A_C*A_R+B_C*B_R)
assert A_C*A_R == 180 and B_C*B_R == 36 and A_C*A_R+B_C*B_R == 216
# 給 SEEDS 用的四角（正規化）
for nm,(x0,y0,c,r) in {'A棟':(ax,ay,A_C,A_R),'B棟':(bx,by,B_C,B_R)}.items():
    print('%s quad: [[%.4f,%.4f],[%.4f,%.4f],[%.4f,%.4f],[%.4f,%.4f]]  rows=%d cols=%d'
          % (nm, x0/W,y0/H, (x0+c*CW)/W,y0/H, (x0+c*CW)/W,(y0+r*CH)/H, x0/W,(y0+r*CH)/H, r, c))
