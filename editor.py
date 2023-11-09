#! python3
"""Editor's collection of wxpj.

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
import cv2
import numpy as np
from numpy import pi,cos,sin
from scipy import signal
## from numpy.fft import fft,ifft,fftfreq
## from numpy.fft import fft2,ifft2,fftshift
## from mpl_toolkits.mplot3d import axes3d
from matplotlib import pyplot as plt
from matplotlib import patches
from matplotlib import cm

from jgdk import Layer, LParam, Button
from wxpyJemacs import MainFrame as Frame


class Plugin(Layer):
    """Plugin as testsuite for editors functions.
    """
    menukey = "Plugins/Functions/&Editor"
    
    def Init(self):
        self.cutoffs = (
            LParam("lo", (0, 10, 0.005), 0.0),
            LParam("hi", (0, 10, 0.005), 0.0),
        )
        self.layout(
            self.cutoffs, title="truncation", # cutoff lo/hi
            row=2, cw=0, lw=16, tw=40
        )
        self.layout((
                Button(self, "imconv", self.test_imconv),
                Button(self, "imcorr", self.test_imcorr),
                Button(self, "ellipse", self.test_ellipse),
            ),
            row=2,
        )
        art = patches.Circle((0, 0), 0, color='r', lw=2, fill=0)
        self.attach_artists(self.graph.axes, art) # -> self.Arts
    
    def test_imconv(self):
        src = self.graph.buffer
        dst = imconv(src, *np.float32(self.cutoffs))
        self.output["*result of imconv*"] = dst
    
    def test_imtrunc(self):
        src = self.graph.buffer
        dst = imtrunc(src, *np.float32(self.cutoffs))
        self.output["*result of imtrunc*"] = dst
    
    def test_imcorr(self):
        src = self.graph.buffer
        self.output["*result of Corr*"] = Corr(src, src)
    
    def test_ellipse(self):
        frame = self.selected_view.frame
        src = frame.buffer
        ellipses = find_ellipses(src, ksize=3)
        print(self.message("Found {} circles.".format(len(ellipses))))
        if ellipses:
            ## Draw the first ellipse if detected.
            el = ellipses[0]
            self.draw_ellipse(el, src, frame)
        else:
            self.Draw()
        print(self.message('\b')) # Show the last message.
    
    def draw_ellipse(self, el, src, frame):
        (cx,cy), (ra,rb), angle = el
        R, n, s = calc_ellipse(src, el)
        p = R * n/s
        q = R * (1-n)/(1-s)
        if abs(p/q) > 1: # signal borderline
            art = self.Arts[0]
            art.center = frame.xyfrompixel(cx, cy)
            art.height = rb * frame.unit
            art.width = ra * frame.unit
            art.angle = -angle
            art.set_visible(1)
            self.message(' '.join((
                "c=({:.1f}, {:.1f})".format(cx, cy),
                "r=({:.1f}, {:.1f})".format(ra, rb),
                "{:.1f} deg".format(angle),
            )))
        self.message("\b; BRIGHTNESS {:.2f}/{:.2f} (S/N {:.2f})".format(p, q, p/q))
        self.selected_view.draw()


## --------------------------------
## Image conv/plot/view
## --------------------------------

def read_buffer(path):
    buf, info = Frame.read_buffer(path)
    if not isinstance(buf, np.ndarray):
        buf = np.array(buf)
    return buf, info


def write_buffer(path, buf):
    return Frame.write_buffer(path, buf)


def imcv(src):
    """Convert the image to a type that can be applied to the cv2 function.
    Note:
        CV2 normally accepts uint8/16 and float32/64.
    """
    if src.dtype in (np.uint32, np.int32): return src.astype(np.float32)
    if src.dtype in (np.uint64, np.int64): return src.astype(np.float64)
    return src


def imtrunc(buf, lo=0, hi=0):
    """Truncate buffer with cutoff (lo, hi) %."""
    a = np.percentile(buf, lo)
    b = np.percentile(buf, 100-hi)
    img = buf.copy()
    img[buf < a] = a
    img[buf > b] = b
    return img


def imconv(buf, lo=0, hi=0):
    """Convert buffer to dst<uint8> with cutoff (lo, hi) %.
    
    >>> dst = (src-a) * 255 / (b-a)
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


## --------------------------------
## maplotlib (in-shell use only)
## --------------------------------

def imshow(buf):
    plt.clf()
    plt.imshow(buf, cmap=cm.gray)
    plt.grid(True)
    plt.show()

