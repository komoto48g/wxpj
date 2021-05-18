#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import cv2
import numpy as np
from matplotlib import patches
from mwx.controls import LParam
from mwx.graphman import Layer


def find_circles(src, rmin=10, rmax=1000, tol=0.75):
    """Find circle with radius (rmin, rmax) excluding
    circles at the edges of the image (within dr: = tol * radius)
  retval -> list of (c:=(x,y), r) sorted by pos
    """
    ## Finds contours in binary image
    ## ▲ src は上書きされるので後で使うときは注意する
    try:
        ## opencv <= 3.4.5
        c, contours, hierarchy = cv2.findContours(src, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    except:
        contours, hierarchy = cv2.findContours(src, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    ## Detect enclosing circles
    circles = [cv2.minEnclosingCircle(v) for v in contours]
    
    ## check: draw contours directly on image (img is src)
    ## img = cv2.drawContours(src.copy(), contours, -1, 255, 1) # linetype=-1 => 塗りつぶし
    
    h, w = src.shape
    
    def distance(v): # 位置で昇順ソートする
        c = v[0]
        return np.hypot(c[0]-w/2, c[1]-h/2)
    
    def isinside(c, r): # 画像の端にある円を除く
        d = tol * r
        return rmin < r < rmax and d < c[0] < w-d and d < c[1] < h-d
    
    return sorted([(c,r) for c,r in circles if isinside(c,r)], key=distance)


class Plugin(Layer):
    """Cetner of Circles finder
    """
    menu = "Plugins/&Basic Tools"
    category = "Basic Tools"
    unloadable = False
    
    lgbt = property(lambda self: self.parent.require('lgbt'))
    
    def Init(self):
        self.rmin = LParam("rmin", (0,1000,1), 20)
        self.rmax = LParam("rmax", (0,1000,1), 500)
        
        self.layout("blur-threshold", self.lgbt.params, show=0, cw=0, lw=40, tw=40)
        self.layout("radii", [
            self.rmin,
            self.rmax
            ],
            cw=0, lw=40, tw=48
        )
        btn1 = wx.Button(self, label="+Bin", size=(40,22))
        btn1.Bind(wx.EVT_BUTTON, lambda v: self.lgbt.calc(otsu=wx.GetKeyState(wx.WXK_SHIFT)))
        btn1.SetToolTip("S-Lbutton to estimate threshold using Otsu algorithm")
        
        btn2 = wx.Button(self, label="+Execute", size=(64,22))
        btn2.Bind(wx.EVT_BUTTON, lambda v: self.run(otsu=wx.GetKeyState(wx.WXK_SHIFT)))
        btn2.SetToolTip("S-Lbutton to estimate threshold using Otsu algorithm")
        
        self.layout(None, [btn1, btn2], row=2)
    
    maxcount = 256 # 選択する点の数を制限する
    
    def run(self, frame=None, **kwargs):
        if not frame:
            frame = self.selected_view.frame
        del self.Arts
        
        ## Search center of circles
        src = self.lgbt.calc(frame, **kwargs)
        circles = find_circles(src, int(self.rmin), int(self.rmax))
        self.message("found {} circles".format(len(circles)))
        
        if circles:
            N = self.maxcount
            if len(circles) > N:
                self.message("\b is too many, chopped (< {})".format(N))
                circles = circles[:N]
            
            xy = []
            for (cx,cy),r in circles:
                x, y = frame.xyfrompixel(cx, cy)
                r *= frame.unit
                
                ## 不特定多数の円を描画する
                art = patches.Circle((x,y), r, color='r', ls='dotted', lw=1, fill=0)
                frame.axes.add_artist(art)
                self.Arts.append(art)
                xy.append((x,y))
            frame.markers = np.array(xy).T # scatter markers if any xy
