#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import cv2
import numpy as np
from numpy import pi,cos,sin,inf
from scipy import optimize
from scipy import signal
from mwx import LParam
from mwx.graphman import Layer
import editor as edi


class Model(object):
    def __init__(self, x, y):
        params = [0.,] * 5
        result = optimize.leastsq(self.residual, params, args=(x,y))
        self.params = result[0]
    
    def __call__(self, x):
        a,b,c,d,e = self.params
        x = np.array(x)
        return a + b * cos(x-c) + d * cos(2*x-e)
        ## return a + b * cos(x-c) + d * cos(2*(x-e))
    
    def residual(self, params, x, y):
        self.params = params
        res = (self(x) - y)**2
        print("\b"*72 + "point({}): residual {:g}".format(len(res), sum(res)), end=' ')
        return res
    
    ## def modi2d(self, buf):
    ##     h, w = buf.shape
    ##     for j,x in enumerate(buf):
    ##         y = (1 - j/h) * 2*pi               # yaxis (from 2pi to 0)
    ##         buf[j] = np.roll(x, -int(self(y))) # roll anti-shift (to modify peak pos)
    
    def mod1d(self, buf):
        """Calculate line profile with modulation correction
        buf : Polar-converted output buffer
      retval -> 1d-array of modulated (+avr.) line profile
        """
        h, w = buf.shape
        data = np.zeros(w)
        for j,x in enumerate(buf):
            y = (1 - j/h) * 2*pi              # yaxis (from 2pi to 0)
            data += np.roll(x, -int(self(y))) # roll anti-shift (to modify peak pos)
        return data / h


def find_ring_center(src, center, lo, hi=None, N=128, tol=0.01):
    """find center of ring pattern in buffer
    Polar 変換した後，角度セグメントに分割して相互相関をとる．
    theta = 0 を基準として，相対変位 [pixels] を計算する
    src : source buffer
 center : initial value of center positoin [nx,ny]
  lo-hi : masking size of radial axis
      N : resizing of angular axis (total step in angle [0:2pi])
  retval ->
        dst(linear-polar-transformed image), guessed center, and fitting model
    """
    h, w = src.shape
    nx, ny = center if center is not None else (w//2, h//2)
    
    dst = cv2.linearPolar(src, (nx,ny), w, cv2.WARP_FILL_OUTLIERS)
    
    ## Mask X (radial) axis
    hi = hi or w//2
    dst[:,:lo] = 0
    dst[:,hi:] = 0
    
    ## Resize Y:angular axis (計算を軽くするためリサイズ)
    rdst = cv2.resize(dst[:,lo:hi].astype(np.float32), (hi-lo, N), interpolation=cv2.INTER_AREA)
    rdst -= rdst.mean()
    ## rdst = cv2.GaussianBlur(rdst, (1,11), 0)
    
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
    ##     ym = np.mean(Y)
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
    
    ## --------------------------------
    ## Do fitting to model curve
    ##   and calculate the total shifts
    ## --------------------------------
    fitting_curve = Model(xx, yy)
    
    edi.plot(xx, yy, '+', X, fitting_curve(X))
    
    a = fitting_curve.params[0] = 0 # :a=0 として(平均を基準とする)全体のオフセット量を評価する
    b = fitting_curve.params[1]
    c = fitting_curve.params[2] % (2*pi)
    
    t = c+pi if b>0 else c # ---> 推定中心方向
    nx -= abs(b) * cos(t)
    ny += abs(b) * sin(t)
    center = (nx, ny)
    return dst, center, fitting_curve


def find_radial_peaks(data):
    """Find radial peaks in Polar-converted buffer
   data : Polar-converted output buffer
    """
    ## Smooth with window (cf. signal.windows) and find local maximas
    ## w = len(data)
    ## lw = max(3, w//200)
    ## window = np.hanning(lw)
    ## ys = np.convolve(window/window.sum(), data, mode='same')
    ## peaks = signal.argrelmax(ys)[0]
    ## 
    ys = data.copy()
    peaks = signal.find_peaks_cwt(ys, widths=np.arange(3,4))
    
    peaks = [p for p in peaks if ys[p] > ys.mean()] # filtered by threshold
    return ys, np.array(peaks)


class Plugin(Layer):
    """Center of Rings finder ver 1.0
    """
    menu = "&Plugins/&Basic Tools"
    category = "Basic Tools"
    unloadable = False
    
    lgbt = property(lambda self: self.parent.require('lgbt'))
    
    def Init(self):
        self.rmin = LParam("rmin", (0,2000,1), 50)
        self.rmax = LParam("rmax", (0,2000,1), inf)
        
        self.layout("blur-threshold", self.lgbt.params, show=0, cw=0, lw=40, tw=40)
        self.layout("radii", [
            self.rmin,
            self.rmax
            ],
            cw=0, lw=36, tw=48
        )
        btn = wx.Button(self, label="+Execute", size=(64,22))
        btn.Bind(wx.EVT_BUTTON, lambda v: self.run(shift=wx.GetKeyState(wx.WXK_SHIFT)))
        
        ## btn.Bind(wx.EVT_BUTTON, lambda v:
        ##     self.thread.Start(self.run, shift=wx.GetKeyState(wx.WXK_SHIFT)))
        ## self.thread = Layer.Thread(self)
        
        btn.SetToolTip("S-Lbutton to enter recusive centering")
        
        self.chkplt = wx.CheckBox(self, label="rdist")
        
        self.layout(None, [btn, self.chkplt], row=2, type='vspin', tw=22)
    
    def run(self, frame=None, shift=0, maxloop=4):
        if not frame:
            frame = self.selected_view.frame
        
        center = edi.centroid(frame.buffer)
        if shift:
            nx, ny = frame.xytopixel(frame.selector)
            if isinstance(nx, int): # for PY2
                center = nx, ny
            else:
                center = nx[0], ny[0]
        
        ## Search center and fit with model (twice at least)
        src = frame.buffer
        for i in range(maxloop):
            buf, center, fitting_curve, = find_ring_center(src, center, lo=int(self.rmin))
        self.fitting_curve = fitting_curve
        
        self.output.load(buf, name="*lin-polar*", localunit=1)
        frame.selector = frame.xyfrompixel(center)
        
        ## Find peaks in radial distribution
        data = fitting_curve.mod1d(buf)
        rdist, peaks = find_radial_peaks(data)
        
        if self.chkplt.Value: # this should be called for MainThread
            edi.clf()
            edi.plot(data)
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
        
        l,r,b,t = frame.extent
        x, y = np.array([(x,y) for x,y in zip(X,Y) if l<x<r and b<y<t]).T
        z = frame.xytoc(x, y)
        oz = (z > 2 * rdist.mean())
        frame.markers = (x[oz][0:-1:3], y[oz][0:-1:3]) # scatter markers onto the arc
        
        ## サークル描画 (確認用)
        self.Arts = self.selected_view.axes.plot(x, y, 'c-', lw=0.5, alpha=0.75)
