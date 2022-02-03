#! python
# -*- coding: utf-8 -*-
import cv2
import numpy as np
from numpy import pi
from numpy.fft import fft,ifft,fft2,ifft2,fftshift,fftfreq
from scipy import signal
from matplotlib import patches
from mwx.controls import LParam
from mwx.graphman import Layer
from plugins.viewfft import fftresize
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
    return signal.savgol_filter(data, lw, polyorder=2)


def blur1d(data, tol=0.01):
    w = len(data)
    lw = int(max(3, tol * w/2))
    if lw % 2 == 0:
        lw += 1
    ## window = np.hanning(lw)
    window = signal.windows.gaussian(lw, std=lw)
    
    ## ys = signal.lfilter(window/window.sum(), 1, data) # 短周期 NG
    ## ys = np.convolve(window/window.sum(), data, mode='same')
    ## return ys

    ## padding dumy data at both edge
    data = np.concatenate((data[:lw][::-1], data, data[-lw:][::-1]))

    ys = np.convolve(window/window.sum(), data, mode='same') # ならし
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
        return x[(lw < x) & (x < w-lw)]
    
    maxima = _edge(maxima)
    minima = _edge(minima)
    return ys, maxima, minima # np.sort(np.append(maxima, minima))


class Plugin(Layer):
    """CTF finder ver 1.0
    """
    menu = "Test"
    
    debug = 0
    
    def Init(self):
        self.rmin = LParam("rmin", (0.001, 0.1, 0.001), 0.05,
                           updater=lambda p: self.calc_ring(True),
                           tip="Ratio to the radius")
        
        self.rmax = LParam("rmax", (0.1, 0.5, 0.01), 0.5,
                           updater=lambda p: self.calc_ring(True),
                           tip="Ratio to the radius")
        
        self.tol = LParam("tol", (0, 0.1, 0.001), 0.01,
                           updater=lambda p: self.calc_peak(True),
                           tip="Ratio to the radius of blurring pixels")
        
        self.layout((
                self.rmin,
                self.rmax,
                self.tol,
            ),
            title="FFT Cond.",
            type='vspin', style='button', lw=28, tw=50,
        )
    
    def init_session(self, session):
        self.reset_params(session.get('params'))
        
        if self.debug:
            print("$(session) = {!r}".format((session)))
            self.__dict__.update(session)
    
    def save_session(self, session):
        session['params'] = self.parameters
        
        if self.debug:
            session.update({
                'axis': self.axis,
                'data': self.data,
                'stig': self.stig,
            })
    
    @property
    def selected_frame(self):
        return self.graph.frame
    
    @property
    def selected_roi(self):
        return fftresize(self.selected_frame.roi, maxsize=1024)
    
    def calc_ring(self, show=False):
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
        r1 = w * self.rmax.value
        dst, self.fitting_curve = find_ring_center(buf, r0, r1, N=256, tol=0.05)
        
        m = w / np.log(r1/r0)
        
        self.axis = r0 / w * np.exp(np.arange(w) / m) # [R0:R1] <= [0:1/2]
        self.data = self.fitting_curve.mod1d(dst)
        
        if 0:
            self.output.load(buf, "*fft of {}*".format(frame.name),
                             localunit=1/w/frame.unit)
        if show:
            self.message("\b Loading log-polar image...")
            dst = self.fitting_curve.mod2d(dst)
            self.output.load(dst, "*log-polar*", pos=0)
        self.message("\b done.")
        
        ## 拡張 log-polar 変換は振幅が m 倍だけ引き延ばされている
        eps, phi = self.fitting_curve.params[3:5]
        self.stig = eps / m * np.exp(phi * 1j)
        print("$result(eps, phi) = {!r}".format((eps, phi)))
    
    def calc_peak(self, show=False):
        """Calc min/max peak detection
        """
        N = self.data.size
        R0 = self.rmin.value
        R1 = self.rmax.value
        tol = self.tol.value
        
        ## r2:data の一定間隔補間データを作ってゼロ点を求める
        newaxis = np.linspace(R0**2, R1**2, N)
        orgdata = np.interp(newaxis, self.axis**2, self.data)
        newdata = smooth1d(orgdata, tol)
        if show:
            edi.plot(newaxis, newdata, '--', lw=1) # original smoothing data
        
        newdata, maxima, minima = find_radial_peaks(newdata, tol)
        
        ## Check validity of zero-points spacing
        hx, hy = newaxis[maxima], newdata[maxima]
        lx, ly = newaxis[minima], newdata[minima]
        
        self.lxy = np.vstack((lx, ly))
        self.hxy = np.vstack((hx, hy))
        ## lp = np.vstack((lx, ly))
        
        ## --------------------------------
        ## filter low peaks
        ## --------------------------------
        threshold = tol/10 * R1**2
        print("$(threshold) = {!r}".format((threshold)))
        lxx = []
        lyy = []
        for i, (x, y) in enumerate(zip(lx, ly)):
            ## Eliminate if near one of high peaks
            if min(abs(x - hx)) < threshold:
                continue
            ## Stop if two low pakes are continuous
            ## if i < len(lx)-1:
            ##     if not np.any((x < hx) & (hx < lx[i+1])):
            ##         break
            if i > 50:
                break
            lxx.append(x)
            lyy.append(y)
        lp = np.vstack((lxx, lyy))
        
        self.lpoints = lp[:,:20] # max N low peaks
        self.newaxis = newaxis
        self.newdata = newdata
        
        ## --------------------------------
        ## output results to verify it
        ## --------------------------------
        
        print("+ {} low peaks found".format(lp.shape[1]))
        if show:
            edi.plot(self.axis**2, self.data, '--', lw=0.5) # raw data
            ## edi.plot(newaxis, orgdata, '--', lw=1) # original data
            edi.plot(newaxis, newdata, '-', lw=1) # interpolated
            edi.plot(lx, ly, 'v') # low peaks
            edi.plot(hx, hy, '^') # high peaks
            edi.plot(*self.lpoints, 'o')    # filtered peaks
            
        if 0:
            try:
                u = self.output.frame.unit
                eps = np.abs(self.stig)
                ang = np.angle(self.stig) * 180/pi
                
                ## 不特定多数の円を描画する (最大 N まで)
                del self.Arts
                for x in self.lpoints[0,:10]:
                    r = N * np.sqrt(x)
                    art = patches.Circle((0,0), 0, color='r', ls='--', lw=0.5, fill=0, alpha=0.5)
                    art.width = 2 * r * (1 + eps) * u
                    art.height = 2 * r * (1 - eps) * u
                    art.angle = ang / 2
                    self.attach_artists(self.output.axes, art)
                self.output.draw()
            except Exception:
                self.message("- no data.")
