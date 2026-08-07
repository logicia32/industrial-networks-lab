"""図の文字はみ出し・重なりを、目視ではなく測定で検出する。

図を書き出すスクリプトを実行し、PNG に落とす直前の figure を掴んで、描画された
文字と図形の bbox（画面座標）を突き合わせる。見るのは4つ:

  1. 枠外       文字が、画像そのものの外へ出ていないか
  2. はみ出し   文字が、自分の入っている枠から出ていないか
  3. 文字重なり 文字同士が重なっていないか
  4. 食い込み   文字が、自分の枠ではない図形（隣の枠・パネル）に乗っていないか

検査対象の文字は ax.text() で置いたものだけでなく、タイトル・軸ラベル・目盛り
ラベル・凡例・suptitle を含む。図が複数の軸を持つ場合は全部の軸を見る。

    python docs/check_figures.py                 # 既定の対象すべて
    python docs/check_figures.py docs/gen_x.py   # 指定したものだけ

終了コードは検出件数（0 なら問題なし）。図を直したあとの確認に使う。
"""

import contextlib
import glob
import io
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for path in (ROOT, HERE):
    if path not in sys.path:
        sys.path.insert(0, path)

import figkit as k          # noqa: E402
import figstyle as fs       # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.patches import (  # noqa: E402
    Circle,
    Ellipse,
    FancyBboxPatch,
    Polygon,
    Rectangle,
)

# 下敷きになりうる図形。矢印は bbox が実体（細い線）とかけ離れるので入れない。
SOLIDS = (FancyBboxPatch, Rectangle, Circle, Ellipse, Polygon)

TOL_PX = 0.5        # 枠線にぴったり接するのは許す
EDGE_TOL_PX = 1.0   # 画像の端は 1px までは許す（アンチエイリアス分）
MIN_AREA_PX = 1.0   # 1 px^2 未満の重なりは無視する
NEAR_PX = 4.0       # これより近いと、重なっていなくても接触して見える


def overlap_area(a, b):
    x0, x1 = max(a.x0, b.x0), min(a.x1, b.x1)
    y0, y1 = max(a.y0, b.y0), min(a.y1, b.y1)
    return (x1 - x0) * (y1 - y0) if x1 > x0 and y1 > y0 else 0.0


def gap(a, b):
    """2つの bbox の隙間（px）。重なっていれば 0。"""
    dx = max(a.x0 - b.x1, b.x0 - a.x1, 0.0)
    dy = max(a.y0 - b.y1, b.y0 - a.y1, 0.0)
    return (dx * dx + dy * dy) ** 0.5


def inside(outer, inner, tol=TOL_PX):
    return (inner.x0 >= outer.x0 - tol and inner.x1 <= outer.x1 + tol
            and inner.y0 >= outer.y0 - tol and inner.y1 <= outer.y1 + tol)


def visible_ticklabels(locs, labels, lim):
    """表示範囲の中にある目盛りラベルだけ返す。

    matplotlib は表示範囲の外の目盛りも artist として持っていて（描画はされない）、
    それを数えると「画像の外に出ている」と誤検出する。
    """
    lo, hi = min(lim), max(lim)
    return [t for loc, t in zip(locs, labels) if lo <= loc <= hi]


def collect_texts(fig, rend):
    """図の中の「見えている文字」を全部集める。ax.texts だけでは足りない。"""
    artists = list(fig.texts)
    for ax in fig.axes:
        artists += list(ax.texts)
        artists.append(ax.title)                    # タイトルは軸 off でも描かれる
        # ax.axis("off") は axison を False にするだけで、目盛りラベルの visible は
        # True のまま残る。描かれていないものを検出しないよう axison で弾く。
        if getattr(ax, "axison", True):
            if ax.xaxis.get_visible():
                artists.append(ax.xaxis.label)
                artists += visible_ticklabels(ax.get_xticks(), ax.get_xticklabels(),
                                              ax.get_xlim())
            if ax.yaxis.get_visible():
                artists.append(ax.yaxis.label)
                artists += visible_ticklabels(ax.get_yticks(), ax.get_yticklabels(),
                                              ax.get_ylim())
        leg = ax.get_legend()
        if leg is not None:
            artists += list(leg.get_texts())
    out = []
    for t in artists:
        if not t.get_visible() or not t.get_text().strip():
            continue
        try:
            bb = t.get_window_extent(rend)
        except Exception:
            continue
        if bb.width <= 0 or bb.height <= 0:
            continue
        out.append((t, bb, t.get_text()))
    return out


