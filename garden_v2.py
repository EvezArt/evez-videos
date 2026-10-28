#!/usr/bin/env python3
"""GARDEN v2 — fast effects only, single-pass, 10s."""
import os,sys,math,subprocess
import numpy as np
from PIL import Image,ImageFont,ImageDraw
import time as _t

FONT_PATH="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
VW,VH=1280,720; FPS=24; DURATION=10.0; N_FRAMES=int(DURATION*FPS)
OUT="/opt/data/cache/scratch/ascii_garden/garden_v2.mp4"

PAL_DENSE=" .:;+=xX$#@\u2588"; PAL_BLOCKS=" \u2591\u2592\u2593\u2588\u2584\u2580"
PAL_GREEK=" \u03b1\u03b2\u03b3\u03b4\u03b5\u03b6\u03b7\u03b8\u03b9\u03ba\u03bb\u03bc\u03bd\u03be\u03c0\u03c1\u03c3\u03c4\u03c6\u03c8\u03c9"
PAL_STARS=" \u00b7\u2726\u2605\u2736\u2728\u25cf\u25a0"
PAL_DOTS=" \u22c5\u2218\u2022\u25cf\u25c9\u2742"
PAL_BRAILLE=" \u2801\u2802\u2803\u2804\u2805\u2806\u2807\u2808\u2809\u280a\u280b\u280c\u280d\u280e\u280f"
PAL_MATH=" \u00b7\u2218\u2022\u00b0\u2248\u2261\u221e\u222b\u2211\u220f\u221a\u2207\u2202\u2206\u03a9"
PAL_HERMES=" .\u00b7~=\u2248\u221e\u26a1\u2726\u2605\u2295\u25ca\u25c6\u25b2\u25bc\u25cf\u25a0"

def hsv2rgb(h,s,v):
    h=h%1.0; c=v*s; x=c*(1-np.abs((h*6)%2-1)); m2=v-c
    r=np.zeros_like(h);g=np.zeros_like(h);b=np.zeros_like(h)
    for mask,rv,gv,bv in [((h<1/6),c,x,0),((h>=1/6)&(h<2/6),x,c,0),((h>=2/6)&(h<3/6),0,c,x),((h>=3/6)&(h<4/6),0,x,c),((h>=4/6)&(h<5/6),x,0,c),(h>=5/6,c,0,x)]:
        if hasattr(rv,'__len__'): r[mask]=rv[mask]
        else: r[mask]=rv
        if hasattr(gv,'__len__'): g[mask]=gv[mask]
        else: g[mask]=gv
        if hasattr(bv,'__len__'): b[mask]=bv[mask]
        else: b[mask]=bv
    return np.clip((r+m2)*255,0,255).astype(np.uint8),np.clip((g+m2)*255,0,255).astype(np.uint8),np.clip((b+m2)*255,0,255).astype(np.uint8)

def mkc(R,G,B,rows,cols):
    o=np.zeros((rows,cols,3),dtype=np.uint8);o[:,:,0]=R;o[:,:,1]=G;o[:,:,2]=B;return o

def val2char(v,mask,pal):
    n=len(pal);idx=np.clip((v*n).astype(int),0,n-1)
    out=np.full(v.shape," ",dtype="U1")
    for i,ch in enumerate(pal): out[mask&(idx==i)]=ch
    return out

def tonemap(c,gamma=0.72):
    f=c.astype(np.float32);sub=f[::4,::4]
    lo=np.percentile(sub,1);hi=np.percentile(sub,99.5)
    if hi-lo<10: hi=lo+10
    f=np.clip((f-lo)/(hi-lo),0,1);np.power(f,gamma,out=f)
    return (f*255).astype(np.uint8)

def blend_canvas(base,top,mode="screen",opacity=1.0):
    af=base.astype(np.float32)/255.0;bf=top.astype(np.float32)/255.0
    if mode=="screen": r=1-(1-af)*(1-bf)
    elif mode=="add": r=np.clip(af+bf,0,1)
    elif mode=="difference": r=np.abs(af-bf)
    elif mode=="exclusion": r=af+bf-2*af*bf
    else: r=bf
    if opacity<1.0: r=af*(1-opacity)+r*opacity
    return np.clip(r*255,0,255).astype(np.uint8)

