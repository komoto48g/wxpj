#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import cv2
import numpy as np
from numpy import pi
from numpy.fft import fft,ifft,fft2,ifft2,fftshift,fftfreq
from scipy import signal
from matplotlib import patches
from mwx.controls import LParam
from mwx.graphman import Layer
from plugins.lcrf import Model
from wxpyJemacs import wait
import editor as edi


def logpolar(src, r0, r1, center=None):
    """Log-Polar transform
    The area radii [r0:r1] of radius N/2 mapsto the same size of src image
    
    cf. cv2.logPolar(src, (nx,ny), M, cv2.INTER_CUBIC)
    """
    h, w = src.shape
    if center is None:
        xc, yc = w//2, h//2
    else:
        xc, yc = center
    
    x = np.arange(w, dtype=np.float32) /w
    y = np.arange(h, dtype=np.float32) * 2*pi /h
    xx, yy = np.meshgrid(x, y)
    
    rh0 = np.log(r0) if r0>0 else 0
    rh1 = np.log(r1)
    r = np.exp(rh0 + (rh1 - rh0) * xx)
    map_x = xc + r * np.cos(yy)
    map_y = yc + r * np.sin(yy)
    dst = cv2.remap(src.astype(np.float32), map_x, map_y, cv2.INTER_CUBIC)
    return dst


def find_ring_center(src, lo, hi, N=256, tol=0.01):
    """find ring pattern in buffer with fixed center
    
    Polar 変換した後，角度セグメントに分割して相互相関をとる．
    center 固定，楕円を計測するために log-polar を使用する．
    theta = 0 を基準として，相対変位 [pixels] を計算する．
    
    src : source buffer (typ. log(abs(fft)))
  lo-hi : masking size of radial axis
      N : resizing of angular axis (total step in angle [0:2pi])
    tol : remove peaks that leap greater than N * tol
  retval ->
        dst(log-polar-transformed image) and fitting model
    """
    h, w = src.shape
    
    dst = logpolar(src, lo, hi)
    
    ## Resize Y (angular) axis (計算を軽くするためリサイズ)
    rdst = cv2.resize(dst.astype(np.float32), (w, N), interpolation=cv2.INTER_AREA)
    
    rdst -= rdst.mean()
    rdst = cv2.GaussianBlur(rdst, (1,11), 0)
    
    temp = rdst[0][::-1] # template of corr; distr at theta=0(=2pi)
    data = []
    for fr in rdst:
        p = signal.fftconvolve(fr, temp, mode='same')
        data.append(p.argmax())
    
    ## 相関の計算は上から行うので，2pi --> 0 の並びのリストになる
    ##   最終的に返す計算結果は逆転させて，0 --> 2pi の並びにする
    Y = np.array(data[::-1]) - w/2
    X = np.arange(0, 1, 1/len(Y)) * 2*pi
    
    ## remove leaps(2): tol より小さいとびを許容する (画素サイズに比例)
    tolr = max(5, tol * w/2)
    xx, yy = [0.], [0.]
    for x,y in zip(X[1:], Y[1:]):
        if abs(y - yy[-1]) < tolr:
            xx.append(x)
            yy.append(y)
    
    fitting_curve = Model(xx, yy)
    
    ## edi.plot(xx, yy, '+', X, fitting_curve(X))
    
    fitting_curve.params[0] = 0 # :a=0 として(平均を基準とする)全体のオフセット量を評価する
    fitting_curve.params[1] = 0
    fitting_curve.params[2] = 0
    
    return dst, fitting_curve


def smooth1d(data, tol=0.01):
    w = len(data)
    lw = int(max(3, tol * w/2))
    if lw % 2 == 0:
        lw += 1
    return signal.savgol_filter(data, lw, polyorder=3)


def blur1d(data, tol=0.01):
    w = len(data)
    lw = int(max(3, tol * w/2))
    ## window = np.hanning(lw)
    window = signal.windows.gaussian(lw, std=lw)
    
    ## padding dumy data at both edge
    data = np.concatenate((data[:lw][::-1], data, data[-lw:][::-1]))
    ys = np.convolve(window/window.sum(), data, mode='same') # ならし
    ## ys = signal.lfilter(window/window.sum(), 1, data) # 短周期は苦手？NG
    return ys[lw:-lw]


def find_radial_peaks(data, tol=0.01):
    """find local maxima/minim's
    smoothing with Gaussian window (signal.windows.gaussian)
    """
    w = len(data)
    lw = int(max(3, tol * w/2))
    
    ys = blur1d(data, tol)
    
    ## maxima = signal.find_peaks_cwt(ys, np.arange(3,4))
    ## minima = signal.find_peaks_cwt(-ys, np.arange(3,4))
    maxima,_attr = signal.find_peaks(ys, width=lw/3)
    minima,_attr = signal.find_peaks(-ys, width=lw/3)
    
    ## maxima = signal.argrelmax(ys)
    ## minima = signal.argrelmin(ys)
    
    ## remove near-edge peaks
    def _edge(x):
        return x[(lw/2 < x) & (x < w-lw/2)]
    maxima = _edge(maxima)
    minima = _edge(minima)
    
    return ys, maxima, minima # np.sort(np.append(maxima, minima))


