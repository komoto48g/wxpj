#! python
# -*- coding: utf-8 -*-
import wx
import cv2
import numpy as np
from numpy import pi,cos,sin
from matplotlib import patches
from mwx.controls import LParam
from mwx.graphman import Layer
## import editor as edi


def find_ellipses(src, rmin, rmax, tol=0.75):
    """Find ellipses with radius (rmin, rmax)
    excluding circles at the edges of the image < tol*r
    
  retval -> list of (c:=(x,y), r:=(ra<rb), angle) sorted by pos
    (cx,cy) : center of the rectangle [pix]
    (ra,rb) : ra:width < rb:height of the rectangle [pix]
      angle : rotation angle in clockwise (from 00:00 o'clock)
    """
    ## Finds contours in binary image
    ## ▲ src は上書きされるので後で使うときは注意する
    try:
        ## opencv <= 3.4.5
        c, contours, hierarchy = cv2.findContours(src, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    except ValueError:
        contours, hierarchy = cv2.findContours(src, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    ## Detect enclosing rectangles
    ellipses = [cv2.fitEllipse(v) for v in contours if len(v) > 4]
    
    ## There should be at least 5 points to fit the ellipse (c,r,a)
    ## To detect small spots, increase the amount of blur.
    
    h, w = src.shape
    
    def distance(v): # 位置で昇順ソートする
        c = v[0]
        return np.hypot(c[0]-w/2, c[1]-h/2)
    
    def isinside(c, r): # 画像の端にある円を除く
        d = tol * r[1]
        return (rmin < r[0] and r[1] < rmax and d < c[0] < w-d and d < c[1] < h-d)
    
    return sorted([(c,r,a) for c,r,a in ellipses if isinside(c,r)], key=distance)


class Plugin(Layer):
    """Cetner of Circles (Ellipses) finder ver.2
    """
    menu = "Plugins/&Basic Tools"
    category = "Basic Tools"
    unloadable = False
    
    lgbt = property(lambda self: self.parent.require('lgbt'))
    
    def Init(self):
        self.radii_params = (
            LParam("rmin", (0,1000,1), 2),
            LParam("rmax", (0,1000,1), 200),
        )
        self.layout(self.lgbt.params, title="blur-threshold", show=0, cw=0, lw=40, tw=40)
        self.layout(self.radii_params, title="radii", cw=0, lw=40, tw=48)
        
        btn1 = wx.Button(self, label="+Bin", size=(40,22))
        btn1.Bind(wx.EVT_BUTTON, lambda v: self.lgbt.calc(otsu=wx.GetKeyState(wx.WXK_SHIFT)))
        btn1.SetToolTip("S-Lbutton to estimate threshold using Otsu algorithm")
        
        btn2 = wx.Button(self, label="+Execute", size=(64,22))
        btn2.Bind(wx.EVT_BUTTON, lambda v: self.run(otsu=wx.GetKeyState(wx.WXK_SHIFT)))
        btn2.SetToolTip("S-Lbutton to estimate threshold using Otsu algorithm")
        
        self.layout((btn1, btn2), row=2)
    
    rmin = property(lambda self: self.radii_params[0])
    rmax = property(lambda self: self.radii_params[1])
    
    def init_session(self, session):
        self.rmin.value = session.get('rmin')
        self.rmax.value = session.get('rmax')
    
    def save_session(self, session):
        session.update({
            'rmin': self.rmin.value,
            'rmax': self.rmax.value,
        })
    
    maxcount = 256 # 選択する点の数を制限する
    maxratio = 5.0 # ひずみの大きい楕円は除外する
    
    def run(self, frame=None, otsu=0, invert=0):
        """Search center of circles"""
        if not frame:
            frame = self.selected_view.frame
        del self.Arts
        
        src = self.lgbt.calc(frame, otsu, invert) # image <uint8>
        
        circles = find_ellipses(src, self.rmin.value, self.rmax.value)
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
                    self.attach_artists(frame.axes, art)
                    
                    ## 検出した楕円の中心を記録する
                    ## xy.append(art.center)
                    
                    ## Show max radius enclosing the area (cf. cv2.minEnclosingCircle)
                    r = int(max(ra, rb) / 2)
                    x, y = int(cx), int(cy)
                    xa = max(0, x-r)
                    ya = max(0, y-r)
                    buf = frame.buffer[ya:y+r+1, xa:x+r+1]
                    
                    ## local maximum
                    ## dy, dx = np.unravel_index(buf.argmax(), buf.shape)
                    
                    ## local maximum :averaged (強度の偏りを考慮する)
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
