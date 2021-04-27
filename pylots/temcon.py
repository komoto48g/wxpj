#! python
# -*- coding: utf-8 -*-
"""Editor's collection of TEM and wx widgets

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from __future__ import (division, print_function,
                        absolute_import, unicode_literals)
import copy
import wx
import mwx
from mwx.graphman import Icon
from mwx.framework import CtrlInterface, TreeList


class ItemData(object):
    """Item data for TreeCtrl
    Tree : parent tree
    name : name of plugin or the module
  status : status of the plugin (default -1)
callback : a function which is called from menu
    """
    STATUS_EXCEPTION = -3
    STATUS_PROCESS = -2
    STATUS_DEFAULT = -1
    STATUS_FAILURE = 0
    STATUS_SUCCESS = 1
    STATUS_ERROR = None
    
    def __init__(self, tree, name=None, callback=None, icon=None, tip=None):
        self.Tree = tree
        self.name = name
        self.status = -1
        self.callback = callback
        self.symbol = {
             -3 : 6,
             -2 : 2,
             -1 : TreeCtrl.icons.index(icon or 'file'), # default icon
          False : 3,
           True : 4,
           None : 5,
        }
        self.tip = tip or ''
        if not tip and callback:
            self.tip = callback.__doc__ or ''
        if not name and callback:
            self.name = callback.__name__
    
    def __deepcopy__(self, memo):
        ## status を出力するために deepcopy(tree) から呼び出されます
        return self.status
    
    def update_status(self, status):
        self.status = status
        self.Tree.SetItemImage(self.ItemId, self.symbol[status])
    
    def call(self, *args, **kwargs):
        """A proxy of the callback function"""
        if not self.callback:
            return
        owner = self.Tree.Parent
        try:
            owner.statusline("[{}]".format(self.name))
            self.update_status(-2)
            ret = self.callback(self, *args, **kwargs)
            if ret in self.symbol: # retvals could be a threading object
                self.update_status(ret)
                owner.statusline("\b {}".format(self.status))
            return ret
        except Exception as e:
            self.update_status(-3)
        finally:
            pass
    
    def control_panel(self):
        """Get owner's plugin (as control panel) if exists, None otherwise."""
        owner = self.Tree.Parent
        try:
            return getattr(owner, self.name)
        except Exception:
            return owner.parent.require(self.name)
    
    def children(self):
        """Generate items in the branch associated with this data:item"""
        this = self.ItemId
        item, cookie = self.Tree.GetFirstChild(this)
        while item.IsOk():
            yield self.Tree.GetItemData(item)
            item, cookie = self.Tree.GetNextChild(this, cookie)