def filter_peaks(xx, yy, threshold=1/2):
    """Return well-spacing peaks (xx, yy)
    Assumption:
    0. The first peak is a true peak.
    1. All peak intensities are likely decreasing
    2. All peak intervals are likely decreasing
       ▲狭い間隔で二つのピークが並ぶことがあるので注意
    """
    pt = np.vstack((xx, yy)).T
    po = pt[0]
    dpo = pt[1] - po
    ls = [po]
    for p in pt[1:]:
        dp = p - po
        if abs(dp[0] / dpo[0] - 1) < threshold:
            ls.append(p)
            po = p
            dpo = dp
    return np.array(ls).T


class Plugin(Layer):
    """CTF finder ver 1.0
    """
    menu = "Test"
    
    def Init(self):
        self.rmin = LParam("rmin", (0.01, 0.1, 0.001), 0.05,
                           updater=lambda p: self.calc_ring(),
                           tip="Ratio to the radius")
        
        self.tol = LParam("tol", (0, 0.1, 0.001), 0.01,
                           updater=lambda p: self.calc_peak(),
                           tip="Ratio to the radius of blurring pixels")
        
        self.layout("FFT Cond.", (
            self.rmin,
            self.tol,
            ),
            type='vspin', style='button', lw=28, tw=50,
        )
        self.circ = patches.Circle((0,0), 0, color='r', ls='solid', lw=0.5, fill=0, zorder=2)
        self.attach_artists(self.output.axes, self.circ)
    
    @property
    def selected_frame(self):
        return self.graph.frame
    
    @property
    def selected_roi(self):
        src = self.selected_frame.buffer
        h, w = src.shape
        n = pow(2, int(np.log2(min(h,w)))-1) # resize to 2^n squared ROI
        i, j = h//2, w//2
        return src[i-n:i+n,j-n:j+n]
    
    @wait
    def calc_ring(self, show=True):
        """Calc log-polar of ring pattern
        """
        frame = self.selected_frame
        src = self.selected_roi
        h, w = src.shape
        
        buf = fftshift(fft2(src))
        buf = np.log(1 + abs(buf))
        buf -= buf.mean()
        
        self.message("Calculating CTF ring...")
        r0 = w * self.rmin.value
        r1 = w * 0.5
        dst, self.fitting_curve = find_ring_center(buf, r0, r1, N=256, tol=0.05)
        
        m = w / np.log(r1/r0)
        
        self.axis = r0 / w * np.exp(np.arange(w) / m) # [R0:R1] <= [0:1/2]
        self.data = self.fitting_curve.mod1d(dst)
        
        if show:
            self.message("\b Loading log-polar image...")
            dst = self.fitting_curve.mod2d(dst)
            self.output.load(dst, "*log-polar*", pos=0)
            self.output.load(buf, "*fft-of-{}*".format(frame.name),
                             localunit=1/w/frame.unit)
        self.message("\b done.")
        
        ## 拡張 log-polar 変換は振幅が m 倍だけ引き延ばされている
        eps, phi = self.fitting_curve.params[3:5]
        self.stigma = eps / m * np.exp(phi * 1j)
        
        ## print("self.stigma =", self.stigma)
        print("$result(eps, phi) = {!r}".format((eps, phi)))
    
    @wait
    def calc_peak(self, show=True):
        """Calc min/max peak detection
        """
        N = self.data.size
        R0 = self.rmin.value
        R1 = 0.5
        TOL = 0.05
        tol = self.tol.value
        
        ## r2:data の一定間隔補間データを作ってゼロ点を求める
        newaxis = np.linspace(R0**2, R1**2, N)
        orgdata = np.interp(newaxis, self.axis**2, self.data)
        newdata = smooth1d(orgdata, tol)
        ## if show:
        ##     edi.plot(newaxis, newdata, '-', lw=1) # original smoothing data
        
        newdata, maxima, minima = find_radial_peaks(newdata, tol)
        
        ## Check validity of zero-points spacing
        hx, hy = newaxis[maxima], newdata[maxima]
        lx, ly = newaxis[minima], newdata[minima]
        ## lp = np.vstack((lx, ly))
        lp = filter_peaks(lx, ly) # low peaks
        
        self.lpoints = lp
        self.newaxis = newaxis
        self.newdata = newdata
        
        print("+ {} low peaks found".format(len(lp.T)))
        if show:
            edi.plot(self.axis**2, self.data, '--', lw=0.5) # raw data
            ## edi.plot(newaxis, orgdata, '--', lw=1) # original data
            edi.plot(newaxis, newdata, '-', lw=1) # interpolated
            edi.plot(lx, ly, 'v') # low peaks
            edi.plot(hx, hy, '^') # high peaks
            edi.plot(*lp, 'o')    # filtered peaks
            
        if show:
            art = self.circ
            u = self.output.frame.unit
            A = self.stigma
            eps = np.abs(A)
            ang = np.angle(A) * 180/pi
            r = N * np.sqrt(lx[0])
            print("eps =", eps)
            print("ang =", ang)
            art.width = 2 * r * (1 + eps) * u
            art.height = 2 * r * (1 - eps) * u
            art.angle = ang / 2
            art.set_visible(1)
            self.output.draw()
