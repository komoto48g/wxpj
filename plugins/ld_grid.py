#! python3
import wx
import numpy as np
from numpy import pi,exp,cos,sin
from scipy import optimize

from jgdk import Layer, Thread, LParam


def _valist(params):
    return list(p.value for p in params)


def calc_dist(u, D, d):
    return complex(D, d) * u * u * np.conj(u)


def calc_aspect(u, r, t):
    t *= pi/180
    ## return ((1+r) * u + (1-r) * np.conj(u) * exp(2j*t)) / 2
    return u + (1-r) * np.conj(u) * exp(2j*t)


class Model(object):
    """グリッドパターンモデル [mm].
    
    grid    : length per grid [mm/gr]
    tilt    : rotation angles of pattern
    xc, yc  : position of center
    """
    nGrid = 30 # number of grid (in x,y) --> (N+1) 本のグリッド線を引く
    
    def __init__(self, parent):
        self.owner = parent
    
    def basegrid(self, params):
        """描画範囲の基準グリッド (複素数配列の組)
        """
        grid, tilt, xc, yc = _valist(params)
        u = grid * exp(1j * tilt * pi/180)
        N = self.nGrid
        ## メッシュ数と分割数は同数である必要はないが，ここでは同数
        lu = u * N * np.linspace(-0.5, 0.5, N+1) # 1/(N)grid
        X = xc + lu
        Y = yc + lu
        return [(X + 1j * y) for y in Y]\
             + [(x + 1j * Y) for x in X]
    
    def residual(self, fitting_params, x, y):
        """最小自乗法の剰余函数
        """
        grid, tilt, xc, yc, ratio, phi, D, d = fitting_params
        z = x + 1j*y
        
        ## φ超過時の補正
        if not -90 < phi < 90:
            ## print("  warning! phi is over limit ({:g})".format(phi))
            if phi < -90: phi += 180
            elif phi > 90: phi -= 180
            fitting_params[5] = phi
        
        if not self.owner.thread.active:
            print("... Iteration stopped")
            raise StopIteration
        
        ## 検索範囲（描画範囲ではない）の基準グリッド (-N:N 十分広く設定する)
        N = int(max(np.hypot(x,y)) / grid) + 1
        u = grid * exp(1j * tilt * pi/180)
        lu = u * np.arange(-N, N+1)
        X, Y = np.meshgrid(lu, lu)
        net = (xc + 1j * yc) + (X + 1j * Y).ravel()
        gr = calc_aspect(net, ratio, phi) + calc_dist(net, D, d)
        
        ## 再近接グリッド点からのズレを評価する (探索範囲のリミットを設ける)
        lim = N * grid
        res = [ min(abs(gr - p))**2 for p in z if abs(p.real) < lim and abs(p.imag) < lim ]
        
        print("\b"*72 + "point({}): residual {:g}".format(len(res), sum(res)), end='')
        return res


