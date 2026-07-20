"""Tests for the region_to_crop helper in kazam.backend.gstreamer.

Uses the same stub pattern as test_gstreamer_source.py so the module can be
imported in a headless environment without a display.
"""
import sys
import types

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst
Gst.init(None)


def _ensure_gstreamer_stubs():
    def _stub(name):
        m = types.ModuleType(name)
        sys.modules[name] = m
        return m

    if "kazam.backend.prefs" not in sys.modules:
        _gdk = _stub("gi.repository.Gdk")
        _gdk.CursorType = type("CursorType", (), {
            "TOP_LEFT_CORNER": 0, "FLEUR": 0, "CROSSHAIR": 0,
        })()
        _stub("gi.repository.GdkX11")

        _prefs_mod = _stub("kazam.backend.prefs")

        class _Prefs:
            debug = False
            test = False
            codec = 0
            framerate = 15
            capture_cursor = True
            capture_cursor_broadcast = True
            video_dest = "/tmp"
            webcam_resolution = 0
            webcam_show_preview = False
            xid_geometry = (0, 0, 100, 100)

        _prefs_mod.prefs = _Prefs()
        _prefs_mod.MODE_SCREENCAST = 0
        _prefs_mod.MODE_SCREENSHOT = 1
        _prefs_mod.MODE_BROADCAST = 2
        _prefs_mod.MODE_WEBCAM = 3
        _prefs_mod.CODEC_RAW = 0
        _prefs_mod.CODEC_H264 = 2
        _prefs_mod.CODEC_VP8 = 1
        _prefs_mod.CODEC_HUFF = 3
        _prefs_mod.CODEC_JPEG = 4
        _prefs_mod.CODEC_LIST = {0: [0, None, "RAW (AVI)", ".avi", True]}
        _prefs_mod.CAM_RESOLUTIONS = {0: (640, 480)}
        _prefs_mod.is_window_offscreen = lambda *a: False
        _prefs_mod.move_window_on_screen = lambda *a: None
        _prefs_mod.get_screen_resolution = lambda: (1920, 1080)
        _prefs_mod.HW = None

    if "kazam.backend.utils" not in sys.modules:
        _utils = _stub("kazam.backend.utils")
        _utils.is_xdotool_installed = lambda: False
        _utils.show_popup = lambda *a, **kw: None

    if "kazam.frontend.window_webcam" not in sys.modules:
        if "kazam.frontend" not in sys.modules:
            _stub("kazam.frontend")
        _wcw = _stub("kazam.frontend.window_webcam")
        _wcw.WebcamWindow = object


_ensure_gstreamer_stubs()

import importlib.util as _ilu
import os as _os

_spec = _ilu.spec_from_file_location(
    "kazam.backend.gstreamer",
    _os.path.join(_os.path.dirname(__file__), "..", "kazam", "backend", "gstreamer.py"),
)
_gs_mod = _ilu.module_from_spec(_spec)
sys.modules["kazam.backend.gstreamer"] = _gs_mod
_spec.loader.exec_module(_gs_mod)

from kazam.backend.gstreamer import region_to_crop


def test_region_to_crop_basic():
    # stream is 1920x1080; user picked a 640x480 box at (100, 50)
    crop = region_to_crop(region=(100, 50, 640, 480), stream_w=1920, stream_h=1080)
    assert crop == {"left": 100, "top": 50, "right": 1920 - (100 + 640),
                    "bottom": 1080 - (50 + 480)}


def test_region_to_crop_clamps_negative():
    crop = region_to_crop(region=(0, 0, 4000, 4000), stream_w=1920, stream_h=1080)
    assert crop["right"] == 0 and crop["bottom"] == 0
