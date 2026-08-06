"""Figure: servo_axis.png  [machine sketch]
A servo axis under CiA 402: master -> drive (CANopen node) -> motor -> rotary load.
Controlword / Target position go down, Statusword comes up.
"""
import os
import figkit as k
from matplotlib.patches import FancyArrowPatch

OUT = os.path.join(os.path.dirname(__file__), "figures", "servo_axis.png")

fig, ax = k.new_diagram(7.4, 4.1, (0, 12), (0, 6.65), equal=True)

k.title(ax, 0.2, 6.35, "A servo axis under CiA 402")

# --- master and drive (left, stacked) ---
k.box(ax, 0.55, 4.95, 3.0, 1.0, "CANopen master\n(controller)", fc=k.TINT_GREY,
      ec=k.INK, tc=k.INK, fontsize=9)
k.box(ax, 0.55, 1.7, 3.0, 1.8, "Servo drive\nCANopen node\nCiA 402",
      fc=k.TINT_GREEN, ec=k.SERIES[2], tc=k.INK, fontsize=9.5, weight="bold")

# CANopen bus link between them
k.arrow(ax, (1.05, 3.55), (1.05, 4.9), color=k.SERIES[2], lw=2.2, style="<->")
k.text(ax, 0.72, 4.22, "CANopen", color=k.SERIES[2], fontsize=8, weight="bold",
       rotation=90)

# the three CiA 402 objects carried on the bus
sig = [
    (4.62, "down", "Controlword   0x6040"),
    (4.24, "down", "Target position   0x607A"),
    (3.86, "up", "Statusword   0x6041"),
]
for y, direction, label in sig:
    if direction == "down":
        k.arrow(ax, (1.6, y + 0.12), (1.6, y - 0.12), color=k.SERIES[1],
                lw=1.4, style="-|>", mutation_scale=9)
        col = k.SERIES[1]
    else:
        k.arrow(ax, (1.6, y - 0.12), (1.6, y + 0.12), color=k.SERIES[0],
                lw=1.4, style="-|>", mutation_scale=9)
        col = k.SERIES[0]
    k.text(ax, 1.85, y, label, ha="left", color=col, fontsize=8,
           weight="medium")

# --- motor ---
k.circle(ax, 5.5, 2.9, 0.95, fc="white", ec=k.INK, lw=1.6)
k.circle(ax, 5.5, 2.9, 0.28, fc=k.TINT_GREY, ec=k.INK, lw=1.2)
k.text(ax, 5.5, 1.55, "Servo motor", color=k.INK, fontsize=9.5, weight="bold")

# drive -> motor cable
k.arrow(ax, (3.55, 2.9), (4.5, 2.9), color=k.INK2, lw=1.7, style="-|>")
k.text(ax, 4.02, 3.25, "power +\nencoder", color=k.INK2, fontsize=7.5)

# shaft
ax.plot([6.45, 7.55], [2.9, 2.9], color=k.INK, lw=3.5, solid_capstyle="round",
        zorder=2)

# --- rotary table / load ---
k.ellipse(ax, 8.75, 2.7, 2.4, 1.0, fc=k.TINT_BLUE, ec=k.SERIES[0], lw=1.6)
k.box(ax, 8.4, 2.95, 0.7, 0.5, "", fc=k.TINT_ORANGE, ec=k.SERIES[1], lw=1.2,
      rounding=0.06)
k.text(ax, 8.75, 1.55, "Rotary table / load", color=k.INK, fontsize=9.5,
       weight="bold")
# rotation hint
ax.add_patch(FancyArrowPatch((8.0, 3.55), (9.5, 3.55),
             connectionstyle="arc3,rad=-0.45", arrowstyle="-|>",
             mutation_scale=11, lw=1.4, color=k.SERIES[0], zorder=4))

k.save(fig, OUT)
print("wrote", OUT)