class Plugin(Layer):
    """Distortion fitting of grid.
    """
    menukey = "Plugins/&Measure Tools/"
    
    Fitting_model = Model
    
    fitting_params = property(
        lambda self: self.grid_params + self.ratio_params + self.dist_params)
    
    def Init(self):
        self.thread = Thread(self)
        
        kwds = dict(handler=self.calc)
        x = 5e-3
        self.dist_params = (
            LParam("D", (-x, x, x/1e5), 0.0, '{:.3g}'.format, **kwds),
            LParam("d", (-x, x, x/1e5), 0.0, '{:.3g}'.format, **kwds),
        )
        self.ratio_params = (
            LParam("γ", (0.5, 1.5, 0.001), 1.0, **kwds),
            LParam("φ", (-90, 90, 0.1), 0.0, **kwds),
        )
        self.grid_params = (
            LParam("grid", (0, 5e4, 0.1), 1.0, **kwds),
            LParam("tilt", (-90, 90, 0.1), 0.0, **kwds),
            LParam("xc", (-200, 200, 0.1), 0.0, **kwds),
            LParam("yc", (-200, 200, 0.1), 0.0, **kwds),
        )
        
        self.btn = wx.Button(self, label="+Execute", size=(80,22))
        self.btn.Bind(wx.EVT_BUTTON, lambda v: self.thread.Start(self.run))
        self.btn.SetToolTip(self.run.__doc__.strip())
        
        self.order = LParam("order", (0,6,1), 3)
        
        self.text = wx.TextCtrl(self, size=(160,60), style=wx.TE_READONLY|wx.TE_MULTILINE)
        
        self.layout(self.dist_params, title="Distortion", type='slider', cw=64, lw=20, tw=64, show=0)
        self.layout(self.ratio_params, title="XY Aspects", type='slider', cw=64, lw=20, tw=64)
        self.layout(self.grid_params, title="Grid parameter", type='slider', cw=56, lw=28, tw=64)
        self.layout((self.btn, self.order), row=2, type='choice', cw=40, lw=36)
        self.layout((self.text,), expand=2)
        
        self.model = self.Fitting_model(self)
        self.init_grid(self.graph.axes)
    
    def init_grid(self, axes):
        grid = self.model.basegrid(self.grid_params)
        self.Arts = [axes.plot([], [], 'k--', lw=0.5, alpha=0.75)[0] for z in grid]\
                  + [axes.plot([], [], 'r-',  lw=0.5, alpha=0.75)[0] for z in grid]
    
    def calc(self):
        """Calculate aspect ratio.
        
        アスペクト比： R1=Y/X, R2=Y2/X2 を計算する．
        アスペクト比ずれ＋３次歪率を考慮したグリッドデータに変換して描画する．
        """
        r, t = _valist(self.ratio_params)
        D, d = _valist(self.dist_params)
        
        grid0 = list(self.model.basegrid(self.grid_params))
        grid1 = list(calc_aspect(z,r,t) + calc_dist(z,D,d) for z in grid0)
        grids = grid0 + grid1 # リスト和
        
        for art,z in zip(self.Arts, grids): # グリッドの設定
            art.set_data(z.real, z.imag)
            art.set_clip_on(False)
        
        self.Draw()
        
        e = (1 - r)
        t *= pi/180
        R1 = (1 - e * cos(2*t)) / (1 + e * cos(2*t))
        R2 = (1 - e * sin(2*t)) / (1 + e * sin(2*t))
        
        ## R50 の歪率指標：アスペクト比ずれ(Y/X)＋３次歪率
        ## R = 50
        ## d = abs(complex(*self.dist_params)) * (R ** 2)
        
        self.text.SetValue("\n".join((
            "Y/X = {:.3f}".format(R1),
            "Y2/X2 = {:.3f}".format(R2),
            "Aspect ε = {:.2%}".format((r-1)*2),
            ## "Total(R50) = {:.2%}".format(d + (r-1)*2),
        )))
        return R1, R2
    
    def run(self, frame=None, skip=False):
        """Calculate parameters for fitting markers as a grid pattern.
        
        [S-Lbutton] Skip estimation of the initial grid params.
        
        Args:
            frame   : target frame
                      If not specified, the last selected frame is given.
            skip    : Skip `find_init_grid` order(0) process.
                      True is given if the shift key is being pressed.
        """
        if not frame:
            frame = self.selected_view.frame
        
        skip = skip or wx.GetKeyState(wx.WXK_SHIFT)
        
        x, y = frame.markers
        if not x.size:
            print(self.message("- Abort: no markers in the frame: {!r}".format(frame.name)))
            return
        
        ## re-init (erase) grid bound to the frame
        self.init_grid(frame.axes)
        
        with self.thread.entry():
            ## 初期グリッドパラメータの見積もり
            if not skip:
                print("estimating initial grid paramtres... order(0)")
                self.find_init_grid(x, y)
            
            ## 最適グリッドパラメータの見積もり
            order = self.order.value
            if order > 0:
                result = optimize.leastsq(self.model.residual,
                    _valist(self.fitting_params), args=(x,y), ftol=10**-order)
                
                for lp, v in zip(self.fitting_params, result[0]):
                    lp.value = v
            
            ## check the final result
            res = self.model.residual(_valist(self.fitting_params), x, y)
            
            print("... refined with order({})".format(order),
                  ":res {:g}".format(np.sqrt(np.average(res)) / frame.unit))
            self.calc()
            
            frame.annotation = ', '.join(self.text.Value.splitlines())
    
    def find_init_grid(self, x, y):
        """Find the initial grid position."""
        lx = []
        ly = []
        ld = []
        for i in range(len(x)):
            d = np.hypot(x-x[i], y-y[i])
            d[i] = np.inf
            j = d.argmin() # j-i 近接スポット間の距離のうち最小のやつ
            ld.append(d[j])
            lx.append(x[j] - x[i])
            ly.append(y[j] - y[i])
            
        ## k = ld.index(np.median(ld))
        k = ld.index(np.percentile(ld, 50, interpolation='nearest'))
        g = ld[k]
        t = np.arctan(ly[k]/lx[k]) * 180/pi
        for lp, v in zip(self.grid_params, (g, t, x[0], y[0])):
            lp.value = v
