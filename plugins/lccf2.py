#! python3
import cv2
import numpy as np
from numpy import pi,cos,sin
from matplotlib import patches

from wxpj import Layer, LParam, Button
import editor as edi


def find_ellipses(src, rmin, rmax):
    ## Find contours in binary image
    ## ▲ src 第一引数は上書きされるので後で参照するときは注意する
    argv = cv2.findContours(src, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    try:
        contours, hierarchy = argv
    except ValueError:
        _c, contours, hierarchy = argv # opencv <= 3.4.5
    
    ## Detect enclosing rectangles
    ## Note:
    ##     At least 5 points are needed to fit an ellipse.
    ##     NaN should be eliminated.
    ellipses = [cv2.fitEllipse(v) for v in contours if len(v) > 4]
    ellipses = filter(lambda v: not np.any(np.isnan(v[0:2])), ellipses) # nan を排除する
    h, w = src.shape
    
    def _inside(v, tol=0.75/2): # 画像の端にある円を除く
        c, r, a = v
        d = tol * r[1]
        return (rmin < r[0] and r[1] < rmax and d < c[0] < w-d and d < c[1] < h-d)
    
    return sorted(filter(_inside, ellipses),
                  key=lambda v: np.hypot(v[0][0]-w/2, v[0][1]-h/2)) # 位置で昇順ソート


class Plugin(Layer):
    """Cetner of Ellipses finder.
    """
    menukey = "Plugins/&Basic Tools/"
    category = "Basic Tools"
    
    lgbt = property(lambda self: self.parent.require('lgbt'))
    
    def Init(self):
        self.rmin = LParam("rmin", (0,1000,1), 2)
        self.rmax = LParam("rmax", (0,1000,1), 200)
        
        btn = Button(self, label="+Execute", handler=self.execute)
        
        self.layout(
            self.lgbt.params,
            title="blur-threshold", cw=0, lw=40, tw=40, show=0
        )
        self.layout((
                self.rmin,
                self.rmax,
            ),
            title="rectangles", cw=0, lw=40, tw=40
        )
        self.layout((btn,))
    
    maxcount = 256 # 選択する点の数を制限する
    maxratio = 5.0 # ひずみの大きい楕円は除外する
    
    def execute(self, frame=None, otsu=True):
        """Set markers at the center of ellipses.
        
        Args:
            frame   : target frame
                      If not specified, the selected frame will be used.
            otsu    : Use Otsu's algorithm.
        """
        if not frame:
            frame = self.selected_view.frame
        del self.Arts
        del frame.markers
        
        src = self.lgbt.execute(frame, otsu)
        
        circles = find_ellipses(src, self.rmin.value, self.rmax.value)
        
        n = len(circles)
        self.message(f"Found {n} circles.")
        if not circles:
            return
        N = self.maxcount
        if n > N:
            self.message(f"Too many circles found. Limiting number to {N}.")
            circles = circles[:N]
        
        xy = []
        for (cx, cy), (ra, rb), angle in circles:
            if ra and rb/ra < self.maxratio:
                ## 不特定多数の円を描画する
                art = patches.Circle((0, 0), 0, color='r', ls='dotted', lw=1, fill=0)
                art.center = frame.xyfrompixel(cx, cy)
                art.height = ra * frame.unit
                art.width = rb * frame.unit
                art.angle = 90-angle
                self.attach_artists(frame.axes, art)
                
                ## 検出した楕円の中心をそのまま記録する
                ## 強度の偏りが出るのを防ぐため，十分ぼかし幅をとること
                xy.append(art.center)
                
                ## r = int(np.hypot(ra, rb) / 2) # max radius enclosing the area rectangle
                ## x, y = int(cx), int(cy)
                ## buf = frame.buffer[y-r:y+r+1, x-r:x+r+1]
                ## img = frame.image[y-r:y+r+1, x-r:x+r+1]
                
                ## local maximum that is found first in the region. ▲偏りが出るので NG
                ## dy, dx = np.unravel_index(buf.argmax(), buf.shape)
                
                ## local maximum :averaged (強度の偏りを考慮する) ▲偏りが出るので NG
                ## yy, xx = np.where(buf == np.amax(buf))
                ## dy, dx = np.average(yy), np.average(xx)
                
                ## centroid of masked array
                ## buf = np.ma.masked_array(img, mask_ellipse(r, ra, rb, angle))
                ## dx, dy = centroid(buf)
                ## x, y = frame.xyfrompixel(x-r+dx, y-r+dy)
                ## xy.append((x, y))
        if xy:
            frame.markers = np.array(xy).T # scatter markers if any xy


def centroid(src):
    """centroids (重心).
    cf. ndi.measurements.center_of_mass
    """
    ## Note:
    ##     moments は findContours と組み合わせても使用される．
    ##     src <int32/float32> はコンター座標とみなされる．
    buf = edi.imconv(src)
    M = cv2.moments(buf)
    cx = M['m10']/M['m00']
    cy = M['m01']/M['m00']
    return cx, cy


def mask_ellipse(r, ra, rb, angle):
    y, x = np.ogrid[-r:r+1, -r:r+1]
    yo, xo = 0, 0
    t = angle * pi/180
    xx = (x-xo) * cos(t) + (y-yo) * sin(t)
    yy = (x-xo) *-sin(t) + (y-yo) * cos(t)
    return np.hypot(xx/ra*2, yy/rb*2) > 1 # 楕円の短径 ra/2 < 長径 rb/2
