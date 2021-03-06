#! python3
# -*- coding: utf-8 -*-
"""Editor's collection of wxpj

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
import cv2
import numpy as np
from numpy import pi,cos,sin
from scipy import signal
## from numpy.fft import fft,ifft,fftfreq
## from numpy.fft import fft2,ifft2,fftshift
from mpl_toolkits.mplot3d import axes3d
from matplotlib import pyplot as plt
from matplotlib import patches
from matplotlib import cm
## from PIL import Image
from jgdk import Layer, LParam, Button


class Plugin(Layer):
    """Plugin as testsuite for editors functions
    """
    menukey = "Plugins/Functions/&Editor"
    
    def Init(self):
        self.hi = LParam("hi", (0, 10 ,0.005), 0)
        self.lo = LParam("lo", (0, 10, 0.005), 0)
        
        self.layout((
                self.hi,
                self.lo,
            ),
            row=2, title="truncation", cw=0, lw=16, tw=40
        )
        self.layout((
                Button(self, "imconv", lambda v: self.test_imconv()),
                Button(self, "imtrunc", lambda v: self.test_imtrunc()),
                Button(self, "imcorr", lambda v: self.test_imcorr()),
                Button(self, "ellipse", lambda v: self.test_ellipse()),
            ),
            row=2,
        )
        self.circ = patches.Circle((0,0), 0, color='r', ls='solid', lw=2, fill=0, zorder=2)
        self.attach_artists(self.graph.axes, self.circ)
    
    def test_imconv(self):
        src = self.graph.buffer
        self.output["*result of imconv*"] = imconv(src, self.hi.value, self.lo.value)
    
    def test_imtrunc(self):
        src = self.graph.buffer
        self.output["*result of imtrunc*"] = imtrunc(src, self.hi.value, self.lo.value)
    
    def test_imcorr(self):
        src = self.graph.buffer
        self.output["*result of Corr*"] = Corr(src, src)
    
    def test_ellipse(self):
        art = self.circ
        frame = self.graph.frame
        src = imtrunc(frame.buffer, self.hi.value, self.lo.value)
        ellipses = find_ellipses(src, ksize=5)
        self.message("Found {} circles".format(len(ellipses)))
        if ellipses:
            el = ellipses[0]
            (cx,cy), (ra,rb), angle = el
            R, n, s = calc_ellipse(src, el)
            p = R * n/s
            q = R * (1-n)/(1-s)
            if p/q > 1: # signal
                art.center = frame.xyfrompixel(cx, cy)
                ## art.height = ra * frame.unit
                ## art.width = rb * frame.unit
                ## art.angle = 90-angle
                art.height = rb * frame.unit
                art.width = ra * frame.unit
                art.angle = -angle
                art.set_visible(1)
            self.message("\b; " + "; ".join((
                "c=({:.1f}, {:.1f})".format(cx, cy),
                "r=({:.1f}, {:.1f})".format(ra, rb),
                "{:.1f} deg".format(angle),
                "brightness {:.2f}/{:.2f} (SN {:.2f})".format(p, q, p/q),
            )))
        else:
            art.set_visible(0)
            p = src.sum() / src.size
            self.message("\b; brightness {:.1f}".format(p))
        self.graph.draw(art)


## --------------------------------
## Image conv/plot/view
## --------------------------------

def imtrunc(buf, hi=0, lo=0):
    """Truncate buffer hi/lo with given tolerance score [%]
    """
    if hi > 0 or lo > 0:
        a = np.percentile(buf, lo)
        b = np.percentile(buf, 100-hi)
        img = buf.copy()
        img[buf < a] = a
        img[buf > b] = b
        return img
    return buf


def imconv(buf, hi=0, lo=0):
    """Convert buffer to dst<uint8> := |(buf-a) * 255/(b-a)|
    hi/lo : cuts vlim with given tolerance score [%]
    """
    if buf.dtype == np.uint8:
        return buf
    
    if buf.dtype in (np.complex64, np.complex128): # fft pattern
        buf = np.log(1 + abs(buf))
    
    if buf.ndim > 2:
        ## R,G,B = buf[..., 0:3]
        ## y = R * 0.299 + G * 0.587 + B * 0.114
        ## return y.astype(buf.dtype)
        buf = cv2.cvtColor(buf, cv2.COLOR_RGB2GRAY) # rgb2gray
    
    a = np.percentile(buf, lo) if lo else buf.min()
    b = np.percentile(buf, 100-hi) if hi else buf.max()
    
    r = (255 / (b - a)) if a < b else 1
    img = np.uint8((buf - a) * r) # copy buffer
    img[buf < a] = 0
    img[buf > b] = 255
    return img


def imshow(buf):
    plt.clf()
    plt.imshow(buf, cmap=cm.gray)
    plt.grid(True)
    plt.show()

def plot(*args, **kwargs):
    """mpl default plot"""
    plt.plot(*args, **kwargs)
    plt.grid(True)
    plt.show()

def mplot(*args, **kwargs):
    """mpl multiplot"""
    for x in args:
        plt.plot(x, **kwargs)
    plt.grid(True)
    plt.show()

def splot(*args, **kwargs):
    """mpl surface plot"""
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.plot_wireframe(*args, **kwargs)
    plt.show()

def scatter(x, y, *args, **kwargs):
    """mpl scatter"""
    art = plt.scatter(x, y, *args, **kwargs)
    plt.grid(True)
    plt.show()

def clf():
    """clear figure (and the stack of memory)"""
    plt.clf()

clear = clf

## --------------------------------
## Image processing
## --------------------------------

def rotate(src, angle):
    ## return ndi.rotate(src, angle)
    h, w = src.shape
    M = cv2.getRotationMatrix2D((w/2, h/2), angle, scale=1)
    return cv2.warpAffine(src, M, (w, h))

## def blur1d(src, lw=11, window=np.hanning):
##     """smooth 1D array
##     window function: hanning, hamming, bartlett, blackman, or, None
##     """
##     w = np.ones(lw,'d') if not window else window(lw)
##     return np.convolve(w/w.sum(), src, mode='same')
## 
## def gaussian_blur1d(src, lw=11, p=1, sigma=4):
##     """smooth 1D array with Gaussian window (cf. cv2.GaussianBlur)
##     lw : length of window
##      p : shape; p = 1 is identical to Normal gaussian,
##                 p = 1/2 the same as Laplace distribution.
##     """
##     window = signal.general_gaussian(lw, p, sig=sigma)
##     f = signal.fftconvolve(window, src)
##     f = (np.average(src) / np.average(f)) * f
##     return np.roll(f, -lw//2)


