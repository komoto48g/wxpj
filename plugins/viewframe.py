#! python3
# -*- coding: utf-8 -*-
"""Property list of buffers

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from pprint import pformat
import wx
from wx import aui
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
import numpy as np
from jgdk import Layer, Icon
from mwx.framework import CtrlInterface

if wx.VERSION < (4,1,0):
    from wx.lib.mixins.listctrl import CheckListCtrlMixin
    
    class CheckListCtrl(wx.ListCtrl, CheckListCtrlMixin):
        def __init__(self, *args, **kwargs):
            wx.ListCtrl.__init__(self, *args, **kwargs)
            CheckListCtrlMixin.__init__(self)
            
            self.ToolTip = ''
            self.IsItemChecked = self.IsChecked # for wx 4.1 compatibility

else:
    class CheckListCtrl(wx.ListCtrl):
        def __init__(self, *args, **kwargs):
            wx.ListCtrl.__init__(self, *args, **kwargs)
            
            ## To avoid $BUG wx 4.1.1 (but default Tooltip will disappear)
            self.ToolTip = ''
            self.EnableCheckBoxes()


class CheckList(CheckListCtrl, ListCtrlAutoWidthMixin, CtrlInterface):
    """ CheckList with FSM
    list item order = buffer order リストアイテムとバッファの並び順 0..n は常に一致します．
    """
    @property
    def selected_items(self):
        return [j for j in range(self.ItemCount) if self.IsSelected(j)]
    
    @property
    def focused_item(self):
        return self.FocusedItem
    
    @property
    def all_items(self):
        rows = range(self.ItemCount)
        cols = range(self.ColumnCount)
        return [[self.GetItemText(j, k) for k in cols] for j in rows]
    
    def __init__(self, parent, target, **kwargs):
        CheckListCtrl.__init__(self, parent, size=(400,130),
                               style=wx.LC_REPORT|wx.LC_HRULES, **kwargs)
        ListCtrlAutoWidthMixin.__init__(self)
        CtrlInterface.__init__(self)
        
        self.parent = parent
        self.Target = target
        
        self.alist = ( # assoc-list of column names
            ("id", 42),
            ("name", 160),
            ("shape", 90),
            ("dtype", 60),
            ("Mb",   40),
            ("unit", 60),
            ## ("mean", 60),
            ## ("std", 60),
            ## ("max", 50),
            ## ("min", 50),
            ("annotation", 240),
        )
        for k, (name, w) in enumerate(self.alist):
            self.InsertColumn(k, name, width=w)
        
        for j, frame in enumerate(self.Target.all_frames):
            self.InsertItem(j, str(j))
            self.UpdateInfo(frame) # update all --> 計算が入ると時間がかかる
        
        self.handler.update({
            0 : {
                            '*' : (0, lambda v: v.Skip()),
               'Lbutton dclick' : (0, self.OnShowItems), # -> frame_shown
                'enter pressed' : (0, self.OnShowItems), # -> frame_shown
               'delete pressed' : (0, self.OnRemoveItems), # -> frame_removed/shown
                  'C-a pressed' : (0, self.OnSelectAllItems),
                  'C-o pressed' : (0, self.OnLoadItems),
                  'C-s pressed' : (0, self.OnSaveItems),
                 'M-up pressed' : (0, self.Target.OnPageUp),
               'M-down pressed' : (0, self.Target.OnPageDown),
            },
        })
        self.handler.clear(0)
        
        self.__dir = True
        self.ToolTip = ''
        self.ToolTip.SetMaxWidth(1000)
        
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LIST_COL_CLICK, self.OnSortItems)
        
        self.context = { # bound to the target
            None: {
                  'frame_shown' : [ None, self.on_frame_shown ],
                 'frame_hidden' : [ None, self.on_frame_hidden ],
                 'frame_loaded' : [ None, self.on_frame_loaded ],
                'frame_removed' : [ None, self.on_frames_removed ],
               'frame_modified' : [ None, self.UpdateInfo ],
                'frame_updated' : [ None, self.UpdateInfo ],
            }
        }
        self.Target.handler.append(self.context)
    
    def Destroy(self):
        self.Target.handler.remove(self.context)
        return CheckListCtrl.Destroy(self)
    
    def UpdateInfo(self, frame):
        ls = ("{}".format(frame.index),
              "{}".format(frame.name),
              "{}".format(frame.buffer.shape),
              "{}".format(frame.buffer.dtype),
          "{:.1f}".format(frame.buffer.nbytes/1e6),
          "{:g}{}".format(frame.unit, '*' if frame.localunit else ''),
          ## "{:.2f}".format(np.mean(frame.buffer)),
          ## "{:.2f}".format(np.std(frame.buffer)),
            ## "{:g}".format(frame.buffer.max()),
            ## "{:g}".format(frame.buffer.min()),
              "{}".format(frame.annotation),
        )
        j = frame.index
        for k, v in enumerate(ls):
            self.SetItem(j, k, v)
        if frame.pathname:
            self.CheckItem(j)
    
    def OnMotion(self, evt):
        j, flag = self.HitTest(evt.Position)
        tip = ''
        if j >= 0:
            attr = self.Target.all_frames[j].attributes
            if attr:
                tip = pformat(attr, width=80, depth=1) # compact=0:PY3
            else:
                tip = "No attributes"
        self.ToolTip = tip
        evt.Skip()
    
    def OnShowItems(self, evt):
        self.Target.select(self.FocusedItem)
    
    def OnRemoveItems(self, evt):
        del self.Target[self.selected_items]
    
    def OnSortItems(self, evt): #<wx._controls.ListEvent>
        col = evt.GetColumn()
        if col == 0: # reverse the first column
            self.__dir = False
        self.__dir = not self.__dir # toggle 0:ascend/1:descend
        
        def _eval(x):
            try:
                return eval(x.replace('*', '')) # localunit* とか
            except Exception:
                return x
        
        frames = self.Target.all_frames
        if frames:
            frame = self.Target.frame
            la = sorted(self.all_items, key=lambda v: _eval(v[col]), reverse=self.__dir)
            frames[:] = [frames[int(c[0])] for c in la] # sort by new Id of items
            
            for j, c in enumerate(la):
                self.Select(j, False)        # 1, deselect all items,
                for k, v in enumerate(c[1:]): # 2, except for id(0), update text:str
                    self.SetItem(j, k+1, v)
            self.Target.select(frame) # invokes [frame_shown] to select the item
    
    def OnSelectAllItems(self, evt):
        for j in range(self.ItemCount):
            self.Select(j)
    
    def OnLoadItems(self, evt):
        self.parent.parent.import_index(target=self.Target)
    
    def OnSaveItems(self, evt):
        self.parent.parent.export_index(
            frames=[self.Target.all_frames[j] for j in self.selected_items] or None)
    
    ## --------------------------------
    ## Actions of frame-handler
    ## --------------------------------
    
    def on_frame_loaded(self, frame):
        j = frame.index
        self.InsertItem(j, str(j))
        for k in range(j+1, self.ItemCount): # id(0) を更新する
            self.SetItem(k, 0, str(k))
        self.UpdateInfo(frame)
    
    def on_frame_shown(self, frame):
        j = frame.index
        self.SetItemFont(j, self.Font.Bold())
        self.Select(j)
        self.Focus(j)
    
    def on_frame_hidden(self, frame):
        j = frame.index
        self.SetItemFont(j, self.Font)
        self.Select(j, False)
    
    def on_frames_removed(self, indices):
        for j in reversed(indices):
            self.DeleteItem(j)
        for k in range(self.ItemCount): # id(0) を更新する
            self.SetItem(k, 0, str(k))


class Plugin(Layer):
    """Property list of Grpah buffers
    """
    menukey = "Plugins/Extensions/&Buffer listbox\tCtrl+b"
    caption = "Property list"
    dockable = False
    unloadable = False
    
    @property
    def all_pages(self):
        return [self.nb.GetPage(i) for i in range(self.nb.PageCount)]
    
    @property
    def selected_buffers(self):
        page = self.nb.CurrentPage
        return page.Target[page.selected_items]
    
    @property
    def focused_buffer(self):
        page = self.nb.CurrentPage
        return page.Target[page.focused_item]
    
    def Init(self):
        self.nb = aui.AuiNotebook(self, size=(400,150),
            style = (aui.AUI_NB_DEFAULT_STYLE|aui.AUI_NB_RIGHT)
                  &~(aui.AUI_NB_CLOSE_ON_ACTIVE_TAB|aui.AUI_NB_MIDDLE_CLICK_CLOSE)
        )
        self.layout((self.nb,), expand=2, border=0)
        self.attach(self.graph, "graph")
        self.attach(self.output, "output")
        
        def on_focus_set(v):
            self.parent.select_view(self.nb.CurrentPage.Target)
            v.Skip()
        
        self.nb.Bind(wx.EVT_CHILD_FOCUS, on_focus_set)
        
        self.Menu[0:0] = [
            (101, "&Edit annotation", "Edit annotation", Icon('edit'),
                lambda v: self.ask()),
            (),
        ]
    
    def attach(self, target, caption):
        if target not in [lc.Target for lc in self.all_pages]:
            lc = CheckList(self, target)
            self.nb.AddPage(lc, caption)
    
    def detach(self, target):
        for k, lc in enumerate(self.all_pages):
            if target is lc.Target:
                self.nb.DeletePage(k)
    
    def show_page(self, target):
        self.nb.SetSelection(next((k
            for k, lc in enumerate(self.all_pages) if target is lc.Target), -1))
    
    def ask(self, prompt='Enter an annotation'):
        """Get response from the user using a dialog box."""
        page = self.nb.CurrentPage
        frames = page.Target.all_frames
        if frames:
            frame = frames[page.focused_item]
            with wx.TextEntryDialog(self, prompt,
                caption='Input Dialog', value=frame.annotation) as dlg:
                if dlg.ShowModal() == wx.ID_OK:
                    for j in page.selected_items:
                        frames[j].annotation = dlg.Value


if __name__ == "__main__":
    import glob
    from jgdk import Frame
    
    app = wx.App()
    frm = Frame(None)
    frm.load_plug(__file__, show=1, dock=0)
    for path in glob.glob(r"C:/usr/home/workspace/images/*.bmp"):
        print("loading path =", path)
        frm.load_buffer(path)
    frm.Show()
    app.MainLoop()
