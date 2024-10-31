#! python3
"""GDK utilus ver 1.0rc
"""
import time
import numpy as np

from mwx.graphman import Frame, Layer, Thread, Graph # noqa
from mwx.controls import Param, LParam, ControlPanel, Clipboard, Icon # noqa
from mwx.controls import Button, ToggleButton, TextCtrl, Choice, Gauge, Indicator # noqa


class Layer(Layer):
    import editor as edi

    su = property(lambda self: self.parent.require('startup'))


class TemLayer(Layer):
    """Layer with TEM notify and detector interface.
    """
    illumination = property(lambda self: self.parent.notify.illumination)
    imaging = property(lambda self: self.parent.notify.imaging)
    omega = property(lambda self: self.parent.notify.omega)
    tem = property(lambda self: self.parent.notify.tem)
    eos = property(lambda self: self.parent.notify.eos)
    hts = property(lambda self: self.parent.notify.hts)
    apts = property(lambda self: self.parent.notify.apts)
    gonio = property(lambda self: self.parent.notify.gonio)
    efilter = property(lambda self: self.parent.notify.efilter)

    ## --------------------------------
    ## Detector interface
    ## --------------------------------
    camerasys = 'JeolCamera'

    @property
    def cameraman(self):
        return self.parent.require(self.camerasys)

    @property
    def camera(self):
        if not self.cameraman:
            print("- No such camera system:", self.camerasys)
            return
        cam = self.cameraman.camera
        if not cam:
            cam = self.cameraman.connect()
        return cam

    def capture(self, view=False, **kwargs):
        """Capture image.
        
        Args:
            view    : If True, the buffer will be loaded into the graph view.
            **kwargs: Additional attributes of the buffer frame.
                      Used only if view is True.
        """
        return self.cameraman.capture(view, **kwargs) # output array is read-only.

    default_delay = 0.5     # delay time before exposing (till afterglow vanishes)
    signal_level = 20       # [counts]
    noise_level = 2         # [counts]
    borderline = 2          # S/N border
    cached_signal = None    # (el, p, q) or None
    cached_buffer = None    # integrated buffer
    cached_exposure = 0     # [sec]
    MAX_EXPOSURE = 1        # [sec]

    def is_signal(self, p, q):
        r = abs(p/q) # S/N ratio as inside/outside the boundary
        ## return (r > self.borderline * 5
        ##     or (r > self.borderline and p > self.noise_level))
        return r > self.borderline and p > self.noise_level

    def delay(self, sec=None):
        if sec is None:
            sec = self.default_delay
        time.sleep(sec) # [sec] wait for afterglow goes off

    def detect_beam_ellipse(self, delays=None, cache=True, cache_t=0, check=True):
        """Detect ellipse pattern in captured `src image.
        
        Args:
            delays  : delay [s] till afterglow vanishes
                      None => default_delay
            cache   : previously cached buffer to integrate
                      If true, integrate images recursively until the signal level is exceeded.
                      If false, no integration.
            cache_t : (internal use only)
            check   : Check the device status before capturing.
                      If true, check all green using det/query command.
        
        Returns:
            el  : the largest ellipse (center, rect, anle), otherwise None if not found.
            p   : density inside the area of mask per exposure time
            q   : density outside
        """
        if check and self.camerasys == 'JeolCamera':
            status = self.parent.notify.handler('det/query')
            
            if status is not None and not all(status):
                raise Exception("the apparatus is not ready to capture images.")
        
        ## Before capturing, delay to clear the cache and wait till afterglow vanishes.
        t = self.camera.exposure
        if delays is None:
            delays = self.default_delay
        self.delay(max(t, delays))
        
        src = self.capture().copy()
        
        if isinstance(cache, np.ndarray): # integrate the cached buffer
            src += cache
            t += cache_t
            cache = (t < self.MAX_EXPOSURE) # True while exposure < 1s
            self.message(f"Cached exposure {t:g} sec.")
        
        ## Find the largest ellipse in src.
        ellipses = self.edi.find_ellipses(src, ksize=3, sortby='size')
        if ellipses:
            el = ellipses[0]
            R, n, s = self.edi.calc_ellipse(src, el)
            p = R * n/s
            q = R * (1-n)/(1-s)
            if p < self.noise_level:
                event = 'detect-nobeam' # too noisy ▲
            elif abs(p/q) < self.borderline:
                event = 'detect-noborder' # not clear △
            else:
                event = 'detect-beam'
        else:
            el = None
            p = q = src.sum() / src.size
            if p < self.noise_level:
                event = 'detect-nosignal' # too dark ▲
            else:
                event = 'detect-noellipse' # not clear △
        
        if ellipses:
            if cache and p < self.signal_level:
                self.camera.exposure += cache_t or t # add exposure time
                return self.detect_beam_ellipse(0, src, t, check)
        
        TemLayer.cached_signal = (el, p, q)
        TemLayer.cached_buffer = src
        TemLayer.cached_exposure = t
        
        self.cameraman.handler(event, (el, p, q))
        return el, p, q

    def detect_beam_center(self):
        """Returns the center of the ellipse.
        (重心ではない)
        """
        el, p, q = self.detect_beam_ellipse()
        if el and self.is_signal(p, q):
            return np.array(el[0]), p, q
        return None, p, q

    def detect_beam_diameter(self):
        """Averaged diameter of beam contour ellipse.
        """
        el, p, q = self.detect_beam_ellipse()
        if el and self.is_signal(p, q):
            ra, rb = el[1]
            return (ra + rb)/2, p, q
        return None, p, q


if __name__ == "__main__":
    from debut import main
    main(debrc=".debrc")