def _vn2d(x,y):
    ix=np.floor(x).astype(np.int64);iy=np.floor(y).astype(np.int64)
    def h(a,b): n=((a*374761393+b*668265263)^((a*374761393+b*668265263)>>13))*1274126177;return ((n^(n>>16))&0x7fffffff).astype(np.float32)/0x7fffffff
    n00=h(ix,iy);n10=h(ix+1,iy);n01=h(ix,iy+1);n11=h(ix+1,iy+1)
    t=np.clip(x-ix,0,1);s=np.clip(y-iy,0,1);t=t*t*(3-2*t);s=s*s*(3-2*s)
    return n00*(1-t)*(1-s)+n10*t*(1-s)+n01*(1-t)*s+n11*t*s

class Grid:
    def __init__(self,fs):
        self.font=ImageFont.truetype(FONT_PATH,fs)
        a,d=self.font.getmetrics();bb=self.font.getbbox("M")
        self.cw=bb[2]-bb[0];self.ch=a+d
        self.cols=VW//self.cw;self.rows=VH//self.ch
        self.ox=(VW-self.cols*self.cw)//2;self.oy=(VH-self.rows*self.ch)//2
        cx,cy=self.cols/2.0,self.rows/2.0;asp=self.cw/self.ch
        self.rr=np.arange(self.rows,dtype=np.float32)[:,None]
        self.cc=np.arange(self.cols,dtype=np.float32)[None,:]
        self.dist=np.sqrt((self.cc-cx)**2+((self.rr-cy)*asp)**2)
        self.angle=np.arctan2((self.rr-cy)*asp,self.cc-cx)
        self.dist_n=np.sqrt(((self.cc-cx)/self.cols)**2+(((self.rr-cy)*asp)/self.rows)**2)
        all_c=set()
        for p in [PAL_DENSE,PAL_BLOCKS,PAL_GREEK,PAL_STARS,PAL_DOTS,PAL_BRAILLE,PAL_MATH,PAL_HERMES]: all_c.update(p)
        all_c.discard(" ")
        self.bm={}
        for ch in all_c:
            img=Image.new("L",(self.cw,self.ch),0);ImageDraw.Draw(img).text((0,0),ch,fill=255,font=self.font)
            self.bm[ch]=np.array(img,dtype=np.float32)/255.0
    def render(self,chars,colors,canvas=None):
        if canvas is None: canvas=np.zeros((VH,VW,3),dtype=np.uint8)
        for row in range(self.rows):
            y=self.oy+row*self.ch
            if y+self.ch>VH: break
            for col in range(self.cols):
                c=chars[row,col]
                if c==" ": continue
                x=self.ox+col*self.cw
                if x+self.cw>VW: break
                if c not in self.bm: continue
                a=self.bm[c];cv=(a[:,:,None]*colors[row,col]).astype(np.uint8)
                canvas[y:y+self.ch,x:x+self.cw]=np.maximum(canvas[y:y+self.ch,x:x+self.cw],cv)
        return canvas

def rvf(g,val_fn,hue_fn,pal,t,sat=0.8,thr=0.03):
    val=np.clip(val_fn(g,t),0,1);mask=val>thr
    ch=val2char(val,mask,pal)
    if callable(hue_fn): h=hue_fn(g,t)%1.0
    else: h=np.full((g.rows,g.cols),float(hue_fn),dtype=np.float32)
    h=np.broadcast_to(h,(g.rows,g.cols)).copy()
    R,G,B=hsv2rgb(h,np.full_like(val,sat),val)
    return g.render(ch,mkc(R,G,B,g.rows,g.cols))

# Value fields — all fast vectorized NumPy
def vf_plasma(g,t):
    v=np.sin(g.cc*0.03+t*0.7)*0.5;v=v+np.sin(g.rr*0.04-t*0.5)*0.4
    v=v+np.sin((g.cc*0.02+g.rr*0.03)+t*0.3)*0.3;v=v+np.sin(g.dist_n*4-t*0.8)*0.3
    return np.clip(v*0.5+0.5,0,1)
