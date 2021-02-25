#! python
# -*- coding: utf-8 -*-
"""Editor's collection of TEM

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import wx
import mwx
from pyJeol.temcon import ItemData, TreeCtrl
from pylots import UserInterface
from mwx.graphman import Layer
import wxpyJemacs as wxpj


class PylotItem(Layer):
    """Pylot item:data layer
    
    The inherited class must have the following methods*
    * execute is called back from the parent tree
    """
    menu = None
    category = "Pylot"
    caption = property(lambda self: self.__module__)
    section = property(lambda self: "{}/{}".format(self.category, self.__module__))
    
    owner = property(lambda self: self.parent.require('Autopylot2'))
    
    @property
    def tree(self):
        return self.item.Tree
    
    @tree.setter
    def tree(self, v):
        self.item.Tree = v
        self.item.Tree[self.section] = self.item
    
    def Init(self):
        self.item = ItemData(self.owner.tree, self.__module__,
                        self.thread(self.owner.call_subprocess),
                        tip=(self.__doc__ or '') + (self.execute.__doc__ or ''))
        ## self.tree.update(self.section, self.item)
        self.tree[self.section] = self.item
        self.tree.reset()
        self.tree.Refresh()
        
        self.layout(None, (
            wxpj.Button(self, "Execute",
                handler=lambda v: self.thread.Start(self.execute), icon='exe',
                    tip=self.execute.__doc__),
            ),
        )
    
    def Destroy(self):
        try:
            del self.tree[self.section]
            self.tree.reset()
        except Exception: # wrapped C/C++ object has been deleted.
            pass
        return Layer.Destroy(self)


class Plugin(UserInterface, Layer):
    """Plugin of Calibrations
    """
    menu = "&Maintenance"
    
    def Init(self):
        self.tree = TreeCtrl(self, size=(160,-1),
            style=wx.TR_DEFAULT_STYLE|wx.TR_HIDE_ROOT
                 |wx.TR_FULL_ROW_HIGHLIGHT|wx.TR_NO_LINES
        )
        def branches(*args):
            return [[x, ItemData(self.tree, x, self.thread(self.call_subprocess))] for x in args]
        
        self.tree[0:0] = [
            ("Settings", [
                ("SYS", ItemData(self.tree, "tem_option", None)),
                ("TEM", ItemData(self.tree, "tem_control", None)),
                ("ROT", ItemData(self.tree, "tem_irot", None)),
            ]),
            ("Calibrations", (
                ("MAG", ItemData(self.tree, None, self.thread(self.calibrate_alpha_mag)),
                    branches(
                        "spot",
                        "shift",
                        "gun",
                        "spa",
                        "pla",
                        "clapt_mag",
                        "saapt_mag",
                        "axis",
                        "stig",
                        "para",
                        "comp2",
                        "iscomp2",
                        "ishift",
                )),
                ("DIFF", ItemData(self.tree, None, self.thread(self.calibrate_alpha_diff)),
                    branches(
                        "diffspot",
                        "diffstig",
                        "tilt",
                        "clapt_diff",
                        "saapt_diff",
                        "comp1",
                        "iscomp1",
                        "itilt",
                )),
                ("LOWMAG", ItemData(self.tree, None, self.thread(self.calibrate_alpha_lowmag)),
                    branches(
                        "lmspot",
                        "lmshift",
                )),
                ("Measure", ItemData(self.tree, None, self.thread(self.calibrate_alpha_measure)),
                    branches(
                        "alpha",
                        "fl",
                )),
                ("Stage", ItemData(self.tree, None, self.thread(self.calibrate_beta_measure)),
                    branches(
                        "stage",
                        "ol",
                )),
            )),
            ## ("*Discipline*", (
            ##     ("ht-axis", ItemData(self.tree, "align2_ht_axis", self.thread(self.call_subprocess))),
            ##     ("anode-axis", ItemData(self.tree, "align2_anode_axis", self.thread(self.call_subprocess))),
            ## ))
        ]
        self.tree.reset()
        ## self.tree.Expand(self.tree.get_item(None, "Calibrations"))
        
        ## --------------------------------
        ## Do layout treectrl, config setting, and statusline
        ## The statusline is used to output the retval of each calibration
        ## --------------------------------
        self.statusline = mwx.StatusBar(self)
        
        self.layout("Configurations", (
            wxpj.Button(self, "Save ALL",
                lambda v: self.config.save(), icon='save',
                    tip="Save ALL configurations of section [TEM]"),
            
            wxpj.Button(self, "Load ALL",
                lambda v: self.config.load(), icon='proc',
                    tip="Load ALL configurations of section [TEM]"),
            
            wxpj.Button(self, "Report Configurations",
                lambda v: self.report_cal(), icon='edit',
                    tip="Export configurations to excel file."),
            ),
            row=2, expand=1, show=0,
        )
        self.layout(None, (
            self.tree,
            self.statusline,
            ),
            row=1, expand=2, border=0, vspacing=0,
        )
    
    def set_current_session(self, session):
        self.tree.set_flags(session)
        ## reload 時は zip(temp,root) 長さが合わないのでさらに追加
        self.tree.restore_session(session) # [0]-Calibrations 以降の拡張プラグインを復元する
        self.tree.reset()
    
    def get_current_session(self):
        return self.tree.get_flags()
    
    def report_cal(self):
        return self.config.export(xlpath="config-report.xlsx",
            keys = (
                'cl3spot', 'cl3sens',
                'cl3para', 'cl3dia',
                'beamshift', 'beamtilt',
                'alpha',
                'fl-focus',
                ## 'ol-focus',
                ),
            )
    
    ## --------------------------------
    ## MAG/DIFF Calibration procs
    ## --------------------------------
    
    def call_subprocess(self, data):
        """Callback of data calibrations"""
        ## ツリー作成時にはまだインスタンスが確定していない
        ## ここで plug インスタンスにアクセスする．なければロードを試みる
        try:
            name = data.name
            self.statusline("[{}]".format(name))
            print(self.message("[{}] processing... (Press C-g to quit)".format(name)))
            
            ## data.call -> data.callback -> thread(call_subprocess) -> plug.execute
            ## plug = getattr(self, name)
            plug = data.control_panel()
            
            data.update_status(-2)
            data.update_status(plug.execute())
            
            status = data.status
            self.statusline("\b {}".format(data.status))
            print(self.message("[{}] retval: {}".format(name, status)))
            return status
        
        except Exception as e:
            print(self.message(e))
            data.update_status(-3)
    
    def calibrate_alpha_mag(self, evt):
        """TEM-MAG Illumination: Fundamental alignment/calibrations"""
        with self.thread:
            with self.save_excursion(mmode='MAG'):
                return all(None is not self.call_subprocess(v)
                        for v in evt.children() if v.status == -1)
    
    def calibrate_alpha_diff(self, evt):
        """TEM-DIFF Illumination: Fundamental alignment/calibrations"""
        with self.thread:
            with self.save_excursion(mmode='DIFF'):
                return all(None is not self.call_subprocess(v)
                        for v in evt.children() if v.status == -1)
    
    def calibrate_alpha_lowmag(self, evt):
        """TEM-LOWMAG Illumination: Fundamental alignment/calibrations"""
        with self.thread:
            with self.save_excursion(mmode='LOWMAG'):
                return all(None is not self.call_subprocess(v)
                        for v in evt.children() if v.status == -1)
    
    def calibrate_alpha_measure(self, evt):
        """Measurement of optically basic quantity"""
        with self.thread:
            with self.save_excursion(mmode='MAG'):
                return all(None is not self.call_subprocess(v)
                        for v in evt.children() if v.status == -1)
    
    def calibrate_beta_measure(self, evt):
        """Calibratoin of OL/Stage"""
        with self.thread:
            with self.save_excursion(mmode='MAG'):
                return all(None is not self.call_subprocess(v)
                        for v in evt.children() if v.status == -1)
