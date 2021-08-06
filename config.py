#! python3
# -*- coding: utf-8 -*-
"""Editor's collection of config utility

Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
import pywintypes
import win32com.client
import configparser
import shutil
import sys
import os
import wx
import numpy as np


def _eval_array(x):
    try:
        return eval(x)
    except Exception:
        return x

def _format_array(arr):
    return (repr(arr)
            .replace('array', 'np.array')
            .replace('       [', '[') # erase (7) phantom of "array(["
            .replace('([[', '([\n[')
            .replace(']])', '],\n])')
            )

class ConfigData(object):
    """Config paraser wraps for sharing data:dict among plugins
    """
    def __init__(self, path, section):
        self.parser = configparser.ConfigParser()
        self.parser.optionxform = str # 大文字／小文字の区別
        self.data = {} # buffer of configuration data
        self.path = path
        self.section = section
        self.load(verbose=0)
    
    def __contains__(self, k):
        return k in self.data
    
    def __getitem__(self, k):
        ## return self.data[k]
        return self.data.get(k)
    
    def __setitem__(self, k, v):
        self.data[k] = v
    
    def load(self, keys=None, verbose=True):
        """Load configurations of the given `section
        if `keys None, load ALL keys from the section
        """
        if verbose:
            if wx.MessageBox("Do you want to reload configuration?\n"
                "\n The current data will be overwritten with the original data"
                "\n {!r} [{}], keys={!r}".format(self.path, self.section, keys),
                self.__module__, style=wx.YES_NO|wx.ICON_INFORMATION) != wx.YES:
                    return
        
        if isinstance(keys, str):
            keys = [keys]
        
        self.parser.read(self.path)
        
        entry = self.parser[self.section]
        for t in keys or entry:
            self.data[t] = _eval_array(entry[t])
    
    def save(self, keys=None, verbose=True):
        """Save configurations of the given `section
        if `keys None, save ALL keys into the section
        """
        if verbose:
            if wx.MessageBox("Do you want to save configuration?\n"
                "\n The current data will be saved and overwrites the original data"
                "\n {!r} [{}], keys={!r}".format(self.path, self.section, keys),
                self.__module__, style=wx.YES_NO|wx.ICON_INFORMATION) != wx.YES:
                    return
        
        if isinstance(keys, str):
            keys = [keys]
        try:
            opt = np.get_printoptions()
            np.set_printoptions(linewidth=256, threshold=np.inf) # printing all(inf) elements
            ## np.set_printoptions(formatter={'float':'{:-12.8g}'.format})
            
            entry = self.parser[self.section]
            for t in keys or entry:
                if t in self.parser.defaults():
                    continue
                entry[t] = _format_array(self.data[t])
            self.parser.write(open(self.path, 'w'))
        finally:
            np.set_printoptions(**opt)
    
    def export(self, keys, r=3, c=3, verbose=True):
        """Export configurations of the given `section
        """
        xlname, _ext = os.path.splitext(os.path.basename(self.path))
        xlpath = os.path.join(os.path.dirname(self.path),
                             "config-report-{}.xlsx".format(xlname))
        if verbose:
            if wx.MessageBox("Exporting config to excel file {!r}".format(xlpath),
                self.__module__, style=wx.YES_NO|wx.ICON_INFORMATION) != wx.YES:
                    return
        try:
            excel = Excel(xlpath)
            sheets = excel.book.Worksheets
            for key in keys:
                try:
                    ws = sheets(key)
                except pywintypes.com_error:
                    ws = sheets.Add(None, sheets(sheets.Count))
                    ws.Name = key
                v = self.data[key]
                if isinstance(v, np.ndarray):
                    h, w = v.shape
                    ws.Range(ws.Cells(r,c), ws.Cells(r+h-1,c+w-1)).Value = v
                else:
                    ws.Cells(r,c).Value = v
            if verbose:
                wx.MessageBox("Exported succesfully.", self.__module__)
        except pywintypes.com_error as e:
            wx.MessageBox(str(e), self.__module__)
        except Exception as e:
            wx.MessageBox("Access denied\n"
                "\n- You don't have permission to access {!r}.".format(xlpath),
                self.__module__, style=wx.ICON_WARNING)


class Excel(object):
    def __init__(self, xlpath, show=True):
        xlpath = os.path.abspath(xlpath)
        if os.path.exists(xlpath):
            try:
                ## get the active instance of Excel app on our system
                self.app = win32com.client.GetActiveObject("Excel.Application")
                self.book = self.app.Workbooks.Open(xlpath)
            except Exception:
                ## create an instance of Excel app and open the book
                try:
                    self.app = win32com.client.gencache.EnsureDispatch("Excel.Application")
                except Exception as e:
                    print("- Failed to ensure dispatch: {}".format(e))
                    try:
                        shutil.rmtree(win32com.__gen_path__)
                    except FileNotFoundError:
                        pass
                    self.app = win32com.client.dynamic.Dispatch("Excel.Application")
                self.book = self.app.Workbooks.Open(xlpath)
        else:
            ## create an instance of Excel app and create a book
            self.app = win32com.client.gencache.EnsureDispatch("Excel.Application")
            self.book = self.app.Workbooks.Add()
            self.book.SaveAs(xlpath)
        self.app.Visible = show


if __name__ == "__main__":
    import mwx
    app = wx.App()
    config = ConfigData(r"C:\usr\home\workspace\tem13\gdk-data\pylots.config", section='TEM')
    config.export(('cl3spot',))
    
    excel = Excel(r"C:\usr\home\workspace\tem13\gdk-data\config-report-pylots.xlsx")
    mwx.deb(excel)
