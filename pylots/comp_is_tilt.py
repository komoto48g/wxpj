#! python
# -*- coding: utf-8 -*-
import scipy as np
from mwx.graphman import Layer
from pylots.temixins import CompInterface, TEM
from pyJeol.legacy.jtypes import DeflSystem


class Plugin(CompInterface, Layer):
    """Plugin of compensation
    Adjust iscomp1-tilt [alpha]
    """
    caption = "ISTILT"
    conf_key = 'compistilt'
    
    ## PYJEM には ISCOMP がないため legacy を直接使う
    ## ISCOMP には取得コマンドがないので，ここでは内部変数で覚えておく
    ## Notify が存在しないので，この値が装置の実際の値と一致するとは限らない
    __index = [0x8000, 0x8000]
    
    @property
    def index(self):
        return np.array(self.__index)
    
    @index.setter
    def index(self, v):
        self.__index = v
        DeflSystem.Write('IS1TILTX', v[0])
        DeflSystem.Write('IS1TILTY', v[1])
    
    wobbler = TEM.IS2
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    deflector = property(lambda self: self.parent.require('beam_shift'))
    
    @property
    def conf_table(self):
        return self.config[self.conf_key][0]
    
    def cal(self):
        with self.save_excursion(mmode='MAG'):
            self.index = [0x8000, 0x8000] # 中点に初期化して開始する
            self.spot.focus()
            return CompInterface.cal(self)
    
    def execute(self):
        with self.thread:
            with self.save_excursion(mmode='MAG'):
                return self.cal()
