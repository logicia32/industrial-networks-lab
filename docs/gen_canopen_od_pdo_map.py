"""Figure: how an Object Dictionary object reaches the wire.

Three layers, top to bottom:
  1. Object Dictionary  -- the source objects (scattered indices)
  2. TPDO1 mapping 0x1A00 -- an ordered list of descriptors 0xIIIISSLL
  3. CAN frame           -- the 8 payload bytes, packed in mapping order
All in-figure text is English (matplotlib default font lacks JP glyphs).
"""
import os
import sys

import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import figstyle as fs

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figures", "canopen_od_pdo_map.png")


def tint(hex_color: str, f: float) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    r = int(r + (255 - r) * f)
    g = int(g + (255 - g) * f)
    b = int(b + (255 - b) * f)
    return f"#{r:02x}{g:02x}{b:02x}"


def rbox(ax, x, y, w, h, fc, ec, lw=1.3, radius=0.14, z=2):
    ax.add_patch(mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z))


def main():
    blue, orange, green = fs.SERIES[0], fs.SERIES[1], fs.SERIES[2]
    gray = fs.INK_MUTED

    # field: (color, od_index, od_name, od_type, descriptor, byte_span)
    # TPDO1 mapping matches servo.py: 0x6064 (4 B) then 0x6041 (2 B).
    fields = [
        (orange, "0x6064:00", "Position actual", "INT32, 4 B",
         "6064 00 20", (0, 4)),
        (blue,   "0x6041:00", "Statusword",      "UINT16, 2 B",
         "6041 00 10", (4, 6)),
    ]

    fig, ax = fs.figure(width=10.4, height=6.2)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(-2.6, 8.3)
    ax.set_ylim(-2.0, 10.4)
    ax.set_title("From Object Dictionary to the wire:   "
                 "OD object  ->  PDO mapping  ->  8-byte CAN frame",
                 color=fs.INK_PRIMARY, fontsize=12.5, pad=12, loc="left")

    # band left labels
    ax.text(-2.5, 8.5, "Object\nDictionary", ha="left", va="center",
            fontsize=10, color=fs.INK_SECONDARY, fontweight="bold")
    ax.text(-2.5, 5.25, "TPDO1 mapping\n0x1A00", ha="left", va="center",
            fontsize=10, color=fs.INK_SECONDARY, fontweight="bold")
    ax.text(-2.5, 1.65, "CAN frame\n(PDO payload)", ha="left", va="center",
            fontsize=10, color=fs.INK_SECONDARY, fontweight="bold")

    od_w = 2.45
    od_y, od_h = 7.55, 1.95
    mp_w = 2.45
    mp_y, mp_h = 4.45, 1.55
    fr_y, fr_h = 1.0, 1.35

    # ---- frame band: 8 byte cells ----
    for k in range(8):
        # find owning field
        owner = None
        for f in fields:
            if f[5][0] <= k < f[5][1]:
                owner = f
                break
        color = owner[0] if owner else gray
        rbox(ax, k, fr_y, 0.94, fr_h, tint(color, 0.80), color,
             lw=1.2, radius=0.08)
        ax.text(k + 0.47, fr_y + fr_h / 2, str(k), ha="center", va="center",
                fontsize=10, color=fs.INK_PRIMARY, zorder=3)
    ax.text(-0.05, fr_y + fr_h + 0.12, "byte #", ha="right", va="bottom",
            fontsize=8, color=fs.INK_MUTED)
    # free bytes 6-7 label (above the cells, clear of the field brackets below)
    ax.text(7.0, fr_y + fr_h + 0.12, "free / unused", ha="center",
            va="bottom", fontsize=8, color=gray, style="italic")

    for color, idx, name, typ, desc, (b0, b1) in fields:
        cx = (b0 + b1) / 2.0  # frame span center == OD/mapping box center

        # OD box
        rbox(ax, cx - od_w / 2, od_y, od_w, od_h, tint(color, 0.86), color)
        ax.text(cx, od_y + od_h - 0.42, idx, ha="center", va="center",
                fontsize=9, color=color, fontweight="bold")
        ax.text(cx, od_y + od_h / 2 - 0.05, name, ha="center", va="center",
                fontsize=9.5, color=fs.INK_PRIMARY)
        ax.text(cx, od_y + 0.34, typ, ha="center", va="center",
                fontsize=8.5, color=fs.INK_SECONDARY)

        # mapping box
        rbox(ax, cx - mp_w / 2, mp_y, mp_w, mp_h, tint(color, 0.86), color)
        sub = fields.index((color, idx, name, typ, desc, (b0, b1))) + 1
        ax.text(cx, mp_y + mp_h - 0.36, f"0x1A00:0{sub}", ha="center",
                va="center", fontsize=8.5, color=color, fontweight="bold")
        ax.text(cx, mp_y + 0.42, "0x " + desc, ha="center", va="center",
                fontsize=10, color=fs.INK_PRIMARY, family="monospace")

        # arrows OD -> mapping -> frame span
        ax.add_patch(FancyArrowPatch(
            (cx, od_y - 0.05), (cx, mp_y + mp_h + 0.05),
            arrowstyle="-|>", mutation_scale=13, color=color, lw=1.6,
            zorder=4))
        ax.add_patch(FancyArrowPatch(
            (cx, mp_y - 0.05), (cx, fr_y + fr_h + 0.05),
            arrowstyle="-|>", mutation_scale=13, color=color, lw=1.6,
            zorder=4))

        # field bracket + label under the frame span
        xl, xr = b0 + 0.06, b1 - 0.06
        yb = fr_y - 0.28
        ax.plot([xl, xl, xr, xr], [yb + 0.12, yb, yb, yb + 0.12],
                color=color, lw=1.3, zorder=2)
        span = f"byte {b0}" if b1 - b0 == 1 else f"bytes {b0}-{b1 - 1}"
        ax.text((xl + xr) / 2, yb - 0.35, f"{name}  ({span})", ha="center",
                va="center", fontsize=8.5, color=color, fontweight="bold")

    # decode legend for the descriptor + endianness note (bottom, clear of arrows)
    ax.text(-2.5, -1.2,
            "descriptor 0xIIIISSLL  =  index(16b) | subindex(8b) | "
            "length-in-bits(8b)",
            ha="left", va="center", fontsize=8.5, color=fs.INK_SECONDARY)
    ax.text(-2.5, -1.75,
            "objects are packed in mapping order; multi-byte values are "
            "little-endian (lowest byte first)",
            ha="left", va="center", fontsize=8.5, color=fs.INK_SECONDARY)

    # 出力先は生成物なのでリポジトリに入っていない。clone 直後でも書けるように作る。
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=140, facecolor=fs.SURFACE, bbox_inches="tight")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
