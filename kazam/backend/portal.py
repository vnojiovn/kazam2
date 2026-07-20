# -*- coding: utf-8 -*-
#
#       portal.py
#
#       Copyright 2026 Sergey Subbotin <ssubbotin@gmail.com>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 3 of the License, or
#       (at your option) any later version.
"""xdg-desktop-portal ScreenCast client for Wayland screen capture."""
import logging
import secrets

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

logger = logging.getLogger("Portal")


class SourceType:
    MONITOR = 1
    WINDOW = 2
    VIRTUAL = 4


class CursorMode:
    HIDDEN = 1
    EMBEDDED = 2
    METADATA = 4


class PersistMode:
    DO_NOT = 0
    TRANSIENT = 1
    PERSISTENT = 2


def generate_token():
    """A unique, D-Bus-handle-safe token (letters/digits/underscore only)."""
    return "kazam_" + secrets.token_hex(8)


def select_sources_options(handle_token, source_types, cursor_embedded, restore_token):
    """Build the a{sv} options dict for ScreenCast.SelectSources."""
    opts = {
        "handle_token": GLib.Variant("s", handle_token),
        "types": GLib.Variant("u", source_types),
        "multiple": GLib.Variant("b", False),
        "cursor_mode": GLib.Variant(
            "u", CursorMode.EMBEDDED if cursor_embedded else CursorMode.HIDDEN
        ),
        "persist_mode": GLib.Variant("u", PersistMode.PERSISTENT),
    }
    if restore_token:
        opts["restore_token"] = GLib.Variant("s", restore_token)
    return opts


def parse_start_response(results):
    """Parse the a{sv} results of ScreenCast.Start.

    Returns (streams, restore_token) where streams is a list of dicts with
    node_id/x/y/width/height/source_type.
    """
    unpacked = results.unpack() if hasattr(results, "unpack") else results
    restore_token = unpacked.get("restore_token")
    streams = []
    for node_id, props in unpacked.get("streams", []):
        width, height = props.get("size", (0, 0))
        x, y = props.get("position", (0, 0))
        streams.append(
            {
                "node_id": node_id,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "source_type": props.get("source_type", SourceType.MONITOR),
            }
        )
    return streams, restore_token


gi.require_version("GObject", "2.0")
from gi.repository import GObject  # noqa: E402

PORTAL_BUS = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
SCREENCAST_IFACE = "org.freedesktop.portal.ScreenCast"
SCREENSHOT_IFACE = "org.freedesktop.portal.Screenshot"
REQUEST_IFACE = "org.freedesktop.portal.Request"


