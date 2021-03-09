#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import cv2
import numpy as np
from mwx.graphman import Layer
from matplotlib import patches
import editor as edi


def find_ellipses(src):
    """Find ellipses
    楕円検出を行うため，5 点以上のコンターが必要．小さいスポットは除外される
    小さいスポットを検出するためにはぼかし量を大きくすればよい
    
  retval -> list of (c:=(x,y), r:=(ra<rb), angle) sorted by pos
    """
    ## Finds contours in binary image
    ## ▲ src は上書きされるので後で使うときは注意する
    c, contours, hierarchy = cv2.findContours(src, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    ## Detect enclosing rectangles
    ## There should be at least 5 points to fit the ellipse
    ellipses = [cv2.fitEllipse(v) for v in contours if len(v) > 4]
    
    h, w = src.shape
    distance = lambda p: np.hypot(p[0]-w/2, p[1]-h/2) # 位置で昇順ソート
    
    return sorted([(c,r,a) for c,r,a in ellipses], key=lambda v: distance(v[0]))


class Plugin(Layer):
    """Cetner of Circles finder ver.2
    """
    menu = "&Plugins/&Basic Tools"
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
        
        self.layout(None, [btn1, btn2], row=2)
    
    maxcount = 256 # 選択する点の数を制限する
    maxratio = 5.0 # ひずみの大きい楕円は除外する
    
    def run(self, frame=None, **kwargs):
        if not frame:
            frame = self.selected_view.frame
        del self.Arts
        
        ## Search center of circles
        src = self.lgbt.calc(frame, **kwargs)
        circles = find_ellipses(src)
        self.message("found {} circles".format(len(circles)))
        
        h, w = src.shape
        if circles:
            N = self.maxcount
            if len(circles) > N:
                self.message("\b is too many, chopped (< {})".format(N))
                circles = circles[:N]
            
            xy = []
            for (cx,cy), (ra,rb), angle in circles:
                if 0 < cx < w and 0 < cy < h and rb/ra < self.maxratio:
                    ## 不特定多数の円を描画する
                    art = patches.Circle((0,0), 0, color='r', ls='dotted', lw=1, fill=0)
                    art.center = frame.xyfrompixel(cx, cy)
                    art.height = ra * frame.unit
                    art.width = rb * frame.unit
                    art.angle = 90-angle
                    frame.axes.add_artist(art)
                    self.Arts.append(art)
                    
                    ## 検出した楕円の中心を記録する．強度の偏りは考慮しない
                    x, y = art.center
                    xy.append((x,y))
                    
            frame.markers = np.array(xy).T # scatter markers if any xy
