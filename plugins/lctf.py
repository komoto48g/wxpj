#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import cv2
import numpy as np
from numpy import pi
from scipy import signal
from plugins.lcrf import Model
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
    ys = np.convolve(window/window.sum(), data, mode='same')
    return ys[lw:-lw]


def find_radial_peaks(data, tol=0.01):
    """find local maxima/minim's
    smoothing with Gaussian window (signal.windows.gaussian)
    """
    ## w = len(data)
    ## lw = int(max(3, tol * w/2))
    ## window = signal.windows.gaussian(lw, std=lw)
    ## ys = np.convolve(window/window.sum(), data, mode='same') # ぼかしならし
    ## ys = signal.lfilter(window/window.sum(), 1, data) # 短周期シフト ? NG
    ys = blur1d(data, tol)
    
    ## maxima = signal.find_peaks_cwt(ys, np.arange(3,4))
    maxima,_attr = signal.find_peaks(ys, width=2)
    
    ## minima = signal.find_peaks_cwt(-ys, np.arange(3,4))
    minima,_attr = signal.find_peaks(-ys, width=2)
    
    ## maxima = signal.argrelmax(ys)
    ## minima = signal.argrelmin(ys)
    
    return ys, maxima, minima # np.sort(np.append(maxima, minima))
