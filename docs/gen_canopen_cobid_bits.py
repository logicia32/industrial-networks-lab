"""Figure: CANopen 11-bit COB-ID structure and priority ordering.

COB-ID = Function Code (4 bit) + Node-ID (7 bit). A smaller COB-ID value
wins the CAN bus arbitration, so lower value = higher priority.
All in-figure text is English (matplotlib default font lacks JP glyphs).
"""
import os
import sys

import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import figstyle as fs

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figures", "canopen_cobid_bits.png")


def tint(hex_color: str, f: float) -> str:
    """Blend a hex color toward white by fraction f (0..1)."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    r = int(r + (255 - r) * f)
    g = int(g + (255 - g) * f)
    b = int(b + (255 - b) * f)
    return f"#{r:02x}{g:02x}{b:02x}"


def rounded(ax, x, y, w, h, fc, ec, lw=1.2, radius=0.6, z=2):
    box = mpatches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z,
    )
    ax.add_patch(box)
    return box


def main():
    fig, ax = fs.figure(width=9.6, height=5.0)
    # strip the data-plot chrome; this is a diagram
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_title("CAN 2.0A COB-ID  =  Function Code (4 bit)  +  Node-ID (7 bit)",
                 color=fs.INK_PRIMARY, fontsize=13, pad=12, loc="left")

    blue = fs.SERIES[0]
    orange = fs.SERIES[1]
    green = fs.SERIES[2]
    amber = fs.SERIES[3]

    # ---- bit-box register (11 bits, MSB left) ----
    n = 11
    box_w = 6.6
    box_h = 13
    start_x = 13.0
    y0 = 68
    fc_fill = tint(blue, 0.80)
    id_fill = tint(green, 0.80)
    for i in range(n):
        bit = 10 - i
        x = start_x + i * box_w
        if i < 4:
            fc, ec = fc_fill, blue
        else:
            fc, ec = id_fill, green
        rounded(ax, x, y0, box_w - 0.5, box_h, fc, ec, lw=1.3, radius=0.5)
        ax.text(x + (box_w - 0.5) / 2, y0 + box_h / 2, f"b{bit}",
                ha="center", va="center", fontsize=9.5, color=fs.INK_PRIMARY,
                zorder=3)
    # MSB / LSB orientation markers at the ends
    ax.text(start_x + (box_w - 0.5) / 2, y0 + box_h + 2.6, "MSB",
            ha="center", va="center", fontsize=8, color=fs.INK_MUTED)
    ax.text(start_x + (n - 1) * box_w + (box_w - 0.5) / 2, y0 + box_h + 2.6,
            "LSB", ha="center", va="center", fontsize=8, color=fs.INK_MUTED)

    # group brackets under the boxes
    fc_left = start_x
    fc_right = start_x + 4 * box_w - 0.5
    id_left = start_x + 4 * box_w
    id_right = start_x + n * box_w - 0.5
    yb = y0 - 3.2

    def bracket(xl, xr, y, color, label):
        ax.plot([xl, xl, xr, xr], [y + 1.6, y, y, y + 1.6],
                color=color, lw=1.4, zorder=2)
        ax.text((xl + xr) / 2, y - 3.6, label, ha="center", va="center",
                fontsize=10, color=color, fontweight="bold")

    bracket(fc_left, fc_right, yb, blue, "Function Code  (4 bit)")
    bracket(id_left, id_right, yb, green, "Node-ID  (7 bit,  1..127)")

    ax.text(50, 55.5,
            "Example:  TPDO1 of Node 3   =   0x180  +  3   =   0x183",
            ha="center", va="center", fontsize=9.5, color=fs.INK_SECONDARY,
            style="italic")

    # ---- priority ladder ----
    ladder_y = 30
    items = [
        ("NMT", "0x000", blue),
        ("SYNC", "0x080", orange),
        ("PDO", "0x180+", green),
        ("SDO", "0x580+", amber),
        ("Heartbeat", "0x700+", fs.INK_MUTED),
    ]
    xs = [17, 33.25, 49.5, 65.75, 82]
    mb_w, mb_h = 13.0, 11.0
    for (name, hx, color), xc in zip(items, xs):
        rounded(ax, xc - mb_w / 2, ladder_y, mb_w, mb_h,
                tint(color, 0.82), color, lw=1.4, radius=0.7)
        ax.text(xc, ladder_y + mb_h - 3.4, name, ha="center", va="center",
                fontsize=10, color=fs.INK_PRIMARY, fontweight="bold")
        ax.text(xc, ladder_y + 3.2, hx, ha="center", va="center",
                fontsize=9.5, color=color, fontweight="bold")

    # priority arrow beneath the ladder
    arr_y = 21
    ax.add_patch(FancyArrowPatch(
        (12, arr_y), (88, arr_y),
        arrowstyle="-|>", mutation_scale=16,
        color=fs.INK_SECONDARY, lw=1.6, zorder=2))
    ax.text(12, arr_y + 3.0, "lower COB-ID value", ha="left", va="center",
            fontsize=9, color=fs.INK_SECONDARY)
    ax.text(88, arr_y + 3.0, "higher COB-ID value", ha="right", va="center",
            fontsize=9, color=fs.INK_SECONDARY)
    ax.text(12, arr_y - 3.6, "wins arbitration  (higher priority)",
            ha="left", va="center", fontsize=9, color=fs.INK_PRIMARY,
            fontweight="bold")
    ax.text(88, arr_y - 3.6, "lower priority", ha="right", va="center",
            fontsize=9, color=fs.INK_SECONDARY)

    # 出力先は生成物なのでリポジトリに入っていない。clone 直後でも書けるように作る。
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=140, facecolor=fs.SURFACE, bbox_inches="tight")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
