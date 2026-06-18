import cairo
import math
from config import ICON_DIR, ICON_PATH


def _base_clock(ctx, cx, cy, r):
    """Draw a clock face at (cx, cy) with radius r onto an existing Cairo context."""
    ctx.set_source_rgba(1, 1, 1, 0.95)
    ctx.set_line_width(1.6)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.stroke()

    ctx.move_to(cx, cy)
    ctx.line_to(cx, cy - r + 1.5)
    ctx.stroke()

    ctx.move_to(cx, cy)
    ctx.line_to(cx + r - 1.5, cy)
    ctx.stroke()

    ctx.set_line_width(1.3)
    ctx.move_to(cx - r + 1, cy - r + 1)
    ctx.line_to(cx - r - 1, cy - r - 1)
    ctx.stroke()
    ctx.move_to(cx + r - 1, cy - r + 1)
    ctx.line_to(cx + r + 1, cy - r - 1)
    ctx.stroke()


def create_tray_icon():
    """Normal clock icon (white)."""
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    size = 22
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surface)
    ctx.set_operator(cairo.OPERATOR_CLEAR)
    ctx.paint()
    ctx.set_operator(cairo.OPERATOR_OVER)
    _base_clock(ctx, 11, 13, 7)
    surface.write_to_png(ICON_PATH)


def create_attention_icon():
    """Clock icon with a red badge — shown when a reminder is firing."""
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    size = 22
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surface)
    ctx.set_operator(cairo.OPERATOR_CLEAR)
    ctx.paint()
    ctx.set_operator(cairo.OPERATOR_OVER)

    # Slightly offset clock to leave room for badge
    _base_clock(ctx, 10, 13, 6.5)

    # Red circle badge top-right
    ctx.set_source_rgba(0.95, 0.2, 0.2, 1.0)
    ctx.arc(18, 4, 3.5, 0, 2 * math.pi)
    ctx.fill()

    # Exclamation mark inside badge
    ctx.set_source_rgba(1, 1, 1, 1)
    ctx.set_line_width(1.3)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(18, 2.2)
    ctx.line_to(18, 5.0)
    ctx.stroke()
    ctx.arc(18, 6.5, 0.55, 0, 2 * math.pi)
    ctx.fill()

    attn_path = str(ICON_DIR / "remainders-attention.png")
    surface.write_to_png(attn_path)
