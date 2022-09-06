#! python3
# -*- coding: utf-8 -*-
"""Jeol package for legacy TEM

Version: None
Author: Kazuya O'moto <komoto@jeol.co.jp>
"""
## try:
##     from . import _cmdl as cmdl
##     from . import _cntf as cntf
## except ImportError:
##     from .src import c4mdl as cmdl
##     from .src import c4ntf as cntf
from . import _cmdl as cmdl
from . import _cntf as cntf
from . import info
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
