#! python3
"""Rigaku camera module.
"""
from datetime import datetime
import traceback

from jgdk import Layer, Param, LParam, Button, Choice
from pyRigaku import Camera


hostnames = [
    'localhost',
    '172.17.41.50',
]

typenames_info = { # pixel_size, h, w, ...
    "HyPix" : (0.100, 385, 775, ),
}


class Plugin(Layer):
    """Rigaku camera manager.
    """
    menukey = "Cameras/&Rigaku camera ver.2"
    
    def Init(self):
        self.binning_selector = Param("bin", (1,), handler=self.set_binning)
        self.exposure_selector = LParam("exp", (0, 5, 0.05), 0.05, handler=self.set_exposure)
        
        self.name_selector = Choice(self,
            choices=list(typenames_info), size=(100,22), readonly=1)
        
        self.host_selector = Choice(self,
            choices=hostnames, size=(100,22))
        
        self.unit_selector = LParam("mm/pix", (0,1,1e-4), 0.1)
        
        self.layout((
                self.binning_selector,
                self.exposure_selector,
            ),
            title="Acquire setting",
            type='vspin', cw=-1, lw=32, tw=40, editable=0,
        )
        self.layout((
                Button(self, "Capture", self.capture_ex, icon='camera'),
            ),
            row=2,
        )
        self.layout((
                self.name_selector,
                self.host_selector,
                self.unit_selector,
                Button(self, "Connect", self.connect, size=(-1,20)),
            ),
            title="Setup", show=0,
            type=None, lw=-1, tw=50, editable=0,
        )
        self.camera = None
    
    ## --------------------------------
    ## Camera Attributes
    ## --------------------------------
    
    def set_exposure(self, p):
        if p.value < 0.01:
            p.value = 0.01
        if self.camera:
            self.camera.exposure = p.value
    
    def set_binning(self, p):
        if self.camera:
            ## self.camera.binning = p.value # *no binning (=1 const.)
            pass
    
    def connect(self):
        name = self.name_selector.value
        host = self.host_selector.value
        if not name:
            self.message("- Camera name is not specified.")
            return
        try:
            self.message(f"Connecting to {name}...")
            if self.camera:
                self.camera.stop()
            
            self.camera = Camera(host)
            self.camera.start()
            
            self.message("Connected to", self.camera)
            
            ## <--- set camera parameter
            ## self.camera.binning = self.binning_selector.value
            ## self.camera.exposure = self.exposure_selector.value
            
            ## ---> get camera info from system
            self.binning_selector.value = self.camera.binning
            self.exposure_selector.value = self.camera.exposure
            return self.camera
        
        except Exception as e:
            self.message("- Connection failed:", e)
            self.camera = None
    
    def capture(self, view=False, **kwargs):
        """Capture image.
        
        Args:
            view    : If True, the buffer will be loaded into the graph view.
            **kwargs: Additional attributes of the buffer frame.
                      Used only if view is True.
        """
        try:
            if self.camera is None:
                self.connect()
            buf = self.camera.cache()
        except Exception:
            traceback.print_exc()
            buf = None
        else:
            if view and buf is not None:
                attributes = {
                    'localunit' : self.camera.pixel_unit,
                       'camera' : self.camera.name,
                        'pixel' : self.camera.pixel_size,
                      'binning' : self.camera.binning,
                     'exposure' : self.camera.exposure,
                 'acq_datetime' : datetime.now(),
                }
                frame = self.graph.load(buf, **attributes, **kwargs)
                self.parent.handler('frame_cached', frame)
        return buf
    
    def capture_ex(self):
        """Capture image and load into the graph view."""
        return self.capture(True)
