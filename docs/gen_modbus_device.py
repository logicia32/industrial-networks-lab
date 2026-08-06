"""Figure: modbus_device.png  [machine sketch]
A DIN-rail Modbus field device (temperature controller / VFD look) wired to a PC.
Shows the reader the physical thing on the far end of the wire.
"""
import os
import figkit as k
from matplotlib.patches import Polygon

OUT = os.path.join(os.path.dirname(__file__), "figures", "modbus_device.png")

fig, ax = k.new_diagram(7.4, 4.4, (0, 12), (0, 7.1), equal=True)
LCD = "#7fd0a8"
BODY = "#e9ece9"

k.title(ax, 0.2, 6.85, "What sits on the other end of the wire")

# --- DIN rail behind the device ---
k.box(ax, 0.6, 5.75, 4.8, 0.32, "", fc=k.TINT_GREY, ec=k.AXIS, lw=1.0,
      rounded=False)
k.text(ax, 5.55, 5.9, "DIN rail", ha="left", color=k.MUTED, fontsize=8.5,
       style="italic")

# --- device body ---
k.box(ax, 1.0, 1.35, 4.0, 4.3, "", fc=BODY, ec=k.INK, lw=1.5, rounding=0.1)
# display
k.box(ax, 1.35, 4.15, 3.3, 1.15, "", fc=k.DARK_PANEL, ec=k.INK, lw=1.0,
      rounding=0.06)
k.text(ax, 3.0, 4.95, "PV   25.4", color=LCD, fontsize=11, weight="bold")
k.text(ax, 3.0, 4.42, "SV   26.0", color="#c9d4e0", fontsize=8.5)
# buttons
for i, bx in enumerate([1.55, 2.35, 3.15, 3.95]):
    k.box(ax, bx, 3.35, 0.55, 0.45, "", fc="white", ec=k.AXIS, lw=1.0,
          rounding=0.08)
# terminal block
for i in range(8):
    tx = 1.3 + i * 0.44
    k.box(ax, tx, 1.55, 0.34, 0.34, "", fc=k.SURFACE, ec=k.AXIS, lw=0.9,
          rounded=False)
k.text(ax, 3.0, 1.98, "I/O terminals", color=k.INK2, fontsize=8)

# --- ports on the right edge ---
k.box(ax, 4.95, 3.55, 0.72, 0.6, "485", fc="white", ec=k.SERIES[1], tc=k.INK,
      fontsize=8.5, weight="bold", rounding=0.06)
k.box(ax, 4.95, 2.55, 0.72, 0.6, "ETH", fc="white", ec=k.SERIES[2], tc=k.INK,
      fontsize=8.5, weight="bold", rounding=0.06)

# device caption
k.text(ax, 3.0, 0.9, "Field device — temperature controller / VFD",
       color=k.INK, fontsize=9.5, weight="bold")

# --- PC / HMI on the right ---
# screen
k.box(ax, 8.35, 3.05, 3.0, 1.7, "", fc="white", ec=k.INK, lw=1.5, rounding=0.06)
k.box(ax, 8.6, 3.3, 2.5, 1.2, "", fc=k.DARK_PANEL, ec=k.INK, lw=0.8,
      rounding=0.04)
k.text(ax, 9.85, 3.9, "Modbus\nmaster", color="#c9d4e0", fontsize=8.5,
       weight="bold")
# base (trapezoid)
ax.add_patch(Polygon([(8.0, 3.0), (11.7, 3.0), (11.35, 2.5), (8.35, 2.5)],
                    closed=True, facecolor=BODY, edgecolor=k.INK, lw=1.4,
                    zorder=2))
k.text(ax, 9.85, 2.1, "PC / HMI  (Modbus master)", color=k.INK, fontsize=9.5,
       weight="bold")

# --- wiring (attach to laptop body, keep labels clear of it) ---
k.arrow(ax, (5.72, 3.85), (8.05, 3.75), color=k.SERIES[1], lw=1.8, style="-")
k.arrow(ax, (5.72, 2.85), (8.05, 3.15), color=k.SERIES[2], lw=1.8, style="-")
k.text(ax, 6.85, 4.15, "Modbus RTU  (RS-485)", color=k.SERIES[1], fontsize=8.5,
       weight="bold")
k.text(ax, 6.85, 2.55, "Modbus TCP  (Ethernet)", color=k.SERIES[2],
       fontsize=8.5, weight="bold")

k.save(fig, OUT)
print("wrote", OUT)