def vf_fbm(g,t,oct=5,freq=0.06,sp=0.2):
    val=np.zeros((g.rows,g.cols),dtype=np.float32);amp=1.0;fx,fy=freq,freq*0.85
    for i in range(oct):
        ph=t*sp*(1+i*0.3);val=val+_vn2d(g.cc*fx+ph+i*17.3,g.rr*fy-ph*0.6+i*31.7)*amp
        amp*=0.5;fx*=2.0;fy*=2.0
    return np.clip(val*0.8,0,1)
def vf_dwarp(g,t,ws=15.0,freq=0.06):
    wx=_vn2d(g.cc*freq*1.3+t*0.2,g.rr*freq+7.1);wy=_vn2d(g.cc*freq+t*0.14+3.2,g.rr*freq*1.1-11.8)
    return np.clip(_vn2d(g.cc*freq*0.8+(wx-0.5)*ws+t*0.1,g.rr*freq*0.7+(wy-0.5)*ws-t*0.06),0,1)
def vf_rings(g,t,n=6,sp=4):
    val=np.zeros((g.rows,g.cols),dtype=np.float32)
    for ri in range(n):
        rad=(ri+1)*sp+t*8;rd=np.abs(g.dist-rad)
        val=np.maximum(val,np.clip((1-rd/(1+t*3)),0,1))
    return val
def vf_spiral(g,t,arms=3,tight=2.5):
    val=np.zeros((g.rows,g.cols),dtype=np.float32)
    for ai in range(arms):
        off=ai*2*np.pi/arms;lr=np.log(g.dist+1)*tight
        ap=g.angle+off-lr+t*0.8;av=np.clip(np.cos(ap*arms)*0.6+0.2,0,1)
        val=np.maximum(val,av*np.clip(1-g.dist_n*0.4,0.15,1))
    return val
def vf_vortex(g,t,twist=3.0):
    tw=g.angle+g.dist_n*twist*np.sin(t*0.5);return np.clip(np.sin(tw*4-t*2)*0.5+0.5,0,1)
def vf_interference(g,t,nw=6):
    val=np.zeros((g.rows,g.cols),dtype=np.float32)
    for i in range(nw):
        a=i*np.pi/nw;f=0.06+i*0.03;sp=0.5+i*0.3
        proj=g.cc*np.cos(a)+g.rr*np.sin(a);val=val+np.sin(proj*f+t*sp)*0.25
    return np.clip(val*0.5+0.5,0,1)

# Hue fields
def hf_ang(off=0.0):
    def fn(g,t): return (g.angle/(2*np.pi)+off+t*0.05)%1.0
    return fn
def hf_tc(speed=0.1):
    def fn(g,t): return np.full((g.rows,g.cols),(t*speed)%1.0,dtype=np.float32)
    return fn
def hf_dist(base=0.5,scale=0.02):
    def fn(g,t): return (base+g.dist*scale+t*0.03)%1.0
    return fn
def hf_fix(hue):
    def fn(g,t): return np.full((g.rows,g.cols),hue,dtype=np.float32)
    return fn
def hf_jewel(t_off=0.0):
    jewels=[0.33,0.58,0.78,0.12]
    def fn(g,t):
        idx=int((t+t_off)*0.15)%4;nidx=(idx+1)%4
        frac=((t+t_off)*0.15)%1.0;h1,h2=jewels[idx],jewels[nidx]
        dh=h2-h1
        if abs(dh)>0.5: dh=dh-np.sign(dh)
        return (h1+dh*frac+g.dist_n*0.03)%1.0
    return fn

# Shaders
def sh_bloom(c,thr=120):
    sm=c[::4,::4].astype(np.float32);br=np.where(sm>thr,sm,0)
    for _ in range(3):
        p=np.pad(br,((1,1),(1,1),(0,0)),mode="edge")
        br=(p[:-2,:-2]+p[:-2,1:-1]+p[:-2,2:]+p[1:-1,:-2]+p[1:-1,1:-1]+p[1:-1,2:]+p[2:,:-2]+p[2:,1:-1]+p[2:,2:])/9.0
    bl=np.repeat(np.repeat(br,4,0),4,1)[:c.shape[0],:c.shape[1]]
    return np.clip(c.astype(np.float32)+bl*0.4,0,255).astype(np.uint8)
