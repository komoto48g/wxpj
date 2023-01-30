#! python3
# -*- coding: utf-8 -*-
"""Jeol detector module

Author: Kazuya O'moto <komoto@jeol.co.jp>
Contributions by Hiroyuki Satoh @JEOL.JP
"""
import json
import httplib2

HTTP = httplib2.Http()
HEADER = {"connection" : "close"}


class Detector:
    """Detecgtor controller
    
    Args:
        name : detector name
        host : host server (default to '172.17.41.1')
    
    Select one of the following detector names:
    
        - TVCAM_U
        - TVCAM_SCR_L
        - TVCAM_SCR_F
    
    Attributes reference keys:
    
        - OutputImageInformation <dict>
        - ExposureTimeValue [msec]
        - GainIndex <int>
        - OffsetIndex <int>
        - BinningIndex <int>
    """
    HOST = "171.17.41.1"
    PORT = "49226/DetectorRESTService/Detector" # host:port/path/
    
    def _request(self, command, method="GET", body=None):
        url = f"http://{self.HOST}:{self.PORT}/{self.name}/{command}"
        res, con = HTTP.request(url, method, body, headers=HEADER)
        return con
    
    def __init__(self, name, host=HOST):
        self.name = name
        self.HOST = host
    
    def __getitem__(self, attr):
        """Get detector setting attributes."""
        return json.loads(self._request("Setting", "GET")).get(attr, None)
    
    def __setitem__(self, attr, value):
        """Set detector setting attributes."""
        return self._request("Setting", "POST", json.dumps({attr: value}))
    
    def StartCreateRawDataCache(self):
        """Start processing to receive live image cache."""
        return self._request("StartCreateRawDataCache", "POST")
    
    def StopCreateRawDataCache(self):
        """Stop processing to receive live image cache."""
        return self._request("StopCreateRawDataCache", "POST")
    
    def CreateRawDataCache(self):
        """Returns a live image cache."""
        return self._request("CreateRawDataCache", "GET")
    
    def LiveStart(self):
        return self._request("LiveStart", "POST")
    
    def LiveStop(self):
        return self._request("LiveStop", "POST")
    
    def AutoFocus(self):
        return self._request("AutoFocus", "POST")
    
    def AutoZ(self):
        return self._request("AutoZ", "POST")
    
    ## --------------------------------
    ## Methods w/backward compatibility
    ## --------------------------------
    
    def get_detectorsetting(self):
        return json.loads(self._request("Setting", "GET"))
    
    def set_detectorsetting(self, content):
        return self._request("Setting", "POST", json.dumps(content))
    
    def set_exposuretime_value(self, value):
        self['ExposureTimeValue'] = value
    
    def set_gainindex(self, value):
        self['GainIndex'] = value
    
    def set_offsetindex(self, value):
        self['OffsetIndex'] = value
    
    def set_binningindex(self, value):
        self['BinningIndex'] = value
