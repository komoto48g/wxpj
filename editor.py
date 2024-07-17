#! python3
"""Editor's collection of wxpj.
"""
import numpy as np
from numpy import pi, cos, sin
from numpy.fft import fft2, fftshift
import cv2
from matplotlib import pyplot as plt
from matplotlib import cm


## --------------------------------
## Image conv/plot/view
## --------------------------------

def read_buffer(path):
    from wxpyJemacs import MainFrame as Frame

    buf, info = Frame.read_buffer(path)
    if not isinstance(buf, np.ndarray):
        buf = np.array(buf)
    return buf, info


def write_buffer(path, buf):
    from wxpyJemacs import MainFrame as Frame

    return Frame.write_buffer(path, buf)


def imcv(src):
    """Convert the image to a type that can be applied to the cv2 function.
    Note:
        CV2 normally accepts uint8/16 and float32/64.
    """
    if src.dtype in (np.uint32, np.int32): return src.astype(np.float32)
    if src.dtype in (np.uint64, np.int64): return src.astype(np.float64)
    return src


def imconv(src, hi=0, lo=0):
    """Convert buffer to dst<uint8> with cutoff hi/lo %.
    
    >>> dst = (src-a) * 255 / (b-a)
    """
    if src.dtype == np.uint8:
        return src
    
    if src.dtype in (np.complex64, np.complex128): # fft pattern
        src = np.log(1 + abs(src))
    
    if src.ndim > 2:
        ## R,G,B = src[..., 0:3]
        ## y = R * 0.299 + G * 0.587 + B * 0.114
        ## return y.astype(src.dtype)
        src = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY) # rgb2gray
    
    a = np.percentile(src, lo) if lo else src.min()
    b = np.percentile(src, 100-hi) if hi else src.max()
    
    r = (255 / (b - a)) if a < b else 1
    img = np.uint8((src - a) * r) # copy buffer
    img[src < a] = 0
    img[src > b] = 255
    return img


## --------------------------------
## maplotlib (in-shell use only)
## --------------------------------

def imshow(src):
    plt.clf()
    plt.imshow(src, cmap=cm.gray)
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
## Image analysis using FFT / misc.
## --------------------------------

def enhanced_fft(src, ratio=1):
    """FFT intensity image with pseudo background subtraction using cv2.linearPolar.
    
    Args:
        ratio: ratio of the polar-transform radius to n,
               where the src shape is (2n, 2n).
    """
    src = fftshift(fft2(src))   # fft2
    buf = np.log(1 + abs(src))  # log intensity
    h, w = buf.shape            # shape: (2n, 2n)
    n = h//2
    rmax = n * ratio
    buf = cv2.linearPolar(buf, (w/2, h/2), rmax, cv2.WARP_FILL_OUTLIERS)
    buf -= sum(buf) / h # バックグラウンド(ぽい)強度を引いてみる
    
    buf = cv2.linearPolar(buf, (w/2, h/2), rmax, cv2.WARP_INVERSE_MAP)
    ## Note:
    ##     ↓逆変換を何度か呼び出すと変な結果になるバグ？▲θ=±πの部分が回復しない
    ## N = np.arange(-n, n, dtype=np.float32),
    ## X, Y = np.meshgrid(N, N)
    ## map_r = w/rmax * np.hypot(Y, X)
    ## map_t = (pi + np.arctan2(Y, X)) * h/2 /pi
    ## buf = cv2.remap(buf.astype(np.float32), map_r, map_t,
    ##                 cv2.INTER_CUBIC, cv2.WARP_FILL_OUTLIERS)
    
    dst = np.exp(buf) - 1 # log --> exp で戻す
    return dst


