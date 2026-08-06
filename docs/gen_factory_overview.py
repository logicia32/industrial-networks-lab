"""Figure: factory_overview.png  [series map]
Layered plant block diagram: Field level -> Fieldbus -> Gateway -> IT/Cloud,
with article tags (1 / 2-3 / 4-5) on the right.
"""
import os
import figkit as k

OUT = os.path.join(os.path.dirname(__file__), "figures", "factory_overview.png")

fig, ax = k.new_diagram(7.4, 4.7, (0, 12), (0, 10.4))

k.title(ax, 0.2, 10.05, "The plant, bottom to top — and where the series looks")

BAND_X, BAND_W = 1.85, 7.4
INNER_H = 0.9

layers = [
    # (lower_y, layer_name, [(center_x, width, label, edge_color)])
    (0.8, "Field\nlevel", [
        (3.1, 2.1, "Sensors", k.AXIS),
        (5.55, 2.1, "Servo drive", k.SERIES[1]),
        (8.0, 2.3, "Temperature\ncontroller", k.SERIES[0]),
    ]),
    (3.2, "Fieldbus", [
        (4.0, 2.6, "Modbus\n(RTU / TCP)", k.SERIES[0]),
        (7.0, 2.6, "CANopen\n(CAN bus)", k.SERIES[1]),
    ]),
    (5.6, "Gateway", [
        (5.55, 5.6, "Gateway  —  OPC UA server (address space)", k.SERIES[2]),
    ]),
    (8.0, "IT / Cloud", [
        (4.0, 2.6, "OPC UA client", k.SERIES[2]),
        (7.0, 2.6, "SCADA / historian", k.SERIES[3]),
    ]),
]

for lower_y, name, boxes in layers:
    # container band
    k.box(ax, BAND_X, lower_y, BAND_W, 1.5, "", fc=k.TINT_GREY, ec=k.AXIS,
          lw=1.0, rounding=0.08, zorder=1)
    k.text(ax, 0.2, lower_y + 0.75, name, ha="left", color=k.INK, fontsize=9.5,
           weight="bold")
    for cx, w, label, ec in boxes:
        k.box(ax, cx - w / 2.0, lower_y + 0.3, w, INNER_H, label, fc="white",
              ec=ec, tc=k.INK, fontsize=9, weight="medium", zorder=2)

# bidirectional flow arrows between layers (read up / command down)
for x in (4.0, 7.0):
    k.arrow(ax, (x, 2.32), (x, 3.18), color=k.MUTED, lw=1.5, style="<->")
    k.arrow(ax, (x, 4.72), (x, 5.58), color=k.MUTED, lw=1.5, style="<->")
    k.arrow(ax, (x, 7.12), (x, 7.98), color=k.MUTED, lw=1.5, style="<->")

# --- article rail on the right ---
pills = [
    (1.15, 1.5, k.TINT_BLUE, k.SERIES[0], "Article 1\nModbus"),
    (3.35, 1.5, k.TINT_ORANGE, k.SERIES[1], "Articles 2-3\nCANopen / servo"),
    (5.7, 3.9, k.TINT_GREEN, k.SERIES[2], "Articles 4-5\nOPC UA / gateway"),
]
for py, ph, fc, ec, label in pills:
    k.box(ax, 9.7, py, 2.15, ph, label, fc=fc, ec=ec, tc=k.INK, fontsize=9,
          weight="bold", rounding=0.12)

k.save(fig, OUT)
print("wrote", OUT)
