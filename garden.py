#!/usr/bin/env python3
"""
STRANGE ATTRACTOR GARDEN — ASCII VIDEO
Oblique Strategy: "Turn it upside down" — inverted arc, complexity → simplicity.
Strange attractors, reaction-diffusion, cellular automata, domain warp.
Jewel tones: emerald, sapphire, amethyst, gold. 1920x1080, 25s.
"""
import os, sys, math, random, subprocess, time as _time
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from PIL import Image, ImageFont, ImageDraw

# ═════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═════════════════════════════════════════════════════════════════════════════
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
VW, VH = 1920, 1080
FPS = 24
DURATION = 25.0
N_FRAMES = int(DURATION * FPS)
N_WORKERS = 4
OUT_DIR = "/opt/data/videos/render"
os.makedirs(OUT_DIR, exist_ok=True)

# ═════════════════════════════════════════════════════════════════════════════
# PALETTES
# ═════════════════════════════════════════════════════════════════════════════
PAL_DENSE    = " .:;+=xX$#@\u2588"
PAL_BLOCKS   = " \u2591\u2592\u2593\u2588\u2584\u2580"
PAL_GREEK    = " \u03b1\u03b2\u03b3\u03b4\u03b5\u03b6\u03b7\u03b8\u03b9\u03ba\u03bb\u03bc\u03bd\u03be\u03c0\u03c1\u03c3\u03c4\u03c6\u03c8\u03c9"
PAL_RUNE     = " .\u16a0\u16a2\u16a6\u16b1\u16b7\u16c1\u16c7\u16d2\u16d6\u16da\u16de\u16df"
PAL_STARS    = " \u00b7\u2726\u2605\u2736\u2728\u25cf\u25a0"
PAL_DOTS     = " \u22c5\u2218\u2022\u25cf\u25c9\u2742"
PAL_BRAILLE  = " \u2801\u2802\u2803\u2804\u2805\u2806\u2807\u2808\u2809\u280a\u280b\u280c\u280d\u280e\u280f"
PAL_MATH     = " \u00b7\u2218\u2022\u00b0\u00b1\u2213\u2248\u2261\u221e\u222b\u2211\u220f\u221a\u2207\u2202\u2206\u03a9"
PAL_HERMES   = " .\u00b7~=\u2248\u221e\u26a1\u2726\u2605\u2295\u25ca\u25c6\u25b2\u25bc\u25cf\u25a0"
PAL_CIRCUIT  = " .\u00b7\u2500\u2502\u250c\u2510\u2514\u2518\u253c\u2261\u25a0\u2588"

# ═════════════════════════════════════════════════════════════════════════════
# COLOR
# ═════════════════════════════════════════════════════════════════════════════
def hsv2rgb(h, s, v):
    h = h % 1.0
    c = v * s; x = c * (1 - np.abs((h*6) % 2 - 1)); m = v - c
    r = np.zeros_like(h); g = np.zeros_like(h); b = np.zeros_like(h)
    masks = [(h < 1/6, c, x), ((h>=1/6)&(h<2/6), x, c),
             ((h>=2/6)&(h<3/6), 0, c), ((h>=3/6)&(h<4/6), 0, x),
             ((h>=4/6)&(h<5/6), x, 0), (h >= 5/6, c, 0)]
    for mask, rv, gv in masks:
        if hasattr(rv, '__len__'): r[mask] = rv[mask]
        else: r[mask] = rv
        if hasattr(gv, '__len__'): g[mask] = gv[mask]
        else: g[mask] = gv
    return (np.clip((r+m)*255, 0, 255).astype(np.uint8),
            np.clip((g+m)*255, 0, 255).astype(np.uint8),
            np.clip((b+m)*255, 0, 255).astype(np.uint8))

def mkc(R, G, B, rows, cols):
    o = np.zeros((rows, cols, 3), dtype=np.uint8)
    o[:,:,0] = R; o[:,:,1] = G; o[:,:,2] = B
    return o

# ═════════════════════════════════════════════════════════════════════════════
# GRID
# ═════════════════════════════════════════════════════════════════════════════
class GridLayer:
    def __init__(self, font_path, font_size, vw=VW, vh=VH):
        self.vw, self.vh = vw, vh
        self.font = ImageFont.truetype(font_path, font_size)
        asc, desc = self.font.getmetrics()
        bbox = self.font.getbbox("M")
        self.cw = bbox[2] - bbox[0]
        self.ch = asc + desc
        self.cols = vw // self.cw
        self.rows = vh // self.ch
        self.ox = (vw - self.cols * self.cw) // 2
        self.oy = (vh - self.rows * self.ch) // 2
        cx, cy = self.cols / 2.0, self.rows / 2.0
        asp = self.cw / self.ch
        self.rr = np.arange(self.rows, dtype=np.float32)[:, None]
        self.cc = np.arange(self.cols, dtype=np.float32)[None, :]
        self.dx = self.cc - cx
        self.dy = (self.rr - cy) * asp
        self.dist = np.sqrt(self.dx**2 + self.dy**2)
        self.angle = np.arctan2(self.dy, self.dx)
        self.dist_n = np.sqrt(((self.cc-cx)/max(self.cols,1))**2 +
                             (((self.rr-cy)*asp)/max(self.rows,1))**2)
        # Pre-rasterize all palette chars
        all_chars = set()
        for pal in [PAL_DENSE, PAL_BLOCKS, PAL_GREEK, PAL_RUNE, PAL_STARS,
                     PAL_DOTS, PAL_BRAILLE, PAL_MATH, PAL_HERMES, PAL_CIRCUIT]:
            all_chars.update(pal)
        all_chars.discard(" ")
        self.bm = {}
        for c in all_chars:
            img = Image.new("L", (self.cw, self.ch), 0)
            ImageDraw.Draw(img).text((0, 0), c, fill=255, font=self.font)
            self.bm[c] = np.array(img, dtype=np.float32) / 255.0

    def render(self, chars, colors, canvas=None):
        if canvas is None:
            canvas = np.zeros((self.vh, self.vw, 3), dtype=np.uint8)
        for row in range(self.rows):
            y = self.oy + row * self.ch
            if y + self.ch > self.vh: break
            for col in range(self.cols):
                c = chars[row, col]
                if c == " ": continue
                x = self.ox + col * self.cw
                if x + self.cw > self.vw: break
                if c not in self.bm: continue
                a = self.bm[c]
                cv = (a[:, :, None] * colors[row, col]).astype(np.uint8)
                canvas[y:y+self.ch, x:x+self.cw] = np.maximum(
                    canvas[y:y+self.ch, x:x+self.cw], cv)
        return canvas

