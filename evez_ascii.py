#!/usr/bin/env python3
"""
EVEZ-OS // ASCII VIDEO — GENERATIVE SURVEILLANCE STATE
A procedural ASCII art video: emergence from void → data breach → network attack → cosmic recursion.
No source material. Pure generative. Python + NumPy + ffmpeg.
"""
import os, sys, math, random, subprocess, time as _time
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from PIL import Image, ImageFont, ImageDraw

# ============================================================================
# CONFIG
# ============================================================================
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_BOLD  = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
VW, VH = 1280, 720
FPS = 24
DURATION = 20.0
N_FRAMES = int(DURATION * FPS)
N_WORKERS = 4
OUT_DIR = "/opt/data/videos/render"
os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================================
# PALETTES
# ============================================================================
PAL_DEFAULT = " .`'-:;!><=+*^~?/|(){}[]#&$@%"
PAL_DENSE    = " .:;+=xX$#@\u2588"
PAL_BLOCKS   = " \u2591\u2592\u2593\u2588\u2584\u2580\u2590\u258c"
PAL_KATA     = " \u00b7\uff66\uff67\uff68\uff69\uff6a\uff6b\uff6c\uff6d\uff6e\uff6f\uff70\uff71\uff72\uff73\uff74\uff75\uff76\uff77"
PAL_GREEK    = " \u03b1\u03b2\u03b3\u03b4\u03b5\u03b6\u03b7\u03b8\u03b9\u03ba\u03bb\u03bc\u03bd\u03be\u03c0\u03c1\u03c3\u03c4\u03c6\u03c8\u03c9"
PAL_RUNE     = " .\u16a0\u16a2\u16a6\u16b1\u16b7\u16c1\u16c7\u16d2\u16d6\u16da\u16de\u16df"
PAL_STARS    = " \u00b7\u2726\u2605\u2736\u2728\u25cf\u25a0"
PAL_DOTS     = " \u22c5\u2218\u2022\u25cf\u25c9\u2742"
PAL_CIRCUIT  = " .\u00b7\u2500\u2502\u250c\u2510\u2514\u2518\u253c\u2261\u25a0\u2588"
PAL_BRAILLE  = " \u2801\u2802\u2803\u2804\u2805\u2806\u2807\u2808\u2809\u280a\u280b\u280c\u280d\u280e\u280f"
PAL_HERMES   = " .\u00b7~=\u2248\u221e\u26a1\u263f\u2726\u2605\u2295\u25ca\u25c6\u25b2\u25bc\u25cf\u25a0"

# ============================================================================
# COLOR
# ============================================================================
def hsv2rgb(h, s, v):
    h = h % 1.0
    c = v * s; x = c * (1 - np.abs((h*6) % 2 - 1)); m = v - c
    masks = [(h < 1/6, c, x, 0), ((h>=1/6)&(h<2/6), x, c, 0),
             ((h>=2/6)&(h<3/6), 0, c, x), ((h>=3/6)&(h<4/6), 0, x, c),
             ((h>=4/6)&(h<5/6), x, 0, c), (h >= 5/6, c, 0, x)]
    r = np.zeros_like(h); g = np.zeros_like(h); b = np.zeros_like(h)
    for mask, rv, gv, bv in masks:
        r[mask] = rv[mask] if hasattr(rv, '__len__') else rv
        g[mask] = gv[mask] if hasattr(gv, '__len__') else gv
        b[mask] = bv[mask] if hasattr(bv, '__len__') else bv
    return (np.clip((r+m)*255, 0, 255).astype(np.uint8),
            np.clip((g+m)*255, 0, 255).astype(np.uint8),
            np.clip((b+m)*255, 0, 255).astype(np.uint8))

def hsv2rgb_scalar(h, s, v):
    h = h % 1.0; c = v*s; x = c*(1-abs((h*6)%2-1)); m2 = v-c
    if h*6 < 1: r2,g2,b2 = c,x,0
    elif h*6 < 2: r2,g2,b2 = x,c,0
    elif h*6 < 3: r2,g2,b2 = 0,c,x
    elif h*6 < 4: r2,g2,b2 = 0,x,c
    elif h*6 < 5: r2,g2,b2 = x,0,c
    else: r2,g2,b2 = c,0,x
    return (int((r2+m2)*255), int((g2+m2)*255), int((b2+m2)*255))

