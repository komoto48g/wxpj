#! python3
# -*- coding: utf-8 -*-
"""deb utility

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
from six.moves import builtins
import mwx
import numpy as np
import editor as edi

builtins.plot = edi.plot
builtins.mplot = edi.mplot
builtins.splot = edi.splot
builtins.imshow = edi.imshow

SHELLSTARTUP = """
import sys
import os
import wx
import mwx
import cv2
import numpy as np
from numpy import pi,nan,inf
from scipy import ndimage as ndi
from numpy.fft import fft,ifft,fft2,ifft2,fftshift,fftfreq
import siteinit as si
import editor as edi
"""

np.set_printoptions(linewidth=256) # default 75


def init_spec(self):
    """Initialize shell/editor environs
    """
    self.Execute(SHELLSTARTUP)
    
    self.set_style({
        "STC_STYLE_DEFAULT"     : "fore:#cccccc,back:#202020,face:MS Gothic,size:9",
        "STC_STYLE_CARETLINE"   : "fore:#ffffff,back:#012456,size:2",
        "STC_STYLE_LINENUMBER"  : "fore:#000000,back:#f0f0f0,size:9",
        "STC_STYLE_BRACELIGHT"  : "fore:#ffffff,back:#202020,bold",
        "STC_STYLE_BRACEBAD"    : "fore:#ffffff,back:#ff0000,bold",
        "STC_STYLE_CONTROLCHAR" : "size:9",
        "STC_P_DEFAULT"         : "fore:#cccccc,back:#202020",
        "STC_P_IDENTIFIER"      : "fore:#cccccc",
        "STC_P_COMMENTLINE"     : "fore:#42c18c,back:#004040",
        "STC_P_COMMENTBLOCK"    : "fore:#42c18c,back:#004040,eol",
        "STC_P_CHARACTER"       : "fore:#a0a0a0",
        "STC_P_STRING"          : "fore:#a0a0a0",
        "STC_P_TRIPLE"          : "fore:#a0a0a0,back:#004040,eol",
        "STC_P_TRIPLEDOUBLE"    : "fore:#a0a0a0,back:#004040,eol",
        "STC_P_STRINGEOL"       : "fore:#808080",
        "STC_P_WORD"            : "fore:#80a0ff",
        "STC_P_WORD2"           : "fore:#ff80ff",
        "STC_P_WORD3"           : "fore:#ff0000,back:#ffff00", # custom style for search word
        "STC_P_DEFNAME"         : "fore:#e0c080,bold",
        "STC_P_CLASSNAME"       : "fore:#e0c080,bold",
        "STC_P_DECORATOR"       : "fore:#e08040",
        "STC_P_OPERATOR"        : "",
        "STC_P_NUMBER"          : "fore:#ffc080",
    })
    self.wrap(0)


def dive(*args):
    """Dive into the process, from your diving point.
To Divers:
    This executes your startup script ($PYTHONSTARTUP:~/.py).
    Then, call spec (post-startup function defined above),
    """
    mwx.deb(*args,
        startup=init_spec,
        execStartupScript=True,
        introText = """
        Anything one man can imagine, other man can make real.
        --- Jules Verne (1828--1905)
        """,
        size=(854,480))


if __name__ == '__main__':
    dive()
