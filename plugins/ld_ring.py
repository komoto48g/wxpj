#! python3
# -*- coding: utf-8 -*-
from itertools import chain
import wx
import cv2
import numpy as np
from numpy import pi,exp,cos,sin
from scipy import optimize
from jgdk import Layer, Thread, LParam
import editor as edi


def _valist(params):
    return list(p.value for p in params)


def calc_dist(u, D, d):
    return complex(D, d) * u * u * np.conj(u)


def calc_aspect(u, r, t):
    t *= pi/180
    ## return ((1+r) * u + (1-r) * np.conj(u) * exp(2j*t)) / 2
    return u + (1-r) * np.conj(u) * exp(2j*t)


def calc_fcc_spacings(a, N=10):
    """ calc reciprocal lattice distance (lattice < N)
    a: lattice constant for FCC
    """
    ln = range(N)
    ls = {(i*i + j*j + k*k)
            for i in ln for j in ln for k in ln
                if not((i+j)%2 or (j+k)%2 or (k+i)%2)}
    lr = a / np.sqrt(np.array(sorted(ls-{0})))
    return lr


class Model(object):
    """FCC 多結晶リングパターンモデル
   Angles : scattering angles [rad] (n=0 included)
      cam : camera length [mm]
    xc,yc : position of center
    """
    nGrid = 10 # 逆格子グリッド
    Index = 2  # fitting ring index (default 3rd ring)
    
    @property
    def Angles(self):
        le = self.owner.em.elambda
        ds = calc_fcc_spacings(a=4.080e-10, N=self.nGrid)
        return sorted(le / ds)[:20]
    
    def __init__(self, parent):
        self.owner = parent
    
    def basegrid(self, params):
        """描画範囲の基準グリッド (複素数配列の組) を返す
        円の描画リストは n=0 を含む必要はないので [1:] を返す．
        """
        cam, xc, yc = _valist(params)
        t = np.linspace(0, 1, 101) * pi
        p = complex(xc, yc)
        return [p + cam * a * exp(2j*t) for a in self.Angles]
    
    def residual(self, fitting_params, x, y):
        """最小自乗法の剰余函数"""
        cam, xc, yc, ratio, phi = fitting_params
        z = calc_aspect(x + 1j*y, 1/ratio, phi) # z = x+iy --> 逆変換 1/r
        
        ## φ超過時の補正
        if not -90 < phi < 90:
            ## print("  warning! phi is over limit ({:g})".format(phi))
            if phi < -90: phi += 180
            elif phi > 90: phi -= 180
            fitting_params[4] = phi
        
        if not self.owner.thread.active:
            print("... Iteration stopped")
            raise StopIteration
        
        ## 真円からのズレを評価する
        x, y = z.real, z.imag
        rc = cam * self.Angles[self.Index]
        res = abs((x-xc)**2 + (y-yc)**2 - rc**2)
        
        print("\b"*72 + "point({}): residual {:g}".format(len(res), sum(res)), end='')
        return res


