#! python3
# -*- coding: utf-8 -*-
"""Plug manager

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from itertools import chain
import wx
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
from mwx import FSM, Frame, MiniFrame
try:
    import pyJem2 as pj
    from legacy import info as jInfo
    from legacy import cntf, cmdl
except ImportError:
    from . import pyJem2 as pj
    from .legacy import info as jInfo
    from .legacy import cntf, cmdl


class NotifyHandler(object):
    """Notify handler
    
    This class has both notify and request stream.
    To communicate with TEM, do the following steps:
    
        1. start() -> open the streams and update the information
        2. update() -> update manually when config changed
        3. bind/unbind transactions to the handler
        4. stop() -> close the streams
    
    Note:
        To check whether the streams are open,
        see cmdl.STREAM, cntf.STREAM, and self.thread.active
    """
    thread = property(lambda self: self.__thread)   #: Notify thread instance
    handler = property(lambda self: self.__handler) #: Notify command handler instance
    
    substr = [''] * 3 # 3-fields for mode:str
    modestr = property(lambda self: ' '.join(self.substr).strip())
    
    def start(self):
        """Open notify/request command stream"""
        self.__thread.Start() # open the notify port
        if cmdl.open():
            self.update()
    
    def stop(self):
        """Close notify/request command stream"""
        self.__thread.Stop() # close the notify port
        cmdl.close()
    
    def update(self):
        """Request information from TEM server"""
        try:
            self.handler("illumination_info", self.illumination.request())
            self.handler("imaging_info", self.imaging.request())
            
            ## 最初の時点では OMEGA-TYPE 不明▲
            self.handler("omega_info", self.omega.request())
            self.handler("filter_info", self.efilter.request())
        except IOError as e:
            print("- NotifyHandler failed to get filter info: {!r}.".format(e))
        
        try:
            self.tem.lsys.read()
            self.handler("lens_notify", self.tem.fsys.read())
            self.handler("defl_notify", self.tem.dsys.read())
            
            self.handler("ht_info", self.hts.request())
            self.handler("eos_info", self.eos.request())
            self.handler("gonio_info", self.gonio.request())
            
            self.handler("beam_valve", self.eos._get_v1_state())
            ## self.handler("scr_info", self.eos._get_scr())
            ## self.handler("det_info", self.eos._get_det()) # ▼not supported
            
            self.handler("scr_info", self.scr_info(self.eos._get_scr()))
            
            ## 最初の時点では APT-EXTYPE 不明▲
            extype = bool(pj.ApertureEx._get_info())
            self.apts = pj.ApertureEx if extype else pj.Aperture
            self.handler("apt_info", self.apts.request())
        except IOError as e:
            print("- NotifyHandler failed to get TEM info: {!r}.".format(e))
    
    def __init__(self, parent, logger):
        self.__parent = parent
        self.__thread = cntf.NotifyThread(log=logger)
        
        TEM = 'TEM'
        STEM = 'ASID'
        BUSY = '-busy'
        
        self.__handler = FSM({
                None : {
            "illumination_info" : [ None, self.on_illumination_notify ], # called when illumination mode changed
                 "imaging_info" : [ None, self.on_imaging_notify ], # called when imaging mode changed
                   "omega_info" : [ None, self.on_omega_notify ], # called when omega mode changed
                     "eos_info" : [ None ], # called when mode changed
                      "ht_info" : [ None ], # called when HT changed (invalid for BK-TEMCENTER)▲
                   "htsub_info" : [ None, self.on_htsub_fork ],
                  "htsub2_info" : [ None ],
                     "apt_info" : [ None ], # called when apertures are drived
                     "det_info" : [ None ], # called when detectors are drived
                     "scr_info" : [ None ], # called when screen are drived (invalid for BK-TEMCENTER)▲
                   "gonio_info" : [ None ], # called when gonio is drived
                  "filter_info" : [ None ], # called when filter is drived
                  "lens_notify" : [ None, lambda v: self.tem.lsys(v),
                                          lambda v: self.tem.fsys(v) ], # called when lense data changed
                  "defl_notify" : [ None, lambda v: self.tem.dsys(v) ], # called when deflector data changed
                  #"lfc_notify" : [ None ], # called when Lens Free Control is used (obsolete)
                     "fl_focus" : [ None ],
                     "br_focus" : [ None ],
                     "auto_htv" : [ None ],
                     "auto_ems" : [ None ],
                   "beam_valve" : [ None ],
                },
                TEM : {
                    "TEM begin" : [ TEM ],
                      "TEM end" : [ STEM ],
           "gonio_motion begin" : [ TEM ],
             "gonio_motion end" : [ TEM ],
                "degauss begin" : [ TEM+BUSY ],
                 "aptsel begin" : [ TEM+BUSY ],
                  "relax begin" : [ TEM+BUSY ],
                },
                TEM+BUSY: {
                  "degauss end" : [ TEM ],
                   "aptsel end" : [ TEM ],
                    "relax end" : [ TEM ],
                },
                STEM : {
                   "ASID begin" : [ STEM ],
                     "ASID end" : [ TEM ],
           "gonio_motion begin" : [ STEM ],
             "gonio_motion end" : [ STEM ],
                "degauss begin" : [ STEM+BUSY ],
                 "aptsel begin" : [ STEM+BUSY ],
                  "relax begin" : [ STEM+BUSY ],
                },
                STEM+BUSY: {
                  "degauss end" : [ STEM ],
                   "aptsel end" : [ STEM ],
                    "relax end" : [ STEM ],
                },
            },
            default = TEM
        )
        
        ## pj で定義されている情報 (Info) を参照する
        
        self.illumination = pj.Illumination() # -> illumination_info
        self.imaging = pj.Imaging() # -> imaging_info
        self.omega = pj.Omega() # -> omega_info
        self.tem = pj.TEM() # -> lsys:lens_notify, defl:defl_notify
        self.eos = pj.EOsys() # -> eos_info
        self.hts = pj.HTsys() # -> ht_info
        self.gonio = pj.Stage() # -> gonio_info
        self.efilter = pj.Filter() # -> filter_info
        
        ## Aperture system typeinfo
        self.apts = pj.ApertureEx
        
        ## pj で定義されない情報はここで実体を定義する
        
        self.htsub_info = jInfo.HTsub_info()
        self.htsub2_info = jInfo.HTsub2_info()
        self.cur_info = jInfo.Current_info()
        self.scr_info = jInfo.Screen_info()
        self.det_info = jInfo.Detector_info()
        
        _NC = cntf.NotifyCommand
        
        self.__thread.add_hooks(
            _NC("N600", "!H", lambda v: self.handler("ASID end" if v[0]==0 else "TEM end", v)),
            _NC("N601", "!H", lambda v: self.handler("TEM begin" if v[0]==0 else "ASID begin", v)),
            
            _NC("N105", "!H10sHH10s", lambda v: self.handler("illumination_info", self.illumination.Info(v))),
            _NC("N101", "!H10sHI10s10s", lambda v: self.handler("imaging_info", self.imaging.Info(v))),
            _NC("N102", "!HH10sHI10s10s", lambda v: self.handler("omega_info", self.omega.Info(v))),
            _NC("N109", "!16HIH", lambda v: self.handler("eos_info", self.eos.Info(v))),
            
            _NC("N128", "!27H", lambda v: self.handler("lens_notify", v)),
            _NC("N132", "!62H", lambda v: self.handler("defl_notify", v)),
            _NC("N121", "!H", lambda v: self.handler("br_focus", v)),
            _NC("N197", "!5H", lambda v: self.handler("fl_focus", v)),
            ## _NC("N221", "!26H", lambda v: self.handler("lfc_notify", v)), # ▲使用しない STEM:!24H, TEM:!26H で異なる
            
            ## _NC("N290", "!HH", self.on_mode_fork), # ▲to be deprecated
            
            _NC("N184", None, lambda v: self.handler("relax begin", None)),
            _NC("N185", None, lambda v: self.handler("relax end", None)),
            
            _NC("N162", "!2H2I2H2IH5dH", self.on_filter_fork),
            
            _NC("N140", "!3H798s", lambda v: self.handler("apt_info", pj.Aperture.Info(v))), # extype=0
            _NC("N141", None,     lambda v: self.handler("aptsel begin", v)), # extype=0
            _NC("N142", "3H798s", lambda v: self.handler("aptsel end", v)),   # extype=0
            _NC("N153", "!15H", lambda v: self.handler("apt_info", pj.ApertureEx.Info(v))), # extype=1
            _NC("N155", "!H", lambda v: self.handler("aptsel begin" if v[0] else "aptsel end", v)), # extype=1
            
            _NC("N532", "!11H", lambda v: self.handler("gonio_motion " + ("begin" if any(v[0:5]) else "end"), v)),
            _NC("N533", "!7d", lambda v: self.handler("gonio_info", self.gonio.Info(v))),
            _NC("N404", "!2I", lambda v: self.handler("cur_info", self.cur_info(v))),
            _NC("N401", "!2H", lambda v: self.handler("scr_info", self.scr_info(v))),
            _NC("N627", "!25H", lambda v: self.handler("det_info", self.det_info(v))),
            _NC("F900", "!19hi5h", lambda v: self.handler("ht_info", self.hts.Info(v))),
            _NC("F901", "!13h", lambda v: self.handler("htsub_info", self.htsub_info(v))),
            _NC("N309", "!i5h", lambda v: self.handler("htsub2_info", self.htsub2_info(v))),
            _NC("N316", "!H", lambda v: self.handler("beam_valve", v)),
            _NC("N800", "!i", lambda v: self.handler("auto_htv", v)),
            _NC("N817", "!6H", lambda v: self.handler("auto_ems", v)),
        )
        self.degauss_sw = 0
    
    def on_filter_fork(self, argv):
        """Called when filter is drived."""
        info = self.efilter.Info(argv)
        self.handler("filter_info", info)
        
        if info["status"]:
            if not self.degauss_sw:
                self.degauss_sw = 1
                self.handler("degauss begin", info)
        elif self.degauss_sw:
            self.degauss_sw = 0
            self.handler("degauss end", info)
    
    ## def on_mode_fork(self, argv):
    ##     """Called when optical mode is changing or changed."""
    ##     id, status = argv
    ##     if status == 0:
    ##         self.handler("mode change", id)
    ##     else:
    ##         self.handler("mode changed", id)
    
    def on_htsub_fork(self, info): #<htsub_info>
        self.handler('ht_info', self.hts.request())
    
    def on_illumination_notify(self, info): #<illumination_info>
        self.substr[0] = "{mode_name}[{spot}-{alpha}]".format(**info)
        self.__parent.message(self.modestr)
    
    def on_imaging_notify(self, info): #<imaging_info>
        self.substr[1] = "{mode_name}[{submodestr}]".format(**info)
        self.__parent.message(self.modestr)
    
    def on_omega_notify(self, info): #<omega_info>
        self.substr[2] = "{mode_name}[{submodestr}]".format(**info).replace('/','_')
        self.__parent.message(self.modestr)


class NotifyLogger(wx.ListCtrl, ListCtrlAutoWidthMixin):
    """Notify logger
    """
    @property
    def selected_items(self):
        return [j for j in range(self.ItemCount) if self.IsSelected(j)]
    
    def __init__(self, parent, **kwargs):
        wx.ListCtrl.__init__(self, parent,
                             style=wx.LC_REPORT|wx.LC_HRULES, **kwargs)
        ListCtrlAutoWidthMixin.__init__(self)
        
        self.alist = ( # assoc list of column names
            ("name", 48),
            ("n",   32),
            ("iid", 32),
            ("pid", 32),
            ("data", 400),
        )
        for k, (name, w) in enumerate(self.alist):
            self.InsertColumn(k, name, width=w)
        
        self.__dir = True
        self.__items = []
        
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LIST_COL_CLICK, self.OnSortItems)
    
    def __call__(self, *args):
        (name, iid, status, pid, data) = args # write notified data to list
        i = 0
        for i, item in enumerate(self.__items):
            if item[0] == name:
                item[1] += 1
                item[2:] = [iid, pid, data] # counter +1, replace the list
                break
        else:
            i = len(self.__items)
            item = [name, 1, iid, pid, data] # format; add counter(1), get rid of status
            self.__items.append(item)
            self.InsertItem(i, str(name))
        
        ## Note: This method is called in threaded NotifyThread.run.
        ##       A RuntimeError can occur while terminating the main thread.
        ## RuntimeError: wrapped C/C++ object of type NotifyLogger has been deleted
        if not self:
            return
        for j, v in enumerate(item):
            self.SetItem(i, j, str(v))
        self.blink(i)
    
    def blink(self, i):
        if self.GetItemBackgroundColour(i) != wx.Colour('yellow'):
            self.SetItemBackgroundColour(i, "yellow")
            def reset_color():
                if self and i < self.ItemCount:
                    self.SetItemBackgroundColour(i, 'white')
            wx.CallAfter(wx.CallLater, 1000, reset_color)
    
    def OnSortItems(self, evt): #<wx._controls.ListEvent>
        col = evt.GetColumn()
        self.__dir = not self.__dir
        self.__items.sort(key=lambda v: v[col], reverse=self.__dir)
        for i, item in enumerate(self.__items):
            for j, v in enumerate(item):
                self.SetItem(i, j, str(v))
    
    def OnMotion(self, evt): #<wx._core.MouseEvent>
        j, flag = self.HitTest(evt.GetPosition())
        text = ''
        if j >= 0:
            item = self.__items[j]
            name = item[0]
            length = len(item[-1].split())
            text = "{}:{} ({}bytes)".format(name, NOTIFY_COMMANDS.get(name) or '?', length)
            text += '\n' + item[-1]
        self.ToolTip = text
        evt.Skip()
    
    def copy(self):
        text = '\n'.join('\t'.join(str(v) for v in self.__items[j]) for j in self.selected_items)
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(wx.TextDataObject(text))
        wx.TheClipboard.Close()
    
    def delete(self):
        for j in reversed(self.selected_items):
            self.DeleteItem(j)
            del self.__items[j]
    
    def delete_all(self):
        self.DeleteAllItems()
        self.__items = []


class NotifyFront(MiniFrame):
    
    def __init__(self, parent):
        MiniFrame.__init__(self, parent,
            title="Notify", size=(640,320), style=wx.DEFAULT_FRAME_STYLE)
        
        self.logger = NotifyLogger(self)
        self.notify = NotifyHandler(self, self.logger)
        
        self.menubar["File"] = (
            (1, "&Run\tCtrl-r", "Start Notify/Request", wx.ITEM_CHECK,
                lambda v: self.notify.start(),
                lambda v: v.Check(self.notify.thread.active)),
            
            (2, "&End\tCtrl-e", "Stop Notify/Request",
                lambda v: self.notify.stop()),
        )
        self.menubar["Edit"] = (
            (10, "&Copy items\tCtrl-c", "Copy selected items",
                lambda v: self.logger.copy()),
                
            (11, "&Delete items\tdelete", "Delete selected items",
                lambda v: self.logger.delete()),
            (),
            (12, "Delete &all items", "Delete all items",
                lambda v: self.logger.delete_all()),
        )
        self.menubar.reset()
        self.StatusBar.Show()
    
    def Destroy(self):
        self.notify.stop()
        return wx.MiniFrame.Destroy(self)


NOTIFY_COMMANDS = {
    "N010" : u"Notify種類 設定",
    "N050" : u"Power Supply(電源供給)状態変化通知",
    "N100" : u"結像系情報通知",
    "N101" : u"結像系情報通知",
    "N102" : u"スペクトル情報通知",
    "N105" : u"照射系情報通知",
    "N106" : u"スポットサイズ通知",
    "N107" : u"α情報通知",
    "N108" : u"Corrector Switch情報通知",
    "N109" : u"EOS情報通知",
    "N110" : u"Wobbler情報通知",
    "N111" : u"Wobbler/偏向系情報通知",
    "N112" : u"レンズWobblerスイッチ情報通知",
    "N113" : u"偏向系Wobblerスイッチ情報通知",
    "N114" : u"レンズWobbler条件情報通知",
    "N115" : u"偏向系Wobbler条件情報通知",
    "N116" : u"Wobbler情報通知(I/O設定値)",
    "N117" : u"Wobbler 振幅用係数変更通知",
    "N118" : u"OUF用係数変更通知",
    "N119" : u"OL Super Fine情報変更通知",
    "N120" : u"レンズ情報通知",
    "N121" : u"Brightness情報通知",
    "N122" : u"OBJ Focus情報通知",
    "N123" : u"Diff Focus情報通知",
    "N124" : u"Brightness Zoom情報通知",
    "N125" : u"FLC情報通知",
    "N126" : u"OUF情報通知",
    "N127" : u"Defocus情報通知",
    "N128" : u"レンズ情報通知",
    "N129" : u"OM2 Reverse情報通知",
    "N130" : u"偏向系情報通知(TEM)",
    "N131" : u"偏向系情報通知(ASID)",
    "N132" : u"偏向系出力値情報 通知(TEM)(Ver2)",
    "N133" : u"偏向系出力値情報 通知(ASID)(Ver2)",
    "N134" : u"1300NEF用 偏向系出力値情報通知",
    "N135" : u"CLA Super Fine情報変更通知",
    "N136" : u"収差補正データ変更通知",
    "N137" : u"FLC ON時ニ、OFF時ノレンズ出力値ヲ通知スルコマンド",
    "N138" : u"拡張タイプ型偏向系出力値情報通知",
    "N139" : u"拡張タイプ型偏向系A/D値情報通知",
    "N140" : u"可動絞リ情報通知",
    "N141" : u"絞リ番号移動開始通知",
    "N142" : u"絞リ番号移動停止通知",
    "N143" : u"拡張タイプ型絞リ穴位置保存座標値通知",
    "N144" : u"拡張タイプ型絞リ移動情報変更通知",
    "N145" : u"絞リ位置検出異常通知",
    "N146" : u"絞リ駆動系異常通知",
    "N147" : u"絞リ駆動リミットオーバー通知",
    "N148" : u"Beam Stopper情報通知",
    "N149" : u"絞リ排他制御ON/OFF状態変更通知",
    "N150" : u"MDS情報通知",
    "N151" : u"ビームブランキング時間",
    "N152" : u"ハードウェアブランキング種類通知",
    "N153" : u"拡張タイプ型絞リ情報変更通知",
    "N154" : u"拡張タイプ型絞リバックラッシュ量変更通知",
    "N155" : u"拡張タイプ型絞リ駆動状態変更通知",
    "N156" : u"拡張タイプ型絞リDelay Time変更通知",
    "N157" : u"拡張タイプ型絞リ構成情報通知",
    "N158" : u"拡張タイプ型絞リ Fine/Coarse 位置 座標値通知",
    "N159" : u"拡張タイプ型Wobbler振幅用係数通知",
    "N160" : u"オメガ情報通知",
    "N161" : u"残留磁場消去完了通知",
    "N162" : u"フィルター情報通知",
    "N163" : u"Energy Shift Object情報通知",
    "N164" : u"X線ストッパー情報通知",
    "N165" : u"スリットマウント Coarseスイッチ情報通知",
    "N166" : u"スリットマウント位置情報通知",
    "N167" : u"1300NEF用FLバランスモード変更通知",
    "N168" : u"12極補正コイル用残留磁場消去開始通知",
    "N169" : u"12極補正コイル用残留磁場消去完了通知",
    "N170" : u"ホロコーン情報通知",
    "N171" : u"イメージシフト 3/4変更通知",
    "N172" : u"GIF Function情報通知",
    "N173" : u"ホログラフィ情報通知",
    "N174" : u"Image Shiftノブ ユーザデータ情報通知",
    "N175" : u"GIF Magリンク情報通知",
    "N176" : u"偏向系ノ中点ヨリ大キイカ小サイカ範囲外情報通知",
    "N177" : u"偏向系ノブ割付情報通知",
    "N178" : u"Alignmentスイッチ偏向系操作対象情報通知",
    "N179" : u"Image Shift Power Upコイル情報変更通知",
    "N180" : u"レンズ緩和情報通知",
    "N181" : u"レンズ緩和トータル時間情報通知",
    "N182" : u"自動緩和レンズ種通知",
    "N183" : u"手動緩和レンズ種通知",
    "N184" : u"レンズ緩和開始通知",
    "N185" : u"レンズ緩和終了通知",
    "N186" : u"LENS U* Link OFF可否状態変更通知",
    "N187" : u"LENS U* Link情報変更通知",
    "N188" : u"LENS U* Link ON可否状態変更通知",
    "N189" : u"Lens Relaxation制御方法通知(Notify)",
    "N190" : u"レンズA/D値情報通知",
    "N191" : u"偏向系A/D値情報通知",
    "N192" : u"レンズA/D値情報通知(OM2対応)",
    "N193" : u"Bake Out開始通知",
    "N194" : u"Bake Out終了通知",
    "N195" : u"OLサーモ断線通知",
    "N196" : u"PL Focus情報通知",
    "N197" : u"FL Focus情報通知",
    "N198" : u"Bake Out残時間通知",
    "N199" : u"Cooling開始通知",
    "N200" : u"Cooling終了通知",
    "N201" : u"レンズ/偏向系 情報通知",
    "N202" : u"アライメントデータSave完了通知",
    "N203" : u"偏向系A/D値情報 通知(Ver2)",
    "N204" : u"フィルタ用データSave完了通知",
    "N205" : u"偏向系AD値情報通知",
    "N206" : u"Bake Ready情報変更通知",
    "N207" : u"アライメントデータ出力値情報ファイル作成完了通知",
    "N210" : u"Aperture自動調整結果通知",
    "N211" : u"拡張タイプ型絞リ座標データSave完了通知",
    "N212" : u"Apertureポテンショ情報通知",
    "N213" : u"拡張タイプ型絞リ現在位置情報IO値通知",
    "N214" : u"拡張タイプ型絞リ警告情報通知",
    "N215" : u"ハードウェアブランキング振幅量変更通知",
    "N216" : u"ビームブランキング情報更新通知",
    "N217" : u"MDSモード毎ノ光学系条件変更通知",
    "N218" : u"Slit水平位置情報通知",
    "N220" : u"OBJ Focus情報通知(OM2対応)",
    "N221" : u"FLC情報通知(OM2対応)",
    "N222" : u"FLCバランス値通知コマンド",
    "N230" : u"OL Compensation値変更通知",
    "N231" : u"IOS動作情報通知",
    "N232" : u"IOS機能 Ready/Not Ready情報通知",
    "N235" : u"最大Dispersion通知",
    "N290" : u"操作条件変更通知",
    "N300" : u"Vacuum情報通知",
    "N301" : u"バルブ情報通知(F810型)",
    "N302" : u"ペニングゲージ情報通知",
    "N303" : u"ピラニーゲージ情報通知",
    "N304" : u"カメラ室リーク情報通知",
    "N305" : u"試料ホルダ情報通知",
    "N306" : u"ACD HEAT情報通知",
    "N307" : u"SIP昼夜運転情報通知",
    "N308" : u"HTモニタ情報通知",
    "N309" : u"HTサブシステム現在値情報通知",
    "N310" : u"FILTER NG通知",
    "N311" : u"バルブ制御空気圧 低下通知",
    "N312" : u"バルブ制御空気圧 回復通知",
    "N313" : u"ACD HEAT開始通知",
    "N314" : u"ACD HEAT終了通知",
    "N315" : u"バルブ情報通知(F816型)",
    "N316" : u"ビームバルブ情報通知",
    "N317" : u"EL Short状態通知",
    "N318" : u"ビームバルブOpen Ready状態通知",
    "N319" : u"ペニングゲージ情報 通知(Ver2)",
    "N320" : u"ピラニ-ゲージ情報 通知(Ver2)",
    "N321" : u"ヘリウムステージ用ペニングゲージモニタ情報通知",
    "N322" : u"ヘリウムステージ用ピラニーゲージモニタ情報通知",
    "N323" : u"ヘリウムステージ用温度情報通知",
    "N324" : u"試料室側ACD HEAT情報通知",
    "N325" : u"Beam Detector値変更通知",
    "N326" : u"Gun SIPバルブ情報通知",
    "N327" : u"クリスタルイオンゲージ情報",
    "N328" : u"試料室側ACD HEAT開始通知",
    "N329" : u"試料室側ACD HEAT終了通知",
    "N330" : u"Gunタイプ変更通知",
    "N331" : u"ターボポンプスイッチ書キ込ミ情報通知",
    "N332" : u"ターボポンプスイッチモニタ情報通知",
    "N333" : u"スパッタイオンポンプスイッチモニタ情報通知",
    "N334" : u"Sleep Mode情報通知",
    "N335" : u"排気系デジタル調整値変更通知",
    "N336" : u"リークテスト用排気系装置状態変化通知",
    "N337" : u"リトラクタブルACD状態変化通知",
    "N338" : u"ACD HEAT Not Ready要因変更通知",
    "N340" : u"制御処理ノ残存時間通知、及ビ処理終了通知",
    "N341" : u"HT新規追加制御情報通知",
    "N342" : u"HT新規追加モニター値通知",
    "N343" : u"PreHeat時間情報通知",
    "N344" : u"PreHeat時間情報通知間隔情報通知",
    "N345" : u"JEOLコレクター用SIAMデータ変更通知",
    "N350" : u"Filament 最大値変更通知",
    "N351" : u"Filament自動昇降圧情報通知",
    "N352" : u"Filament Alignment 変更通知",
    "N355" : u"拡張型Filament Not Ready要因変化通知",
    "N356" : u"サーキュレーションヒータ情報変更通知",
    "N358" : u"コンディショニング短絡棒切リ換エ動作状態変更通知",
    "N359" : u"コンディショニング短絡棒切リ換エ動作停止情報通知",
    "N360" : u"HT制御情報通知",
    "N361" : u"コンディショニング短絡棒警告システム連動状態変更通知",
    "N400" : u"Photo情報通知",
    "N401" : u"スクリーン情報通知",
    "N402" : u"露光モード変更通知",
    "N403" : u"Photo異常通知",
    "N404" : u"照射電流密度通知",
    "N405" : u"検出器情報通知",
    "N406" : u"スクリーン角度ノI/O情報通知",
    "N410" : u"撮影履歴情報通知",
    "N450" : u"OBJ FOCUSステップ値 通知",
    "N500" : u"HT通信Enable/Disable通知",
    "N501" : u"Gonio通信Enable/Disable通知",
    "N502" : u"Panel通信Enable/Disable通知",
    "N510" : u"速度テーブル情報通知",
    "N511" : u"試料位置再生開始通知",
    "N512" : u"試料位置再生完了通知",
    "N513" : u"バックラッシュ補正テーブル通知",
    "N514" : u"X/Y軸 入力信号 通知",
    "N515" : u"Gonioノ速度テーブル番号変更通知",
    "N516" : u"ホルダーユーセントリック値変更通知",
    "N517" : u"Stage Neutral開始通知",
    "N518" : u"リニアアクチュエータ速度変更通知",
    "N520" : u"サブシステムEMG解除通知",
    "N530" : u"Gonio緊急状態解除通知",
    "N531" : u"ゴニオ緊急情報通知",
    "N532" : u"ゴニオ情報通知",
    "N533" : u"ゴニオ座標情報通知",
    "N534" : u"ゴニオ速度モード変更通知",
    "N535" : u"ピエゾ座標情報通知",
    "N539" : u"トラックボール速度モード変更通知",
    "N540" : u"6軸用 ゴニオ情報通知",
    "N541" : u"6軸用 ゴニオ座標情報通知",
    "N542" : u"6軸用 速度モード変更通知",
    "N543" : u"6軸用 ゴニオ緊急情報通知",
    "N550" : u"最大加速電圧リミットEnable/Disable変更通知",
    "N551" : u"HT Compensator変更通知",
    "N560" : u"ルームランプ状態通知",
    "N590" : u"HTサブシステム情報通知",
    "N591" : u"ゴニオサブシステム情報通知",
    "N592" : u"パネルサブシステム情報通知",
    "N600" : u"観察モード移行開始通知",
    "N601" : u"観察モード移行終了通知",
    "N610" : u"SAAF検出器駆動回転角度情報通知",
    "N611" : u"SAAF検出器状態情報通知",
    "N619" : u"観察モード、補助選択モード変更通知",
    "N620" : u"ASID EOS情報通知",
    "N621" : u"走査条件情報通知",
    "N622" : u"スキャンローテーション情報通知",
    "N623" : u"検出器情報通知",
    "N624" : u"スキャンスピード情報通知",
    "N625" : u"イメージ選択通知",
    "N626" : u"ASIDモード時カメラ長情報 通知",
    "N627" : u"検出器IN/OUT状態通知",
    "N628" : u"イメージ変更通知",
    "N629" : u"検出器コントラスト/ブライトネス情報 通知",
    "N630" : u"イメージステータス通知",
    "N631" : u"指定ワークシートステータス通知",
    "N632" : u"BEI検出器ゲインCoarseデータ通知",
    "N633" : u"Selective Detect Angle Series(結像側カメラ長系列)番号情報通知",
    "N634" : u"スキャンローテーション変更通知コマンド(0.1°刻ミ対応)",
    "N635" : u"交流磁場同期状態変更通知",
    "N636" : u"SHIFT TILT INVERT情報変更",
    "N637" : u"スキャンローテーションスイッチ情報通知",
    "N638" : u"検出器位置情報変更通知",
    "N639" : u"スキャンローテーションモード毎ノ角度情報通知",
    "N640" : u"ACB実行開始通知",
    "N641" : u"ACB実行終了通知",
    "N642" : u"ACBユーザデータ通知",
    "N643" : u"ACBメンテナンスデータ通知",
    "N645" : u"Scan Coil情報通知",
    "N650" : u"STEMカスタムモードデータテーブルSave完了通知",
    "N651" : u"STEMカスタムモードデータテーブル変更通知",
    "N652" : u"STEMカスタムモード文字列情報通知",
    "N653" : u"STEMカスタムモード時ノSelective Detect Angle Series(結像側カメラ長系列)番号情報通知",
    "N654" : u"STEMカスタムプローブノ走査倍率カードコピー完了通知",
    "N655" : u"ノイズキャンセラステータス変更通知",
    "N660" : u"STEM用レンズデータ半固定値情報変更通知",
    "N661" : u"TEM用レンズデータ半固定値情報変更通知",
    "N670" : u"ノブアサインSTEM用レンズ変更通知",
    "N671" : u"ノブアサインTEM用レンズ変更通知",
    "N680" : u"デスキャン走査条件情報通知",
    "N681" : u"デスキャンローテーションスイッチ情報通知",
    "N682" : u"デスキャンローテーションオフセット変更通知",
    "N683" : u"デスキャン_コイル情報通知",
    "N684" : u"デスキャンスイッチ情報通知",
    "N685" : u"デスキャン制御設定情報通知",
    "N686" : u"偏向系_スキャン_固定モード通知",
    "N687" : u"スキャンローテーション角度連動モード通知",
    "N800" : u"HT変更通知",
    "N801" : u"Small LCD通信異常通知",
    "N810" : u"A1変更通知",
    "N811" : u"A2変更通知",
    "N812" : u"バイアス変更通知",
    "N813" : u"Filament変更通知",
    "N814" : u"Ωフィルタ重畳電圧変更通知",
    "N815" : u"自動エミッション制御Emission条件変更通知",
    "N816" : u"自動エミッション制御A1昇降動作条件変更通知",
    "N817" : u"自動エミッション制御動作状態変更通知",
    "N820" : u"I/Oデータ複数通知",
    "N821" : u"IMコイルAC励磁状態通知",
    "N890" : u"AUTOスイッチ押下通知",
    "N891" : u"Functionキー押下通知",
    "N900" : u"起動タスク情報通知",
    "N901" : u"EM情報通知",
    "N902" : u"装置状態変更通知",
    "N910" : u"シャットダウン情報通知",
    "N920" : u"Main System通信 Enable/Disable通知",
    "N930" : u"自動試料交換装置Emergency情報通知",
    "N931" : u"自動試料交換装置エラー通知",
    "N932" : u"自動試料交換装置動作待チ原因通知",
    "N940" : u"水冷系Warning情報通知",
    "N950" : u"通過コマンド登録通知",
    "N951" : u"コマンド停止設定通知",
    "N960" : u"機能ノ有効/無効状態通知",
    "F900" : u"HT定期通知",
    "F901" : u"HT情報通知",
    "F930" : u"排気系情報通知",
    "F973" : u"試料ホルダータイプ通知",
}


if __name__ == "__main__":
    cmdl.HOST = cntf.HOST = "localhost"
    ## cmdl.OFFLINE = True
    
    class TestFrame(Frame):
        def __init__(self, *args, **kwargs):
            Frame.__init__(self, *args, **kwargs)
            
            self.nfront = NotifyFront(self)
            self.notify = self.nfront.notify
            self.notify.start()
            self.notify.handler.debug = 4
            
            self.menubar["File"][-4:-4] += (
                (1, "&Notifyee\tF11", "Notify logger frame", wx.ITEM_CHECK,
                    lambda v: self.nfront.Show(v.IsChecked()),
                    lambda v: v.Check(self.nfront.IsShown())),
            )
            self.menubar.reset()
        
        def Destroy(self):
            self.nfront.Destroy()
            return Frame.Destroy(self)
    
    app = wx.App()
    frm = TestFrame(None)
    ## frm = NotifyFront(None)
    frm.Show()
    app.MainLoop()
