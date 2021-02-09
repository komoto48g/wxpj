#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import cv2
import scipy as np
from matplotlib import patches
from mwx import LParam
from mwx.graphman import Layer


def find_circles(src, rmin=10, rmax=1000):
    ## Finds contours in binary image
    ## ▲ src は上書きされるので後で使うときは注意する
    c, contours, hierarchy = cv2.findContours(src, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    ## detect enclosing circles [(nx,ny), c]
    circles = [cv2.minEnclosingCircle(v) for v in contours]
    
    ## check: draw contours directly on image (! img is src)
    ## img = cv2.drawContours(src.copy(), contours, -1, 255, 1) # linetype=-1 => 塗りつぶし
    
    ## 外接円の半径が (rmin, rmax) 以内にあるものを (x,y,r) リストにして返す
    ## ただし，画像の端にある円 (dr := tol * radius 以内) は除外する
    tol = 0.75
    h, w = src.shape
    isinside = lambda p,dr: dr < p[0] < w-dr and dr < p[1] < h-dr
    distance = lambda p: np.hypot(p[0]-w/2, p[1]-h/2) # 位置で昇順ソート
    
    ls = [(c,r) for c,r in circles if rmin < r < rmax and isinside(c, r*tol)]
    return sorted(ls, key=lambda v: distance(v[0]))


class Plugin(Layer):
    """Cetner of Circles finder
    """
    menu = "&Plugins/&Basic Tools"
    category = "Basic Tools"
    unloadable = False
    
    def Init(self):
        self.params = (
            LParam("rmin", (0,1000,1), 20),
            LParam("rmax", (0,1000,1), 500),
        )
        self.layout("blur-threshold", self.lgbt.params, show=0, cw=0, lw=40, tw=40)
        self.layout("radii", self.params, cw=0, lw=40, tw=48)
        
        btn1 = wx.Button(self, label="+Bin", size=(40,22))
        btn1.Bind(wx.EVT_BUTTON, lambda v: self.lgbt.calc(otsu=wx.GetKeyState(wx.WXK_SHIFT)))
        btn1.SetToolTip("S-Lbutton to estimate threshold using Otsu algorithm")
        
        btn2 = wx.Button(self, label="+Execute", size=(64,22))
        btn2.Bind(wx.EVT_BUTTON, lambda v: self.run(otsu=wx.GetKeyState(wx.WXK_SHIFT)))
        btn2.SetToolTip("S-Lbutton to estimate threshold using Otsu algorithm")
        
        self.layout(None, [btn1, btn2], row=2)
    
    lgbt = property(lambda self: self.parent.require('lgbt'))
    
    rmin = property(lambda self: self.params[0])
    rmax = property(lambda self: self.params[1])
    
    maxcount = 256 # 選択する点の数を制限する
    
    def run(self, frame=None, **kwargs):
        if not frame:
            frame = self.graph.frame
        del self.Arts
        
        ## Search center of circles
        src = self.lgbt.calc(frame, **kwargs) # --> output
        circles = find_circles(src, int(self.rmin), int(self.rmax))
        self.message("found {} circles".format(len(circles)))
        
        if circles:
            N = self.maxcount
            if len(circles) > N:
                self.message("\b is too many, chopped (< {})".format(N))
                circles = circles[:N]
            xy = []
            for (nx,ny),r in circles:
                x, y = frame.xyfrompixel(nx, ny)
                r *= frame.unit
                
                ## 不特定多数の Arts を描画する
                art = patches.Circle((x,y), r, color='r', ls='dotted', lw=1, fill=0)
                frame.axes.add_artist(art)
                self.Arts.append(art)
                xy.append((x,y))
            frame.markers = np.array(xy).T # scatter markers if any xy