def mkc(R, G, B, rows, cols):
    o = np.zeros((rows, cols, 3), dtype=np.uint8)
    o[:,:,0] = R; o[:,:,1] = G; o[:,:,2] = B
    return o

# ============================================================================
# GRID
# ============================================================================
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
        self.dist_n = np.sqrt(((self.cc-cx)/max(self.cols,1))**2 + (((self.rr-cy)*asp)/max(self.rows,1))**2)
        # Pre-rasterize common chars
        all_chars = set()
        for pal in [PAL_DEFAULT, PAL_DENSE, PAL_BLOCKS, PAL_KATA, PAL_GREEK,
                     PAL_RUNE, PAL_STARS, PAL_DOTS, PAL_CIRCUIT, PAL_BRAILLE, PAL_HERMES]:
            all_chars.update(pal)
        all_chars.update("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .:-=+*/|<>")
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
                canvas[y:y+self.ch, x:x+self.cw] = np.maximum(canvas[y:y+self.ch, x:x+self.cw], cv)
        return canvas

# ============================================================================
# VAL2CHAR
# ============================================================================
def val2char(v, mask, pal):
    n = len(pal)
    idx = np.clip((v * n).astype(int), 0, n - 1)
    out = np.full(v.shape, " ", dtype="U1")
    for i, ch in enumerate(pal):
        out[mask & (idx == i)] = ch
    return out

# ============================================================================
# TONEMAP
# ============================================================================
def tonemap(canvas, gamma=0.72):
    f = canvas.astype(np.float32)
    sub = f[::4, ::4]
    lo = np.percentile(sub, 1)
    hi = np.percentile(sub, 99.5)
    if hi - lo < 10: hi = lo + 10
    f = np.clip((f - lo) / (hi - lo), 0, 1)
    np.power(f, gamma, out=f)
    return (f * 255).astype(np.uint8)

# ============================================================================
# BLEND
# ============================================================================
def blend_canvas(base, top, mode="screen", opacity=1.0):
    af = base.astype(np.float32) / 255.0
    bf = top.astype(np.float32) / 255.0
    if mode == "screen":   result = 1 - (1-af)*(1-bf)
    elif mode == "add":    result = np.clip(af + bf, 0, 1)
    elif mode == "multiply": result = af * bf
    elif mode == "difference": result = np.abs(af - bf)
    elif mode == "exclusion":  result = af + bf - 2*af*bf
    elif mode == "overlay":    result = np.where(af < 0.5, 2*af*bf, 1-2*(1-af)*(1-bf))
    elif mode == "lighten":    result = np.maximum(af, bf)
    elif mode == "darken":     result = np.minimum(af, bf)
    else: result = bf
    if opacity < 1.0:
        result = af * (1-opacity) + result * opacity
    return np.clip(result * 255, 0, 255).astype(np.uint8)

# ============================================================================
# _render_vf — the workhorse
# ============================================================================
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

# ============================================================================
# VALUE FIELDS
# ============================================================================
def vf_plasma(g, f, t, S):
    v = np.sin(g.cc * 0.03 + t * 0.7) * 0.5
    v = v + np.sin(g.rr * 0.04 - t * 0.5) * 0.4
    v = v + np.sin((g.cc*0.02 + g.rr*0.03) + t*0.3) * 0.3
    v = v + np.sin(g.dist_n * 4 - t * 0.8) * 0.3
    return np.clip(v * 0.5 + 0.5, 0, 1)

def vf_rings(g, f, t, S, n_base=6, spacing=4):
    n = n_base
    sp = spacing
    val = np.zeros((g.rows, g.cols), dtype=np.float32)
    for ri in range(n):
        rad = (ri+1)*sp + t*8
        rd = np.abs(g.dist - rad)
        val = np.maximum(val, np.clip((1 - rd/(1+t*3)), 0, 1))
    return val

def vf_tunnel(g, f, t, S, speed=3.0, complexity=6):
    tunnel_d = 1.0 / (g.dist_n + 0.08)
    v1 = np.sin(tunnel_d*2 - t*speed) * 0.45 + 0.55
    v2 = np.sin(g.angle*complexity + tunnel_d*1.5 - t*2) * 0.35 + 0.55
    return np.clip(v1*0.5 + v2*0.5, 0, 1)

