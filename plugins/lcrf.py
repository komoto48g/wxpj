#! python3
# -*- coding: utf-8 -*-
import wx
import cv2
import numpy as np
from numpy import pi,cos,sin
from scipy import optimize
from scipy import signal
from matplotlib import patches
from jgdk import Layer, LParam
import editor as edi


def linpolar(src, r0, r1, center=None):
    """Linear-Polar transform
    The area radii [r0:r1] mapsto the same size of src image
    
    cf. cv2.linearPolar(src, (xc, yc), R, cv2.INTER_CUBIC)
    """
    h, w = src.shape
    if center is None:
        xc, yc = w//2, h//2
    else:
        xc, yc = center
    
    x = np.arange(w, dtype=np.float32) /w
    y = np.arange(h, dtype=np.float32) * 2*pi /h
    xx, yy = np.meshgrid(x, y)
    
    r = r0 + (r1 - r0) * xx
    map_x = xc + r * np.cos(yy)
    map_y = yc + r * np.sin(yy)
    dst = cv2.remap(src.astype(np.float32), map_x, map_y, cv2.INTER_CUBIC)
    return dst


class Model(object):
    """Cor-fitting model function
    """
    def __init__(self, x, y):
        params = [0.,] * 5
        x = np.array(x)
        y = np.array(y)
        result = optimize.leastsq(self.residual, params, args=(x,y))
        self.params = result[0]
    
    def __call__(self, x):
        a,b,c,d,e = self.params
        return a + b * cos(x-c) + d * cos(2*x-e)
    
    def residual(self, params, x, y):
        self.params = params
        res = (self(x) - y)**2
        print("\b"*72 + "point({}): residual {:g}".format(len(res), sum(res)), end=' ')
        return res
    
    def mod2d(self, buf):
        """Calculate modulated image
        buf : polar-transformed output buffer
      retval -> 2D-array of modulated image
        """
        h, w = buf.shape
        shift = [self(x) for x in np.arange(0,h)/h * 2*pi][::-1] # shift vector
        ## axis = np.arange(0., w)
        data = np.resize(0., (h, w))
        for j,(x,v) in enumerate(zip(buf, shift)):
            data[j] = np.roll(x, -int(v))
            ## data[j] = np.interp(axis+v, axis, x)
        return data
    
    def mod1d(self, buf):
        """Calculate line profile averaged with modulation correction
        buf : polar-transformed output buffer
      retval -> 1D-array of modulated (+avr.) line profile
        """
        h, w = buf.shape
        data = sum(self.mod2d(buf))
        return data / h


