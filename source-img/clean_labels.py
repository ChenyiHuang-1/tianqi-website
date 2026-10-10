import sys, glob
from PIL import Image, ImageDraw
import statistics as st
STOP={'p-aluminium-foil-paper.webp':68,'p-bright-silver-foil.webp':75,'p-pet-bright-silver-board.webp':70,'p-pet-matte-pillar-holographic-board.webp':69,'p-pet-matte-silver-board.webp':71,'p-pet-plain-holographic-silver-board.webp':74,'p-pet-transfer-silver-board.webp':66,'p-plain-holographic-transfer-silver-board.webp':77}
def clean(path, out):
    im = Image.open(path).convert("RGB"); W, H = im.size; px = im.load()
    pur = [(x, y) for y in range(int(H*.12)) for x in range(int(W*.7))
           if (lambda r,g,b: b > 110 and b > r+30 and b > g+30)(*px[x, y])]
    if len(pur) < 200: return False
    xs = sorted(p[0] for p in pur); ys = sorted(p[1] for p in pur)
    x0, x1 = xs[len(xs)//200], xs[-len(xs)//200-1]; y0, y1 = ys[len(ys)//200], ys[-len(ys)//200-1]
    col = tuple(int(st.median(px[x, y][i] for x, y in pur[::7])) for i in range(3))
    d = ImageDraw.Draw(im)
    d.rectangle((x0-1, max(0,y0-1), x1+1, y1+1), fill=col)
    # right label column: from header right edge to where the card ends
    yy = y1 + 6; cx0 = x1 + 2; cx1 = cx0
    while cx1 < W-1 and sum(px[cx1, yy]) < 735: cx1 += 1
    grey = tuple(int(st.median(px[x, yy+2][i] for x in range(cx0, cx1))) for i in range(3))
    # find divider line below the vertical label
    ystop = int(H*.2)
    for y in range(y1+25, int(H*.3)):
        dark = sum(1 for x in range(cx0, cx1) if sum(px[x, y]) < sum(grey)-60)
        if cx1 > cx0 and dark > .6*(cx1-cx0): ystop = y - 2; break
    ystop = STOP[path]
    d.rectangle((cx0+2, 0, cx1-2, ystop), fill=grey)
    im.save(out, "WEBP", quality=82, method=6); print(path, (x0,y0,x1,y1), (cx0,cx1,ystop)); return True
for f in sys.argv[2:]: clean(f, sys.argv[1] + "/" + f)
