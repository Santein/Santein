"""A looping pixel-art view of a Mediterranean city on the sea, drawn strictly
in Santein's PaleAle palette (8 shades, lightest -> darkest).

Native resolution 160x100, nearest-neighbour upscaled. Output: animated GIF.
"""

import math
import os
import random
from PIL import Image

PAL_HEX = ["eaf9ff", "beebff", "79d7ff", "4fb8ff",
           "2d8cff", "1f5fd6", "163a8a", "0b183d"]
PAL = [int(h[i:i + 2], 16) for h in PAL_HEX for i in (0, 2, 4)]

W, H = 160, 100
SCALE = 5
NF = 32          # frames in the loop
WL = 58          # waterline row
LAND_R = 92      # where the town's headland meets the sea

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def bay(x, y):
    return BAYER[y & 3][x & 3] / 16.0


def hashf(x, y):
    n = (x * 73856093) ^ (y * 19349663)
    return ((n * 2654435761) % 65536) / 65536.0


class Canvas:
    def __init__(self):
        self.p = [[7] * W for _ in range(H)]

    def set(self, x, y, i):
        if 0 <= x < W and 0 <= y < H:
            self.p[y][x] = max(0, min(7, i))

    def get(self, x, y):
        if 0 <= x < W and 0 <= y < H:
            return self.p[y][x]
        return None

    def shade(self, x, y, v):
        """Ordered-dither a fractional palette position onto the canvas."""
        i = int(math.floor(v))
        if bay(x, y) < v - i:
            i += 1
        self.set(x, y, i)

    def rect(self, x0, y0, x1, y1, i):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, i)


# --------------------------------------------------------------------------
# terrain
# --------------------------------------------------------------------------

def terrain(x):
    """Top of the headland the town is built on: high left, into the sea right."""
    t = max(0.0, min(1.0, x / LAND_R))
    y = 33 + (WL - 33) * (t ** 1.6)
    y -= 2.0 * math.sin(x * 0.17) + 1.2 * math.sin(x * 0.06 + 1.0)
    return y


def volcano(x):
    """Vesuvius on the far horizon: two shoulders and a notched crater."""
    a = 1.0 - abs(x - 136) / 31.0
    if a <= 0:
        return None
    y = WL - 26 * (a ** 0.72)
    if abs(x - 136) <= 2:                   # the crater notch
        y += 2.0
    return y


# --------------------------------------------------------------------------
# town layout (fixed seed: identical in every frame)
# --------------------------------------------------------------------------

random.seed(1988)

BUILDINGS = []      # (x, w, top, base, wall, lit, roof, pitched)
WINDOWS = []        # (x, y, w, h, phase, shade)


def add_row(lift, wall, lit, roof, wmin, wmax, hmin, hmax, win_shade, xmax):
    x = -6
    while x < xmax:
        w = random.randint(wmin, wmax)
        base = terrain(x + w * 0.5) - lift
        h = random.randint(hmin, hmax)
        top = int(base - h)
        pitched = random.random() < 0.35
        BUILDINGS.append((x, w, top, int(base), wall, lit, roof, pitched))
        for wy in range(top + 3, int(base) - 1, 4):
            for wx in range(x + 2, x + w - 2, 4):
                if random.random() < 0.6:
                    WINDOWS.append((wx, wy, 2, 2, random.random(), win_shade))
        x += w + random.randint(0, 3)


# back to front: each row sits lower on the slope and reads darker
add_row(18, 4, 3, 5, 8, 13, 5, 7, 2, LAND_R - 38)
add_row(12, 4, 3, 5, 9, 14, 5, 8, 2, LAND_R - 30)
add_row(6, 5, 4, 6, 10, 16, 6, 9, 2, LAND_R - 22)
add_row(1, 6, 5, 7, 11, 18, 7, 10, 1, LAND_R - 12)

CHURCH_X = 34
CHURCH_BASE = int(terrain(CHURCH_X + 6)) - 13
TOWER_X = 54
TOWER_BASE = int(terrain(TOWER_X + 3)) - 4
TOWER_TOP = TOWER_BASE - 22


