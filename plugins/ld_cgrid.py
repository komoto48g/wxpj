#! python3
from itertools import chain
import numpy as np
from numpy import pi,exp

import ld_grid as base


class Model(base.Model):
    def basegrid(self, params):
        """描画範囲の基準グリッド (複素数配列の組)
        """
        grid, tilt, xc, yc = params
        u = grid * exp(1j * tilt * pi/180)
        N = self.nGrid
        lu = u * N * np.linspace(-0.5, 0.5, N+1) # 1/(N)grid
        X = lu
        Y = lu
        return [(X + 1j * y) for y in Y]\
             + [(x + 1j * Y) for x in X]
    
    def residual(self, fitting_params, x, y):
        """最小自乗法の剰余函数"""
        self.owner.thread.check()
        
        grid, tilt, ratio, phi = fitting_params
        xc, yc = 0, 0
        z = x + 1j*y
        
        ## φ超過時の補正
        if not -90 < phi < 90:
            ## print("  warning! phi is over limit ({:g})".format(phi))
            if phi < -90: phi += 180
            elif phi > 90: phi -= 180
            fitting_params[3] = phi
        
        ## 検索範囲（描画範囲ではない）の基準グリッド (-N:N 十分広く設定する)
        N = int(max(np.hypot(x,y)) / grid) + 1
        u = grid * exp(1j * tilt * pi/180)
        lu = u * np.arange(-N, N+1)
        X, Y = np.meshgrid(lu, lu)
        net = (xc + 1j * yc) + (X + 1j * Y).ravel()
        gr = base.calc_aspect(net, ratio, phi)
        
        ## 再近接グリッド点からのズレを評価する (探索範囲のリミットを設ける)
        lim = N * grid
        res = [ min(abs(gr - p))**2 for p in z if abs(p.real) < lim and abs(p.imag) < lim ]
        
        print("\b"*72 + "point({}): residual {:g}".format(len(res), sum(res)), end='')
        return res


class Plugin(base.Plugin):
    """Distortion fitting of grid.
    (override) with fixed origin center.
    """
    Fitting_model = Model
    fitting_params = property(
        lambda self: self.grid_params[:2] + self.ratio_params)
    
    def Init(self):
        base.Plugin.Init(self)
        
        for lp in chain(self.dist_params, self.grid_params[2:]):
            for k in lp.knobs:
                k.Enable(0)
        self.show(0, False)
