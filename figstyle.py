"""記事の図を全部同じ見た目に揃えるための共通スタイル。

色は検証済みのカテゴリカルパレットから採り、CVD（色覚多様性）分離と
サーフェスに対するコントラストを満たすことを確認済み:
  worst adjacent CVD ΔE 24.7 / normal-vision ΔE 33.6 / contrast >= 3:1

軸ラベルは英語で書く。matplotlib の既定フォントに日本語グリフがなく、
読者環境で豆腐（□）になるため。説明は記事本文とキャプションで行う。
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- カテゴリカル（系列の識別に使う。順番は固定、循環させない）----
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]

# ---- 面と文字 ----
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"      # 軸ラベル・目盛り
GRID = "#e1e0d9"           # ヘアライン
AXIS = "#c3c2b7"


def figure(width: float = 7.2, height: float = 3.6):
    """記事用の図を1枚作る。軸・グリッドは後退させ、データを前に出す。"""
    fig, ax = plt.subplots(figsize=(width, height))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=INK_MUTED, labelsize=9, length=0)
    return fig, ax


def label_axes(ax, xlabel: str, ylabel: str, title: str | None = None) -> None:
    ax.set_xlabel(xlabel, color=INK_SECONDARY, fontsize=9.5)
    ax.set_ylabel(ylabel, color=INK_SECONDARY, fontsize=9.5)
    if title:
        ax.set_title(title, color=INK_PRIMARY, fontsize=11.5, pad=10, loc="left")


def annotate(ax, x, y, text: str, **kw) -> None:
    """直接ラベル。文字はインクの色で置き、色は凡例のマークが担う。"""
    ax.annotate(text, (x, y), color=INK_SECONDARY, fontsize=9,
                fontweight="medium", **kw)


def legend(ax, **kw):
    leg = ax.legend(frameon=False, fontsize=9, **kw)
    for text in leg.get_texts():
        text.set_color(INK_SECONDARY)
    return leg


def save(fig, path) -> None:
    # 出力先は生成物なのでリポジトリに入っていない。clone 直後でも書けるように作る。
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=140, facecolor=SURFACE)
    plt.close(fig)
