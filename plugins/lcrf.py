#! python
# -*- coding: shift-jis -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import cv2
import scipy as np
from scipy import pi,cos,sin
from scipy import optimize
from scipy import signal
from mwx import LParam
from mwx.graphman import Layer
import editor as edi


class Model(object):
    params = [0,0,0,0,0]
    
    def __call__(self, x):
        a,b,c,d,e = self.params
        return a + b * cos(x-c) + d * cos(2*(x-e))
    
    def residual(self, params, x, y):
        self.params = params
        return (self(x) - y)**2
    
    def fit(self, x, y):
        result = optimize.leastsq(self.residual, self.params, args=(x,y))
        self.params = result[0]


def find_ring_center(src, center, lo, hi=None, N=128):
    """find center of ring pattern in buffer
    Polar �ϊ�������C�p�x�Z�O�����g�ɕ������đ��ݑ��ւ��Ƃ�D
    theta = 0 ����Ƃ��āC���Εψ� [pixels] ���v�Z����
    src : source buffer
 center : initial value of center positoin [nx,ny]
  lo-hi : masking size of radial axis
      N : resizing of angular axis (total step in angle [0:2pi])
  retval ->
        dst(linear-polar-transformed image), guessed center, and fitting model
    """
    h, w = src.shape
    nx, ny = center if center is not None else (w//2, h//2)
    dst = cv2.linearPolar(src, (nx,ny), w, cv2.WARP_FILL_OUTLIERS)
    
    ## Mask X (radial) axis
    hi = hi or w//2
    dst[:,:lo] = 0
    dst[:,hi:] = 0
    
    ## Resize Y (angular) axis (�v�Z���y�����邽�߃��T�C�Y)
    buf = dst.astype(np.float32)
    rdst = cv2.resize(buf[:,lo:hi], (hi-lo, N), interpolation=cv2.INTER_AREA)
    rdst -= rdst.mean()
    temp = rdst[0][::-1] # template of corr; distr at theta = 0
    data = []
    for fr in rdst:
        p = signal.fftconvolve(fr, temp, mode='same')
        data.append(p.argmax())
    
    ## ���ւ̌v�Z�͏ォ��s���̂ŁC2pi --> 0 �̕��т̃��X�g�ɂȂ�
    ##   �ŏI�I�ɕԂ��v�Z���ʂ͋t�]�����āC0 --> 2pi �̕��тɂ���
    Y = np.array(data[::-1]) - (hi-lo)/2
    X = np.arange(0, 1, 1/len(Y)) * 2*pi
    
    ## remove serges �}���ȕω� (���֌v�Z�̌��ʂ̂Ƃ�) �����O����
    ## if 1:
    ##     ym = np.mean(Y)
    ##     ys = np.std(Y)
    ##     xy = [(x,y) for x,y in zip(X,Y) if -2*ys < y-ym < 2*ys]
    ##     X, Y = np.array(xy).T
    
    ## remove serges (2) tol ��菬�����Ƃт����e���� (��f�T�C�Y�ɔ��)
    tol = 0.02 * w
    xx, yy = [X[0]], [Y[0]]
    for x,y in zip(X[1:], Y[1:]):
        if abs(y - yy[-1]) < tol:
            xx.append(x)
            yy.append(y)
    
    ## --------------------------------
    ## Do fitting to model curve
    ##   and calculate the total shifts
    ## --------------------------------
    
    fitting_curve = Model()
    fitting_curve.fit(xx, yy)
    
    ## print(fitting_curve.params) # ���p�����[�^���傫������邱�Ƃ�����̂Œ���
    ## edi.plot(xx, yy, '+', X, fitting_curve(X))
    
    a = fitting_curve.params[0] #= 0 # :a=0 �Ƃ���(���ς���Ƃ���)�S�̂̃I�t�Z�b�g�ʂ�]������
    b = fitting_curve.params[1]
    c = fitting_curve.params[2] % (2*pi)
    n = max(nx, ny)
    if abs(a) > n or abs(b) > n: # ���t�B�b�e�B���O�p�����[�^�ُ�D����Ɏ��s
        return find_ring_center(src, None, lo, hi, N)
    
    t = c+pi if b>0 else c # ---> ���蒆�S����
    nx -= abs(b) * cos(t)
    ny += abs(b) * sin(t)
    center = (nx, ny)
    return dst, center, fitting_curve


def find_radial_peaks(buf, rmod, lo, hi=None, pw=5):
    """Find radial peaks in Polar-converted buffer
    
    buf : Polar-converted output buffer
   rmod : radial modulation function = fitting_curve
     pw : peak width(s) to be found
    """
    h, w = buf.shape
    data = np.zeros(w)
    for j,x in enumerate(buf):
        y = (1 - j/h) * 2*pi              # yaxis (from 2pi to 0)
        data += np.roll(x, -int(rmod(y))) # roll anti-shift (to modify peak pos)
    data /= h
    
    ## Smooth with window (cf. np.signal.windows) and find peaks in
    lw = w // 200
    if lw < 3:
        lw = 3
    window = np.hanning(lw)
    rdist = np.convolve(window/window.sum(), data, mode='same')
    
    ## widths = [pw]
    widths = np.array([pw])
    peaks = np.signal.find_peaks_cwt(rdist, widths)
    
    hi = hi or np.hypot(h,w) // 2
    peaks = [p for p in peaks if lo < p < hi # limit the range of searched radius
                and rdist[p] > rdist.mean()] # and by threshold
    return rdist, peaks


class Plugin(Layer):
    """Center of Rings finder ver 1.0
    """
    menu = "&Plugins/&Basic Tools"
    category = "Basic Tools"
    unloadable = False
    
    def Init(self):
        self.params = (
            LParam("rmin", (0,2000,1), 50),
            LParam("rmax", (0,2000,1), np.nan),
        )
        self.layout("blur-threshold", self.lgbt.params, show=0, cw=0, lw=40, tw=40)
        self.layout("radii", self.params, cw=0, lw=36, tw=48)
        
        btn = wx.Button(self, label="+Execute", size=(64,22))
        btn.Bind(wx.EVT_BUTTON, lambda v: self.run(shift=wx.GetKeyState(wx.WXK_SHIFT)))
        btn.SetToolTip("S-Lbutton to enter recusive centering")
        
        self.chkplt = wx.CheckBox(self, label="rdist")
        
        self.layout(None, [btn, self.chkplt], row=2, type='vspin', tw=22)
    
    lgbt = property(lambda self: self.parent.require('lgbt'))
    
    rmin = property(lambda self: self.params[0])
    rmax = property(lambda self: self.params[1])
    
    maxloop = 4 # �T�����[�v�̉񐔐��� maximum loop
    
    def run(self, frame=None, shift=0):
        if not frame:
            frame = self.graph.frame
        
        center = edi.centroid(frame.buffer)
        ## center = None
        if shift:
            nx, ny = frame.xytopixel(frame.selector)
            if isinstance(nx, int): # for PY2
                center = nx, ny
            else:
                center = nx[0], ny[0]
        
        ## Search center and fit with model (twice at least)
        src = frame.buffer
        for i in range(self.maxloop):
            buf, center, fitting_curve, = find_ring_center(src, center, lo=int(self.rmin))
            ## print("center =", center)
        
        self.output.load(buf, name="*linpolar*", localunit=1)
        frame.selector = frame.xyfrompixel(center)
        
        ## Find peaks in radial distribution
        rdist, peaks = find_radial_peaks(buf, fitting_curve, lo=int(self.rmin))
        
        if self.chkplt.Value:
            edi.clf()
            edi.plot(rdist)
            edi.plot(peaks, rdist[peaks], 'o')
        print("peaks =", peaks)
        
        ## ���x�̍����Ƃ���ɂ��������� (oz) �Ƀ}�[�J�[��ł� (100/3 ���x)
        j = np.argmax(rdist[peaks])
        a = np.linspace(0,1,100) * 2*pi
        nr = peaks[j] + fitting_curve(a)
        r = nr * frame.unit
        xc, yc = frame.selector # center position
        X = xc + r * np.cos(a)
        Y = yc + r * np.sin(a)
        
        l,r,b,t = frame.extent
        x, y = np.array([(x,y) for x,y in zip(X,Y) if l<x<r and b<y<t]).T
        z = frame.xytoc(x, y)
        oz = (z > 2 * rdist.mean())
        frame.markers = (x[oz][0:-1:3], y[oz][0:-1:3]) # scatter markers onto the arc
        
        ## �T�[�N���`�� (�m�F�p)
        ## self.Arts = self.graph.axes.plot(x, y, 'c-', lw=0.5, alpha=0.75)
        ## self.Arts[0].set_data(x, y) # draw line arc
        ## self.Draw()
