#! python
# -*- coding: shift-jis -*-
import scipy as np
from mwx.graphman import Layer
from pylots.temixins import CompInterface, TEM
from pyJeol.legacy import DeflSystem


class Plugin(CompInterface, Layer):
    """Plugin of compensation
    Adjust iscomp1-shift [alpha]
    """
    caption = "ISSHIFT"
    conf_key = 'compisshift'
    
    ## PYJEM �ɂ� ISCOMP ���Ȃ����� legacy �𒼐ڎg��
    ## ISCOMP �ɂ͎擾�R�}���h���Ȃ��̂ŁC�����ł͓����ϐ��Ŋo���Ă���
    ## Notify �����݂��Ȃ��̂ŁC���̒l�����u�̎��ۂ̒l�ƈ�v����Ƃ͌���Ȃ�
    __index = [0x8000, 0x8000]
    
    @property
    def index(self):
        return np.array(self.__index)
    
    @index.setter
    def index(self, v):
        self.__index = v
        DeflSystem.Write('IS1SHIFTX', v[0])
        DeflSystem.Write('IS1SHIFTY', v[1])
    
    wobbler = TEM.IS1
    
    spot = property(lambda self: self.parent.require('beam_spot'))
    deflector = property(lambda self: self.parent.require('beam_tilt'))
    
    @property
    def conf_table(self):
        return self.config[self.conf_key][0]
    
    def cal(self):
        with self.save_excursion(mmode='DIFF'):
            self.index = [0x8000, 0x8000] # ���_�ɏ��������ĊJ�n����
            self.spot.focus()
            return CompInterface.cal(self)
    
    def execute(self):
        with self.thread:
            with self.save_excursion(mmode='DIFF'):
                return self.cal()