def gradx(src, ksize=5):
    """gradients: diff by Sobel (????????????)"""
    return cv2.Sobel(src, cv2.CV_32F, 1, 0, ksize)

def grady(src, ksize=5):
    """gradients: diff by Sobel (????????????)"""
    return cv2.Sobel(src, cv2.CV_32F, 0, 1, ksize)

def grad2(src, ksize=5):
    """gradients: diff by Laplacian (????????????)"""
    return cv2.Laplacian(src, cv2.CV_32F, ksize=ksize)


def Corr(src, tmp):
    """Correlation product
    using an fft-based array flipped convolution (i.e. correlation)
    cf. cv2.phaseCorrelate: translational shifts between two images
    """
    src = src.astype(np.float32) - src.mean()
    tmp = tmp.astype(np.float32) - tmp.mean()
    if src.ndim == 1:
        return signal.fftconvolve(src, tmp[::-1], mode='same')
    else:
        ## *not-FFT-based* is too slow
        ## return signal.convolve2d(src, tmp[::-1,::-1], mode='same')
        ## return signal.correlate2d(src, tmp, mode='same', boundary='fill')
        return signal.fftconvolve(src, tmp[::-1,::-1], mode='same')


## --------------------------------
## Image analysis
##   find peaks, figures, etc.
## --------------------------------

def centroid(src):
    """centroids (??????)
    cf. ndi.measurements.center_of_mass
    """
    M = cv2.moments(src)
    cx = M['m10']/M['m00']
    cy = M['m01']/M['m00']
    return cx, cy


