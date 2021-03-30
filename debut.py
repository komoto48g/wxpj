#! python
# -*- coding: utf-8 -*-
"""deb utility

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import numpy as np

SHELLSTARTUP = """
from __future__ import division, print_function
from __future__ import unicode_literals
from __future__ import absolute_import
import sys
import os
import wx
import mwx
import cv2
import numpy as np
from numpy import pi,nan,inf
from scipy import ndimage as ndi
from numpy.fft import fft,ifft,fft2,ifft2,fftshift,fftfreq
from matplotlib import pyplot as plt
import siteinit as si
import editor as edi
edit = self.edit
graph = self.graph
output = self.output
"""

def init_spec(self):
    """Initialize self<Inspector> interface
    """
    np.set_printoptions(linewidth=256)
    shell = self.shell
    
    @shell.define_key('C-tab')
    def insert_space_like_tab():
        """タブの気持ちになって半角スペースを入力する"""
        shell.eat_white_forward()
        _text, lp = shell.CurLine
        n = lp % 4
        shell.write(' ' * (4-n))
    
    @shell.define_key('C-S-tab')
    def delete_backward_space_like_tab():
        """SHIFT+タブの気持ちになって半角スペースを消す"""
        shell.eat_white_forward()
        _text, lp = shell.CurLine
        n = lp % 4 or 4
        for i in range(n):
            p = shell.cur
            if shell.preceding_char == ' ' and p != shell.bol:
                shell.Replace(p-1, p, '')
            else: break
    
    ## --------------------------------
    ## Inspector's shell style
    ## --------------------------------
    shell.set_style({
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
        "STC_P_DEFNAME"         : "fore:#e0c080,bold",
        "STC_P_CLASSNAME"       : "fore:#e0c080,bold",
        "STC_P_DECORATOR"       : "fore:#e08040",
        "STC_P_OPERATOR"        : "",
        "STC_P_NUMBER"          : "fore:#ffc080",
    })
    shell.wrap(0)
    
    shell.Execute(SHELLSTARTUP)


if __name__ == '__main__':
    import wx
    import mwx
    app = wx.App()
    inspector = mwx.MinidebFrame(None)
    inspector.Unbind(wx.EVT_CLOSE)
    init_spec(inspector)
    inspector.Show()
    inspector.shell.SetFocus()
    app.MainLoop()