def vf_vortex(g, f, t, S, twist=3.0):
    twisted = g.angle + g.dist_n * twist * np.sin(t * 0.5)
    val = np.sin(twisted * 4 - t * 2) * 0.5 + 0.5
    return np.clip(val * (0.5 + 0.3), 0, 1)

def vf_spiral(g, f, t, S, n_arms=3, tightness=2.5):
    val = np.zeros((g.rows, g.cols), dtype=np.float32)
    for ai in range(n_arms):
        offset = ai * 2*np.pi / n_arms
        log_r = np.log(g.dist + 1) * tightness
        arm_phase = g.angle + offset - log_r + t * 0.8
        arm_val = np.clip(np.cos(arm_phase * n_arms) * 0.6 + 0.2, 0, 1)
        arm_val *= np.clip(1 - g.dist_n*0.4, 0.15, 1)
        val = np.maximum(val, arm_val)
    return val

def vf_interference(g, f, t, S, n_waves=6):
    val = np.zeros((g.rows, g.cols), dtype=np.float32)
    for i in range(n_waves):
        angle = i * np.pi / n_waves
        freq = 0.06 + i * 0.03; sp = 0.5 + i * 0.3
        proj = g.cc * np.cos(angle) + g.rr * np.sin(angle)
        val += np.sin(proj*freq + t*sp) * 0.25
    return np.clip(val * 0.5 + 0.5, 0, 1)

def _value_noise_2d(x, y):
    ix = np.floor(x).astype(np.int64)
    iy = np.floor(y).astype(np.int64)
    n = ix * 374761393 + iy * 668265263
    n = (n ^ (n >> 13)) * 1274126177
    n00 = ((n ^ (n >> 16)) & 0x7fffffff).astype(np.float32) / 0x7fffffff
    n1x = ((ix+1) * 374761393 + iy * 668265263)
    n1x = (n1x ^ (n1x >> 13)) * 1274126177
    n10 = ((n1x ^ (n1x >> 16)) & 0x7fffffff).astype(np.float32) / 0x7fffffff
    n0y = (ix * 374761393 + (iy+1) * 668265263)
    n0y = (n0y ^ (n0y >> 13)) * 1274126177
    n01 = ((n0y ^ (n0y >> 16)) & 0x7fffffff).astype(np.float32) / 0x7fffffff
    n11 = ((ix+1) * 374761393 + (iy+1) * 668265263)
    n11 = (n11 ^ (n11 >> 13)) * 1274126177
    n11 = ((n11 ^ (n11 >> 16)) & 0x7fffffff).astype(np.float32) / 0x7fffffff
    t = np.clip(x - ix, 0, 1); s = np.clip(y - iy, 0, 1)
    t = t*t*(3-2*t); s = s*s*(3-2*s)
    return n00*(1-t)*(1-s) + n10*t*(1-s) + n01*(1-t)*s + n11*t*s

def vf_fbm(g, f, t, S, octaves=5, freq=0.06, speed=0.2):
    val = np.zeros((g.rows, g.cols), dtype=np.float32)
    amp = 1.0; fx, fy = freq, freq*0.85
    for i in range(octaves):
        phase = t * speed * (1 + i * 0.3)
        val += _value_noise_2d(g.cc*fx + phase + i*17.3, g.rr*fy - phase*0.6 + i*31.7) * amp
        amp *= 0.5; fx *= 2.0; fy *= 2.0
    return np.clip(val * 0.8, 0, 1)

def vf_domain_warp(g, f, t, S, warp_strength=15.0, freq=0.06):
    wx = _value_noise_2d(g.cc*freq*1.3 + t*0.2, g.rr*freq + 7.1)
    wy = _value_noise_2d(g.cc*freq + t*0.14 + 3.2, g.rr*freq*1.1 - 11.8)
    wx = (wx - 0.5) * warp_strength
    wy = (wy - 0.5) * warp_strength
    return np.clip(_value_noise_2d(g.cc*freq*0.8 + wx + t*0.1, g.rr*freq*0.7 + wy - t*0.06), 0, 1)

# ============================================================================
# HUE FIELDS
# ============================================================================
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

# ============================================================================
# SHADERS
# ============================================================================
def sh_bloom(c, thr=120):
    sm = c[::4, ::4].astype(np.float32)
    br = np.where(sm > thr, sm, 0)
    for _ in range(3):
        p = np.pad(br, ((1,1),(1,1),(0,0)), mode="edge")
        br = (p[:-2,:-2]+p[:-2,1:-1]+p[:-2,2:]+p[1:-1,:-2]+p[1:-1,1:-1]+p[1:-1,2:]+p[2:,:-2]+p[2:,1:-1]+p[2:,2:]) / 9.0
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

