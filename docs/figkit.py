"""Diagram helpers shared by the docs/gen_*.py figure scripts.

These figures are schematics (boxes / arrows / machine sketches), not data
plots, so we reuse figstyle's palette and surface but turn the axes off and
draw with matplotlib patches. All in-figure text is English on purpose: the
default matplotlib font has no Japanese glyphs (they render as tofu boxes),
so Japanese explanation lives in the article captions instead.
"""

import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import figstyle as fs  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import (  # noqa: E402
    FancyArrowPatch,
    FancyBboxPatch,
    Rectangle,
    Circle,
    Ellipse,
)

# Re-export the palette so gen scripts can `from figkit import fs, ...`.
SURFACE = fs.SURFACE
INK = fs.INK_PRIMARY
INK2 = fs.INK_SECONDARY
MUTED = fs.INK_MUTED
GRID = fs.GRID
AXIS = fs.AXIS
SERIES = fs.SERIES

# A few soft fills derived for schematic backgrounds (light tints).
TINT_BLUE = "#dbe8f8"
TINT_ORANGE = "#fbe0d1"
TINT_GREEN = "#d3efe3"
TINT_YELLOW = "#faedc4"
TINT_GREY = "#eceae3"
DARK_PANEL = "#1f2733"


def new_diagram(width, height, xlim, ylim, equal=False):
    """Blank schematic canvas: surface background, axes off, fixed limits."""
    fig, ax = plt.subplots(figsize=(width, height))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    if equal:
        ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, label="", fc="white", ec=INK, tc=INK,
        fontsize=9.5, lw=1.3, rounded=True, rounding=0.12, weight="medium",
        zorder=2, ha="center", va="center", label_dy=0.0):
    """Draw a rectangle (rounded by default) with centered text. (x,y)=lower-left."""
    if rounded:
        patch = FancyBboxPatch(
            (x, y), w, h,
            boxstyle=f"round,pad=0,rounding_size={rounding}",
            linewidth=lw, edgecolor=ec, facecolor=fc, zorder=zorder,
            mutation_aspect=1.0,
        )
    else:
        patch = Rectangle((x, y), w, h, linewidth=lw, edgecolor=ec,
                          facecolor=fc, zorder=zorder)
    ax.add_patch(patch)
    if label:
        ax.text(x + w / 2.0, y + h / 2.0 + label_dy, label, ha=ha, va=va,
                color=tc, fontsize=fontsize, fontweight=weight, zorder=zorder + 1,
                linespacing=1.25)
    return (x + w / 2.0, y + h / 2.0)


def arrow(ax, xy_from, xy_to, color=INK2, lw=1.5, style="-|>",
          mutation_scale=13, zorder=3, connectionstyle=None, ls="-"):
    """Directional arrow between two points."""
    kw = dict(arrowstyle=style, mutation_scale=mutation_scale, lw=lw,
              color=color, zorder=zorder, linestyle=ls,
              shrinkA=0, shrinkB=0)
    if connectionstyle:
        kw["connectionstyle"] = connectionstyle
    ax.add_patch(FancyArrowPatch(xy_from, xy_to, **kw))


def text(ax, x, y, s, color=INK2, fontsize=9.5, ha="center", va="center",
         weight="medium", zorder=5, style="normal", rotation=0):
    ax.text(x, y, s, color=color, fontsize=fontsize, ha=ha, va=va,
            fontweight=weight, zorder=zorder, fontstyle=style, rotation=rotation,
            linespacing=1.25)


def title(ax, x, y, s, fontsize=12.5, color=INK, ha="left"):
    ax.text(x, y, s, color=color, fontsize=fontsize, ha=ha, va="center",
            fontweight="bold")


def circle(ax, cx, cy, r, fc="white", ec=INK, lw=1.4, zorder=2):
    ax.add_patch(Circle((cx, cy), r, facecolor=fc, edgecolor=ec, lw=lw,
                        zorder=zorder))


def ellipse(ax, cx, cy, w, h, fc="white", ec=INK, lw=1.4, zorder=2):
    ax.add_patch(Ellipse((cx, cy), w, h, facecolor=fc, edgecolor=ec, lw=lw,
                        zorder=zorder))


def save(fig, path):
    # 出力先は生成物なのでリポジトリに入っていない。clone 直後でも書けるように作る。
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fig.savefig(path, dpi=140, facecolor=SURFACE, bbox_inches="tight",
                pad_inches=0.12)
    plt.close(fig)
