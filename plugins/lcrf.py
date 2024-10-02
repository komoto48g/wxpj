#! python3
import wx
import cv2
import numpy as np
from numpy import pi
from scipy import optimize
from scipy import signal
from matplotlib import pyplot as plt
from matplotlib import patches

from wxpj import Layer, LParam
import editor as edi


class Model(object):
    """Cor-fitting model function.
    """
    def __init__(self, x, y):
        params = [0.,] * 5
        x = np.array(x)
        y = np.array(y)
        result = optimize.leastsq(self.residual, params, args=(x,y))
        self.params = result[0]
    
    def __call__(self, x):
        a, b, c, d, e = self.params
        return a + b * np.cos(x-c) + d * np.cos(2*x-e)
    
    def residual(self, params, x, y):
        self.params = params
        res = (self(x) - y)**2
        print("\b"*72 + "point({}): residual {:g}".format(len(res), sum(res)), end=' ')
        return res
    
    def mod2d(self, buf):
        """Calculate modulated image.
        
        Args:
            buf : polar-transformed output buffer
        
        Returns:
            2D-array of modulated image
        """
        h, w = buf.shape
        rsv = [self(x) for x in np.arange(0,h)/h * 2*pi][::-1] # radial-shift vectors
        data = np.resize(0., (h, w))
        for j, (x, v) in enumerate(zip(buf, rsv)):
            data[j] = np.roll(x, -int(v))
        return data
    
    def mod1d(self, buf):
        """Calculate line profile averaged with modulation correction.
        
        Args:
            buf : polar-transformed output buffer
        
        Returns:
            1D-array of modulated (+avr.) line profile
        """
        h, w = buf.shape
        data = sum(self.mod2d(buf))
        return data / h