def sh_scanlines(c, intensity=0.08, spacing=3):
    m = np.ones(c.shape[0], dtype=np.float32)
    m[::spacing] = 1.0 - intensity
    return np.clip(c * m[:, None, None], 0, 255).astype(np.uint8)

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

def sh_glitch_bands(c, intensity=0.3):
    n = int(3 + intensity * 10)
    out = c.copy()
    for _ in range(n):
        y = random.randint(0, c.shape[0]-1)
        h = random.randint(1, 4)
        shift = int((random.random()-0.5) * 40 * intensity)
        if shift != 0 and y+h < c.shape[0]:
            out[y:y+h] = np.roll(out[y:y+h], shift, axis=1)
    return out

def sh_color_grade(c, tint):
    o = c.astype(np.float32)
    o[:,:,0] *= tint[0]; o[:,:,1] *= tint[1]; o[:,:,2] *= tint[2]
    return np.clip(o, 0, 255).astype(np.uint8)

def sh_crt(c, strength=0.05):
    h, w = c.shape[:2]; cy, cx = h/2, w/2
    Y = np.arange(h, dtype=np.float32)[:, None]
    X = np.arange(w, dtype=np.float32)[None, :]
    ny = (Y - cy) / cy; nx = (X - cx) / cx
    r2 = nx**2 + ny**2
    factor = 1 + strength * r2
    sx = np.clip((nx * factor * cx + cx), 0, w-1).astype(np.int32)
    sy = np.clip((ny * factor * cy + cy), 0, h-1).astype(np.int32)
    return c[sy, sx]

# ============================================================================
# FEEDBACK
# ============================================================================
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
            if m > 0 and n > 0:
                cropped = self.buf[m:-m or None, n:-n or None]
                from PIL import Image as _I
                self.buf = np.array(_I.fromarray(
                    np.clip(cropped*255,0,255).astype(np.uint8)
                ).resize((w, h), _I.NEAREST)).astype(np.float32) / 255.0
        result = blend_canvas(canvas, np.clip(self.buf*255,0,255).astype(np.uint8), blend, opacity)
        self.buf = result.astype(np.float32) / 255.0
        return result

# ============================================================================
# SHADER CHAIN
# ============================================================================
class ShaderChain:
    def __init__(self):
        self.steps = []
    def add(self, name, **kwargs):
        self.steps.append((name, kwargs)); return self
    def apply(self, canvas, f=None, t=0):
        for name, kw in self.steps:
            if name == "bloom":       canvas = sh_bloom(canvas, kw.get("thr", 120))
            elif name == "vignette":  canvas = sh_vignette(canvas, kw.get("s", 0.22))
            elif name == "grain":     canvas = sh_grain(canvas, int(kw.get("amt", 10)))
            elif name == "scanlines": canvas = sh_scanlines(canvas, kw.get("intensity", 0.08), kw.get("spacing", 3))
            elif name == "chromatic": canvas = sh_chromatic(canvas, kw.get("amt", 3))
            elif name == "kaleidoscope": canvas = sh_kaleidoscope(canvas.copy(), kw.get("folds", 6))
            elif name == "glitch_bands": canvas = sh_glitch_bands(canvas, kw.get("intensity", 0.3))
            elif name == "color_grade": canvas = sh_color_grade(canvas, kw.get("tint", (1,1,1)))
            elif name == "crt":       canvas = sh_crt(canvas, kw.get("strength", 0.05))
        return canvas

# ============================================================================
# SYNTHETIC FEATURES (no audio source)
# ============================================================================
def synth_features(t):
    """Synthesize audio-like features from time for generative mode."""
    f = {}
    f["rms"] = 0.3 + 0.15 * np.sin(t * 0.5) + 0.1 * np.sin(t * 2.3)
    f["bass"] = 0.3 + 0.2 * np.sin(t * 0.3) ** 2
    f["mid"] = 0.3 + 0.15 * np.sin(t * 1.2)
    f["hi"] = 0.3 + 0.1 * np.sin(t * 3.1)
    f["beat"] = 1.0 if (t * 2) % 1 < 0.05 else 0.0
    f["bdecay"] = max(0, np.sin(t * 2) * 0.5 + 0.3 * np.exp(-((t % 0.5) * 10)))
    f["sub_r"] = 0.3 + 0.1 * np.sin(t * 0.7)
    f["cent"] = 0.5 + 0.2 * np.sin(t * 0.4)
    return f

