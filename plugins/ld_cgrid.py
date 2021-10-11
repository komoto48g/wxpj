#! python
# -*- coding: utf-8 -*-
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
from itertools import chain
import numpy as np
from numpy import pi,exp
import plugins.ld_grid as base
## reload(base)

class Model(base.Model):
    def residual(self, fitting_params, x, y):
        """最小自乗法の剰余函数"""
        xc, yc = 0, 0
        grid, tilt, ratio, phi = fitting_params
        z = x + 1j*y
        
        ## φ超過時の補正
        if not -90 < phi < 90:
            ## print("  warning! phi is over limit ({:g})".format(phi))
            if phi < -90: phi += 180
            elif phi > 90: phi -= 180
            fitting_params[3] = phi
        
        if not self.owner.thread.is_active:
            print("... Iteration stopped")
            raise StopIteration
        
        ## 検索範囲（描画範囲ではない）の基準グリッド (十分広く設定する)
        N = int(max(np.hypot(x,y)) / grid) + 1
        u = grid * exp(1j * tilt * pi/180)
        lu = u * np.arange(-N, N+1)
        X, Y = np.meshgrid(lu, lu)
        net = (xc + 1j * yc) + (X + 1j * Y).ravel()
        gr = base.calc_aspect(net, ratio, phi)
        
        ## 再近接グリッド点からのズレを評価する (ただし，探索範囲のリミットが設けられる)
        lim = N * grid
        res = [ min(abs(gr - p))**2 for p in z if abs(p.real) < lim and abs(p.imag) < lim ]
        
        print("\b"*72 + "point({}): residual {:g}".format(len(res), sum(res)), end='')
        return res


class Plugin(base.Plugin):
    """Distortion fitting of grid (override) with fixed origin center
    """
    menu = "Plugins/Measure &Cetntral-dist"
    
    Fitting_model = Model
    fitting_params = property(
        lambda self: self.grid_params[:2] + self.ratio_params)
    
    def Init(self):
        base.Plugin.Init(self)
        
        for lp in chain(self.dist_params, self.grid_params[2:]):
            for k in lp.knobs:
                k.Enable(0)
        self.show(0, False)
