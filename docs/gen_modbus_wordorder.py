"""Figure: modbus_wordorder.png
One 32-bit value 0xAABBCCDD shown in four byte/word orders: ABCD, CDAB, BADC, DCBA.
Each byte keeps its colour so you can watch it move.
"""
import os
import figkit as k

OUT = os.path.join(os.path.dirname(__file__), "figures", "modbus_wordorder.png")

fig, ax = k.new_diagram(7.4, 4.0, (0, 12), (0, 7.4))

# per-byte colour (fill tint, edge)
CMAP = {
    "A": (k.TINT_BLUE, k.SERIES[0]),
    "B": (k.TINT_ORANGE, k.SERIES[1]),
    "C": (k.TINT_GREEN, k.SERIES[2]),
    "D": (k.TINT_YELLOW, k.SERIES[3]),
}
HEX = {"A": "0xAA", "B": "0xBB", "C": "0xCC", "D": "0xDD"}

k.title(ax, 0.2, 7.15, "One 32-bit value 0xAABBCCDD, four byte / word orders")

# legend
lx = 0.6
for letter in "ABCD":
    fc, ec = CMAP[letter]
    k.box(ax, lx, 6.25, 0.55, 0.55, letter, fc=fc, ec=ec, tc=k.INK,
          fontsize=11, weight="bold", rounding=0.08)
    k.text(ax, lx + 0.75, 6.52, HEX[letter], ha="left", color=k.INK2,
           fontsize=9)
    lx += 2.1
k.text(ax, 9.3, 6.52, "A = most significant byte", ha="left", color=k.MUTED,
       fontsize=8.5, style="italic")

# byte column geometry
bw, bh = 1.45, 0.85
xs = [3.0, 4.5, 6.55, 8.05]          # b0, b1 | b2, b3  (gap between words)
cen = [x + bw / 2.0 for x in xs]

# word headers
k.text(ax, (cen[0] + cen[1]) / 2.0, 5.75, "word 0  (register N)",
       color=k.INK, fontsize=9, weight="bold")
k.text(ax, (cen[2] + cen[3]) / 2.0, 5.75, "word 1  (register N+1)",
       color=k.INK, fontsize=9, weight="bold")
ax.plot([xs[0], xs[1] + bw], [5.5, 5.5], color=k.AXIS, lw=1.0)
ax.plot([xs[2], xs[3] + bw], [5.5, 5.5], color=k.AXIS, lw=1.0)

rows = [
    ("ABCD", "big-endian"),
    ("CDAB", "word-swapped"),
    ("BADC", "byte-swapped"),
    ("DCBA", "little-endian"),
]
ys = [4.5, 3.4, 2.3, 1.2]

for (order, name), y in zip(rows, ys):
    k.text(ax, 2.4, y + bh / 2.0, order, ha="right", color=k.INK, fontsize=12,
           weight="bold")
    for i, letter in enumerate(order):
        fc, ec = CMAP[letter]
        k.box(ax, xs[i], y, bw, bh, letter, fc=fc, ec=ec, tc=k.INK,
              fontsize=15, weight="bold", rounding=0.08)
    k.text(ax, 9.9, y + bh / 2.0, name, ha="left", color=k.INK2, fontsize=9.5)

k.save(fig, OUT)
print("wrote", OUT)
