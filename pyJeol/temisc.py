#! python3
"""Editor's collection of TEM miscellaneous functions

Author: Kazuya O'moto <komoto@jeol.co.jp>
see also: scipy.constants
"""
import numpy as np
from numpy import pi,sqrt


P_HBAR      = 1.054589e-34  # J.s
P_H         = 6.626176e-34  # J.s
P_C         = 2.997925e+8   # c [m/s]
P_E         = 1.602189e-19  # electron.charge [C]
P_K         = 1.380662e-23  # Boltzmann const k [J/K]
P_DE        = 8.854185e-12  # dielectric const 1/cc/MU
P_MU        = 1.256637e-6   # magnetic permeability 4pi * E-7
P_EM        = 9.109534e-31  # electron.mass [kg]
P_PM        = 1.672649e-27  # proton.mass [kg]
P_NM        = 1.674929e-27  # neutron.mass [kg]
P_UM        = 1.6605390e-27 # unified atomic mass (=1Da,1u) 1/12 of C12

P_e_m       = 1.758805e+11  # e/m
P_m_e       = 5.685680e-12  # m/e
P_e_2mcc    = 9.784667e-7   # e/2mcc
P_e_2m_sqrt = 2.965472e+5   # sqrt(e/2m) [m/s]


class Environ(object):
    """Electro-optik environment base class.
    """
    def __init__(self, v):
        self.acc_v = v
        self.ustar = u = v * (1 + P_e_2mcc * v)
        self.cstar = (1 + 2 * P_e_2mcc * v) / (1 + P_e_2mcc * v)
        self.elambda = P_H / sqrt(2 * P_EM * P_E * u)
        self.elgamma = 1 + 2 * P_e_2mcc * v
        self.elbeta  = sqrt(1 - 1 / self.elgamma**2)
        
        ## Xb = mv/e = sqrt(2mU/e) [ T.m ]
        self.Xb = sqrt(2 * P_EM * u / P_E)
        
        ## Xe = mvv/e = (2U/gamma) [ V ]
        self.Xe = 2 * u / self.elgamma
        
        ## Round lens rotation angle coefficient [deg/A]
        ## j2deg := sqrt(e/8mU) mu * j = (1/2Xb * mu) * j
        self.j2deg = 180/pi * P_MU / 2 / self.Xb


def mrange(*args):
    """10(Log)-step mag numbers as jeol style.
    Returns a split list of ranges that accept mag values in [1e-1:1e+9).
    
    Args:
        args: i,j,k,...l,m
              -> [0:i),[i:j),[j:k),...[l:m]
    
    >>> mrange(a,b) # -> [a:b]
    >>> mrange(a,b,c) # -> [a:b), [b:c]
    """
    if len(args) == 2:
        a, b = args
        return np.array([x for x in mrange.mags if a <= x <= b], dtype=np.int32)
    lm = list(args)
    lm[-1] += 0.02  # 最後の引数は含めるようにかさ上げしておく
    return [mrange(a, b-0.01) for (a, b) in zip(lm, lm[1:])]

mrange.mags = [m * (10**n) for n in range(-1,8)
                           for m in (1,1.2,1.5,2,2.5,3,4,5,6,8)]


class HexadecimalMixin(object):
    def __init__(self, hi, lo, validate=True):
        hi, lo = int(hi), int(lo)
        self.value = (hi << self.BITS) + lo
        
        if not validate and lo <= self.LO:
            self.coarse = hi
            self.fine = lo
        else:
            m = self.HI << self.BITS # 上位 BIT 最大値
            c = self.LO // 2         # 下位 BIT 中間値
            if self.value < c:
                self.coarse = 0
                self.fine = self.value
            elif self.value > m + c:
                self.coarse = self.HI
                self.fine = self.value - m
            else:
                hi, lo = divmod(self.value - c, self.offset)
                self.coarse = hi
                self.fine = lo + c
    
    def __int__(self):
        return self.value
    
    def __str__(self):
        return "{:,d} ({:04X},{:04X}) ".format(self.value, self.coarse, self.fine)


class FLHex(HexadecimalMixin):
    """FL hex 19bit/12bit.
    
    HI: ■□□□■□□□■□□□                FFF<<7 = 524,160
    LO:               ■□□□■□□□■□□□  FFF    =   4,095
    
    Init with a pare of hex values := (coarse, fine).
    If validate is True, lo is forced become near the medium point.
    
    >>> Hex(hi, lo, validate)
    # or
    >>> Hex(0, value) # with one decimal value
    """
    HI = 0xfff
    LO = 0xfff
    BITS = 7
    offset = (1 << BITS)
    maxval = (HI << BITS) + LO


class OLHex(HexadecimalMixin):
    """OL hex 21bit/16bit.
    
    HI: ■□□□■□□□■□□□■□□□            FFFF<<5 = 2,097,120
    LO:           ■□□□■□□□■□□□■□□□  FFFF    =    65,535
    
    Init with a pare of hex values := (coarse, fine).
    If validate is True, lo is forced become near the medium point.
    
    >>> Hex(hi, lo, validate)
    # or
    >>> Hex(0, value) # with one decimal value
    """
    HI = 0xffff
    LO = 0xffff
    BITS = 5
    offset = (1 << BITS)
    maxval = (HI << BITS) + LO


if __name__ == "__main__":
    hbar = P_HBAR
    h    = P_H
    c    = P_C
    e    = P_E
    k    = P_K
    m    = P_EM
    de   = P_DE
    mu   = P_MU
    
    print(np.int32(mrange.mags))
    print(np.int32(mrange(100,100e3)))
    
    for m in mrange(100,1000,10e3,100e3,1e6):
        print(np.int32(m))
    
    print("$FLHex.maxval = {!r}".format(FLHex.maxval))
    print(
        FLHex(0xccc, 0xccc, False),
        FLHex(0xccc, 0xccc, True),
        FLHex(0xfff, 0xfff),
        '',
        FLHex(0xffff, 0xfff, False),
        FLHex(0xffff, 0xfff, True),
        '',
        FLHex(0, 0xfff, False),
        FLHex(0, 0xfff, True),
        FLHex(0, 0xffff, False),
        FLHex(0, 0xffff, True),
        FLHex(0, 528256),
        '',
        sep='\n'
    )