def draw_town(c):
    for (bx, bw, top, base, wall, lit, roof, pitched) in BUILDINGS:
        c.rect(bx, top, bx + bw - 1, base, wall)
        for y in range(top, base + 1):          # sunlit right-hand faces
            c.set(bx + bw - 1, y, lit)
            c.set(bx + bw - 2, y, lit)
        for y in range(top + 1, base + 1):      # shadowed left edge
            c.set(bx, y, min(7, wall + 1))
        if pitched:                             # low tiled roof
            for k in range(3):
                for x in range(bx + k, bx + bw - k):
                    c.set(x, top - k, roof if k else lit)
        else:                                   # flat roof with a parapet
            for x in range(bx, bx + bw):
                c.set(x, top, lit)
                c.set(x, top - 1, roof)

    # church: body, dome, cross
    c.rect(CHURCH_X, CHURCH_BASE - 11, CHURCH_X + 12, CHURCH_BASE, 6)
    for y in range(CHURCH_BASE - 11, CHURCH_BASE + 1):
        c.set(CHURCH_X + 12, y, 5)
        c.set(CHURCH_X + 11, y, 5)
    cx, cy, r = CHURCH_X + 6, CHURCH_BASE - 11, 6
    for y in range(cy - r, cy + 1):
        for x in range(cx - r, cx + r + 1):
            dx, dy = (x - cx) / r, (y - cy) / r
            if dx * dx + dy * dy <= 1.0:
                c.set(x, y, 5 if dx > 0.2 else 6)
    for y in range(cy - r - 3, cy - r):
        c.set(cx, y, 5)
    c.set(cx - 1, cy - r - 2, 5)
    c.set(cx + 1, cy - r - 2, 5)

    # campanile
    c.rect(TOWER_X, TOWER_TOP, TOWER_X + 6, TOWER_BASE, 6)
    for y in range(TOWER_TOP, TOWER_BASE + 1):
        c.set(TOWER_X + 6, y, 5)
        c.set(TOWER_X + 5, y, 5)
    c.rect(TOWER_X + 2, TOWER_TOP + 6, TOWER_X + 4, TOWER_TOP + 10, 7)
    for x in range(TOWER_X - 1, TOWER_X + 8):
        c.set(x, TOWER_TOP, 5)
        c.set(x, TOWER_TOP - 1, 6)
    for k in range(3):
        for x in range(TOWER_X + k, TOWER_X + 7 - k):
            c.set(x, TOWER_TOP - 2 - k, 6 if k else 5)


# --------------------------------------------------------------------------
# frame
# --------------------------------------------------------------------------

SUN_X, SUN_Y, SUN_R = 104, 33, 8

CLOUDS = [(10, 13, 30, 5, 0.9), (74, 8, 36, 4, 0.55),
          (126, 20, 22, 4, 1.3), (44, 24, 18, 3, 0.35)]

BOATS = [(92, 68, 0.9), (140, 78, -0.6), (110, 90, 1.4)]
GULLS = [(18, 18, 2.1), (48, 11, 1.5)]