# ═════════════════════════════════════════════════════════════════════════════
# VAL2CHAR
# ═════════════════════════════════════════════════════════════════════════════
def val2char(v, mask, pal):
    n = len(pal)
    idx = np.clip((v * n).astype(int), 0, n - 1)
    out = np.full(v.shape, " ", dtype="U1")
    for i, ch in enumerate(pal):
        out[mask & (idx == i)] = ch
    return out

# ═════════════════════════════════════════════════════════════════════════════
# TONEMAP
# ═════════════════════════════════════════════════════════════════════════════
def tonemap(canvas, gamma=0.72):
    f = canvas.astype(np.float32)
    sub = f[::4, ::4]
    lo = np.percentile(sub, 1)
    hi = np.percentile(sub, 99.5)
    if hi - lo < 10: hi = lo + 10
    f = np.clip((f - lo) / (hi - lo), 0, 1)
    np.power(f, gamma, out=f)
    return (f * 255).astype(np.uint8)

# ═════════════════════════════════════════════════════════════════════════════
# BLEND
# ═════════════════════════════════════════════════════════════════════════════
def blend_canvas(base, top, mode="screen", opacity=1.0):
    af = base.astype(np.float32) / 255.0
    bf = top.astype(np.float32) / 255.0
    if mode == "screen":   r = 1 - (1-af)*(1-bf)
    elif mode == "add":    r = np.clip(af + bf, 0, 1)
    elif mode == "multiply": r = af * bf
    elif mode == "difference": r = np.abs(af - bf)
    elif mode == "exclusion":  r = af + bf - 2*af*bf
    elif mode == "overlay":    r = np.where(af < 0.5, 2*af*bf, 1-2*(1-af)*(1-bf))
    elif mode == "lighten":    r = np.maximum(af, bf)
    else: r = bf
    if opacity < 1.0: r = af * (1-opacity) + r * opacity
    return np.clip(r * 255, 0, 255).astype(np.uint8)

# ═════════════════════════════════════════════════════════════════════════════
# _render_vf
# ═════════════════════════════════════════════════════════════════════════════
def _render_vf(g, val_fn, hue_fn, pal, f, t, S, sat=0.8, threshold=0.03):
    val = np.clip(val_fn(g, f, t, S), 0, 1)
    mask = val > threshold
    ch = val2char(val, mask, pal)
    if callable(hue_fn):
        h = hue_fn(g, f, t, S) % 1.0
    else:
        h = np.full((g.rows, g.cols), float(hue_fn), dtype=np.float32)
    h = np.broadcast_to(h, (g.rows, g.cols)).copy()
    R, G, B = hsv2rgb(h, np.full_like(val, sat), val)
    co = mkc(R, G, B, g.rows, g.cols)
    return g.render(ch, co)

# ═════════════════════════════════════════════════════════════════════════════
# NOISE
# ═════════════════════════════════════════════════════════════════════════════
def _value_noise_2d(x, y):
    ix = np.floor(x).astype(np.int64)
    iy = np.floor(y).astype(np.int64)
    n00 = ((ix * 374761393 + iy * 668265263) ^ ((ix * 374761393 + iy * 668265263) >> 13)) * 1274126177
    n00 = ((n00 ^ (n00 >> 16)) & 0x7fffffff).astype(np.float32) / 0x7fffffff
    ix1 = ix + 1
    n10 = ((ix1 * 374761393 + iy * 668265263) ^ ((ix1 * 374761393 + iy * 668265263) >> 13)) * 1274126177
    n10 = ((n10 ^ (n10 >> 16)) & 0x7fffffff).astype(np.float32) / 0x7fffffff
    iy1 = iy + 1
    n01 = ((ix * 374761393 + iy1 * 668265263) ^ ((ix * 374761393 + iy1 * 668265263) >> 13)) * 1274126177
    n01 = ((n01 ^ (n01 >> 16)) & 0x7fffffff).astype(np.float32) / 0x7fffffff
    n11 = ((ix1 * 374761393 + iy1 * 668265263) ^ ((ix1 * 374761393 + iy1 * 668265263) >> 13)) * 1274126177
    n11 = ((n11 ^ (n11 >> 16)) & 0x7fffffff).astype(np.float32) / 0x7fffffff
    t = np.clip(x - ix, 0, 1); s = np.clip(y - iy, 0, 1)
    t = t*t*(3-2*t); s = s*s*(3-2*s)
    return n00*(1-t)*(1-s) + n10*t*(1-s) + n01*(1-t)*s + n11*t*s