def find_ring_center(src, center, lo, hi, N=256, tol=0.01):
    """Find center of ring pattern in buffer.
    
    極座標変換した後，角度セグメントに分割して相互相関をとる．
    center シフトを推定するために linear-polar を使用する．
    theta = 0 を基準として，相対変位 [pixels] を計算する．
    
    Args:
        src     : source buffer
        center  : initial value of center position [nx,ny]
        lo-hi   : masking size of radial axis
        N       : resizing of angular axis (total step in angle [0:2pi])
        tol     : remove peaks that leap greater than N * tol
    
    Returns:
        dst(linear-polar-transformed image), guessed center, and fitting model
    """
    h, w = src.shape
    lo = int(max(lo, 0))
    hi = int(min(hi, w//2))
    
    src = edi.imcv(src)
    dst = cv2.linearPolar(src, center, w, cv2.WARP_FILL_OUTLIERS)
    
    ## Mask X (radial) axis
    dst[:,:lo] = 0
    dst[:,hi:] = 0
    
    ## Resize Y:angular axis (計算を軽くするためリサイズ)
    rdst = cv2.resize(dst[:,lo:hi].astype(np.float32),
                      (hi-lo, N), interpolation=cv2.INTER_AREA)
    rdst -= rdst.mean()
    
    ## Mask spot noize (異常ピクセルぽいのをゼロにする > 5 sigma)
    s = np.std(rdst)
    rdst[(rdst < -5*s) | (rdst > 5*s)] = 0
    
    temp = rdst[0][::-1] # template of corr; distr at theta = 0
    data = []
    for fr in rdst:
        p = signal.fftconvolve(fr, temp, mode='same')
        data.append(p.argmax())
    
    ## 相関の計算は上から行うので，2pi --> 0 の並びになる
    ## 最終的に返す計算結果は逆転させて，0 --> 2pi の並びにする
    Y = np.array(data[::-1]) - (hi-lo)/2
    X = np.arange(0, 1, 1/len(Y)) * 2*pi
    
    ## remove leaps(2): tol より小さいとびを許容する (画素サイズに比例)
    if 1:
        tolr = max(5, tol * w/2) # default < 0.5% までなら許しちゃる
        xx, yy = [X[0]], [Y[0]]
        for x, y in zip(X[1:], Y[1:]):
            if abs(y - yy[-1]) < tolr:
                xx.append(x)
                yy.append(y)
    
    fitting_curve = Model(xx, yy)
    
    ## plt.plot(xx, yy, '+', X, fitting_curve(X))
    ## plt.grid(True)
    ## plt.show()
    
    a = fitting_curve.params[0] = 0 # (平均を基準とする) 全体のオフセット量
    b = fitting_curve.params[1]
    c = fitting_curve.params[2] % (2*pi)
    
    t = c if b>0 else c+pi # tmax: 推定中心方向
    nx, ny = center
    nx += abs(b) * np.cos(t)
    ny -= abs(b) * np.sin(t)
    return dst, (nx, ny), fitting_curve


def find_radial_peaks(data, tol=0.01):
    """Find radial peaks in polar-transformed buffer.
    
    Args:
        data : polar-transformed output buffer
    """
    w = len(data)
    lw = int(max(3, tol * w/2))
    window = signal.windows.gaussian(lw, std=lw)
    ys = np.convolve(window/window.sum(), data, mode='same')
    ## ys = data
    peaks,_attr = signal.find_peaks(ys, width=1)
    peaks = [p for p in peaks if ys[p] > ys.mean()] # filtered by threshold
    return ys, peaks


class Plugin(Layer):
    """Center of Rings finder ver 1.0
    """
    menukey = "Plugins/&Basic Tools/"
    category = "Basic Tools"
    
    lgbt = property(lambda self: self.parent.require('lgbt'))
    
    def Init(self):
        self.rmin = LParam("rmin", (0, 1, 0.01), 0.1, handler=self.set_radii)
        self.rmax = LParam("rmax", (0, 2, 0.01), 1.0, handler=self.set_radii)
        
        btn = wx.Button(self, label="+Execute", size=(64,22))
        btn.Bind(wx.EVT_BUTTON, lambda v: self.execute(shift=wx.GetKeyState(wx.WXK_SHIFT)))
        btn.SetToolTip(self.execute.__doc__.strip())
        
        self.chkplt = wx.CheckBox(self, label="rdist")
        
        self.layout(
            self.lgbt.params,
            title="blur-threshold", cw=0, lw=40, tw=40, show=0
        )
        self.layout((
                self.rmin,
                self.rmax
            ),
            title="radii", cw=0, lw=40, tw=40
        )
        self.layout((btn, self.chkplt), row=2)
    
    target_view = None
    
    def execute(self, frame=None, shift=False, maxloop=5):
        """Set markers on the diffraction ring.
        
        Search center position and fit the model parameters.
        Find the peaks in the radial distribution using polar-transformation.
        Plot some markers on the ring pattern.
        [S-Lbutton] Use the selector as the initial center position.
        
        Args:
            frame   : target frame
                      If not specified, the selected frame will be used.
            shift   : The selector is used as the initial center position.
            maxloop : maximum number of loops to search for the center position.
        """
        if not frame:
            frame = self.selected_view.frame
        if not frame:
            return
        self.target_view = frame.parent
        
        src = frame.buffer
        h, w = src.shape
        
        if shift and frame.selector.size > 0:
            nx, ny = frame.xytopixel(*frame.selector)
            c = int(nx[0]), int(ny[0])
        else:
            c = (w//2, h//2)
        
        ## Search center and fit with model
        lo = h/2 * self.rmin.value
        hi = h/2 * self.rmax.value
        for i in range(maxloop):
            buf, _c, fitting_curve, = find_ring_center(src, c, lo, hi)
            d = np.hypot(c[0]-_c[0], c[1]-_c[1])
            if d < 1:
                break
            c = _c
        self.fitting_curve = fitting_curve
        
        frame.selector = c = frame.xyfrompixel(*_c) # set selector to the center
        
        self.output.load(buf, "*lin-polar*", localunit=1)
        
        ## Find peaks in radial distribution
        rdist = fitting_curve.mod1d(buf)
        
        ## Find radial peaks in polar-transformed buffer
        rdist, peaks = find_radial_peaks(rdist)
        
        if self.chkplt.Value: # this should be called for MainThread
            plt.clf()
            plt.plot(rdist)
            plt.plot(peaks, rdist[peaks], 'o')
            plt.grid(True)
            plt.show()
        print("peaks =", peaks)
        
        ## 強度の高いところにおおざっぱ (oz) にマーカーを打つ (100/3 程度)
        j = np.argmax(rdist[peaks])
        a = np.linspace(0, 1, 100) * 2*pi
        nr = peaks[j] + fitting_curve(a)
        r = nr * frame.unit
        
        X = c[0] + r * np.cos(a)
        Y = c[1] + r * np.sin(a)
        
        l,r,b,t = frame.get_extent()
        x, y = np.array([(x, y) for x, y in zip(X, Y) if l < x < r and b < y < t]).T
        z = frame.xytoc(x, y)
        oz = (z > 2 * rdist.mean())
        frame.markers = (x[oz][0:-1:3], y[oz][0:-1:3]) # scatter markers onto the arc
        
        ## サークル描画 (確認用)
        del self.Arts
        self.attach_artists(frame.axes,
            patches.Circle(c, lo * frame.unit, color='c', ls='--', lw=1/2, fill=0),
            patches.Circle(c, hi * frame.unit, color='c', ls='--', lw=1/2, fill=0),
        )
        self.Arts += frame.axes.plot(x, y, 'c-', lw=0.5, alpha=0.75)
    
    def set_radii(self, p):
        """Set threshold ratio of [min:max] radii that gives a peak search range.
        Default is [0.1:1.0] to the image height.
        """
        view = self.target_view
        if not view or not view.frame:
            return
        frame = view.frame
        h, w = frame.buffer.shape
        try:
            c1, c2 = self.Arts[:2]
            c1.radius = h/2 * self.rmin.value * frame.unit
            c2.radius = h/2 * self.rmax.value * frame.unit
            self.Draw()
        except ValueError:
            pass
