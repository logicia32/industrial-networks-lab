"""Figure: modbus_addr_map.png
Three ways to name the same Modbus holding register cell, and the -1 shift.
"""
import os
import figkit as k

OUT = os.path.join(os.path.dirname(__file__), "figures", "modbus_addr_map.png")

fig, ax = k.new_diagram(7.4, 3.9, (0, 12), (0, 6.6))

k.title(ax, 0.2, 6.25, "One holding register, three names")

# column centres
cx = [2.2, 6.0, 9.8]
headers = [
    ("Documentation\n(Modicon)", k.TINT_BLUE, k.SERIES[0]),
    ("Data model\n(register # in table)", k.TINT_ORANGE, k.SERIES[1]),
    ("On the wire\n(PDU address)", k.TINT_GREEN, k.SERIES[2]),
]
for x, (lab, fc, ec) in zip(cx, headers):
    k.box(ax, x - 1.65, 4.9, 3.3, 0.95, lab, fc=fc, ec=ec, tc=k.INK,
          fontsize=9.5)

# main example row
rowy = 3.15
vals = ["40001", "#1", "0x0000"]
fills = ["white", "white", "white"]
edges = [k.SERIES[0], k.SERIES[1], k.SERIES[2]]
for x, v, ec in zip(cx, vals, edges):
    k.box(ax, x - 1.0, rowy, 2.0, 0.95, v, fc="white", ec=ec, tc=k.INK,
          fontsize=13, weight="bold")

k.arrow(ax, (3.2, rowy + 0.47), (5.0, rowy + 0.47), color=k.MUTED, lw=1.6)
# 矢印の上に置く。下げすぎると右隣の枠の角に乗る
k.text(ax, 4.05, rowy + 1.20, "drop 4xxxx prefix", fontsize=8, color=k.INK2)
k.arrow(ax, (7.0, rowy + 0.47), (8.8, rowy + 0.47), color=k.SERIES[1], lw=2.0)
k.text(ax, 7.9, rowy + 1.15, "− 1", fontsize=12, color=k.SERIES[1],
       weight="bold")

# secondary example row (fainter)
row2 = 1.75
vals2 = ["40002", "#2", "0x0001"]
for x, v, ec in zip(cx, vals2, edges):
    k.box(ax, x - 1.0, row2, 2.0, 0.9, v, fc=k.SURFACE, ec=k.AXIS, tc=k.INK2,
          fontsize=12, weight="medium")
k.arrow(ax, (3.2, row2 + 0.45), (5.0, row2 + 0.45), color=k.GRID, lw=1.4)
k.arrow(ax, (7.0, row2 + 0.45), (8.8, row2 + 0.45), color=k.GRID, lw=1.4)

# vendor-specific note
k.box(ax, 0.3, 0.35, 11.4, 0.9,
      "Zero-based vs one-based mapping is vendor specific  —  confirm it in the device manual",
      fc=k.TINT_GREY, ec=k.AXIS, tc=k.INK2, fontsize=8.5, rounding=0.1)

k.save(fig, OUT)
print("wrote", OUT)
