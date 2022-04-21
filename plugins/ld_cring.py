#! python3
# -*- coding: utf-8 -*-
from itertools import chain
import plugins.ld_ring as base

## import mwx
## mwx.reload(base)

class Model(base.Model):
    def residual(self, fitting_params, x, y):
        """最小自乗法の剰余函数"""
        xc, yc = 0, 0
        cam, ratio, phi = fitting_params
        z = base.calc_aspect(x + 1j*y, 1/ratio, phi) # z = x+iy --> 逆変換 1/r
        
        ## φ超過時の補正
        if not -90 < phi < 90:
            ## print("  warning! phi is over limit ({:g})".format(phi))
            if phi < -90: phi += 180
            elif phi > 90: phi -= 180
            fitting_params[2] = phi
        
        if not self.owner.thread.is_active:
            print("... Iteration stopped")
            raise StopIteration
        
        ## 真円からのズレを評価する
        x, y = z.real, z.imag
        rc = cam * self.Angles[self.Index]
        res = abs((x-xc)**2 + (y-yc)**2 - rc**2)
        
        print("\b"*72 + "point({}): residual {:g}".format(len(res), sum(res)), end='')
        return res


class Plugin(base.Plugin):
    """Distortion fitting of ring (override) with fixed origin center
    """
    menu = "Plugins/Measure &Cetntral-dist"
    
    Fitting_model = Model
    fitting_params = property(
        lambda self: self.grid_params[:1] + self.ratio_params)
    
    def Init(self):
        base.Plugin.Init(self)
        
        for lp in chain(self.dist_params, self.grid_params[1:]):
            for k in lp.knobs:
                k.Enable(0)
        self.show(0, False)
