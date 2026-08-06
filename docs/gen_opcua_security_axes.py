"""Figure: OPC UA security is three independent axes.

  1. MessageSecurityMode  -- WHAT protection (None / Sign / SignAndEncrypt)
  2. SecurityPolicy        -- WHICH algorithms (Basic256Sha256 ...)
  3. UserIdentityToken     -- WHO the user is (Anonymous / UserName / X509)

Axes 1 and 2 secure the communication channel (application authentication);
axis 3 authenticates the user. The two groups are boxed and colored apart.
All in-figure text is English (matplotlib default font lacks JP glyphs).
"""
import os
import sys

import matplotlib.patches as mpatches

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import figstyle as fs

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figures", "opcua_security_axes.png")


def tint(hex_color: str, f: float) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    r = int(r + (255 - r) * f)
    g = int(g + (255 - g) * f)
    b = int(b + (255 - b) * f)
    return f"#{r:02x}{g:02x}{b:02x}"


def rbox(ax, x, y, w, h, fc, ec, lw=1.3, radius=1.2, z=2):
    ax.add_patch(mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z))


def chip_row(ax, chips, y, color, x0=23.0, h=7.6, fontsize=8.6):
    """chips: list of (label, highlight_bool). Draws left to right."""
    char_w, pad, gap, min_w = 0.92, 2.8, 1.7, 9.0
    x = x0
    for label, hi in chips:
        w = max(min_w, len(label) * char_w + pad)
        if hi:
            fc, lw, tc, fw = tint(color, 0.66), 2.0, fs.INK_PRIMARY, "bold"
        else:
            fc, lw, tc, fw = "white", 1.2, fs.INK_SECONDARY, "normal"
        rbox(ax, x, y, w, h, fc, color, lw=lw, radius=1.4, z=3)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
                fontsize=fontsize, color=tc, fontweight=fw, zorder=4)
        x += w + gap
    return x


def main():
    blue, green = fs.SERIES[0], fs.SERIES[2]

    fig, ax = fs.figure(width=10.6, height=5.9)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 97)
    ax.set_title("OPC UA security: three independent axes "
                 "(pick one option from each)",
                 color=fs.INK_PRIMARY, fontsize=13, pad=12, loc="left")

    # ---- application-authentication panel (axes 1 and 2) ----
    rbox(ax, 21, 45, 78, 41, tint(blue, 0.93), blue, lw=1.6, radius=1.6, z=1)
    ax.text(60, 83.0, "Application authentication  -  secures the "
            "communication channel", ha="center", va="center",
            fontsize=9.5, color=blue, fontweight="bold")

    ax.text(23, 78.0, "1.  MessageSecurityMode", ha="left", va="center",
            fontsize=10.5, color=fs.INK_PRIMARY, fontweight="bold")
    ax.text(23, 74.3, "WHAT protection is applied to each message",
            ha="left", va="center", fontsize=8.6, color=fs.INK_SECONDARY,
            style="italic")
    chip_row(ax, [("None", False), ("Sign", False),
                  ("SignAndEncrypt", True)], 64.0, blue)

    ax.text(23, 60.3, "2.  SecurityPolicy", ha="left", va="center",
            fontsize=10.5, color=fs.INK_PRIMARY, fontweight="bold")
    ax.text(23, 56.5, "WHICH cryptographic algorithm suite is used",
            ha="left", va="center", fontsize=8.6, color=fs.INK_SECONDARY,
            style="italic")
    chip_row(ax, [("None", False), ("Basic256Sha256", True),
                  ("Aes128Sha256RsaOaep", False),
                  ("Aes256Sha256RsaPss", False)], 47.5, blue)

    # ---- user-authentication panel (axis 3) ----
    rbox(ax, 21, 8, 78, 29, tint(green, 0.93), green, lw=1.6, radius=1.6, z=1)
    ax.text(60, 34.0, "User authentication  -  who is the user behind "
            "the session", ha="center", va="center",
            fontsize=9.5, color=green, fontweight="bold")

    ax.text(23, 28.4, "3.  UserIdentityToken", ha="left", va="center",
            fontsize=10.5, color=fs.INK_PRIMARY, fontweight="bold")
    ax.text(23, 24.6, "WHO the user is",
            ha="left", va="center", fontsize=8.6, color=fs.INK_SECONDARY,
            style="italic")
    chip_row(ax, [("Anonymous", False), ("UserName", True),
                  ("X509", False), ("IssuedToken", False)], 13.5, green)

    # ---- left group labels ----
    ax.text(10.5, 66, "Application\nlayer", ha="center", va="center",
            fontsize=11, color=blue, fontweight="bold")
    ax.text(10.5, 61, "(the channel)", ha="center", va="center",
            fontsize=8.5, color=fs.INK_SECONDARY)
    ax.text(10.5, 24.5, "User\nlayer", ha="center", va="center",
            fontsize=11, color=green, fontweight="bold")
    ax.text(10.5, 19.5, "(the person)", ha="center", va="center",
            fontsize=8.5, color=fs.INK_SECONDARY)

    # ---- bottom caption ----
    ax.text(0, 2.6,
            "The three axes are chosen independently.  Highlighted chips = "
            "one example session (SignAndEncrypt + Basic256Sha256 + UserName).",
            ha="left", va="center", fontsize=8.8, color=fs.INK_SECONDARY)

    # 出力先は生成物なのでリポジトリに入っていない。clone 直後でも書けるように作る。
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=140, facecolor=fs.SURFACE, bbox_inches="tight")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