def collect_boxes(fig, rend):
    boxes = []
    for ax in fig.axes:
        for p in ax.patches:
            if isinstance(p, SOLIDS) and p.get_visible():
                boxes.append((p, p.get_window_extent(rend)))
    return boxes


def analyse(fig, name, tight):
    """tight=True は bbox_inches="tight" で保存される図。

    tight は内容に外接するよう切り抜くので、公称キャンバスの外に出た文字も PNG に
    写る。つまり画像の端で切れることが起こらないので、枠外の検査はしない。
    """
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()

    texts = collect_texts(fig, rend)
    boxes = collect_boxes(fig, rend)
    canvas = fig.bbox

    found = []

    for t, tb, s in texts:
        # 持ち主の枠 = アンカーを含む枠のうち最小のもの
        try:
            x, y = t.get_transform().transform(t.get_position())
        except Exception:
            x = y = None
        own = []
        if x is not None:
            own = [(p, b) for p, b in boxes if b.x0 <= x <= b.x1 and b.y0 <= y <= b.y1]

        # 1. 画像の外へ出ていないか（切り抜かずに保存する図だけ）
        if not tight and not inside(canvas, tb, EDGE_TOL_PX):
            over = max(canvas.x0 - tb.x0, tb.x1 - canvas.x1,
                       canvas.y0 - tb.y0, tb.y1 - canvas.y1)
            found.append(f"枠外       {s!r:44.44} 画像の外へ {over:5.1f}px")

        # 2. 自分の枠からのはみ出し
        if own:
            _, ob = min(own, key=lambda pb: pb[1].width * pb[1].height)
            if not inside(ob, tb):
                dx = max(0.0, ob.x0 - tb.x0, tb.x1 - ob.x1)
                dy = max(0.0, ob.y0 - tb.y0, tb.y1 - ob.y1)
                found.append(f"はみ出し   {s!r:44.44} 横 {dx:5.1f}px / 縦 {dy:5.1f}px")

        # 4. 持ち主でない塗り図形への食い込み
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
            elif not own and gap(tb, b) < NEAR_PX:
                # 近接は「宙に浮いた文字」だけ見る。自分の枠に入っている文字は、
                # 枠が隣の図形と接していても枠が視覚的に守るので鳴らさない。
                found.append(f"近接       {s!r:44.44} 図形まで {gap(tb, b):4.1f}px")

    # 3. 文字同士の重なり
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            area = overlap_area(texts[i][1], texts[j][1])
            if area > MIN_AREA_PX:
                found.append(
                    f"文字重なり {texts[i][2]!r:26.26} x {texts[j][2]!r:26.26} {area:8.0f}px^2")

    found = sorted(set(found))
    print(f"=== {name}  （文字 {len(texts)} / 枠 {len(boxes)} / 軸 {len(fig.axes)}）")
    print("\n".join("  " + f for f in found) if found else "  問題なし")
    return len(found)


def default_targets():
    """gen_*.py に加えて、追従カーブを書き出すデモも見る。

    cia402_follow.png だけは figstyle 経由（切り抜きなし）で保存されるので、
    枠外の検査が意味を持つ唯一の図になる。
    """
    targets = sorted(glob.glob(os.path.join(HERE, "gen_*.py")))
    demo = os.path.join(ROOT, "02_canopen", "run_servo_demo.py")
    if os.path.exists(demo):
        targets.append(demo)
    return targets


def main(scripts):
    total = 0
    for script in scripts:
        figs = []
        # 図を掴むだけで PNG は書かない。save 経由と savefig 直呼びの両方を押さえる。
        # figkit.save は bbox_inches="tight"、figstyle.save は切り抜きなし。
        k.save = lambda fig, path, _f=figs: _f.append((fig, True))
        fs.save = lambda fig, path, _f=figs: _f.append((fig, False))
        Figure.savefig = (
            lambda self, *a, _f=figs, **kw: _f.append(
                (self, kw.get("bbox_inches") == "tight")))
        # 図を書き出したスクリプトの「wrote ...」等は、検査中は紛らわしいので捨てる。
        with contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(script, run_name="__main__")
        name = os.path.basename(script)
        if not figs:
            print(f"=== {name}\n  （図を書き出していない）")
            continue
        for i, (fig, tight) in enumerate(figs):
            label = name if len(figs) == 1 else f"{name} [{i + 1}/{len(figs)}]"
            total += analyse(fig, label, tight)
    print(f"\n合計 {total} 件")
    return total


if __name__ == "__main__":
    sys.exit(min(main(sys.argv[1:] or default_targets()), 125))