class TreeCtrl(wx.TreeCtrl, CtrlInterface, TreeList):
    icons = (
    'folder', # 0: 
      'file', # 1: (default) no symbol
        '->', # 2: (busy) in process
         'w', # 3: (false) 0=failure
         'v', # 4: (true) 1=success
        '!!', # 5: (nan) error
       '!!!', # 6: (nil) exception
    )
    def __init__(self, parent, **kwargs):
        wx.TreeCtrl.__init__(self, parent, **kwargs)
        CtrlInterface.__init__(self)
        TreeList.__init__(self)
        
        self.li = wx.ImageList(16,16)
        for icon in self.icons:
            self.li.Add(Icon(icon, (16,16)))
        self.SetImageList(self.li)
        
        self.handler.update({
            0 : {
             '*Rbutton pressed' : (0, self.OnRightDown),
               'Lbutton dclick' : (0, self.OnLeftDclick),
                       'motion' : (0, self.OnMotion),
            },
        })
        self.root = None
    
    def reset(self):
        self.DeleteAllItems()
        
        self.root = self.AddRoot("The root")
        for branch in self:
            self.set_item(self.root, *branch)
    
    def update(self, key, value):
        self[key] = value
        if not self.root:
            return self.reset()
        rootkey = key.partition('/')[0]
        self.set_item(self.root, rootkey, self[rootkey])
    
    def set_item(self, parent, key, *values):
        if '/' in key:
            a, b = key.split('/', 1)
            child = self.get_item(parent, a)
            return self.set_item(child, b, *values)
        
        parent = parent or self.root
        item = self.get_item(parent, key) or self.AppendItem(parent, key)
        data = values[0]
        ## if isinstance(data, ItemData): # NG: when reloaded, <ItemData> being a new class,
        if not isinstance(data, (list,tuple)): # we only check if it is a list or not.
            self.SetItemData(item, data)
            data.ItemId = item # set reference to the own item <-data
            
            if len(values) == 1: # => (key, data)
                data.update_status(data.status) # to resotre session
                return
            
            data.symbol[-1] = 0 # set default icon as 'folder'
        
        for branch in values[-1]: # => (key, data, branches)
            self.set_item(item, *branch)
        self.SetItemImage(item, image=0)
    
    def get_item(self, parent, key):
        if '/' in key:
            a, b = key.split('/', 1)
            child = self.get_item(parent, a)
            return self.get_item(child, b)
        
        parent = parent or self.root
        item, cookie = self.GetFirstChild(parent)
        while item.IsOk():
            if key == self.GetItemText(item):
                return item
            item, cookie = self.GetNextChild(parent, cookie)
    
    def get_flags(self, root=None):
        """Get all flags in branches of root or self"""
        ## temp = TreeList()
        ## for branch in root or self:
        ##     key, data = branch[0], branch[-1]
        ##     if not isinstance(data, (list,tuple)):
        ##         temp[key] = data.status
        ##     else:
        ##         temp[key] = list(self.get_flags(data))
        ## return temp
        return copy.deepcopy(list(self)) # => ItemData.__deepcopy__
    
    def set_flags(self, temp, root=None):
        """Set temp flags to the root or self as most as possible
        temp : TreeList template of flags to copy to the `root
        """
        for org, branch in zip(temp, root or self):
            tag, flags = org[0], org[-1]
            key, data = branch[0], branch[-1]
            if key != tag:
                raise KeyError("Failed to restore status: "
                               "got inconsistent keys {!r}, {!r})".format(tag, key))
            if not isinstance(data, (list,tuple)):
                data.update_status(flags)
            else:
                self.set_flags(flags, data)
    
    ## --------------------------------
    ## TreeCtrl:Interface event handler
    ## --------------------------------
    
    def OnMotion(self, evt):
        item, flag = self.HitTest(evt.GetPosition())
        if item.IsOk():
            data = self.GetItemData(item)
            if data:
                self.SetToolTip("{}".format(data.tip))
        else:
            self.SetToolTip("")
        evt.Skip()
    
    def OnLeftDclick(self, evt):
        item, flags = self.HitTest(evt.GetPosition())
        if item.IsOk():  # and flags & (0x10|0x20|0x40|0x80):
            data = self.GetItemData(item)
            if data:
                panel = data.control_panel()
                if isinstance(panel, wx.Window):
                    panel.Show()
                else:
                    wx.MessageBox("Item {!r} does not have a control".format(data.name))
                    pass
        evt.Skip()
    
    def OnRightDown(self, evt):
        item, flags = self.HitTest(evt.GetPosition())
        if item.IsOk(): # and flags & (0x10|0x20|0x40|0x80):
            self.SelectItem(item)
            data = self.GetItemData(item)
            if data:
                panel = data.control_panel()
                
                mwx.Menu.Popup(self.Parent, (
                    (1, "clear", Icon(''), lambda v: data.update_status(-1)),
                    (2, "execute", Icon('->'),
                        lambda v: data.call(),
                        lambda v: v.Enable(data.callback is not None
                                       and data.status is not True)),
                    (),
                    (3, "pass", Icon('v'), lambda v: data.update_status(True)),
                    (4, "fail", Icon('w'), lambda v: data.update_status(False)),
                    (5, "nil", Icon('x'), lambda v: data.update_status(None)),
                    (),
                    (6, "Maintenance for {!r}".format(data.name), Icon('proc'),
                        lambda v: panel.Show(),
                        lambda v: v.Enable(isinstance(panel, wx.Window))),
                ))
        evt.Skip()
