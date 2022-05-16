#! python3
# -*- coding: utf-8 -*-
"""Template of Layer

Version: 1.0
Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
import cv2
from jgdk import Layer, LParam, Button


class Plugin(Layer):
    """Plugin template ver.1
    """
    menu = "Plugins/&Template"
    menustr = "&template ver.1"
    category = "Test"
    caption = "temp.1"
    
    def Init(self):
        self.ksize = LParam("ksize", (1,99,2), 13,
                            tip="kernel window size")
        
        self.btn = Button(self, label="Run", size=(-1,22),
                          handler=lambda v: self.run(), icon='->')
        
        self.layout((self.ksize, self.btn),
            title="Gaussian blur", row=1,
            type='vspin', cw=-1, lw=36, tw=30,
        )
    
    def run(self):
        k = self.ksize.value
        src = self.graph.buffer
        dst = cv2.GaussianBlur(src, (k,k), 0.)
        self.output.load(dst, "*gauss*")
