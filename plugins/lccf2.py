#! python
# -*- coding: shift-jis -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import scipy as np
from matplotlib import patches
from mwx import LParam
from mwx.graphman import Layer
import editor as edi


class Plugin(Layer):
    """Cetner of Circles finder ver.2
    """
    menu = "&Plugins/&Basic Tools"
    category = "Basic Tools"
    unloadable = False
    
    def Init(self):
        self.params = (
            LParam("frmin", (0,1,1e-3), np.nan),
            LParam("frmax", (0,1,1e-3), np.nan),
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
    
    maxcount = 256 # �I������_�̐��𐧌�����
    maxratio = 5.0 # �Ђ��݂̑傫���ȉ~�͏��O����
    
    def run(self, frame=None, **kwargs):
        if not frame:
            frame = self.graph.frame
        del self.Arts
        
        ## Search center of circles
        rmin = self.params[0].value
        rmax = self.params[1].value
        if rmin is np.nan: rmin = None
        if rmax is np.nan: rmax = None
        
        src = frame.buffer
        dst = self.lgbt.calc(frame, **kwargs) # calc binary image
        circles = edi.find_ellipses(dst, rmin, rmax, sortby='pos')
        self.message("found {} circles".format(len(circles)))
        
        ## 1. maxcount `N �ȏ�̓t�B�b�e�B���O�ɂ͑�������̂Ő�������
        ## 2. �ȉ~�̒��Z�a�䂪�傫�����̂́C�������X�|�b�g�łȂ����ߏ��O����
        ## 
        ## ** �ȉ~���o���s�����߁C5 �_�ȏ�̃R���^�[���K�v�D�������X�|�b�g�͏��O�����
        ##    �������X�|�b�g�����o���邽�߂ɂ͂ڂ����ʂ�傫�����邱��
        if circles:
            N = self.maxcount
            if len(circles) > N:
                self.message("\b is too many, chopped (< {})".format(N))
                circles = circles[:N] # (N) ��������̂ŁC�摜��������߂��̂����I��
            
            xy = []
            for (cx,cy), (ra,rb), angle in circles:
                if rb/ra < self.maxratio:
                    ## �s���葽���� Arts ��`�悷��
                    art = patches.Circle((0,0), 0, color='r', ls='dotted', lw=1, fill=0)
                    art.center = frame.xyfrompixel(cx, cy)
                    art.height = ra * frame.unit
                    art.width = rb * frame.unit
                    art.angle = 90-angle
                    frame.axes.add_artist(art)
                    self.Arts.append(art)
                    ## xy.append(art.center)
                    
                    ## --> centr-of-mass: ���x�d�S���Ƃ�
                    r = int(min(ra,rb) /2)
                    nx, ny = int(cx), int(cy)
                    
                    h, w = src.shape
                    ya, yb = max(0, ny-r), min(ny+r+1, h)
                    xa, xb = max(0, nx-r), min(nx+r+1, w)
                    
                    buf = src[ya:yb, xa:xb] # crop around (cx,cy)
                    dx, dy = edi.centroid(buf)
                    x, y = frame.xyfrompixel(nx-r+dx, ny-r+dy)
                    xy.append((x,y))
                    
            frame.markers = np.array(xy).T # scatter markers if any xy