# ============================================================================
# SCENE FUNCTIONS (module-level for pickling)
# ============================================================================

def fx_void_emergence(r, f, t, S):
    """Scene 1: Emergence from void — dark plasma slowly brightening."""
    g = r["md"]
    progress = min(t / 5.0, 1.0)
    bright = 0.1 + progress * 0.7
    val = vf_plasma(g, f, t, S) * bright
    h = (0.6 + g.dist_n * 0.15 + t * 0.02) % 1.0
    h = np.broadcast_to(h, (g.rows, g.cols)).copy()
    mask = val > 0.03
    ch = val2char(val, mask, PAL_HERMES)
    R, G, B = hsv2rgb(h, np.full_like(val, 0.6), val)
    co = mkc(R, G, B, g.rows, g.cols)
    return g.render(ch, co)

def fx_matrix_breach(r, f, t, S):
    """Scene 2: Matrix rain — katakana data stream, green terminal."""
    g = r["md"]
    rows, cols = g.rows, g.cols
    pal = PAL_KATA
    if "ry" not in S or len(S["ry"]) != cols:
        S["ry"] = np.random.uniform(-rows, 0, cols).astype(np.float32)
        S["rsp"] = np.random.uniform(0.5, 2.5, cols).astype(np.float32)
        S["rln"] = np.random.randint(8, 35, cols)
        S["rch"] = np.random.randint(1, len(pal), (rows, cols))
    speed = 0.8 + f.get("bass", 0.3) * 3
    S["ry"] += S["rsp"] * speed
    rst = (S["ry"] - S["rln"]) > rows
    S["ry"][rst] = np.random.uniform(-30, -2, rst.sum())
    ch = np.full((rows, cols), " ", dtype="U1")
    co = np.zeros((rows, cols, 3), dtype=np.uint8)
    heads = S["ry"].astype(int)
    for c in range(cols):
        head = heads[c]
        trail_len = S["rln"][c]
        for i in range(trail_len):
            row = head - i
            if 0 <= row < rows:
                fade = 1.0 - i / trail_len
                ci = S["rch"][row, c] % len(pal)
                ch[row, c] = pal[ci]
                if i == 0:
                    v = int(min(255, fade * 300))
                    co[row, c] = (int(v*0.7), v, int(v*0.7))
                else:
                    v = int(fade * 200)
                    co[row, c] = (int(v*0.05), v, int(v*0.2))
    canvas_a = g.render(ch, co)
    # Overlay: interference on sm grid
    g2 = r["sm"]
    canvas_b = _render_vf(g2, lambda g,f,t,S: vf_interference(g,f,t,S)*0.3,
                          hf_fixed(0.33), PAL_CIRCUIT, f, t, S, sat=0.4, threshold=0.05)
    return blend_canvas(canvas_a, canvas_b, "screen", 0.5)

def fx_network_attack(r, f, t, S):
    """Scene 3: Glitch attack — interference + glitch + data corruption."""
    g = r["md"]
    g2 = r["sm"]
    canvas_a = _render_vf(g, lambda g,f,t,S: vf_interference(g,f,t,S,6)*1.2,
                          hf_angle(0.0), PAL_CIRCUIT, f, t, S, sat=0.85, threshold=0.05)
    canvas_b = _render_vf(g2, lambda g,f,t,S: vf_domain_warp(g,f,t,S, warp_strength=20)*1.3,
                          hf_time_cycle(0.12), PAL_BRAILLE, f, t, S, sat=0.7, threshold=0.04)
    result = blend_canvas(canvas_a, canvas_b, "screen", 0.7)
    # Glitch overlay
    if f.get("beat", 0) > 0.5:
        result = sh_glitch_bands(result, 0.5)
    return result

