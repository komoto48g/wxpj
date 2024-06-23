#! python3
"""Jeol package for legacy TEM
"""
## from .src import cmdl
## from .src import cntf
from . import _cmdl as cmdl
from . import _cntf as cntf


def set_host(host, offline=False):
    cmdl.OFFLINE = offline
    cmdl.HOST = host
    cntf.HOST = host