# ═════════════════════════════════════════════════════════════════════════════
# VALUE FIELDS
# ═════════════════════════════════════════════════════════════════════════════
def vf_plasma(g, f, t, S):
    v = np.sin(g.cc * 0.03 + t * 0.7) * 0.5
    v = v + np.sin(g.rr * 0.04 - t * 0.5) * 0.4
    v = v + np.sin((g.cc*0.02 + g.rr*0.03) + t*0.3) * 0.3
    v = v + np.sin(g.dist_n * 4 - t * 0.8) * 0.3
    return np.clip(v * 0.5 + 0.5, 0, 1)

def vf_fbm(g, f, t, S, octaves=5, freq=0.06, speed=0.2):
    val = np.zeros((g.rows, g.cols), dtype=np.float32)
    amp = 1.0; fx, fy = freq, freq*0.85
    for i in range(octaves):
        ph = t * speed * (1 + i * 0.3)
        val = val + _value_noise_2d(g.cc*fx + ph + i*17.3, g.rr*fy - ph*0.6 + i*31.7) * amp
        amp *= 0.5; fx *= 2.0; fy *= 2.0
    return np.clip(val * 0.8, 0, 1)

def vf_domain_warp(g, f, t, S, warp_strength=15.0, freq=0.06):
    wx = _value_noise_2d(g.cc*freq*1.3 + t*0.2, g.rr*freq + 7.1)
    wy = _value_noise_2d(g.cc*freq + t*0.14 + 3.2, g.rr*freq*1.1 - 11.8)
    wx = (wx - 0.5) * warp_strength
    wy = (wy - 0.5) * warp_strength
    return np.clip(_value_noise_2d(g.cc*freq*0.8 + wx + t*0.1,
                                    g.rr*freq*0.7 + wy - t*0.06), 0, 1)

def vf_spiral(g, f, t, S, n_arms=3, tightness=2.5):
    val = np.zeros((g.rows, g.cols), dtype=np.float32)
    for ai in range(n_arms):
        offset = ai * 2*np.pi / n_arms
        log_r = np.log(g.dist + 1) * tightness
        arm_phase = g.angle + offset - log_r + t * 0.8
        arm_val = np.clip(np.cos(arm_phase * n_arms) * 0.6 + 0.2, 0, 1)
        arm_val = arm_val * np.clip(1 - g.dist_n*0.4, 0.15, 1)
        val = np.maximum(val, arm_val)
    return val

def vf_vortex(g, f, t, S, twist=3.0):
    twisted = g.angle + g.dist_n * twist * np.sin(t * 0.5)
    val = np.sin(twisted * 4 - t * 2) * 0.5 + 0.5
    return np.clip(val * 0.9, 0, 1)

def vf_rings(g, f, t, S, n_base=6, spacing=4):
    val = np.zeros((g.rows, g.cols), dtype=np.float32)
    for ri in range(n_base):
        rad = (ri+1)*spacing + t*8
        rd = np.abs(g.dist - rad)
        val = np.maximum(val, np.clip((1 - rd/(1+t*3)), 0, 1))
    return val

def vf_interference(g, f, t, S, n_waves=6):
    val = np.zeros((g.rows, g.cols), dtype=np.float32)
    for i in range(n_waves):
        angle = i * np.pi / n_waves
        freq = 0.06 + i * 0.03; sp = 0.5 + i * 0.3
        proj = g.cc * np.cos(angle) + g.rr * np.sin(angle)
        val = val + np.sin(proj*freq + t*sp) * 0.25
    return np.clip(val * 0.5 + 0.5, 0, 1)

def vf_tunnel(g, f, t, S, speed=3.0, complexity=6):
    td = 1.0 / (g.dist_n + 0.08)
    v1 = np.sin(td*2 - t*speed) * 0.45 + 0.55
    v2 = np.sin(g.angle*complexity + td*1.5 - t*2) * 0.35 + 0.55
    return np.clip(v1*0.5 + v2*0.5, 0, 1)

