"""図の文字はみ出し・重なりを、目視ではなく測定で検出する。

gen_*.py を実行し、PNG に落とす直前の figure を掴んで、描画された文字と図形の
bbox（画面座標）を突き合わせる。見るのは3つ:

  1. はみ出し     文字が、自分の入っている枠から出ていないか
  2. 文字重なり   文字同士が重なっていないか
  3. 食い込み     文字が、自分の枠ではない図形（隣の枠・パネル）に乗っていないか

    python docs/check_figures.py                 # docs/gen_*.py を全部
    python docs/check_figures.py docs/gen_x.py   # 指定したものだけ

終了コードは検出件数（0 なら問題なし）。図を直したあとの確認に使う。
"""

import glob
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for path in (os.path.dirname(HERE), HERE):
    if path not in sys.path:
        sys.path.insert(0, path)

import figkit as k          # noqa: E402
import figstyle as fs       # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

TOL_PX = 0.5        # 枠線にぴったり接するのは許す
MIN_AREA_PX = 1.0   # 1 px^2 未満の重なりは無視する


def overlap_area(a, b):
    x0, x1 = max(a.x0, b.x0), min(a.x1, b.x1)
    y0, y1 = max(a.y0, b.y0), min(a.y1, b.y1)
    return (x1 - x0) * (y1 - y0) if x1 > x0 and y1 > y0 else 0.0


def inside(outer, inner):
    return (inner.x0 >= outer.x0 - TOL_PX and inner.x1 <= outer.x1 + TOL_PX
            and inner.y0 >= outer.y0 - TOL_PX and inner.y1 <= outer.y1 + TOL_PX)


def analyse(fig, name):
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    ax = fig.axes[0]

    boxes = [(p, p.get_window_extent(rend)) for p in ax.patches
             if isinstance(p, (FancyBboxPatch, Rectangle))]
    texts = [(t, t.get_window_extent(rend), t.get_text()) for t in ax.texts
             if t.get_text().strip()]

    def owners_of(t):
        """文字のアンカーを含む枠。いちばん小さいものを持ち主とみなす。"""
        x, y = ax.transData.transform(t.get_position())
        return [(p, b) for p, b in boxes if b.x0 <= x <= b.x1 and b.y0 <= y <= b.y1]

    found = []
    for t, tb, s in texts:
        own = owners_of(t)
        if own:
            _, ob = min(own, key=lambda pb: pb[1].width * pb[1].height)
            if not inside(ob, tb):
                dx = max(0.0, ob.x0 - tb.x0, tb.x1 - ob.x1)
                dy = max(0.0, ob.y0 - tb.y0, tb.y1 - ob.y1)
                found.append(f"はみ出し   {s!r:44.44} 横 {dx:5.1f}px / 縦 {dy:5.1f}px")
        own_ids = {id(p) for p, _ in own}
        for p, b in boxes:
            if id(p) in own_ids:
                continue
            fc = p.get_facecolor()
            if len(fc) >= 4 and fc[3] <= 0.05:      # 塗りなしの枠は下敷きにならない
                continue
            area = overlap_area(tb, b)
            if area > MIN_AREA_PX:
                found.append(f"食い込み   {s!r:44.44} {area:8.0f}px^2")

    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            area = overlap_area(texts[i][1], texts[j][1])
            if area > MIN_AREA_PX:
                found.append(
                    f"文字重なり {texts[i][2]!r:26.26} x {texts[j][2]!r:26.26} {area:8.0f}px^2")

    found = sorted(set(found))
    print(f"=== {name}")
    print("\n".join("  " + f for f in found) if found else "  問題なし")
    return len(found)


def main(scripts):
    total = 0
    for script in scripts:
        captured = {}
        # 図を掴むだけで PNG は書かない。save 経由と savefig 直呼びの両方を押さえる。
        k.save = fs.save = lambda fig, path, _c=captured: _c.setdefault("fig", fig)
        Figure.savefig = lambda self, *a, _c=captured, **kw: _c.setdefault("fig", self)
        runpy.run_path(script, run_name="__main__")
        fig = captured.get("fig")
        if fig is None:
            print(f"=== {os.path.basename(script)}\n  （図を書き出していない）")
            continue
        total += analyse(fig, os.path.basename(script))
    print(f"\n合計 {total} 件")
    return total


if __name__ == "__main__":
    args = sys.argv[1:] or sorted(glob.glob(os.path.join(HERE, "gen_*.py")))
    sys.exit(min(main(args), 125))