def plot(*args, **kwargs):
    plt.plot(*args, **kwargs)
    plt.grid(True)
    plt.show()

def mplot(*args, **kwargs):
    for x in args:
        plt.plot(x, **kwargs)
    plt.grid(True)
    plt.show()

def splot(*args, **kwargs):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.plot_wireframe(*args, **kwargs)
    plt.show()

def scatter(x, y, *args, **kwargs):
    art = plt.scatter(x, y, *args, **kwargs)
    plt.grid(True)
    plt.show()

def clf():
    """clear figure (and the stack of memory)."""
    ## plt.close()
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
##     """Smooth 1D array.
##     window function: hanning, hamming, bartlett, blackman, or, None
##     """
##     w = np.ones(lw,'d') if not window else window(lw)
##     return np.convolve(w/w.sum(), src, mode='same')
## 
## def gaussian_blur1d(src, lw=11, p=1, sigma=4):
##     """Smooth 1D array with Gaussian window (cf. cv2.GaussianBlur).
##     lw : length of window
##      p : shape; p = 1 is identical to Normal gaussian,
##                 p = 1/2 the same as Laplace distribution.
##     """
##     window = signal.general_gaussian(lw, p, sig=sigma)
##     f = signal.fftconvolve(window, src)
##     f = (np.average(src) / np.average(f)) * f
##     return np.roll(f, -lw//2)


def gradx(src, ksize=5):
    """Gradients: diff by Sobel (１次微分)."""
    return cv2.Sobel(src, cv2.CV_32F, 1, 0, ksize)

def grady(src, ksize=5):
    """Gradients: diff by Sobel (１次微分)."""
    return cv2.Sobel(src, cv2.CV_32F, 0, 1, ksize)

def grad2(src, ksize=5):
    """Gradients: diff by Laplacian (２次微分)."""
    return cv2.Laplacian(src, cv2.CV_32F, ksize=ksize)


## --------------------------------
## Image FFT misc.
## --------------------------------