# ─── Strange Attractor ───────────────────────────────────────────────────────
def vf_strange_attractor(g, f, t, S, attractor="clifford", n_points=40000,
                          warmup=300, bri=0.9, seed=42):
    key = "attr_" + attractor
    if key + "_done" not in S:
        # Time-varying params
        a = -1.4 + np.sin(t * 0.05) * 0.3
        b = 1.6 + np.cos(t * 0.07) * 0.2
        c = 1.0 + np.sin(t * 0.03 + 1) * 0.3
        d = 0.7 + np.cos(t * 0.04 + 2) * 0.2
        rng = np.random.RandomState(seed)
        x = rng.uniform(-0.1, 0.1, n_points).astype(np.float64)
        y = rng.uniform(-0.1, 0.1, n_points).astype(np.float64)
        for _ in range(warmup):
            if attractor == "clifford":
                xn = np.sin(a*y) + c*np.cos(a*x)
                yn = np.sin(b*x) + d*np.cos(b*y)
            else:  # de_jong
                xn = np.sin(a*y) - np.cos(b*x)
                yn = np.sin(c*x) - np.cos(d*y)
            x, y = xn, yn
        # Store in S
        S[key + "_x"] = x
        S[key + "_y"] = y
        S[key + "_done"] = True
    x = S[key + "_x"]
    y = S[key + "_y"]
    # Continue iterating (slow drift)
    a = -1.4 + np.sin(t * 0.05) * 0.3
    b = 1.6 + np.cos(t * 0.07) * 0.2
    c2 = 1.0 + np.sin(t * 0.03 + 1) * 0.3
    d2 = 0.7 + np.cos(t * 0.04 + 2) * 0.2
    if attractor == "clifford":
        xn = np.sin(a*y) + c2*np.cos(a*x)
        yn = np.sin(b*x) + d2*np.cos(b*y)
    else:
        xn = np.sin(a*y) - np.cos(b*x)
        yn = np.sin(c2*x) - np.cos(d2*y)
    x, y = xn, yn
    S[key + "_x"] = x
    S[key + "_y"] = y
    # Bin to grid
    margin = 0.1
    x_min, x_max = x.min() - margin, x.max() + margin
    y_min, y_max = y.min() - margin, y.max() + margin
    gx = ((x - x_min) / (x_max - x_min) * (g.cols - 1)).astype(np.int32)
    gy = ((y - y_min) / (y_max - y_min) * (g.rows - 1)).astype(np.int32)
    valid = (gx >= 0) & (gx < g.cols) & (gy >= 0) & (gy < g.rows)
    gx, gy = gx[valid], gy[valid]
    density = np.zeros((g.rows, g.cols), dtype=np.float32)
    np.add.at(density, (gy, gx), 1.0)
    density = np.log1p(density)
    mx = density.max()
    if mx > 0: density = density / mx
    return np.clip(density * bri, 0, 1)