def fftcrop(src, center=None):
    """Crop src image in 2^k square ROI centered at (x, y)."""
    h, w = src.shape
    m = min(h, w)
    n = 1 if m < 2 else 2 ** int(np.log2(m) - 1) # +-m/2
    x, y = center or (w//2, h//2)
    return src[y-n:y+n, x-n:x+n]


def Corr(src, tmp, mode='same'):
    """Correlation product
    using an fft-based array flipped convolution (i.e. correlation).
    
    cf. cv2.phaseCorrelate: translational shifts between two images
    """
    from scipy import signal

    src = src.astype(np.float32) - src.mean()
    tmp = tmp.astype(np.float32) - tmp.mean()
    if src.ndim == 1:
        return signal.fftconvolve(src, tmp[::-1], mode)
    else:
        ## *not-FFT-based* is too slow
        ## return signal.convolve2d(src, tmp[::-1,::-1], mode='same')
        ## return signal.correlate2d(src, tmp, mode='same', boundary='fill')
        return signal.fftconvolve(src, tmp[::-1,::-1], mode)


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


def eval_match_shift(src, tmp, d=4):
    """Evaluate shift [pix] of src from tmp (template) using cv2.matchTemplate.
    
    Args:
        d : Cut the template pattern divided by d from tmp.
    """
    h, w = tmp.shape
    xo, yo = w//2, h//2  # center position
    wt, ht = w//d, h//d  # template pattern (tmp divided by d)
    xt = xo - wt//2
    yt = yo - ht//2
    dst, (x, y) = match_pattern(src, tmp[yt:yt+ht, xt:xt+wt])
    h, w = dst.shape
    dx = x - w//2
    dy = y - h//2
    return dx, dy


def eval_corr_shift(src, tmp, crop=False, subpix=False):
    """Evaluate shift [pix] of src from tmp (template) using Corr.
    
    Args:
       crop   : Limit image size 2^k using fftcrop.
       subpix : Return the shift value in sub-pixel.
    """
    if crop:
        src = fftcrop(src)
        tmp = fftcrop(tmp)
    dst = Corr(src, tmp)
    if subpix:
        x, y, z, _ok = find_local_extremum2d(dst)
    else:
        y, x = np.unravel_index(dst.argmax(), dst.shape)
    h, w = dst.shape
    dx = x - w//2
    dy = y - h//2
    return dx, dy


## --------------------------------
## Image analysis; Detect ellipses
## --------------------------------

def find_ellipses(src, ksize=1, otsu=True, sortby='size'):
    """Find the rotated rectangle in which the ellipse is inscribed.
    Otsu's method is used for thresholding src image.
    
    Args:
        ksize   : size of blur window
        sortby  : key of sorted list (pos or size:default)
    
    Returns:
        RotatedRect: (cx,cy), (ra,rb), angle
        
        (cx,cy) : center of the rectangle [pix]
        (ra,rb) : ra:width < rb:height of the rectangle [pix]
        angle   : rotation angle in clockwise (from 00:00 o'clock)
    
    Note:
        Filter ellipses with rectangle sizes from ra to rb:
        >>> ls = [(c,r,a) for c,r,a in ellipses if ra < r[0] and r[1] < rb]
    """
    src = imconv(src) # src image is overwritten
    h, w = src.shape
    if ksize > 1:
        src = cv2.GaussianBlur(src, (ksize, ksize), 0)
    
    if 0 <= otsu < 1:
        t = np.percentile(src, 100 * otsu)
        t, buf = cv2.threshold(src, t, 255, cv2.THRESH_BINARY)
    else:
        t, buf = cv2.threshold(src, 0, 255, cv2.THRESH_OTSU)
    
    argv = cv2.findContours(buf, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    try:
        contours, hierarchy = argv
    except ValueError:
        _c, contours, hierarchy = argv # opencv <= 3.4.5
    
    ## Detect enclosing rectangles.
    ## Note: There should be at least 5 points to fit the ellipse.
    ##       To detect small spots, increase the amount of blur.
    ellipses = [cv2.fitEllipse(v) for v in contours if len(v) > 4]
    
    ellipses = filter(lambda v: not np.any(np.isnan(v[0:2])), ellipses) # nan を排除する
    
    if sortby == 'size':
        return sorted(ellipses, key=lambda v: v[1][0], reverse=1) # 大きさで降順ソート
    else:
        return sorted(ellipses, key=lambda v: np.hypot(v[0][0]-w/2, v[0][1]-h/2)) # 位置で昇順ソート


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
    
    src = src.astype(np.float32) # カウント数 sum<int32> では不十分
    
    N = src.sum()   # 全カウント数
    S = src.size    # 全ピクセル数
    R = N / S       # Averaged count/pix
    Np = src[mask].sum() # 楕円の領域に入るカウント数
    Sp = mask.sum()      # 〃              ピクセル数
    
    n = Np / N  # カウント数比
    s = Sp / S  # ピクセル数比
    return R, n, s


## --------------------------------
## Image analysis; Detect peaks
## --------------------------------

def _qrsp(x, y):
    """x[3],y[3]: x,y 近接した３点から 2次式で極値の箇所を推定する．
    
    Returns:
        dx, dy : 中央位置 (x[1], y[1]) からの差分値
        convex : 極値が凸：極大であるかどうか a<0 ?
        inside : 極値が範囲内に存在するか ?
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
    dx, dy, convex, ok = _qrsp(x[j-1:j+2], y[j-1:j+2]) # ３点評価
    
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
    
    dx, dzx, cx, ok_x = _qrsp([-1,0,1], src[i, j-1:j+2])
    dy, dzy, cy, ok_y = _qrsp([-1,0,1], src[i-1:i+2, j])
    
    valid = ok_x and ok_y and (max and cx and cy) or not (max or cx or cy)
    if valid:
        return j+dx, i+dy, src[i,j]+dzx+dzy, valid
    return nx, ny, src[ny,nx], valid