class PortalScreenCast(GObject.GObject):
    """Drives the ScreenCast handshake, emitting ready/failed/cancelled."""

    __gsignals__ = {
        "ready": (GObject.SIGNAL_RUN_LAST, None, (object, object)),     # (fd, streams)
        "failed": (GObject.SIGNAL_RUN_LAST, None, (str,)),
        "cancelled": (GObject.SIGNAL_RUN_LAST, None, ()),
        "closed": (GObject.SIGNAL_RUN_LAST, None, ()),                  # session ended
    }

    def __init__(self, source_types, cursor_embedded, restore_token=None):
        GObject.GObject.__init__(self)
        self.source_types = source_types
        self.cursor_embedded = cursor_embedded
        self.restore_token = restore_token
        self.session_handle = None
        self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self._unique_name = self._bus.get_unique_name().lstrip(":").replace(".", "_")
        self._proxy = Gio.DBusProxy.new_sync(
            self._bus, Gio.DBusProxyFlags.NONE, None,
            PORTAL_BUS, PORTAL_PATH, SCREENCAST_IFACE, None,
        )

    def _request_path(self, token):
        return "/org/freedesktop/portal/desktop/request/{0}/{1}".format(
            self._unique_name, token
        )

    def _subscribe_response(self, token, callback):
        """Subscribe to the Response signal for a request token; auto-unsubscribes."""
        sub_id = {}

        def _on_response(conn, sender, path, iface, signal, params):
            self._bus.signal_unsubscribe(sub_id["id"])
            code, results = params.unpack()
            callback(code, results)

        sub_id["id"] = self._bus.signal_subscribe(
            PORTAL_BUS, REQUEST_IFACE, "Response", self._request_path(token),
            None, Gio.DBusSignalFlags.NONE, _on_response,
        )

    def run(self):
        token = generate_token()
        self._subscribe_response(token, self._on_create_session)
        self._proxy.call_sync(
            "CreateSession",
            GLib.Variant("(a{sv})", ({
                "session_handle_token": GLib.Variant("s", generate_token()),
                "handle_token": GLib.Variant("s", token),
            },)),
            Gio.DBusCallFlags.NONE, -1, None,
        )

    def _on_create_session(self, code, results):
        if code != 0:
            self._fail_or_cancel(code)
            return
        self.session_handle = results["session_handle"]
        token = generate_token()
        self._subscribe_response(token, self._on_select_sources)
        opts = select_sources_options(
            token, self.source_types, self.cursor_embedded, self.restore_token
        )
        self._proxy.call_sync(
            "SelectSources",
            GLib.Variant("(oa{sv})", (self.session_handle, opts)),
            Gio.DBusCallFlags.NONE, -1, None,
        )

    def _on_select_sources(self, code, results):
        if code != 0:
            self._fail_or_cancel(code)
            return
        token = generate_token()
        self._subscribe_response(token, self._on_start)
        self._proxy.call_sync(
            "Start",
            GLib.Variant("(osa{sv})", (
                self.session_handle, "", {"handle_token": GLib.Variant("s", token)},
            )),
            Gio.DBusCallFlags.NONE, -1, None,
        )

    def _on_start(self, code, results):
        if code != 0:
            self._fail_or_cancel(code)
            return
        streams, restore_token = parse_start_response(results)
        if not streams:
            self.emit("failed", "Portal returned no streams")
            return
        self.restore_token = restore_token
        # Emit "closed" if the session ends out from under us — e.g. the user
        # clicks GNOME's "stop sharing" indicator. The app treats that like a
        # normal finish instead of letting the pipeline error out.
        self._bus.signal_subscribe(
            PORTAL_BUS, "org.freedesktop.portal.Session", "Closed",
            self.session_handle, None, Gio.DBusSignalFlags.NONE,
            lambda *a: self.emit("closed"))
        try:
            fd_list = Gio.UnixFDList.new()
            reply, out_fd_list = self._proxy.call_with_unix_fd_list_sync(
                "OpenPipeWireRemote",
                GLib.Variant("(oa{sv})", (self.session_handle, {})),
                Gio.DBusCallFlags.NONE, -1, fd_list, None,
            )
            fd_index = reply.unpack()[0]
            fd = out_fd_list.get(fd_index)
        except GLib.Error as exc:
            self.emit("failed", "OpenPipeWireRemote failed: {0}".format(exc))
            return
        self.emit("ready", fd, streams)

    def _fail_or_cancel(self, code):
        if code == 1:
            self.emit("cancelled")
        else:
            self.emit("failed", "Portal request failed (code {0})".format(code))

    def close(self):
        if self.session_handle:
            try:
                session = Gio.DBusProxy.new_sync(
                    self._bus, Gio.DBusProxyFlags.NONE, None,
                    PORTAL_BUS, self.session_handle,
                    "org.freedesktop.portal.Session", None,
                )
                session.call_sync("Close", None, Gio.DBusCallFlags.NONE, -1, None)
            except GLib.Error:
                pass
            self.session_handle = None


class PortalScreenshot(GObject.GObject):
    """Takes a non-interactive screenshot via the portal, emitting ready(path)."""

    __gsignals__ = {
        "ready": (GObject.SIGNAL_RUN_LAST, None, (str,)),   # local file path
        "failed": (GObject.SIGNAL_RUN_LAST, None, (str,)),
        "cancelled": (GObject.SIGNAL_RUN_LAST, None, ()),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self._unique_name = self._bus.get_unique_name().lstrip(":").replace(".", "_")
        self._proxy = Gio.DBusProxy.new_sync(
            self._bus, Gio.DBusProxyFlags.NONE, None,
            PORTAL_BUS, PORTAL_PATH, SCREENSHOT_IFACE, None,
        )

    def run(self):
        token = generate_token()
        request_path = "/org/freedesktop/portal/desktop/request/{0}/{1}".format(
            self._unique_name, token)
        sub = {}

        def _on_response(conn, sender, path, iface, signal, params):
            self._bus.signal_unsubscribe(sub["id"])
            code, results = params.unpack()
            if code == 1:
                self.emit("cancelled")
            elif code != 0:
                self.emit("failed", "Screenshot failed (code {0})".format(code))
            else:
                uri = results.get("uri", "")
                if uri.startswith("file://"):
                    self.emit("ready", uri[len("file://"):])
                else:
                    self.emit("failed", "Screenshot returned no file")

        sub["id"] = self._bus.signal_subscribe(
            PORTAL_BUS, REQUEST_IFACE, "Response", request_path,
            None, Gio.DBusSignalFlags.NONE, _on_response)
        self._proxy.call_sync(
            "Screenshot",
            GLib.Variant("(sa{sv})", ("", {
                "handle_token": GLib.Variant("s", token),
                "interactive": GLib.Variant("b", False),
            })),
            Gio.DBusCallFlags.NONE, -1, None)