def frame(f):
    ph = 2 * math.pi * f / NF
    c = Canvas()

    # --- sky: dithered gradient, deep at the zenith, pale at the horizon ---
    for y in range(0, WL):
        t = y / (WL - 1.0)
        v = 4.4 - 4.0 * (t ** 1.3)
        for x in range(W):
            c.shade(x, y, v)

    # --- sun, with a soft halo, sitting over the open water ---
    for y in range(max(0, SUN_Y - SUN_R - 9), min(WL, SUN_Y + SUN_R + 10)):
        for x in range(SUN_X - SUN_R - 11, SUN_X + SUN_R + 12):
            d = math.hypot(x - SUN_X, (y - SUN_Y) * 1.04)
            if d <= SUN_R:
                c.set(x, y, 0)
            elif d <= SUN_R + 2.0:
                c.set(x, y, 1)
            elif d <= SUN_R + 10:
                g = (d - SUN_R - 2.0) / 8.0
                if bay(x, y) > g:
                    cur = c.get(x, y)
                    if cur is not None:
                        c.set(x, y, min(cur, 2 if g < 0.5 else 3))

    # --- clouds drifting, wrapping around the sky ---
    for (cx0, cy, cw, chh, spd) in CLOUDS:
        cx = cx0 + spd * 4.0 * math.sin(ph + cx0 * 0.11)
        for x in range(int(cx), int(cx + cw)):
            u = max(0.0, min(1.0, (x - cx) / cw))
            hgt = chh * (math.sin(u * math.pi) ** 0.7)
            lump = 0.7 + 0.5 * math.sin(u * 11.0 + cx0)
            hgt *= lump
            for y in range(int(cy - hgt), int(cy + hgt * 0.4) + 1):
                if 0 <= y < WL:
                    c.set(x, y, 2 if y < cy - hgt * 0.35 else 3)

    # --- Vesuvius still smoking: a pale plume leaning off the crater ---
    for k in range(15):
        t = k / 14.0
        sy = (WL - 26) - 1 - k * 1.1 - (f % 8) * 0.32
        sx = 136 + t * 7 + 1.6 * math.sin(t * 4.0 + ph)
        rad = 1.1 + t * 1.9
        for dy in range(-int(rad), int(rad) + 1):
            for dx in range(-int(rad), int(rad) + 1):
                if dx * dx + dy * dy > rad * rad:
                    continue
                if bay(int(sx) + dx, int(sy) + dy) > 0.8 - t * 0.62:
                    continue
                yy = int(sy) + dy
                if 0 <= yy < WL:
                    c.set(int(sx) + dx, yy, 1 if t < 0.45 else 2)

    sky_only = [row[:] for row in c.p]      # remembered, to mask reflections

    # --- Vesuvius on the far horizon, hazy ---
    for x in range(W):
        vy = volcano(x)
        if vy is None:
            continue
        for y in range(int(vy), WL):
            lit = (x - 133) / 9.0 + (y - vy) * 0.010
            v = 4.5 - 1.4 * max(0.0, min(1.0, lit))
            if y > WL - 4:
                v += 1.0
            c.shade(x, y, v)

    # --- the headland the town stands on, cut into terraces ---
    for x in range(0, LAND_R + 1):
        ty = terrain(x)
        for y in range(int(ty), WL):
            depth = y - ty
            if y > WL - 5:
                c.set(x, y, 7)                    # rock at the waterline
            elif depth < 1.5:
                c.set(x, y, 5)                    # sunlit crest of the slope
            elif int(depth) % 6 == 2:
                c.set(x, y, 5)                    # terrace edge catching light
            else:
                c.set(x, y, 6)

    # cypresses dotted along the bare part of the slope
    for cxp in (64, 69, 73, 78, 82, 86, 89):
        gy = int(terrain(cxp))
        for k in range(9):
            wdt = 0 if k < 2 else (1 if k < 6 else 2)
            for dx in range(-wdt, wdt + 1):
                c.set(cxp + dx, gy - 9 + k, 7 if dx <= 0 else 6)

    draw_town(c)

    # --- lit windows, blinking on their own slow phases ---
    for (wx, wy, ww, wh, wph, shade) in WINDOWS:
        lit = 0.5 + 0.5 * math.sin(ph * 2 + wph * 12.0)
        if lit > 0.3:
            i = shade if lit > 0.72 else shade + 1
            for y in range(wy, wy + wh):
                for x in range(wx, wx + ww):
                    if y < WL - 1:
                        c.set(x, y, i)

    # --- the quay where the town meets the water ---
    for x in range(0, LAND_R + 1):
        c.set(x, WL - 1, 7)
        c.set(x, WL - 2, 6 if x % 7 else 7)

    # --- sea base: deep, with a gentle vertical gradient ---
    for y in range(WL, H):
        t = (y - WL) / (H - WL - 1.0)
        v = 6.35 - 0.8 * t
        for x in range(W):
            c.shade(x, y, v)

    # --- reflection of the skyline, wobbling ---
    for y in range(WL, min(H, WL + 16)):
        d = y - WL
        strength = 0.95 - d / 16.0
        wob = 1.7 * math.sin(d * 0.5 + ph) + 1.0 * math.sin(d * 0.23 - ph * 2)
        for x in range(W):
            if bay(x, y) > strength:
                continue
            sx, sy = int(round(x + wob)), 2 * WL - y - 1
            src = c.get(sx, sy)
            if src is None or not (0 <= sx < W and 0 <= sy < H):
                continue
            if src == sky_only[sy][sx]:          # sky does not reflect as an object
                continue
            c.set(x, y, min(7, src + 2))

    # --- the sun's road on the water: the brightest thing in the frame ---
    for y in range(WL, H):
        d = y - WL
        half = 2.5 + d * 0.5 + 1.6 * math.sin(d * 0.6 + ph)
        for x in range(int(SUN_X - half), int(SUN_X + half) + 1):
            if not (0 <= x < W):
                continue
            edge = 1.0 - abs(x - SUN_X) / max(1.0, half)
            glit = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(
                hashf(x, y) * 39.0 + ph * 3 - y * 0.4))
            k = (0.35 + 0.9 * edge) * glit * (1.0 - d / 46.0)
            if k > 0.70:
                c.set(x, y, 0)
            elif k > 0.52:
                c.set(x, y, 1)
            elif k > 0.34:
                c.set(x, y, 2)
            elif k > 0.20:
                c.set(x, y, 4)

    # --- scrolling wave dashes ---
    random.seed(7)
    for y in range(WL + 3, H, 3):
        d = y - WL
        for _ in range(3 + d // 6):
            base = random.random() * W
            ln = 2 + int(random.random() * (2 + d // 6))
            sway = (1.0 + d * 0.16) * math.sin(ph + base * 0.13)
            if math.sin(ph * 2 + base * 0.7 + d * 0.3) < -0.45:
                continue
            x0 = base + sway
            for x in range(int(x0), int(x0) + ln):
                cur = c.get(x, y)
                if cur is not None and cur >= 5:
                    c.set(x, y, cur - 2)

    # --- the harbour mole reaching out into the bay, with its lighthouse ---
    MOLE_Y, MOLE_END = WL + 9, 58
    for x in range(-2, MOLE_END + 1):
        c.set(x, MOLE_Y - 1, 4 if x % 9 else 5)   # sunlit top of the wall
        c.set(x, MOLE_Y, 7)
        c.set(x, MOLE_Y + 1, 7)
        c.set(x, MOLE_Y + 2, 7)
    for y in range(MOLE_Y - 10, MOLE_Y):        # the tower
        c.set(MOLE_END - 3, y, 7)
        c.set(MOLE_END - 2, y, 6)
        c.set(MOLE_END - 1, y, 4)
        c.set(MOLE_END, y, 3)
    beacon = math.sin(ph * 3) > 0.15
    for dx in range(-2, 2):
        c.set(MOLE_END + dx, MOLE_Y - 11, 0 if beacon else 4)
    if beacon:                                   # the light throwing out
        for k in (3, 4, 6):
            c.set(MOLE_END + k, MOLE_Y - 11, 2)
            c.set(MOLE_END - 4 - k, MOLE_Y - 11, 2)

    # --- little boats bobbing across the bay ---
    for (bx0, by, spd) in BOATS:
        bx = int(bx0 + spd * 3.5 * math.sin(ph + bx0 * 0.2))
        yy = by + int(round(math.sin(ph * 2 + bx0) * 0.9))
        for x in range(bx, bx + 5):
            c.set(x, yy, 7)
        c.set(bx + 1, yy - 1, 7)
        for k in range(3):
            c.set(bx + 2, yy - 1 - k, 1)
        c.set(bx + 3, yy - 1, 1)

    # --- two gulls crossing the sky ---
    for i, (gx0, gy0, gspd) in enumerate(GULLS):
        gx = ((gx0 + 15) + gspd * 0 + (f / NF) * (W + 30)) % (W + 30) - 15
        gy = gy0 + math.sin(ph * 2 + i * 2.0) * 2.5
        flap = 1 if (f // 4 + i) % 2 else 0
        for dx, dy in ((-2, flap), (-1, -1 + flap), (0, 0),
                       (1, -1 + flap), (2, flap)):
            c.set(int(gx + dx), int(gy + dy), 6)

    img = Image.new("P", (W, H))
    img.putpalette(PAL + [0] * (768 - len(PAL)))
    img.putdata([c.p[y][x] for y in range(H) for x in range(W)])
    return img.resize((W * SCALE, H * SCALE), Image.NEAREST)


if __name__ == "__main__":
    frames = [frame(f) for f in range(NF)]
    OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "paleale-city.gif")
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=90, loop=0, optimize=True, disposal=1)
    frames[0].save(OUT.replace(".gif", "-still.png"))
    print("wrote", OUT)