def find_ring_center(src, center, lo, hi, N=256, tol=0.01):
    """find center of ring pattern in buffer
    
    極座標変換した後，角度セグメントに分割して相互相関をとる．
    center シフトを推定するために linear-polar を使用する．
    theta = 0 を基準として，相対変位 [pixels] を計算する．
    
    src : source buffer
 center : initial value of center position [nx,ny]
  lo-hi : masking size of radial axis
      N : resizing of angular axis (total step in angle [0:2pi])
    tol : remove peaks that leap greater than N * tol
  retval ->
        dst(linear-polar-transformed image), guessed center, and fitting model
    """
    h, w = src.shape
    nx, ny = center if center is not None else (w//2, h//2)
    
    dst = cv2.linearPolar(src, (nx,ny), w, cv2.WARP_FILL_OUTLIERS)
    
    ## Mask X (radial) axis
    lo = int(max(lo, 0))
    hi = int(min(hi, w//2))
    dst[:,:lo] = 0
    dst[:,hi:] = 0
    
    ## Resize Y:angular axis (計算を軽くするためリサイズ)
    rdst = cv2.resize(dst[:,lo:hi].astype(np.float32), (hi-lo, N), interpolation=cv2.INTER_AREA)
    rdst -= rdst.mean()
    
    temp = rdst[0][::-1] # template of corr; distr at theta = 0
    data = []
    for fr in rdst:
        p = signal.fftconvolve(fr, temp, mode='same')
        data.append(p.argmax())
    
    ## 相関の計算は上から行うので，2pi --> 0 の並びのリストになる
    ##   最終的に返す計算結果は逆転させて，0 --> 2pi の並びにする
    Y = np.array(data[::-1]) - (hi-lo)/2
    X = np.arange(0, 1, 1/len(Y)) * 2*pi
    
    ## remove leaps(1): 急激な変化 (相関計算の結果のとび) を除外する
    ## if 0:
    ##     ym = np.median(Y)
    ##     ys = np.std(Y)
    ##     xy = [(x,y) for x,y in zip(X,Y) if -ys < y-ym < ys]
    ##     xx, yy = np.array(xy).T
    
    ## remove leaps(2): tol より小さいとびを許容する (画素サイズに比例)
    if 1:
        tolr = max(5, tol * w/2) # default < 0.5% までなら許しちゃる
        xx, yy = [X[0]], [Y[0]]
        for x,y in zip(X[1:], Y[1:]):
            if abs(y - yy[-1]) < tolr:
                xx.append(x)
                yy.append(y)
    
    fitting_curve = Model(xx, yy)
    
    ## edi.plot(xx, yy, '+', X, fitting_curve(X))
    
    a = fitting_curve.params[0] = 0 # :a=0 として(平均を基準とする)全体のオフセット量を評価する
    b = fitting_curve.params[1]
    c = fitting_curve.params[2] % (2*pi)
    
    ## t = c+pi if b>0 else c # 推定中心方向
    ## nx -= abs(b) * cos(t)
    ## ny += abs(b) * sin(t)
    t = c if b>0 else c+pi # tmax: 推定中心方向
    nx += abs(b) * cos(t)
    ny -= abs(b) * sin(t)
    center = (nx, ny)
    return dst, center, fitting_curve


def find_radial_peaks(data, tol=0.01):
    """Find radial peaks in Polar-converted buffer
    data : Polar-converted output buffer
    """
    w = len(data)
    lw = int(max(3, tol * w/2))
    window = signal.windows.gaussian(lw, std=lw)
    ys = np.convolve(window/window.sum(), data, mode='same')
    ## ys = data
    peaks,_attr = signal.find_peaks(ys, width=1)
    peaks = [p for p in peaks if ys[p] > ys.mean()] # filtered by threshold
    return ys, peaks


class Plugin(Layer):
    """Center of Rings finder ver 1.0
    """
    menukey = "Plugins/&Basic Tools/"
    category = "Basic Tools"
    unloadable = False
    
    lgbt = property(lambda self: self.parent.require('lgbt'))
    
    def Init(self):
        self.rmin = LParam("rmin", (0, 1, 0.01), 0.1, handler=self.set_radii)
        self.rmax = LParam("rmax", (0, 2, 0.01), 1.0, handler=self.set_radii)
        
        self.layout(self.lgbt.params, title="blur-threshold", cw=0, lw=40, tw=40, show=0)
        self.layout((self.rmin, self.rmax), title="radii", cw=0, lw=40, tw=40)
        
        btn = wx.Button(self, label="+Execute", size=(64,22))
        btn.Bind(wx.EVT_BUTTON, lambda v: self.run(shift=wx.GetKeyState(wx.WXK_SHIFT)))
        btn.SetToolTip("S-Lbutton to enter recursive centering")
        
        self.chkplt = wx.CheckBox(self, label="rdist")
        
        self.layout((btn, self.chkplt), row=2)
    
    def run(self, frame=None, shift=0, maxloop=4):
        if not frame:
            frame = self.selected_view.frame
        del self.Arts
        
        src = frame.buffer
        h, w = src.shape
        center = (w//2, h//2)
        ## center = edi.centroid(src)
        if shift:
            nx, ny = frame.xytopixel(frame.selector)
            center = nx[0], ny[0]
        
        ## Search center and fit with model (twice at least)
        lo = h/2 * self.rmin.value
        hi = h/2 * self.rmax.value
        for i in range(maxloop):
            buf, center, fitting_curve, = find_ring_center(src, center, lo, hi)
        self.fitting_curve = fitting_curve
        
        self.output.load(buf, "*lin-polar*", localunit=1)
        frame.selector = frame.xyfrompixel(center)
        
        ## Find peaks in radial distribution
        rdist = fitting_curve.mod1d(buf)
        
        ## Find radial peaks in polar-converted buffer
        ## peaks = signal.find_peaks_cwt(rdist, widths=np.arange(3,4))
        ## peaks = [p for p in peaks if rdist[p] > rdist.mean()] # filtered by threshold
        rdist, peaks = find_radial_peaks(rdist)
        
        if self.chkplt.Value: # this should be called for MainThread
            edi.clf()
            edi.plot(rdist)
            edi.plot(peaks, rdist[peaks], 'o')
        print("peaks =", peaks)
        
        ## 強度の高いところにおおざっぱ (oz) にマーカーを打つ (100/3 程度)
        j = np.argmax(rdist[peaks])
        a = np.linspace(0,1,100) * 2*pi
        nr = peaks[j] + fitting_curve(a)
        r = nr * frame.unit
        xc, yc = frame.selector # center position
        X = xc + r * np.cos(a)
        Y = yc + r * np.sin(a)
        
        l,r,b,t = frame.get_extent()
        x, y = np.array([(x,y) for x,y in zip(X,Y) if l<x<r and b<y<t]).T
        z = frame.xytoc(x, y)
        oz = (z > 2 * rdist.mean())
        frame.markers = (x[oz][0:-1:3], y[oz][0:-1:3]) # scatter markers onto the arc
        
        ## サークル描画 (確認用)
        self.attach_artists(frame.axes,
            patches.Circle((xc, yc), lo*frame.unit, color='c', ls='--', lw=1/2, fill=0),
            patches.Circle((xc, yc), hi*frame.unit, color='c', ls='--', lw=1/2, fill=0),
        )
        self.Arts += frame.axes.plot(x, y, 'c-', lw=0.5, alpha=0.75)
    
    def set_radii(self, p):
        frame = self.selected_view.frame
        h, w = frame.buffer.shape
        lo = h/2 * self.rmin.value
        hi = h/2 * self.rmax.value
        xc, yc = frame.selector
        if len(xc) == 0: # no selector
            xc, yc = 0, 0
        del self.Arts
        ## サークル描画 (確認用)
        self.attach_artists(frame.axes,
            patches.Circle((xc, yc), lo*frame.unit, color='c', ls='--', lw=1/2, fill=0),
            patches.Circle((xc, yc), hi*frame.unit, color='c', ls='--', lw=1/2, fill=0),
        )
        self.Draw()
