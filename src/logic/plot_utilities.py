import pandas as pd
import numpy as np
import re
from colorsys import rgb_to_hls, hls_to_rgb

_rgb_re = re.compile(r"^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*([\d.]+))?\s*\)$", re.IGNORECASE)

def _parse_color_any(c: str):
    c = c.strip()
    if c.startswith("#"):
        h = c[1:]
        if len(h) == 3:
            r, g, b = (int(h[i]*2, 16) for i in range(3))
        elif len(h) == 6:
            r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        else:
            raise ValueError(f"Unsupported hex color length: {c}")
        return (r/255.0, g/255.0, b/255.0)
    m = _rgb_re.match(c)
    if m:
        r, g, b = (int(m.group(i)) for i in (1,2,3))
        return (r/255.0, g/255.0, b/255.0)
    raise ValueError(f"Color format not supported for adjustment: {c}")

def _to_hex(r: float, g: float, b: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(int(max(0,min(1,r))*255),
                                        int(max(0,min(1,g))*255),
                                        int(max(0,min(1,b))*255))

def adjust_color_any(color: str, *, lighten: float = 0.0, darken: float = 0.0) -> str:
    if lighten and darken:
        raise ValueError("Use either lighten or darken, not both.")
    r, g, b = _parse_color_any(color)
    h, l, s = rgb_to_hls(r, g, b)
    if lighten > 0:
        l = l + (1 - l) * lighten
    elif darken > 0:
        l = l * (1 - darken)
    r2, g2, b2 = hls_to_rgb(h, l, s)
    return _to_hex(r2, g2, b2)