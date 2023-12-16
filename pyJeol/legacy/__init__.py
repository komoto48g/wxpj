#! python3
"""Jeol package for legacy TEM

Version: None
Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
from . import _cmdl as cmdl
from . import _cntf as cntf
from .jtypes import LensParam # as Lens
from .jtypes import LensSystem, DeflSystem, FocusSystem

cmdl.TIMEOUT = 4
cmdl.OFFLINE = False

cmdl.HOST = "172.17.41.1"
cmdl.PORT = 2001 # REQUESTPORT

cntf.HOST = "172.17.41.1"
cntf.PORT = 2010 # NOTIFYPORT

def set_host(host, offline=False):
    cmdl.OFFLINE = offline
    cmdl.HOST = host
    cntf.HOST = host
