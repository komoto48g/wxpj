#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import cv2
import numpy as np
from numpy import pi,cos,sin
from mwx.graphman import Layer
from matplotlib import patches
import editor as edi


def find_ellipses(src, tol=0.75):
    """Find ellipses
    楕円検出を行うため，5 点以上のコンターが必要．小さいスポットは除外される
    小さいスポットを検出するためにはぼかし量を大きくすればよい
    画像の端にある円を除く
    
  retval -> list of (c:=(x,y), r:=(ra<rb), angle) sorted by pos
    """
    ## Finds contours in binary image
    ## ▲ src は上書きされるので後で使うときは注意する
    try:
        ## opencv <= 3.4.5
        c, contours, hierarchy = cv2.findContours(src, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    except ValueError:
        contours, hierarchy = cv2.findContours(src, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    ## Detect enclosing rectangles
    ## Note: there should be at least 5 points to fit the ellipse (c,r,a)
    ellipses = [cv2.fitEllipse(v) for v in contours if len(v) > 4]
    
    h, w = src.shape
    
    def distance(v): # 位置で昇順ソートする
        c = v[0]
        return np.hypot(c[0]-w/2, c[1]-h/2)
    
    def isinside(c, r): # 画像の端にある円を除く
        d = tol * max(r)
        return d < c[0] < w-d and d < c[1] < h-d
    
    return sorted([(c,r,a) for c,r,a in ellipses if isinside(c,r)], key=distance)


class Plugin(Layer):
    """Cetner of Circles (Ellipses) finder ver.2
    """
    menu = "Plugins/&Basic Tools"
    category = "Basic Tools"
    unloadable = False
    
    lgbt = property(lambda self: self.parent.require('lgbt'))
    
    def Init(self):
        self.layout("blur-threshold", self.lgbt.params, show=0, cw=0, lw=40, tw=40)
        
        btn1 = wx.Button(self, label="+Bin", size=(40,22))
        btn1.Bind(wx.EVT_BUTTON, lambda v: self.lgbt.calc(otsu=wx.GetKeyState(wx.WXK_SHIFT)))
        btn1.SetToolTip("S-Lbutton to estimate threshold using Otsu algorithm")
        
        btn2 = wx.Button(self, label="+Execute", size=(64,22))
        btn2.Bind(wx.EVT_BUTTON, lambda v: self.run(otsu=wx.GetKeyState(wx.WXK_SHIFT)))
        btn2.SetToolTip("S-Lbutton to estimate threshold using Otsu algorithm")
        
        self.layout(None, (btn1, btn2), row=2)
    
    maxcount = 256 # 選択する点の数を制限する
    maxratio = 5.0 # ひずみの大きい楕円は除外する
    
    def run(self, frame=None, otsu=0, invert=0):
        """Search center of circles"""
        if not frame:
            frame = self.selected_view.frame
        del self.Arts
        
        src = self.lgbt.calc(frame, otsu, invert) # image <uint8>
        
        circles = find_ellipses(src)
        self.message("found {} circles".format(len(circles)))
        
        if circles:
            N = self.maxcount
            if len(circles) > N:
                self.message("\b is too many, chopped (< {})".format(N))
                circles = circles[:N]
            
            h, w = src.shape
            xy = []
            for (cx,cy), (ra,rb), angle in circles:
                if ra and rb/ra < self.maxratio:
                    ## 不特定多数の円を描画する
                    art = patches.Circle((0,0), 0, color='r', ls='dotted', lw=1, fill=0)
                    art.center = frame.xyfrompixel(cx, cy)
                    art.height = ra * frame.unit
                    art.width = rb * frame.unit
                    art.angle = 90-angle
                    self.set_artists(frame, art)
                    
                    ## 検出した楕円の中心を記録する．強度の偏りは考慮しない
                    ## xy.append(art.center)
                    
                    r = int(max(ra,rb)/2) # max radius enclosing the area cf. cv2.minEnclosingCircle
                    x, y = int(cx), int(cy)
                    xa = max(0, x-r)
                    ya = max(0, y-r)
                    buf = frame.buffer[ya:y+r+1, xa:x+r+1]
                    
                    ## local maximum
                    ## dy, dx = np.unravel_index(buf.argmax(), buf.shape)
                    
                    ## local maximum :averaged
                    yy, xx = np.where(buf == np.amax(buf))
                    dy, dx = np.average(yy), np.average(xx)
                    
                    xy.append(frame.xyfrompixel(xa+dx, ya+dy))
                    
                    ## centroid of masked array
                    ## buf = np.ma.masked_array(buf, mask_ellipse(ra, rb, angle))
                    ## dx, dy = edi.centroid(buf)
                    ## xy.append(frame.xyfrompixel(xa+dx, ya+dy))
                    
            frame.markers = np.array(xy).T # scatter markers if any xy


def mask_ellipse(ra, rb, angle):
    r = int(max(ra, rb) /2) # max radius enclosing the area cf. cv2.minEnclosingCircle
    y, x = np.ogrid[-r:r, -r:r]
    yo, xo = 0, 0
    t = angle * pi/180
    xx = (x-xo) * cos(t) + (y-yo)*sin(t)
    yy = (x-xo) *-sin(t) + (y-yo)*cos(t)
    return np.hypot(xx/ra*2, yy/rb*2) > 1 # 楕円の短径 ra/2 < 長径 rb/2
