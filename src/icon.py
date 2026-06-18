import cairo
import math
from config import ICON_DIR, ICON_PATH


def create_tray_icon():
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    size = 22
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surface)

    ctx.set_operator(cairo.OPERATOR_CLEAR)
    ctx.paint()
    ctx.set_operator(cairo.OPERATOR_OVER)
    ctx.set_source_rgba(1, 1, 1, 0.95)
    ctx.set_line_width(1.6)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    ctx.arc(11, 13, 7, 0, 2 * math.pi)
    ctx.stroke()

    ctx.move_to(11, 13)
    ctx.line_to(11, 8)
    ctx.stroke()

    ctx.move_to(11, 13)
    ctx.line_to(15.5, 13)
    ctx.stroke()

    ctx.set_line_width(1.4)
    ctx.move_to(7.5, 7.5)
    ctx.line_to(5.5, 5.5)
    ctx.stroke()
    ctx.move_to(14.5, 7.5)
    ctx.line_to(16.5, 5.5)
    ctx.stroke()

    surface.write_to_png(ICON_PATH)