def fftcrop(src, maxsize=2048, center=None):
    """Resize src image to 2**N squared ROI."""
    h, w = src.shape
    m = min(h, w, maxsize)
    n = pow(2, int(np.log2(m))-1) # binary digits
    x, y = center or (w//2, h//2)
    return src[y-n:y+n, x-n:x+n]


def Corr(src, tmp, mode='same'):
    """Correlation product
    using an fft-based array flipped convolution (i.e. correlation).
    
    cf. cv2.phaseCorrelate: translational shifts between two images
    """
    src = src.astype(np.float32) - src.mean()
    tmp = tmp.astype(np.float32) - tmp.mean()
    if src.ndim == 1:
        return signal.fftconvolve(src, tmp[::-1], mode)
    else:
        ## *not-FFT-based* is too slow
        ## return signal.convolve2d(src, tmp[::-1,::-1], mode='same')
        ## return signal.correlate2d(src, tmp, mode='same', boundary='fill')
        return signal.fftconvolve(src, tmp[::-1,::-1], mode)


## --------------------------------
## Image analysis
##   find peaks, ellipses, etc.
## --------------------------------

def centroid(src):
    """centroids (重心).
    cf. ndi.measurements.center_of_mass
    """
    M = cv2.moments(src)
    cx = M['m10']/M['m00']
    cy = M['m01']/M['m00']
    return cx, cy


def find_ellipses(src, frmin=None, frmax=None, ksize=1, sortby='size'):
    """Find the rotated rectangle in which the ellipse is inscribed.
    
    Args:
        frmin   : min threshold ratio (to src.shape) of ellipses to find
        frmax   : max threshold
        ksize   : size of blur window
        sortby  : key of sorted list (pos or size:default)
    
    Returns:
        RotatedRect: (cx,cy), (ra,rb), angle
        
        (cx,cy) : center of the rectangle [pix]
        (ra,rb) : ra:width < rb:height of the rectangle [pix]
        angle   : rotation angle in clockwise (from 00:00 o'clock)
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
        return sorted(ls, key=lambda v: v[1][0], reverse=1) # 大きさで降順ソート
    
    return sorted(ls, key=lambda v: np.hypot(v[0][0]-w/2, v[0][1]-h/2)) # 位置で昇順ソート


def calc_ellipse(src, ellipse):
    """Calculate the count density.
    
    Returns:
        R : averaged count/pixel (N/S)
        n : ratio of count / N
        s : ratio of pixel / S
    
    Note:
        To get power density p:inside, q:outside,
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
    mask = np.hypot(xx/ra*2, yy/rb*2) < 1 # 楕円の短径 ra/2 < 長径 rb/2
    
    N = src.sum()   # 全カウント数
    S = src.size    # 全ピクセル数
    R = N / S       # Averaged count/pix
    Np = src[mask].sum() # 楕円の領域に入るカウント数
    Sp = mask.sum()      # 〃              ピクセル数
    
    n = Np / N  # カウント数比
    s = Sp / S  # ピクセル数比
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
    """x[3],y[3]: x,y 近接した３点から 2次式で極値の箇所を推定する．
    
    Returns:
        中央位置 x[1] からの差分値 (dx,dy)
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
    """Estimates the max/min peak pos y[x] and the value.
    2次式で極値の箇所を推定する．
    
    x は昇順ソートされていること．少なくとも３点なくてはならない
    推定位置が範囲内になければ，範囲内の極値点と判定結果を返す
    
    Returns:
        convex : 極値が凸：極大であるかどうか a<0 ?
        valid  : 求める推定値 (最大／最小) 存在し，かつ，範囲内に収まっているか ?
    """
    N = len(x)
    if N < 3:
        raise ValueError("find_local_extremum: data length must be more than 2")
    
    n = np.argmax(y) if max else np.argmin(y)   # 最大か最小のどちらかを求める
    j = 1 if n==0 else N-2 if n==N-1 else n     # 端であれば内側にずらしておく
    dx, dy, convex, ok = qrsp(x[j-1:j+2], y[j-1:j+2]) # ３点評価
    
    valid = ok and (max and convex) or (not max and not convex)
    if valid:
        xo = x[j] + dx # 凸で範囲内 (max)，もしくは 凹で範囲内 (min)
        yo = y[j] + dy
    else:
        xo = x[n] # 極値は範囲内に存在するが，求める最大／最小ではない，もしくは，
        yo = y[n] # 極値は範囲外であるが，外挿は危険なので，範囲内の最大／最小を返す
    return xo, yo, convex, valid


def find_local_extremum2d(src, max=True):
    """Estimate the max/min peak pos [x,y] and the value.
    2次式で極値の箇所を推定する．
    
    推定位置が範囲内にあるとは限らない．
    max:凹，min:凸，および，鞍点の場合は None を返す
    """
    h, w = src.shape
    n = src.argmax() if max else src.argmin()   # 最大か最小のどちらかを求める
    ny, nx = np.unravel_index(n, src.shape)     # 極大値 or 極小値の位置 (x,y)
    
    j = 1 if nx==0 else w-2 if nx==w-1 else nx  # 端であれば内側にずらしておく
    i = 1 if ny==0 else h-2 if ny==h-1 else ny  # 〃
    
    dx, dzx, cx, ok_x = qrsp([-1,0,1], src[i, j-1:j+2])
    dy, dzy, cy, ok_y = qrsp([-1,0,1], src[i-1:i+2, j])
    
    valid = ok_x and ok_y and (max and cx and cy) or not (max or cx or cy)
    if valid:
        return j+dx, i+dy, src[i,j]+dzx+dzy, valid
    return nx, ny, src[ny,nx], valid


def match_pattern(src, temp, method=cv2.TM_CCOEFF_NORMED):
    """Match_pattern of src image to template image.
    
    The depth must be (CV_8U or CV_32F)
    
    The comparison method is one of the following:
        'TM_CCOEFF', 'TM_CCOEFF_NORMED',
        'TM_CCORR',  'TM_CCORR_NORMED',
        'TM_SQDIFF', 'TM_SQDIFF_NORMED',
    """
    src = imconv(src)
    temp = imconv(temp)
    res = cv2.matchTemplate(src, temp, method)
    minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(res)
    if method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
        return res, minLoc
    return res, maxLoc


def eval_shift(src, src2, div=4):
    """Evaluate image shfit src --> src2 in pix.
    """
    h, w = src.shape
    xo, yo = w//2, h//2
    wt, ht = w//div, h//div  # template pattern in the src divided by div
    xt = xo - wt//2
    yt = yo - ht//2
    temp = src[yt:yt+ht, xt:xt+wt]
    
    dst, (x, y) = match_pattern(src2, temp)
    ho, wo = dst.shape
    dx = x - wo//2
    dy = y - ho//2
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