def fx_cosmic_vortex(r, f, t, S):
    """Scene 4: Cosmic vortex — spiral + vortex, deep space colors."""
    g = r["md"]
    g2 = r["sm"]
    canvas_a = _render_vf(g, lambda g,f,t,S: vf_spiral(g,f,t,S, n_arms=4, tightness=3.0)*1.2,
                          hf_angle(0.6), PAL_STARS, f, t, S, sat=0.8, threshold=0.04)
    canvas_b = _render_vf(g2, lambda g,f,t,S: vf_vortex(g,f,t,S, twist=5.0)*0.8,
                          hf_time_cycle(0.06), PAL_GREEK, f, t, S, sat=0.6, threshold=0.05)
    result = blend_canvas(canvas_a, canvas_b, "screen", 0.6)
    return result

def fx_cathedral(r, f, t, S):
    """Scene 5: Cathedral climax — three-grid kaleidoscopic explosion."""
    g = r["md"]
    g2 = r["sm"]
    g3 = r["lg"]
    canvas_a = _render_vf(g2, lambda g,f,t,S: vf_interference(g,f,t,S,7)*1.3,
                          hf_angle(0.0), PAL_RUNE, f, t, S, sat=0.8, threshold=0.04)
    canvas_b = _render_vf(g, lambda g,f,t,S: vf_rings(g,f,t,S, n_base=10, spacing=3)*1.4,
                          hf_distance(0.3, 0.02), PAL_STARS, f, t, S, sat=0.9, threshold=0.03)
    canvas_c = _render_vf(g3, lambda g,f,t,S: vf_plasma(g,f,t,S)*0.8,
                          hf_time_cycle(0.1), PAL_BLOCKS, f, t, S, sat=0.7, threshold=0.05)
    result = blend_canvas(canvas_a, canvas_b, "screen", 0.8)
    result = blend_canvas(result, canvas_c, "difference", 0.4)
    if f.get("bdecay", 0) > 0.3:
        result = sh_kaleidoscope(result.copy(), folds=6)
    return result

def fx_organic_dissolution(r, f, t, S):
    """Scene 6: Organic dissolution — domain warp, fading to void."""
    g = r["sm"]
    progress = min(t / 4.0, 1.0)
    bright = max(0.1, 1.0 - progress * 0.7)
    canvas = _render_vf(g, lambda g,f,t,S: vf_domain_warp(g,f,t,S, warp_strength=25)*bright,
                        hf_distance(0.55, 0.02), PAL_DOTS, f, t, S, sat=0.5, threshold=0.04)
    # Faint vortex underneath
    g2 = r["md"]
    canvas_b = _render_vf(g2, lambda g,f,t,S: vf_vortex(g,f,t,S, twist=8.0)*0.2*bright,
                          hf_fixed(0.7), PAL_GREEK, f, t, S, sat=0.3, threshold=0.06)
    return blend_canvas(canvas_b, canvas, "screen", 0.6)

# ============================================================================
# SCENE TABLE
# ============================================================================
SCENES = [
    {"start": 0.0,  "end": 4.0,  "name": "void",       "fx": fx_void_emergence,
     "grid": "md", "gamma": 0.65,
     "shaders": [("bloom", {"thr": 100}), ("vignette", {"s": 0.3})],
     "feedback": {"decay": 0.8, "blend": "screen", "opacity": 0.2,
                  "transform": "zoom", "transform_amt": 0.008}},

    {"start": 4.0,  "end": 9.0,  "name": "matrix",      "fx": fx_matrix_breach,
     "grid": "md", "gamma": 0.70,
     "shaders": [("crt", {"strength": 0.04}), ("scanlines", {"intensity": 0.1}),
                 ("bloom", {"thr": 110}), ("grain", {"amt": 6})],
     "feedback": {"decay": 0.7, "blend": "screen", "opacity": 0.15}},

    {"start": 9.0,  "end": 13.0, "name": "attack",      "fx": fx_network_attack,
     "grid": "md", "gamma": 0.60,
     "shaders": [("chromatic", {"amt": 5}), ("glitch_bands", {"intensity": 0.4}),
                 ("bloom", {"thr": 90}), ("grain", {"amt": 12})],
     "feedback": {"decay": 0.6, "blend": "add", "opacity": 0.2,
                  "transform": "zoom", "transform_amt": 0.02}},

    {"start": 13.0, "end": 16.5, "name": "cosmic",      "fx": fx_cosmic_vortex,
     "grid": "md", "gamma": 0.70,
     "shaders": [("bloom", {"thr": 100}), ("chromatic", {"amt": 3}),
                 ("vignette", {"s": 0.2}), ("grain", {"amt": 6})],
     "feedback": {"decay": 0.75, "blend": "screen", "opacity": 0.3,
                  "transform": "zoom", "transform_amt": 0.012, "hue_shift": 0.015}},

    {"start": 16.5, "end": 19.0, "name": "cathedral",  "fx": fx_cathedral,
     "grid": "sm", "gamma": 0.60,
     "shaders": [("bloom", {"thr": 90}), ("chromatic", {"amt": 4}),
                 ("kaleidoscope", {"folds": 6}), ("grain", {"amt": 8})],
     "feedback": {"decay": 0.7, "blend": "screen", "opacity": 0.35,
                  "transform": "zoom", "transform_amt": 0.015, "hue_shift": 0.02}},

    {"start": 19.0, "end": 20.0, "name": "dissolve",   "fx": fx_organic_dissolution,
     "grid": "sm", "gamma": 0.75,
     "shaders": [("bloom", {"thr": 120}), ("vignette", {"s": 0.35})],
     "feedback": None},
]

