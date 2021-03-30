#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import cv2
import numpy as np
from numpy import pi,cos,sin,inf
from scipy import interpolate
from scipy import optimize
from scipy import signal
from plugins.lcrf import Model
from mwx.graphman import Layer
import editor as edi


def find_ring_center(src, lo=0.1, hi=1.0, N=256, tol=0.01):
    h, w = src.shape
    nx, ny = w//2, h//2
    nn = w/2
    M = nn / np.log(nn)
    dst = cv2.logPolar(src, (nx,ny), M, cv2.INTER_LINEAR|cv2.WARP_FILL_OUTLIERS)
    
    ## Mask X (radial) axis => sqrt(R) < r < R
    lo = int(nn + M * np.log(lo))
    hi = int(nn + M * np.log(hi))
    dst[:,:lo] = 0
    dst[:,hi:] = 0
    
    ## Resize Y (angular) axis (計算を軽くするためリサイズ)
    rdst = cv2.resize(dst[:,lo:hi].astype(np.float32), (hi-lo, N), interpolation=cv2.INTER_AREA)
    
    rdst -= rdst.mean()
    rdst = cv2.GaussianBlur(rdst, (1,11), 0)
    
    temp = rdst[0][::-1] # template of corr; distr at theta = 0
    data = []
    for fr in rdst:
        p = signal.fftconvolve(fr, temp, mode='same')
        data.append(p.argmax())
    
    ## 相関の計算は上から行うので，2pi --> 0 の並びのリストになる
    ##   最終的に返す計算結果は逆転させて，0 --> 2pi の並びにする
    Y = np.array(data[::-1]) - (hi-lo)/2
    X = np.arange(0, 1, 1/len(Y)) * 2*pi
    
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
    
    fitting_curve.params[0] = 0 # :a=0 として(平均を基準とする)全体のオフセット量を評価する
    return dst, fitting_curve


def find_radial_peaks(data):
    w = len(data)
    lw = max(5, w//200)
    ## window = np.hanning(lw)
    window = signal.windows.gaussian(lw, std=1)
    
    data = np.convolve(window/window.sum(), data, mode='same')
    ## data = signal.lfilter(window/window.sum(), 1, data)
    
    ## dx = 0.5
    ## x = np.arange(w)
    ## f = interpolate.interp1d(x, data, kind='cubic') # kind: linear(1), quadratic(2), cubic(3)
    ## xnew = np.arange(0, w-1, dx)
    ## ys = f(xnew)
    ys = data
    
    maxima = signal.argrelmax(ys)
    ## maxima = signal.find_peaks_cwt(ys, np.arange(2,4))
    ## maxima,_ = signal.find_peaks(ys, width=2)
    
    minima = signal.argrelmin(ys)
    ## minima = signal.find_peaks_cwt(-ys, np.arange(2,4))
    ## minima,_ = signal.find_peaks(-ys, width=2)
    
    peaks = np.sort(np.append(maxima, minima))
    
    ## peaks-spacing 1 pixel 以下であれば不精確なので除外する．
    ## 最初に 3 pixel 以上の間隔のある点まで移動し，
    ## そこから 2pixel 以下の点を検出する．
    ps = np.diff(peaks)
    print("ps =", ps)
    j = k = 0
    while k - j < 4:
        j = k + next((i for i,x in enumerate(ps[k:]) if x > 2))
        k = j + next((i for i,x in enumerate(ps[j:]) if x < 2), -1-j) # otherwise -1
        if k == -1:
            break
    return ys, np.array(peaks[j:k], dtype=int)