def sh_vig(c,s=0.22):
    h,w=c.shape[:2];Y=np.linspace(-1,1,h)[:,None];X=np.linspace(-1,1,w)[None,:]
    m=np.clip(1.0-np.sqrt(X**2+Y**2)*s,0.15,1).astype(np.float32)
    return np.clip(c*m[:,:,None],0,255).astype(np.uint8)
def sh_grain(c,amt=8):
    n=np.random.randint(-amt,amt+1,(c.shape[0]//2,c.shape[1]//2,1),dtype=np.int16)
    n=np.repeat(np.repeat(n,2,0),2,1)[:c.shape[0],:c.shape[1]]
    return np.clip(c.astype(np.int16)+n,0,255).astype(np.uint8)
def sh_chrom(c,amt=3):
    if amt<1: return c
    a=int(amt);o=c.copy();o[:,a:,0]=c[:,:-a,0];o[:,:-a,2]=c[:,a:,2];return o
def sh_kaleidoscope(c,folds=6):
    h,w=c.shape[:2];cy,cx=h//2,w//2
    Y=np.arange(h,dtype=np.float32)[:,None]-cy;X=np.arange(w,dtype=np.float32)[None,:]-cx
    ang=np.arctan2(Y,X);dist=np.sqrt(X**2+Y**2);wedge=2*np.pi/folds
    folded=np.abs((ang%wedge)-wedge/2)
    ny=np.clip((cy+dist*np.sin(folded)).astype(int),0,h-1)
    nx=np.clip((cx+dist*np.cos(folded)).astype(int),0,w-1)
    return c[ny,nx]
def sh_soft_focus(c,strength=0.2):
    sm=c[::2,::2].astype(np.float32);p=np.pad(sm,((1,1),(1,1),(0,0)),mode="edge")
    bl=(p[:-2,:-2]+p[:-2,1:-1]+p[:-2,2:]+p[1:-1,:-2]+p[1:-1,1:-1]+p[1:-1,2:]+p[2:,:-2]+p[2:,1:-1]+p[2:,2:])/9.0
    bl=np.repeat(np.repeat(bl,2,0),2,1)[:c.shape[0],:c.shape[1]]
    return np.clip(c*(1-strength)+bl*strength,0,255).astype(np.uint8)

class FB:
    def __init__(self): self.buf=None
    def apply(self,c,decay=0.8,blend="screen",op=0.4,tf="zoom",ta=0.015,hs=0.0):
        if self.buf is None: self.buf=c.astype(np.float32)/255.0;return c
        self.buf*=decay
        if tf=="zoom":
            h,w=self.buf.shape[:2];m=max(1,int(h*ta));n=max(1,int(w*ta))
            cr=self.buf[m:-m or None,n:-n or None]
            self.buf=np.array(Image.fromarray(np.clip(cr*255,0,255).astype(np.uint8)).resize((w,h),Image.NEAREST)).astype(np.float32)/255.0
        c=blend_canvas(c,np.clip(self.buf*255,0,255).astype(np.uint8),blend,op)
        self.buf=c.astype(np.float32)/255.0;return c

class SC:
    def __init__(self): self.s=[]
    def add(self,n,**kw): self.s.append((n,kw));return self
    def apply(self,c,t=0):
        for n,kw in self.s:
            if n=="bloom": c=sh_bloom(c,kw.get("thr",120))
            elif n=="vignette": c=sh_vig(c,kw.get("s",0.22))
            elif n=="grain": c=sh_grain(c,int(kw.get("amt",8)))
            elif n=="chromatic": c=sh_chrom(c,kw.get("amt",3))
            elif n=="kaleidoscope": c=sh_kaleidoscope(c.copy(),kw.get("folds",6))
            elif n=="soft_focus": c=sh_soft_focus(c,kw.get("strength",0.2))
        return c

# Scene table
SCENES=[
    (0.0,2.5,0.60,[("bloom",{"thr":90}),("chromatic",{"amt":3}),("vignette",{"s":0.25}),("grain",{"amt":6})],
     {"decay":0.75,"blend":"screen","op":0.35,"ta":0.012,"hs":0.02}),
    (2.5,5.0,0.65,[("bloom",{"thr":100}),("soft_focus",{"strength":0.2}),("vignette",{"s":0.2})],
     {"decay":0.8,"blend":"screen","op":0.2,"ta":0.008}),
    (5.0,7.5,0.68,[("bloom",{"thr":100}),("chromatic",{"amt":2}),("vignette",{"s":0.2}),("grain",{"amt":5})],
     {"decay":0.7,"blend":"screen","op":0.3,"ta":0.01,"hs":0.015}),
    (7.5,10.0,0.75,[("bloom",{"thr":120}),("soft_focus",{"strength":0.25}),("vignette",{"s":0.3})],
     None),
]

def scene_at(t):
    g_md=grids["md"];g_sm=grids["sm"]
    if t<2.5:  # Interference kaleidoscope
        ca=rvf(g_md,lambda g,t: vf_interference(g,t,7)*1.2,hf_jewel(0.0),PAL_MATH,t,sat=0.85,thr=0.04)
        cb=rvf(g_sm,lambda g,t: vf_dwarp(g,t,18)*0.25,hf_fix(0.58),PAL_DOTS,t,sat=0.4,thr=0.05)
        r=blend_canvas(cb,ca,"screen",0.9)
        if t>1.0: r=sh_kaleidoscope(r.copy(),folds=8)
        return r
    elif t<5.0:  # fBM organic
        ca=rvf(g_sm,lambda g,t: vf_fbm(g,t,4,0.05,0.1)*1.1,hf_dist(0.33,0.02),PAL_DOTS,t,sat=0.7,thr=0.04)
        cb=rvf(g_md,lambda g,t: vf_dwarp(g,t,12)*0.3,hf_fix(0.33),PAL_GREEK,t,sat=0.5,thr=0.05)
        return blend_canvas(cb,ca,"screen",0.8)
    elif t<7.5:  # Domain warp + spiral
        ca=rvf(g_md,lambda g,t: vf_dwarp(g,t,22)*1.1,hf_jewel(2.0),PAL_GREEK,t,sat=0.75,thr=0.04)
        cb=rvf(g_sm,lambda g,t: vf_fbm(g,t,5,0.04,0.15)*0.5,hf_dist(0.58,0.02),PAL_BRAILLE,t,sat=0.5,thr=0.05)
        return blend_canvas(ca,cb,"screen",0.6)
    else:  # Resolution — calm noise
        g=g_md
        val=_vn2d(g.cc*0.35+(t-7.5)*0.15,g.rr*0.30+(t-7.5)*0.12)
        val2=_vn2d(g.cc*0.70+(t-7.5)*0.08+50,g.rr*0.65+(t-7.5)*0.06+70)
        val=np.clip(val*0.5+val2*0.3,0,1)*0.35
        h=np.full((g.rows,g.cols),0.12,dtype=np.float32);mask=val>0.02
        ch=val2char(val,mask,PAL_HERMES);R,G,B=hsv2rgb(h,np.full_like(val,0.35),val)
        return g.render(ch,mkc(R,G,B,g.rows,g.cols))

def get_cfg(t):
    for s,e,g,sh,fb in SCENES:
        if s<=t<e: return g,sh,fb
    return SCENES[-1][2],SCENES[-1][3],SCENES[-1][4]

# Init
g_md=Grid(16);g_sm=Grid(10)
grids={"md":g_md,"sm":g_sm}
fb_buf=FB()

print(f"GARDEN v2 — {VW}x{VH} @ {FPS}fps | {DURATION}s | {N_FRAMES} frames")
cmd=["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{VW}x{VH}","-r",str(FPS),"-i","pipe:0","-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p",OUT]
log_fh=open(OUT.replace(".mp4",".log"),"w")
pipe=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log_fh)
t0=_t.time()
for fi in range(N_FRAMES):
    t=fi/FPS
    canvas=scene_at(t)
    gamma,shaders,fb_cfg=get_cfg(t)
    canvas=tonemap(canvas,gamma=gamma)
    if fb_cfg: canvas=fb_buf.apply(canvas,**fb_cfg)
    chain=SC()
    for sn,kw in shaders: chain.add(sn,**kw)
    canvas=chain.apply(canvas,t=t)
    pipe.stdin.write(canvas.tobytes())
pipe.stdin.close();pipe.wait();log_fh.close()
el=_t.time()-t0
print(f"\n✓ {OUT} | {os.path.getsize(OUT)/1024:.0f}KB | {el:.1f}s")