# ============================================================================
# RENDER
# ============================================================================
def get_scene_at(t):
    scene = SCENES[0]
    for s in SCENES:
        if t >= s["start"]:
            scene = s
    return scene

def render_segment(seg_idx, frame_start, frame_end, scene_dict):
    """Render a segment of frames to a clip file."""
    # Initialize grids for this process
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
    for sn, kw in scene_dict.get("shaders", []):
        chain.add(sn, **kw)

    fx_fn = scene_dict["fx"]
    gamma = scene_dict.get("gamma", 0.72)
    fb_cfg = scene_dict.get("feedback", None)

    for fi in range(frame_start, frame_end):
        t = fi / FPS
        f = synth_features(t)
        canvas = fx_fn(grids, f, t - scene_dict["start"], S)
        canvas = tonemap(canvas, gamma=gamma)
        if fb and fb_cfg:
            canvas = fb.apply(canvas, **fb_cfg)
        canvas = chain.apply(canvas, f=f, t=t)
        pipe.stdin.write(canvas.tobytes())

    pipe.stdin.close()
    pipe.wait()
    stderr_fh.close()
    return clip_path

def main():
    print(f"EVEZ-OS // ASCII VIDEO — GENERATIVE SURVEILLANCE STATE")
    print(f"Resolution: {VW}x{VH} @ {FPS}fps | Duration: {DURATION}s | Frames: {N_FRAMES}")
    print(f"Workers: {N_WORKERS} | Scenes: {len(SCENES)}")

    # Split frames across workers
    frames_per_worker = N_FRAMES // N_WORKERS
    segments = []
    for i in range(N_WORKERS):
        fs = i * frames_per_worker
        fe = (i + 1) * frames_per_worker if i < N_WORKERS - 1 else N_FRAMES
        if fs >= fe:
            continue
        # Find the scene for this segment's midpoint
        mid_t = (fs + fe) / 2 / FPS
        scene = get_scene_at(mid_t)
        segments.append((i, fs, fe, scene))

    t0 = _time.time()
    print(f"\nRendering {len(segments)} segments in parallel...")

    with ProcessPoolExecutor(max_workers=N_WORKERS) as pool:
        futures = {
            pool.submit(render_segment, idx, fs, fe, scene): idx
            for idx, fs, fe, scene in segments
        }
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                path = fut.result()
                print(f"  ✓ Segment {idx} → {path}")
            except Exception as e:
                print(f"  ✗ Segment {idx} FAILED: {e}")

    elapsed = _time.time() - t0
    print(f"\nRender complete: {elapsed:.1f}s")

    # Concatenate clips
    print("Concatenating clips...")
    concat_path = os.path.join(OUT_DIR, "concat.txt")
    with open(concat_path, "w") as cf:
        for idx, fs, fe, scene in sorted(segments, key=lambda x: x[0]):
            clip = os.path.join(OUT_DIR, f"clip_{idx:02d}.mp4")
            if os.path.exists(clip):
                cf.write(f"file '{clip}'\n")

    output_path = os.path.join(OUT_DIR, "evez_ascii_video.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", output_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    print(f"\n✓ Output: {output_path}")
    print(f"  Size: {os.path.getsize(output_path) / 1024:.0f}KB")
    print(f"  Total render time: {elapsed:.1f}s")

if __name__ == "__main__":
    main()
