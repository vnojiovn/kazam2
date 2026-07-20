"""Tests for pipewiresrc video source functions in kazam.backend.gstreamer.

These functions depend on GStreamer only (no GTK/display needed).
We stub out the GTK/Gdk chain that gstreamer.py pulls in transitively so the
module can be imported in a headless CI environment.
"""
import sys
import types

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst
Gst.init(None)


def _ensure_gstreamer_stubs():
    """Register lightweight stubs for GTK-dependent imports before loading
    kazam.backend.gstreamer.  Safe to call multiple times."""

    def _stub(name):
        m = types.ModuleType(name)
        sys.modules[name] = m
        return m

    if "kazam.backend.prefs" not in sys.modules:
        # Gdk / GdkX11 stubs (prefs.py does `from gi.repository import Gdk, GdkX11`)
        _gdk = _stub("gi.repository.Gdk")
        _gdk.CursorType = type("CursorType", (), {
            "TOP_LEFT_CORNER": 0, "FLEUR": 0, "CROSSHAIR": 0,
        })()
        _stub("gi.repository.GdkX11")

        _prefs_mod = _stub("kazam.backend.prefs")

        class _Prefs:
            debug = False
            test = False
            codec = 0           # CODEC_RAW
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

# Now import is safe — stubs are in place before the module is loaded.
import importlib.util as _ilu
import os as _os

_spec = _ilu.spec_from_file_location(
    "kazam.backend.gstreamer",
    _os.path.join(_os.path.dirname(__file__), "..", "kazam", "backend", "gstreamer.py"),
)
_gs_mod = _ilu.module_from_spec(_spec)
sys.modules["kazam.backend.gstreamer"] = _gs_mod
_spec.loader.exec_module(_gs_mod)

# Re-export as the name the tests reference
import pytest

# Use the loaded module directly
gstreamer = _gs_mod


def test_pipewiresrc_available_is_bool():
    assert isinstance(gstreamer.pipewiresrc_available(), bool)


@pytest.mark.skipif(
    not gstreamer.pipewiresrc_available(),
    reason="gstreamer1.0-pipewire not installed",
)
def test_make_pipewire_source_sets_fd_and_path():
    # fd=-1 is accepted as a property value; we only assert wiring here.
    src = gstreamer.make_pipewire_source(fd=-1, node_id=99)
    assert src is not None
    assert src.get_property("path") == "99"