class Plugin(Layer):
    """Distortion fitting of ring
    """
    menukey = "Plugins/&Measure Tools/"
    
    su = property(lambda self: self.parent.require('startup'))
    em = property(lambda self: self.su.em)
    
    Fitting_model = Model
    fitting_params = property(
        lambda self: self.grid_params + self.ratio_params)
    
    def Init(self):
        self.thread = Thread(self)
        
        x = 5e-3
        self.dist_params = (
            LParam("D", (-x, x, x/1e5), 0.0, '{:.3G}'.format),
            LParam("d", (-x, x, x/1e5), 0.0, '{:.3G}'.format),
        )
        self.ratio_params = (
            LParam("γ", (0.5, 1.5, 0.001), 1.0),
            LParam("φ", (-90, 90, 0.1), 0.0),
        )
        self.grid_params = (
            LParam("cam", (0, 5e4, 0.1), 100.0),
            LParam("xc", (-200, 200, 0.1), 0.0),
            LParam("yc", (-200, 200, 0.1), 0.0),
        )
        for lp in chain(self.dist_params, self.ratio_params, self.grid_params):
            lp.bind(lambda v: self.calc())
        
        self.btn = wx.Button(self, label="+Execute", size=(80,22))
        self.btn.Bind(wx.EVT_BUTTON,
            lambda v: self.thread.Start(self.run, skip=wx.GetKeyState(wx.WXK_SHIFT)))
        
        self.btn.SetToolTip("S-Lbutton to skip estimating near-max peak")
        
        self.order = LParam("ring", (1,10,1), 3)
        
        self.text = wx.TextCtrl(self, size=(160,60), style=wx.TE_READONLY|wx.TE_MULTILINE)
        
        self.layout(self.dist_params, title="Distortion", cw=64, lw=20, tw=64, show=0)
        self.layout(self.ratio_params, title="XY Aspects", cw=64, lw=20, tw=64)
        self.layout(self.grid_params, title="Grid parameter", cw=56, lw=28, tw=64)
        self.layout((self.btn, self.order), row=2, type='choice', cw=40, lw=36)
        self.layout((self.text,), expand=2)
        
        self.model = self.Fitting_model(self)
        self.init_grid(self.graph.axes)
    
    def init_grid(self, axes):
        grid = self.model.basegrid(self.grid_params)
        self.Arts = [axes.plot([], [], 'k--', lw=0.5, alpha=0.75)[0] for z in grid]\
                  + [axes.plot([], [], 'r-',  lw=0.5, alpha=0.75)[0] for z in grid]
    
    def calc(self):
        """アスペクト比： R1=Y/X, R2=Y2/X2 を計算する
        アスペクト比ずれ＋３次歪率を考慮したグリッドデータに変換して描画する
        """
        r, t = _valist(self.ratio_params)
        D, d = _valist(self.dist_params)
        
        grid0 = list(self.model.basegrid(self.grid_params))
        grid1 = list(calc_aspect(z,r,t) + calc_dist(z,D,d) for z in grid0)
        grids = grid0 + grid1 # リスト和
        
        for art,z in zip(self.Arts, grids): # グリッドの設定
            art.set_data(z.real, z.imag)
        
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
        if not frame:
            frame = self.selected_view.frame
        del self.Arts
        
        x, y = frame.markers
        if not x.size:
            print(self.message("- Abort: no markers in the frame: {!r}".format(frame.name)))
            return
        
        ## re-init (erase) grid bound to the frame
        self.init_grid(frame.axes)
        
        with self.thread:
            ## 近傍にあるピーク位置をぼかして検出する
            if not skip:
                nx, ny = frame.xytopixel(x, y)
                nx, ny = self.find_near_maximum(frame.buffer, nx, ny, times=2)
                x, y = frame.markers = frame.xyfrompixel(nx, ny)
            
            ## 最適グリッドパラメータの見積もり
            self.model.Index = self.order.value - 1
            
            result = optimize.leastsq(self.model.residual,
                _valist(self.fitting_params), args=(x,y), ftol=1e-6)
            
            for lp, v in zip(self.fitting_params, result[0]):
                lp.value = v
            
            ## check final result
            res = self.model.residual(_valist(self.fitting_params), x, y)
            
            print("... refined with order({})".format(6),
                  ":res {:g}".format(np.sqrt(np.average(res)) / frame.unit))
            self.calc()
            
            frame.update_attributes(
                results = self.parameters,
                annotation = ', '.join(self.text.Value.splitlines()),
            )
    
    def find_near_maximum(self, src, nx, ny, n=5, times=2):
        h, w = src.shape
        k = h // 200
        k += k%2 + 1
        buf = edi.imconv(src, hi=0.01, lo=0.01)
        src = cv2.GaussianBlur(buf, (k,k), 0)
        ## Note: Gaussian をかけるので実際のピーク位置とずれることがある．
        for x in range(times):
            pp = []
            for x, y in zip(nx, ny):
                if n < x < w-n and n < y < h-n:
                    buf = src[y-n:y+n+1, x-n:x+n+1] # crop around (x,y)
                    ly, lx = np.unravel_index(np.argmax(buf), buf.shape)
                    pp.append((x+lx-n, y+ly-n))
            nx, ny = np.array(pp).T
        return nx, ny


if __name__ == "__main__":
    la = calc_fcc_spacings(4.08e-10)
    print("la =", la)
    
    model = Model(None)
    print(*enumerate(model.Angles), sep='\n')
