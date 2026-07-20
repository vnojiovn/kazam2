# -*- coding: utf-8 -*-
#
#       session.py
#
#       Copyright 2026 Sergey Subbotin <ssubbotin@gmail.com>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 3 of the License, or
#       (at your option) any later version.
import os


def get_session_type():
    """Return the lowercased XDG_SESSION_TYPE, or '' if unset."""
    return os.environ.get("XDG_SESSION_TYPE", "").strip().lower()


def is_wayland():
    """True when running under a Wayland session."""
    if get_session_type() == "wayland":
        return True
    if get_session_type() == "x11":
        return False
    # Fall back to the compositor socket when XDG_SESSION_TYPE is unset.
    return bool(os.environ.get("WAYLAND_DISPLAY"))
