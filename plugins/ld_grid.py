#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
from itertools import chain
import wx
import numpy as np
from numpy import pi,exp,cos,sin
from scipy import optimize
from mwx import LParam
from mwx.graphman import Layer


def calc_dist(u, D, d):
    return complex(D, d) * u * u * np.conj(u)


def calc_aspect(u, r, t):
    t *= pi/180
    ## return ((1+r) * u + (1-r) * np.conj(u) * exp(2j*t)) / 2
    return u + (1-r) * np.conj(u) * exp(2j*t)


class Model(object):
    """グリッドパターンモデル [mm]
     grid : length per grid [mm/gr]
     tilt : rotation angles of pattern
    xc,yc : position of center
    """
    nGrid = 30 # number of grid (in x,y) --> (N+1) 本のグリッド線を引く
    
    def __init__(self, parent):
        self.owner = parent
    
    def basegrid(self, params):
        """描画範囲の基準グリッド (複素数配列の組) を返す
        メッシュ数と分割数は同数である必要はないが，ここでは同数．
        """
        grid, tilt, xc, yc = np.float32(params)
        u = grid * exp(1j * tilt * pi/180)
        N = self.nGrid
        lu = u * N * np.linspace(-0.5, 0.5, N+1) # 1/(N)grid
        X = xc + lu
        Y = yc + lu
        return [(X + 1j * y) for y in Y]\
             + [(x + 1j * Y) for x in X]
        
        ## メッシュ数と分割数は同数の場合，これでＯＫ
        ## X, Y = np.meshgrid(lu, lu)
        ## return (xc + 1j * yc) + np.vstack((X + 1j * Y, Y + 1j * X))
    
    def residual(self, fitting_params, x, y):
        """最小自乗法の剰余函数"""
        grid, tilt, xc, yc, ratio, phi, D, d = fitting_params
        z = x + 1j*y
        
        ## φ超過時の補正
        if not -90 < phi < 90:
            ## print("  warning! phi is over limit ({:g})".format(phi))
            if phi < -90: phi += 180
            elif phi > 90: phi -= 180
            fitting_params[5] = phi
        
        if not self.owner.thread.is_active:
            print("... Iteration stopped")
            raise StopIteration
        
        ## 検索範囲（描画範囲ではない）の基準グリッド (-N:N 十分広く設定する)
        N = int(max(np.hypot(x,y)) / grid) + 1
        u = grid * exp(1j * tilt * pi/180)
        lu = u * np.arange(-N, N+1)
        X, Y = np.meshgrid(lu, lu)
        net = (xc + 1j * yc + X + 1j * Y).ravel()
        gr = calc_aspect(net, ratio, phi) + calc_dist(net, D, d)
        
        ## 再近接グリッド点からのズレを評価する (探索範囲のリミットを設ける)
        lim = N * grid
        res = [ min(abs(gr - p))**2 for p in z if abs(p.real) < lim and abs(p.imag) < lim ]
        
        print("\b"*72 + "point({}): residual {:g}".format(len(res), sum(res)), end='')
        return res


class Plugin(Layer):
    """Distortion fitting of grid
    """
    menu = "&Plugins/Measure &Distortion"
    
    Fitting_model = Model
    fitting_params = property(
        lambda self: self.grid_params + self.ratio_params + self.dist_params)
    
    def Init(self):
        self.thread = Layer.Thread(self)
        
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
            LParam("grid", (0, 5e4, 0.1), 1.0),
            LParam("tilt", (-90, 90, 0.1), 0.0),
            LParam("xc", (-200, 200, 0.1), 0.0),
            LParam("yc", (-200, 200, 0.1), 0.0),
        )
        for lp in chain(self.dist_params, self.ratio_params, self.grid_params):
            lp.bind(lambda v: self.calc())
        
        self.btn = wx.Button(self, label="+Execute", size=(80,22))
        self.btn.Bind(wx.EVT_BUTTON,
            lambda v: self.thread.Start(self.run, skip=wx.GetKeyState(wx.WXK_SHIFT)))
        
        self.btn.SetToolTip("S-Lbutton to skip estimating grid params")
        
        self.order = LParam("order", (0,6,1), 3)
        
        self.text = wx.TextCtrl(self, size=(160,60), style=wx.TE_READONLY|wx.TE_MULTILINE)
        
        self.layout("Distortion", self.dist_params, cw=64, lw=20, tw=64, show=0)
        self.layout("XY Aspects", self.ratio_params, cw=64, lw=20, tw=64)
        self.layout("Grid paramter", self.grid_params, cw=56, lw=28, tw=64)
        self.layout(None, [self.btn, self.order], row=2, type='choice', cw=40, lw=36)
        self.layout(None, [self.text], expand=2)
        
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
        r, t = np.float32(self.ratio_params)
        D, d = np.float32(self.dist_params)
        
        grid0 = list(self.model.basegrid(self.grid_params))
        grid1 = list(calc_aspect(z,r,t) + calc_dist(z,D,d) for z in grid0)
        grids = grid0 + grid1 # リスト和
        
        for art,z in zip(self.Arts, grids): # グリッドの設定
            art.set_data(z.real, z.imag)
        self.Draw()
        
        ## e = (1-r) / (1+r)
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
        
        x, y = frame.markers
        if not x.size:
            print(self.message("- Abort: no markers in the frame: {!r}".format(frame.name)))
            return
        
        ## re-init (erase) grid bound to the frame
        self.init_grid(frame.axes)
        
        with self.thread:
            ## 初期グリッドパラメータの見積もり
            if not skip:
                print("estimating initial grid paramtres... order(0)")
                self.find_near_grid(x, y)
            
            ## 最適グリッドパラメータの見積もり
            order = self.order.value
            if order > 0:
                result = optimize.leastsq(self.model.residual,
                    np.float32(self.fitting_params), args=(x,y), ftol=10**-order)
                
                for lp,v in zip(self.fitting_params, result[0]):
                    lp.value = v
            
            ## check final result
            res = self.model.residual(np.float32(self.fitting_params), x, y)
            
            print("... refined with order({})".format(order),
                  ":res {:g}".format(np.sqrt(np.average(res)) / frame.unit))
            self.calc()
    
    def find_near_grid(self, x, y):
        dx = np.diff(x)
        dy = np.diff(y)
        dl = np.hypot(dx,dy) # 近接スポットの距離のうち最小のやつを求める
        j = dl.argmin()
        g = dl[j]
        t = np.arctan(dy[j]/dx[j]) * 180/pi
        for lp,v in zip(self.grid_params, (g, t, x[j], y[j])):
            lp.value = v


if __name__ == "__main__":
    model = Model(None)
    print(*enumerate(model.basegrid((100, 0, 0, 0))), sep='\n')