def find_ellipses(src, frmin=None, frmax=None, ksize=1, sortby='size'):
    """Find the rotated rectangle in which the ellipse is inscribed
    
    frmin : min threshold ratio (to src.shape) of ellipses to find
    frmax : max threshold
    ksize : size of blur window
   sortby : key of sorted list (pos or size:default)
   
  retval -> RotatedRect: (cx,cy), (ra,rb), angle
    (cx,cy) : center of the rectangle [pix]
    (ra,rb) : ra:width < rb:height of the rectangle [pix]
      angle : rotation angle in clockwise (from 00:00 o'clock)
    """
    src = imconv(src) # src image is overwritten
    h, w = src.shape
    rmin = 2
    rmax = np.hypot(h, w)
    if frmin: rmin = rmax * frmin
    if frmax: rmax = rmax * frmax
    if ksize > 1:
        src = cv2.GaussianBlur(src, (ksize, ksize), 0)
    
    t, buf = cv2.threshold(src, 0, 255, cv2.THRESH_OTSU)
    try:
        ## opencv <= 3.4.5
        c, contours, hierarchy = cv2.findContours(buf, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    except ValueError:
        contours, hierarchy = cv2.findContours(buf, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    ## There should be at least 5 points to fit the ellipse
    ellipses = [cv2.fitEllipse(v) for v in contours if len(v) > 4]
    ls = [(c,r,a) for c,r,a in ellipses if rmin < r[0] and r[1] < rmax]
    
    if sortby == 'size':
        return sorted(ls, key=lambda v: v[1][0], reverse=1) # ???????????????????????????
    
    return sorted(ls, key=lambda v: np.hypot(v[0][0]-w/2, v[0][1]-h/2)) # ????????????????????????


def calc_ellipse(src, ellipse):
    """Calculate the count density
  retval -> R : averaged count/pixel (N/S)
            n : ratio of count / N
            s : ratio of pixel / S
    Note: power density p:inside, q:outside,
          p = R * n/s
          q = R * (1-n)/(1-s)
    """
    (cx,cy), (ra,rb), angle = ellipse
    h, w = src.shape
    y, x = np.ogrid[-h/2:h/2, -w/2:w/2]
    yo, xo = cy-h/2, cx-w/2
    t = angle * pi/180
    xx = (x-xo) * cos(t) + (y-yo)*sin(t)
    yy = (x-xo) *-sin(t) + (y-yo)*cos(t)
    mask = np.hypot(xx/ra*2, yy/rb*2) < 1 # ??????????????? ra/2 < ?????? rb/2
    
    N = src.sum()   # ??????????????????
    S = src.size    # ??????????????????
    R = N / S       # Averaged count/pix
    Np = src[mask].sum() # ???????????????????????????????????????
    Sp = mask.sum()      # ???              ???????????????
    
    n = Np / N  # ??????????????????
    s = Sp / S  # ??????????????????
    return R, n, s


## def find_peaks(y):
##     peaks, dic = signal.find_peaks(y,
##             height = y.mean(),      # height of peaks
##           distance = None,          # minimal horizontal distance
##          threshold = None,          # threshold of peaks (the vertical distance to its neighbouring)
##         prominence = 0.05,          # prominence of peaks
##              width = y.size/1000,   # width of peaks
##     )
##     return peaks

## def find_peaks(y):
##     widths = np.array([2.0])
##     return signal.find_peaks_cwt(y, widths)


def qrsp(x, y):
    """2??????????????????????????????????????????
    x[3],y[3]: x,y ??????????????????????????????
  retval -> ???????????? x[1] ?????????????????? (dx,dy)
    """
    x0 = x[0]-x[1]
    x2 = x[2]-x[1]
    dy0 = (y[0]-y[1]) / x0
    dy2 = (y[2]-y[1]) / x2
    a = (dy2 - dy0) / (x2 - x0)
    b = (dy0*x2 - dy2*x0) / (x2 - x0)
    ## cf. a,b,c = np.polyfit(x, y, 2)
    dx = -b/a/2
    dy = dx * b/2
    return dx, dy, a<0, x0<dx<x2,


def find_local_extremum(x, y, max=True):
    """2??????????????????????????????????????????
    Estimates the `max|min peak pos y[x] and the value
    x ???????????????????????????????????????????????????????????????????????????????????????
    ???????????????????????????????????????????????????????????????????????????????????????
  retval ->
    convex : ?????????????????????????????????????????? a<0 ?
     valid : ?????????????????? (???????????????) ?????????????????????????????????????????????????????? ?
    """
    N = len(x)
    if N < 3:
        raise ValueError("find_local_extremum: data length must be more than 2")
    n = np.argmax(y) if max else np.argmin(y) # ??????????????????????????????????????????
    j = 1 if n==0 else N-2 if n==N-1 else n # ????????????????????????????????????????????????
    dx, dy, convex, ok = qrsp(x[j-1:j+2], y[j-1:j+2]) # ????????????
    
    valid = ok and (max and convex) or (not max and not convex)
    if valid:
        xo = x[j] + dx # ??????????????? (max)??????????????? ??????????????? (min)
        yo = y[j] + dy
    else:
        xo = x[n] # ?????????????????????????????????????????????????????????????????????????????????????????????
        yo = y[n] # ????????????????????????????????????????????????????????????????????????????????????????????????
    return xo, yo, convex, valid


def find_local_extremum2d(src, max=True):
    """2??????????????????????????????????????????
    Estimates the `max|min peak pos [x,y] and the value
    ??????????????????????????????????????????????????????max:??????min:???????????????????????????????????? None ?????????
    """
    Ny, Nx = src.shape
    n = src.argmax() if max else src.argmin()
    ny, nx = np.unravel_index(n, src.shape)
    jx = 1 if nx==0 else Nx-2 if nx==Nx-1 else nx
    jy = 1 if ny==0 else Ny-2 if ny==Ny-1 else ny
    dx, dzx, cx, ok_x = qrsp([-1,0,1], src[jy, jx-1:jx+2])
    dy, dzy, cy, ok_y = qrsp([-1,0,1], src[jy-1:jy+2, jx])
    
    valid = ok_x and ok_y and (max and cx and cy) or not (max or cx or cy)
    if valid:
        return jx+dx, jy+dy, src[jy,jx]+dzx+dzy, valid
    return nx, ny, src[ny,nx], valid


def match_pattern(src, temp, method=cv2.TM_CCOEFF_NORMED):
    """Match_pattern of image `src to template image
    depth must be (CV_8U or CV_32F)
    
    All the 6 methods for comparison in a list `method
    in ('TM_CCOEFF', 'TM_CCOEFF_NORMED',
        'TM_CCORR',  'TM_CCORR_NORMED',
        'TM_SQDIFF', 'TM_SQDIFF_NORMED')
    """
    src = imconv(src)
    temp = imconv(temp)
    res = cv2.matchTemplate(src, temp, method)
    minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(res)
    if method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
        return res, minLoc
    return res, maxLoc


def eval_shift(src, src2, div=4):
    h, w = src.shape
    ht, wt = h//div, w//div  # template pattern in the src divided by `div
    xt = int((w - wt) / 2)   # template position lt = (xt, yt)
    yt = int((h - ht) / 2)   # 
    temp = src[yt:yt+ht, xt:xt+wt]
    
    dst, (l,t) = match_pattern(src2, temp)
    ho, wo = dst.shape
    dx = l - wo//2
    dy = t - ho//2
    return np.array((dx, dy))


if __name__ == "__main__":
    z = np.array([
        [2.0, 2.0, 2.0],
        [2.0, 2.1, 2.0],
        [2.0, 2.0, 2.0],
    ])
    print(find_local_extremum2d(z, True))
    print(find_local_extremum2d(z, False))
    print()
    
    ## fig = plt.figure()
    ## ax = fig.add_subplot(111, projection='3d')
    ## x, y = np.mgrid[-1:1:3j,-1:1:3j]
    ## ax.plot_wireframe(x, y, z)
    ## plt.show()
    
    x = np.array([-1, 0, 1])
    y = np.array([0.2, 0.4, 0.5])
    
    print("qrsp(x,y) =", qrsp(x,y))
    print("find_local_extremum(x,y) =", find_local_extremum(x,y))
    
    a,b,c = np.polyfit(x, y, 2)
    p = np.poly1d((a,b,c))
    xx = np.linspace(2*x[0],2*x[-1],100)
    plot(xx, p(xx), x, y)


if __name__ == "__main__":
    import wx
    from jgdk import Frame
    
    app = wx.App()
    frm = Frame(None)
    frm.load_plug(__file__, show=1, dock=4)
    frm.load_buffer(u"C:/usr/home/workspace/images/sample.bmp")
    frm.Show()
    app.MainLoop()