# ─── Reaction-Diffusion ──────────────────────────────────────────────────────
def vf_reaction_diffusion(g, f, t, S, feed=0.055, kill=0.062,
                           da=1.0, db=0.5, dt=1.0, steps=6, init_mode="spots"):
    key = "rd_" + str(g.rows) + "x" + str(g.cols)
    if key + "_a" not in S:
        A = np.ones((g.rows, g.cols), dtype=np.float32)
        B = np.zeros((g.rows, g.cols), dtype=np.float32)
        if init_mode == "spots":
            rng = np.random.RandomState(42)
            for _ in range(max(3, g.rows * g.cols // 200)):
                r, c = rng.randint(2, g.rows-2), rng.randint(2, g.cols-2)
                B[r-1:r+2, c-1:c+2] = 1.0
        elif init_mode == "center":
            cr, cc = g.rows//2, g.cols//2
            B[cr-3:cr+3, cc-3:cc+3] = 1.0
        elif init_mode == "ring":
            mask = (g.dist_n > 0.2) & (g.dist_n < 0.35)
            B[mask] = 1.0
        S[key + "_a"] = A
        S[key + "_b"] = B
    A = S[key + "_a"].copy()
    B = S[key + "_b"].copy()
    f_mod = feed + f.get("bass", 0.3) * 0.003
    k_mod = kill + f.get("hi", 0.3) * 0.002
    for _ in range(steps):
        pA = np.pad(A, 1, mode="wrap")
        pB = np.pad(B, 1, mode="wrap")
        lapA = (pA[:-2,1:-1]+pA[2:,1:-1]+pA[1:-1,:-2]+pA[1:-1,2:])*0.2 + \
               (pA[:-2,:-2]+pA[:-2,2:]+pA[2:,:-2]+pA[2:,2:])*0.05 - A
        lapB = (pB[:-2,1:-1]+pB[2:,1:-1]+pB[1:-1,:-2]+pB[1:-1,2:])*0.2 + \
               (pB[:-2,:-2]+pB[:-2,2:]+pB[2:,:-2]+pB[2:,2:])*0.05 - B
        ABB = A * B * B
        A = np.clip(A + (da*lapA - ABB + f_mod*(1-A)) * dt, 0, 1)
        B = np.clip(B + (db*lapB + ABB - (f_mod+k_mod)*B) * dt, 0, 1)
    S[key + "_a"] = A
    S[key + "_b"] = B
    return np.clip(B * 2.0, 0, 1)

# ─── Game of Life ─────────────────────────────────────────────────────────────
def vf_game_of_life(g, f, t, S, rule="life", steps_per_frame=1,
                     density=0.3, fade=0.92, seed=42):
    presets = {"life": ({3}, {2,3}), "coral": ({3}, {4,5,6,7,8}),
               "maze": ({3}, {1,2,3,4,5}), "anneal": ({4,6,7,8}, {3,5,6,7,8})}
    birth, survive = presets.get(rule, presets["life"])
    key = "gol_" + str(g.rows) + "x" + str(g.cols)
    if key + "_grid" not in S:
        rng = np.random.RandomState(seed)
        S[key + "_grid"] = (rng.random((g.rows, g.cols)) < density).astype(np.float32)
        S[key + "_display"] = S[key + "_grid"].copy()
    grid = S[key + "_grid"]
    display = S[key + "_display"]
    for _ in range(steps_per_frame):
        padded = np.pad(grid > 0.5, 1, mode="wrap").astype(np.int8)
        neighbors = (padded[:-2,:-2]+padded[:-2,1:-1]+padded[:-2,2:]+
                     padded[1:-1,:-2]+padded[1:-1,2:]+
                     padded[2:,:-2]+padded[2:,1:-1]+padded[2:,2:])
        alive = grid > 0.5
        new_alive = np.zeros_like(grid, dtype=bool)
        for b in birth: new_alive = new_alive | (~alive & (neighbors == b))
        for s2 in survive: new_alive = new_alive | (alive & (neighbors == s2))
        grid = new_alive.astype(np.float32)
    display = np.where(grid > 0.5, 1.0, display * fade)
    S[key + "_grid"] = grid
    S[key + "_display"] = display
    return np.clip(display, 0, 1)

# ═════════════════════════════════════════════════════════════════════════════
# HUE FIELDS
# ═════════════════════════════════════════════════════════════════════════════
def hf_angle(offset=0.0):
    def fn(g, f, t, S): return (g.angle / (2*np.pi) + offset + t * 0.05) % 1.0
    return fn

def hf_time_cycle(speed=0.1):
    def fn(g, f, t, S): return np.full((g.rows, g.cols), (t*speed) % 1.0, dtype=np.float32)
    return fn

def hf_distance(base=0.5, scale=0.02):
    def fn(g, f, t, S): return (base + g.dist * scale + t * 0.03) % 1.0
    return fn

def hf_fixed(hue):
    def fn(g, f, t, S): return np.full((g.rows, g.cols), hue, dtype=np.float32)
    return fn

# ─── Jewel Tone Hue Fields (custom for this project) ──────────────────────────
def hf_jewel_cycle(t_offset=0.0):
    """Cycle through jewel tones: emerald (0.33), sapphire (0.58), amethyst (0.78), gold (0.12)."""
    jewels = [0.33, 0.58, 0.78, 0.12]
    def fn(g, f, t, S):
        idx = int((t + t_offset) * 0.15) % len(jewels)
        next_idx = (idx + 1) % len(jewels)
        frac = ((t + t_offset) * 0.15) % 1.0
        # Smooth blend between adjacent jewel hues
        h1, h2 = jewels[idx], jewels[next_idx]
        # Shortest path
        dh = h2 - h1
        if abs(dh) > 0.5: dh = dh - np.sign(dh)
        h = (h1 + dh * frac + g.dist_n * 0.03) % 1.0
        return h
    return fn

# ═════════════════════════════════════════════════════════════════════════════
# SHADERS
# ═════════════════════════════════════════════════════════════════════════════
def sh_bloom(c, thr=120):
    sm = c[::4, ::4].astype(np.float32)
    br = np.where(sm > thr, sm, 0)
    for _ in range(3):
        p = np.pad(br, ((1,1),(1,1),(0,0)), mode="edge")
        br = (p[:-2,:-2]+p[:-2,1:-1]+p[:-2,2:]+p[1:-1,:-2]+p[1:-1,1:-1]+
              p[1:-1,2:]+p[2:,:-2]+p[2:,1:-1]+p[2:,2:]) / 9.0
    bl = np.repeat(np.repeat(br, 4, axis=0), 4, axis=1)[:c.shape[0], :c.shape[1]]
    return np.clip(c.astype(np.float32) + bl * 0.4, 0, 255).astype(np.uint8)

def sh_vignette(c, s=0.22):
    h, w = c.shape[:2]
    Y = np.linspace(-1, 1, h)[:, None]; X = np.linspace(-1, 1, w)[None, :]
    mask = np.clip(1.0 - np.sqrt(X**2 + Y**2) * s, 0.15, 1).astype(np.float32)
    return np.clip(c * mask[:, :, None], 0, 255).astype(np.uint8)

def sh_grain(c, amt=10):
    noise = np.random.randint(-amt, amt+1, (c.shape[0]//2, c.shape[1]//2, 1), dtype=np.int16)
    noise = np.repeat(np.repeat(noise, 2, axis=0), 2, axis=1)[:c.shape[0], :c.shape[1]]
    return np.clip(c.astype(np.int16) + noise, 0, 255).astype(np.uint8)

def sh_chromatic(c, amt=3):
    if amt < 1: return c
    a = int(amt); o = c.copy()
    o[:, a:, 0] = c[:, :-a, 0]
    o[:, :-a, 2] = c[:, a:, 2]
    return o

def sh_kaleidoscope(c, folds=6):
    h, w = c.shape[:2]; cy, cx = h//2, w//2
    Y = np.arange(h, dtype=np.float32)[:, None] - cy
    X = np.arange(w, dtype=np.float32)[None, :] - cx
    angle = np.arctan2(Y, X); dist = np.sqrt(X**2 + Y**2)
    wedge = 2 * np.pi / folds
    folded = np.abs((angle % wedge) - wedge/2)
    ny = np.clip((cy + dist * np.sin(folded)).astype(int), 0, h-1)
    nx = np.clip((cx + dist * np.cos(folded)).astype(int), 0, w-1)
    return c[ny, nx]

def sh_color_grade(c, tint):
    o = c.astype(np.float32)
    o[:,:,0] *= tint[0]; o[:,:,1] *= tint[1]; o[:,:,2] *= tint[2]
    return np.clip(o, 0, 255).astype(np.uint8)

def sh_scanlines(c, intensity=0.06, spacing=3):
    m = np.ones(c.shape[0], dtype=np.float32)
    m[::spacing] = 1.0 - intensity
    return np.clip(c * m[:, None, None], 0, 255).astype(np.uint8)

def sh_soft_focus(c, strength=0.3):
    sm = c[::2, ::2].astype(np.float32)
    p = np.pad(sm, ((1,1),(1,1),(0,0)), mode="edge")
    bl = (p[:-2,:-2]+p[:-2,1:-1]+p[:-2,2:]+p[1:-1,:-2]+p[1:-1,1:-1]+
          p[1:-1,2:]+p[2:,:-2]+p[2:,1:-1]+p[2:,2:]) / 9.0
    bl = np.repeat(np.repeat(bl, 2, axis=0), 2, axis=1)[:c.shape[0], :c.shape[1]]
    return np.clip(c * (1-strength) + bl * strength, 0, 255).astype(np.uint8)

# ═════════════════════════════════════════════════════════════════════════════
# FEEDBACK
# ═════════════════════════════════════════════════════════════════════════════
class FeedbackBuffer:
    def __init__(self):
        self.buf = None
    def apply(self, canvas, decay=0.8, blend="screen", opacity=0.4,
              transform="zoom", transform_amt=0.015, hue_shift=0.0):
        if self.buf is None:
            self.buf = canvas.astype(np.float32) / 255.0
            return canvas
        self.buf *= decay
        if transform == "zoom":
            h, w = self.buf.shape[:2]
            m = max(1, int(h * transform_amt)); n = max(1, int(w * transform_amt))
            cropped = self.buf[m:-m or None, n:-n or None]
            self.buf = np.array(Image.fromarray(
                np.clip(cropped*255,0,255).astype(np.uint8)
            ).resize((w, h), Image.NEAREST)).astype(np.float32) / 255.0
        result = blend_canvas(canvas, np.clip(self.buf*255,0,255).astype(np.uint8), blend, opacity)
        self.buf = result.astype(np.float32) / 255.0
        return result

# ═════════════════════════════════════════════════════════════════════════════
# SHADER CHAIN
# ═════════════════════════════════════════════════════════════════════════════
class ShaderChain:
    def __init__(self): self.steps = []
    def add(self, name, **kw): self.steps.append((name, kw)); return self
    def apply(self, canvas, f=None, t=0):
        for name, kw in self.steps:
            if name == "bloom":       canvas = sh_bloom(canvas, kw.get("thr", 120))
            elif name == "vignette":  canvas = sh_vignette(canvas, kw.get("s", 0.22))
            elif name == "grain":     canvas = sh_grain(canvas, int(kw.get("amt", 10)))
            elif name == "chromatic": canvas = sh_chromatic(canvas, kw.get("amt", 3))
            elif name == "kaleidoscope": canvas = sh_kaleidoscope(canvas.copy(), kw.get("folds", 6))
            elif name == "color_grade": canvas = sh_color_grade(canvas, kw.get("tint", (1,1,1)))
            elif name == "scanlines":  canvas = sh_scanlines(canvas, kw.get("intensity", 0.06), kw.get("spacing", 3))
            elif name == "soft_focus": canvas = sh_soft_focus(canvas, kw.get("strength", 0.3))
        return canvas

# ═════════════════════════════════════════════════════════════════════════════
# SYNTH FEATURES
# ═════════════════════════════════════════════════════════════════════════════
def synth_features(t):
    return {
        "rms": 0.3 + 0.15*np.sin(t*0.5) + 0.1*np.sin(t*2.3),
        "bass": 0.3 + 0.2*np.sin(t*0.3)**2,
        "mid": 0.3 + 0.15*np.sin(t*1.2),
        "hi": 0.3 + 0.1*np.sin(t*3.1),
        "beat": 1.0 if (t*2)%1 < 0.05 else 0.0,
        "bdecay": max(0, np.sin(t*2)*0.5 + 0.3),
        "sub_r": 0.3 + 0.1*np.sin(t*0.7),
        "cent": 0.5 + 0.2*np.sin(t*0.4),
    }

# ═════════════════════════════════════════════════════════════════════════════
# SCENE FUNCTIONS — module-level for pickling
# ═════════════════════════════════════════════════════════════════════════════

def fx_attractor_dawn(r, f, t, S):
    """Scene 1: Strange attractor at maximum complexity — Clifford attractor."""
    g = r["md"]
    g2 = r["sm"]
    # Main: strange attractor density
    val = vf_strange_attractor(g, f, t, S, attractor="clifford", n_points=50000, bri=1.0)
    h = hf_jewel_cycle(0.0)(g, f, t, S)
    mask = val > 0.04
    ch = val2char(val, mask, PAL_MATH)
    R, G, B = hsv2rgb(h, np.full_like(val, 0.85), val)
    co = mkc(R, G, B, g.rows, g.cols)
    canvas_a = g.render(ch, co)
    # Background: domain warp on sm, dim
    canvas_b = _render_vf(g2, lambda g,f,t,S: vf_domain_warp(g,f,t,S, warp_strength=18)*0.25,
                          hf_fixed(0.58), PAL_DOTS, f, t, S, sat=0.4, threshold=0.05)
    result = blend_canvas(canvas_b, canvas_a, "screen", 0.9)
    # Kaleidoscope for "upside down" symmetry
    if t > 2.0:
        result = sh_kaleidoscope(result.copy(), folds=8)
    return result

def fx_coral_growth(r, f, t, S):
    """Scene 2: Reaction-diffusion coral — organic, growing."""
    g = r["sm"]
    g2 = r["md"]
    val = vf_reaction_diffusion(g, f, t, S, feed=0.037, kill=0.060,
                                 steps=5, init_mode="spots")
    h = hf_distance(0.33, 0.02)(g, f, t, S)
    mask = val > 0.03
    ch = val2char(val, mask, PAL_DOTS)
    R, G, B = hsv2rgb(h, np.full_like(val, 0.7), val)
    co = mkc(R, G, B, g.rows, g.cols)
    canvas_a = g.render(ch, co)
    # Underlay: fBM on md, emerald
    canvas_b = _render_vf(g2, lambda g,f,t,S: vf_fbm(g,f,t,S, octaves=4, freq=0.05, speed=0.1)*0.3,
                          hf_fixed(0.33), PAL_GREEK, f, t, S, sat=0.5, threshold=0.05)
    return blend_canvas(canvas_b, canvas_a, "screen", 0.8)

def fx_cellular_ghosts(r, f, t, S):
    """Scene 3: Game of Life with fading ghost trails."""
    g = r["sm"]
    g2 = r["lg"]
    # Life with ghost trails
    val = vf_game_of_life(g, f, t, S, rule="life", steps_per_frame=1, fade=0.93, density=0.3)
    h = hf_time_cycle(0.06)(g, f, t, S)
    mask = val > 0.05
    ch = val2char(val, mask, PAL_BLOCKS)
    R, G, B = hsv2rgb(h, np.full_like(val, 0.8), val)
    co = mkc(R, G, B, g.rows, g.cols)
    canvas_a = g.render(ch, co)
    # Coral automaton on lg for chunky texture
    val2 = vf_game_of_life(g2, f, t, S, rule="coral", steps_per_frame=1, fade=0.85, density=0.15, seed=99)
    h2 = hf_fixed(0.78)(g2, f, t, S)
    ch2 = val2char(val2, val2 > 0.05, PAL_RUNE)
    R2, G2, B2 = hsv2rgb(h2, np.full_like(val2, 0.6), val2)
    co2 = mkc(R2, G2, B2, g2.rows, g2.cols)
    canvas_b = g2.render(ch2, co2)
    return blend_canvas(canvas_a, canvas_b, "screen", 0.5)

def fx_organic_flow(r, f, t, S):
    """Scene 4: Domain warp garden — flowing organic texture."""
    g = r["md"]
    g2 = r["sm"]
    canvas_a = _render_vf(g, lambda g,f,t,S: vf_domain_warp(g,f,t,S, warp_strength=22)*1.1,
                          hf_jewel_cycle(2.0), PAL_GREEK, f, t, S, sat=0.75, threshold=0.04)
    canvas_b = _render_vf(g2, lambda g,f,t,S: vf_fbm(g,f,t,S, octaves=5, freq=0.04, speed=0.15)*0.5,
                          hf_distance(0.58, 0.02), PAL_BRAILLE, f, t, S, sat=0.5, threshold=0.05)
    result = blend_canvas(canvas_a, canvas_b, "screen", 0.6)
    return result

def fx_cosmic_spiral(r, f, t, S):
    """Scene 5: Spiral vortex — cosmic moment, resolving."""
    g = r["md"]
    g2 = r["sm"]
    canvas_a = _render_vf(g, lambda g,f,t,S: vf_spiral(g,f,t,S, n_arms=4, tightness=3.0)*1.2,
                          hf_angle(0.58), PAL_STARS, f, t, S, sat=0.8, threshold=0.04)
    canvas_b = _render_vf(g2, lambda g,f,t,S: vf_vortex(g,f,t,S, twist=6.0)*0.7,
                          hf_time_cycle(0.04), PAL_DOTS, f, t, S, sat=0.5, threshold=0.05)
    return blend_canvas(canvas_a, canvas_b, "screen", 0.5)

def fx_resolution(r, f, t, S):
    """Scene 6: Fine noise resolving to stillness — gold, calm, diffuse."""
    g = r["md"]
    # High-frequency value noise — features smaller than row height, no banding
    val = _value_noise_2d(g.cc * 0.35 + t * 0.15, g.rr * 0.30 + t * 0.12)
    val2 = _value_noise_2d(g.cc * 0.70 + t * 0.08 + 50, g.rr * 0.65 + t * 0.06 + 70)
    val = np.clip(val * 0.5 + val2 * 0.3, 0, 1) * 0.35
    h = np.full((g.rows, g.cols), 0.12, dtype=np.float32)  # gold
    mask = val > 0.02
    ch = val2char(val, mask, PAL_HERMES)
    R, G, B = hsv2rgb(h, np.full_like(val, 0.35), val)
    co = mkc(R, G, B, g.rows, g.cols)
    return g.render(ch, co)

# ═════════════════════════════════════════════════════════════════════════════
# SCENE TABLE
# ═════════════════════════════════════════════════════════════════════════════
SCENES = [
    {"start": 0.0,  "end": 5.0,  "name": "attractor", "fx": fx_attractor_dawn,
     "grid": "md", "gamma": 0.60,
     "shaders": [("bloom", {"thr": 90}), ("chromatic", {"amt": 3}),
                 ("vignette", {"s": 0.25}), ("grain", {"amt": 6})],
     "feedback": {"decay": 0.75, "blend": "screen", "opacity": 0.35,
                  "transform": "zoom", "transform_amt": 0.012, "hue_shift": 0.02}},

    {"start": 5.0,  "end": 9.0,  "name": "coral",     "fx": fx_coral_growth,
     "grid": "sm", "gamma": 0.65,
     "shaders": [("bloom", {"thr": 100}), ("soft_focus", {"strength": 0.2}),
                 ("vignette", {"s": 0.2})],
     "feedback": {"decay": 0.8, "blend": "screen", "opacity": 0.2,
                  "transform": "zoom", "transform_amt": 0.008}},

    {"start": 9.0,  "end": 13.0, "name": "cellular",  "fx": fx_cellular_ghosts,
     "grid": "sm", "gamma": 0.68,
     "shaders": [("bloom", {"thr": 110}), ("scanlines", {"intensity": 0.04}),
                 ("grain", {"amt": 4})],
     "feedback": {"decay": 0.85, "blend": "screen", "opacity": 0.15}},

    {"start": 13.0, "end": 17.0, "name": "organic",   "fx": fx_organic_flow,
     "grid": "md", "gamma": 0.70,
     "shaders": [("bloom", {"thr": 100}), ("chromatic", {"amt": 2}),
                 ("vignette", {"s": 0.2}), ("grain", {"amt": 5})],
     "feedback": {"decay": 0.7, "blend": "screen", "opacity": 0.3,
                  "transform": "zoom", "transform_amt": 0.01, "hue_shift": 0.015}},

    {"start": 17.0, "end": 21.0, "name": "cosmic",    "fx": fx_cosmic_spiral,
     "grid": "md", "gamma": 0.72,
     "shaders": [("bloom", {"thr": 95}), ("vignette", {"s": 0.18}),
                 ("grain", {"amt": 4})],
     "feedback": {"decay": 0.75, "blend": "screen", "opacity": 0.25,
                  "transform": "zoom", "transform_amt": 0.01}},

    {"start": 21.0, "end": 25.0, "name": "resolution", "fx": fx_resolution,
     "grid": "md", "gamma": 0.78,
     "shaders": [("bloom", {"thr": 130}), ("soft_focus", {"strength": 0.25}),
                 ("vignette", {"s": 0.3})],
     "feedback": None},
]

# ═════════════════════════════════════════════════════════════════════════════
# RENDER
# ═════════════════════════════════════════════════════════════════════════════
def get_scene_at(t):
    scene = SCENES[0]
    for s in SCENES:
        if t >= s["start"]: scene = s
    return scene

def render_segment(seg_idx, frame_start, frame_end, scene_dict):
    grids = {}
    for key, sz in [("xs",8),("sm",10),("md",16),("lg",20),("xl",24)]:
        grids[key] = GridLayer(FONT_PATH, sz)
    clip_path = os.path.join(OUT_DIR, f"clip_{seg_idx:02d}.mp4")
    log_path = clip_path.replace(".mp4", ".log")
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "pipe:0",
           "-c:v", "libx264", "-preset", "fast", "-crf", "18",
           "-pix_fmt", "yuv420p", clip_path]
    stderr_fh = open(log_path, "w")
    pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=stderr_fh)
    S = {}
    fb = FeedbackBuffer() if scene_dict.get("feedback") else None
    chain = ShaderChain()
    for sn, kw in scene_dict.get("shaders", []): chain.add(sn, **kw)
    fx_fn = scene_dict["fx"]
    gamma = scene_dict.get("gamma", 0.72)
    fb_cfg = scene_dict.get("feedback", None)
    for fi in range(frame_start, frame_end):
        t = fi / FPS
        f = synth_features(t)
        canvas = fx_fn(grids, f, t - scene_dict["start"], S)
        canvas = tonemap(canvas, gamma=gamma)
        if fb and fb_cfg: canvas = fb.apply(canvas, **fb_cfg)
        canvas = chain.apply(canvas, f=f, t=t)
        pipe.stdin.write(canvas.tobytes())
    pipe.stdin.close(); pipe.wait(); stderr_fh.close()
    return clip_path

def main():
    print(f"STRANGE ATTRACTOR GARDEN — ASCII VIDEO")
    print(f"{VW}x{VH} @ {FPS}fps | {DURATION}s | {N_FRAMES} frames | {N_WORKERS} workers")
    frames_per = N_FRAMES // N_WORKERS
    segments = []
    for i in range(N_WORKERS):
        fs = i * frames_per; fe = (i+1) * frames_per if i < N_WORKERS-1 else N_FRAMES
        if fs >= fe: continue
        mid_t = (fs + fe) / 2 / FPS
        scene = get_scene_at(mid_t)
        segments.append((i, fs, fe, scene))
    t0 = _time.time()
    print(f"\nRendering {len(segments)} segments...")
    with ProcessPoolExecutor(max_workers=N_WORKERS) as pool:
        futures = {pool.submit(render_segment, idx, fs, fe, scene): idx
                   for idx, fs, fe, scene in segments}
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                path = fut.result()
                print(f"  ✓ Segment {idx} → {os.path.basename(path)}")
            except Exception as e:
                print(f"  ✗ Segment {idx} FAILED: {e}")
    elapsed = _time.time() - t0
    print(f"\nRender: {elapsed:.1f}s")
    # Concatenate
    concat_path = os.path.join(OUT_DIR, "concat.txt")
    with open(concat_path, "w") as cf:
        for idx, fs, fe, scene in sorted(segments, key=lambda x: x[0]):
            clip = os.path.join(OUT_DIR, f"clip_{idx:02d}.mp4")
            if os.path.exists(clip): cf.write(f"file '{clip}'\n")
    output_path = os.path.join(OUT_DIR, "strange_attractor_garden.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                     "-i", concat_path, "-c:v", "libx264", "-preset",
                     "fast", "-crf", "18", "-pix_fmt", "yuv420p",
                     output_path], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    size = os.path.getsize(output_path) / 1024
    print(f"\n✓ {output_path}")
    print(f"  {size:.0f}KB | {elapsed:.1f}s render")

if __name__ == "__main__":
    main()
