"""Figure: modbus_frame_overlay.png
Same PDU, two wrappers: RTU = [addr][FC][data][CRC], TCP = [MBAP 7B][FC][data].
The centred [FC][data] = PDU is highlighted; TCP has no CRC.
"""
import os
import figkit as k

OUT = os.path.join(os.path.dirname(__file__), "figures", "modbus_frame_overlay.png")

fig, ax = k.new_diagram(7.6, 4.0, (0, 12), (0, 7.2))

k.title(ax, 0.2, 6.95, "Same PDU, two wrappers")

# shared column geometry (FC + data span both rows so the PDU lines up).
# small gaps between boxes leave room for the PDU highlight outline.
top_y, bot_y, bh = 4.4, 1.8, 1.15
FC_X, FC_W = 5.0, 1.25          # FC:   5.00 .. 6.25
DAT_X, DAT_W = 6.35, 2.95       # Data: 6.35 .. 9.30
ADDR_X, ADDR_W = 3.3, 1.6       # addr: 3.30 .. 4.90（"Slave addr" の幅に余白を持たせる）
CRC_X, CRC_W = 9.4, 1.5         # CRC:  9.40 .. 10.90
MBAP_X, MBAP_W = 2.1, 2.8       # MBAP: 2.10 .. 4.90（左の "TCP (Ethernet)" を避ける）

# --- highlighted PDU band (sits in the gaps, behind the boxes) ---
k.box(ax, 4.93, bot_y - 0.35, 4.44, (top_y + bh) - (bot_y - 0.35) + 0.35,
      "", fc="none", ec=k.SERIES[0], lw=1.8, rounding=0.15, zorder=1)
k.text(ax, (FC_X + DAT_X + DAT_W) / 2.0, 6.15,
       "PDU — identical payload", color=k.SERIES[0], fontsize=10, weight="bold")

# --- RTU (top) ---
k.text(ax, 0.3, top_y + bh / 2.0, "RTU\n(RS-485)", ha="left", color=k.INK,
       fontsize=10, weight="bold")
k.box(ax, ADDR_X, top_y, ADDR_W, bh, "Slave addr\n1 B", fc=k.TINT_GREY,
      ec=k.AXIS, tc=k.INK2, fontsize=9)
k.box(ax, FC_X, top_y, FC_W, bh, "FC\n1 B", fc=k.TINT_BLUE, ec=k.SERIES[0],
      tc=k.INK, fontsize=9.5, weight="bold")
k.box(ax, DAT_X, top_y, DAT_W, bh, "Data\nN bytes", fc=k.TINT_BLUE,
      ec=k.SERIES[0], tc=k.INK, fontsize=9.5, weight="bold")
k.box(ax, CRC_X, top_y, CRC_W, bh, "CRC\n2 B", fc=k.TINT_ORANGE,
      ec=k.SERIES[1], tc=k.INK, fontsize=9)

# --- TCP (bottom) ---
k.text(ax, 0.3, bot_y + bh / 2.0, "TCP\n(Ethernet)", ha="left", color=k.INK,
       fontsize=10, weight="bold")
k.box(ax, MBAP_X, bot_y, MBAP_W, bh, "MBAP header\n7 B", fc=k.TINT_GREEN,
      ec=k.SERIES[2], tc=k.INK, fontsize=9.5)
k.box(ax, FC_X, bot_y, FC_W, bh, "FC\n1 B", fc=k.TINT_BLUE, ec=k.SERIES[0],
      tc=k.INK, fontsize=9.5, weight="bold")
k.box(ax, DAT_X, bot_y, DAT_W, bh, "Data\nN bytes", fc=k.TINT_BLUE,
      ec=k.SERIES[0], tc=k.INK, fontsize=9.5, weight="bold")

# "no CRC in TCP" callout where the RTU CRC would sit
k.box(ax, CRC_X, bot_y, CRC_W, bh, "", fc=k.SURFACE, ec=k.AXIS, lw=1.0,
      rounding=0.1)
k.text(ax, CRC_X + CRC_W / 2.0, bot_y + bh / 2.0, "no CRC", color=k.SERIES[1],
       fontsize=9.5, weight="bold", style="italic")
k.arrow(ax, (CRC_X + CRC_W / 2.0, top_y - 0.05),
        (CRC_X + CRC_W / 2.0, bot_y + bh + 0.05),
        color=k.SERIES[1], lw=1.5, style="-|>")

# MBAP contents footnote
k.text(ax, MBAP_X + MBAP_W / 2.0, bot_y - 0.55,
       "MBAP: transaction id, protocol id, length, unit id",
       color=k.INK2, fontsize=8, ha="center")

k.save(fig, OUT)
print("wrote", OUT)
