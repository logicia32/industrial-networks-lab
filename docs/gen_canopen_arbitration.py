"""Figure: CAN non-destructive bitwise arbitration.

Three nodes start transmitting at the same time. On the wired-AND bus a
dominant bit (0) overrides a recessive bit (1). A node that transmits a
recessive bit but reads back a dominant bit has lost, and stops driving
the bus; the winner's frame is never disturbed.
All in-figure text is English (matplotlib default font lacks JP glyphs).
"""
import os
import sys

from matplotlib.patches import Rectangle

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import figstyle as fs

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figures", "canopen_arbitration.png")

ALERT = "#d64545"
N = 8  # bit periods shown

# dominant = 0 (low), recessive = 1 (high). MSB first.
BUS = [0, 0, 0, 0, 1, 0, 1, 1]
A = [0, 0, 0, 0, 1, 0, 1, 1]           # winner, full frame
B_OWN = [0, 0, 1]                       # loses at bit 3 (index 2)
C_OWN = [0, 1]                          # loses at bit 2 (index 1)


def merged(own, loss_idx):
    """Node drives its own bits up to the losing bit, then only follows
    the bus level as a receiver."""
    return list(own[:loss_idx + 1]) + BUS[loss_idx + 1:]


def wave_pts(bits, yb, h):
    xs, ys = [], []
    for k, b in enumerate(bits):
        lvl = yb + (h if b == 1 else 0)
        xs += [k, k + 1]
        ys += [lvl, lvl]
    return xs, ys


def draw_wave(ax, bits, yb, h, color, solid_until, lw=2.2):
    xs, ys = wave_pts(bits[:solid_until + 1], yb, h)
    ax.plot(xs, ys, color=color, lw=lw, solid_capstyle="round", zorder=4)
    if solid_until < len(bits) - 1:
        s = solid_until + 1
        xs2, ys2 = wave_pts(bits[s:], yb, h)
        xs2 = [x + s for x in xs2]
        last = yb + (h if bits[solid_until] == 1 else 0)
        first = yb + (h if bits[s] == 1 else 0)
        ax.plot([s, s], [last, first], color=color, lw=1.0, alpha=0.30,
                linestyle=(0, (3, 3)), zorder=3)
        ax.plot(xs2, ys2, color=color, lw=1.4, alpha=0.30,
                linestyle=(0, (3, 3)), zorder=3)


def main():
    fig, ax = fs.figure(width=10.2, height=6.0)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(-3.4, N + 0.5)
    ax.set_ylim(-1.0, 13.6)
    ax.set_title("CAN non-destructive arbitration   "
                 "(dominant 0 overrides recessive 1 on the wired-AND bus)",
                 color=fs.INK_PRIMARY, fontsize=12.5, pad=12, loc="left")

    blue, orange, green = fs.SERIES[0], fs.SERIES[1], fs.SERIES[2]
    h = 1.15

    rows = [
        ("Node A", "wins", A, len(A) - 1, blue, 10.0),
        ("Node B", "loses at bit 3", merged(B_OWN, 2), 2, orange, 7.6),
        ("Node C", "loses at bit 2", merged(C_OWN, 1), 1, green, 5.2),
        ("CAN bus", "wired-AND result", BUS, len(BUS) - 1, fs.INK_PRIMARY, 1.9),
    ]
    top_guide = 12.35

    # bit-period guide lines + top bit numbers
    for k in range(N + 1):
        ax.plot([k, k], [1.2, top_guide], color=fs.GRID, lw=0.8, zorder=0)
    for k in range(N):
        ax.text(k + 0.5, 12.75, str(k + 1), ha="center", va="center",
                fontsize=8.5, color=fs.INK_MUTED)
    ax.text(-3.3, 12.75, "bit #", ha="left", va="center", fontsize=8.5,
            color=fs.INK_MUTED)

    # shade the arbitration-decided region (bits 1..3) vs the winner frame
    ax.add_patch(Rectangle((0, 1.2), 3, top_guide - 1.2, facecolor="#efe9df",
                           edgecolor="none", alpha=0.55, zorder=0))
    ax.text(1.5, 12.1, "arbitration", ha="center", va="center",
            fontsize=9, color=fs.INK_SECONDARY, style="italic")
    ax.text(5.5, 12.1, "winner's frame continues (intact)", ha="center",
            va="center", fontsize=9, color=fs.INK_SECONDARY, style="italic")

    # faint connectors from each loss point down to the bus column
    for bit_idx, yb in ((1, 5.2), (2, 7.6)):
        xc = bit_idx + 0.5
        ax.plot([xc, xc], [1.9 + h, yb + h], color=fs.AXIS, lw=0.9,
                linestyle=(0, (1, 2)), zorder=1)

    for name, role, bits, solid, color, yb in rows:
        lw = 2.6 if name == "CAN bus" else 2.2
        draw_wave(ax, bits, yb, h, color, solid, lw=lw)
        ax.plot([0, N], [yb, yb], color=fs.GRID, lw=0.7, zorder=1)
        ax.plot([0, N], [yb + h, yb + h], color=fs.GRID, lw=0.7, zorder=1)
        ax.text(-3.3, yb + h / 2 + 0.30, name, ha="left", va="center",
                fontsize=10.5, color=color, fontweight="bold")
        ax.text(-3.3, yb + h / 2 - 0.42, role, ha="left", va="center",
                fontsize=8.5, color=fs.INK_SECONDARY)
        ax.text(N + 0.18, yb + h, "1", ha="left", va="center", fontsize=8,
                color=fs.INK_MUTED)
        ax.text(N + 0.18, yb, "0", ha="left", va="center", fontsize=8,
                color=fs.INK_MUTED)

    # loss markers: node drove recessive (high) but the bus was dominant (low)
    for bit_idx, yb in ((1, 5.2), (2, 7.6)):
        xc = bit_idx + 0.5
        yhi = yb + h
        ax.scatter([xc], [yhi], s=95, facecolor="white", edgecolor=ALERT,
                   linewidth=1.8, zorder=6)
        ax.plot([xc], [yhi], marker="x", color=ALERT, markersize=7,
                markeredgewidth=2.0, zorder=7)

    ax.text(-3.3, 0.1,
            "1 = recessive (bus high)      0 = dominant (bus low)",
            ha="left", va="center", fontsize=8.5, color=fs.INK_SECONDARY)
    ax.text(-3.3, -0.75,
            "x = node drove 1 but read back 0  ->  lost, stops driving",
            ha="left", va="center", fontsize=8.5, color=ALERT)

    # 出力先は生成物なのでリポジトリに入っていない。clone 直後でも書けるように作る。
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=140, facecolor=fs.SURFACE, bbox_inches="tight")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
