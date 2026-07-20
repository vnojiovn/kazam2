# -*- coding: utf-8 -*-
#
#       window_area_wl.py
#
#       Copyright 2026 Sergey Subbotin <ssubbotin@gmail.com>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 3 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
#
# Wayland region picker. A screen-covering window cannot be transparent on
# Wayland (Mutter unredirects fullscreen windows, discarding alpha), so instead
# of dimming the live desktop we display a still screenshot of it: the window is
# opaque, we paint the screenshot, darken it, and reveal the selection brightly.
# The screenshot is captured at physical resolution, so the selection rectangle
# maps 1:1 to the PipeWire capture stream pixels.
import logging
import cairo
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, Gdk, GdkPixbuf  # noqa: E402

logger = logging.getLogger("AreaWL")


class AreaWindowWL(GObject.GObject):
    __gsignals__ = {"area-selected": (GObject.SIGNAL_RUN_LAST, None, (int, int, int, int)),
                    "area-cancelled": (GObject.SIGNAL_RUN_LAST, None, ())}

    def __init__(self, screenshot_path):
        GObject.GObject.__init__(self)
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(screenshot_path)
        # The screenshot is at physical resolution; the selected region is
        # reported in these (= capture stream) pixel coordinates.
        self.screen_w = self.pixbuf.get_width()
        self.screen_h = self.pixbuf.get_height()
        self.startx = self.starty = self.endx = self.endy = 0
        self.disp_w = self.disp_h = 1
        self.drawing = False
        self.window = Gtk.Window()
        self.window.set_decorated(False)
        # We paint every pixel ourselves (the screenshot); without this GTK
        # paints its opaque theme background over our drawing (a blank window).
        self.window.set_app_paintable(True)
        self.window.fullscreen()
        self.window.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                               Gdk.EventMask.BUTTON_RELEASE_MASK |
                               Gdk.EventMask.POINTER_MOTION_MASK |
                               Gdk.EventMask.KEY_PRESS_MASK)
        self.window.connect("button-press-event", self._on_press)
        self.window.connect("motion-notify-event", self._on_motion)
        self.window.connect("button-release-event", self._on_release)
        self.window.connect("draw", self._on_draw)
        self.window.connect("key-press-event", self._on_key)
        self.window.show_all()

    def _sel_rect(self):
        x = min(self.startx, self.endx)
        y = min(self.starty, self.endy)
        return x, y, abs(self.endx - self.startx), abs(self.endy - self.starty)

    def _on_press(self, w, e):
        self.startx, self.starty = int(e.x), int(e.y)
        self.endx, self.endy = int(e.x), int(e.y)
        self.drawing = True

    def _on_motion(self, w, e):
        if self.drawing:
            self.endx, self.endy = int(e.x), int(e.y)
            self.window.queue_draw()

    def _on_release(self, w, e):
        self.drawing = False
        x, y, ww, hh = self._sel_rect()
        self.window.destroy()
        if ww > 2 and hh > 2:
            # Map display coordinates to screenshot (= stream) pixels.
            sx = self.screen_w / self.disp_w
            sy = self.screen_h / self.disp_h
            region = (int(x * sx), int(y * sy), int(ww * sx), int(hh * sy))
            logger.debug("disp=%dx%d shot=%dx%d sel(disp)=%d,%d,%d,%d -> region(shot)=%s",
                         self.disp_w, self.disp_h, self.screen_w, self.screen_h,
                         x, y, ww, hh, region)
            self.emit("area-selected", region[0], region[1], region[2], region[3])
        else:
            self.emit("area-cancelled")

    def _on_key(self, w, e):
        if e.keyval == Gdk.KEY_Escape:
            self.window.destroy()
            self.emit("area-cancelled")

    def _paint_screenshot(self, ctx):
        ctx.save()
        ctx.scale(self.disp_w / self.screen_w, self.disp_h / self.screen_h)
        Gdk.cairo_set_source_pixbuf(ctx, self.pixbuf, 0, 0)
        ctx.paint()
        ctx.restore()

    def _on_draw(self, w, ctx):
        alloc = w.get_allocation()
        self.disp_w, self.disp_h = alloc.width, alloc.height
        # Opaque window: draw the screenshot, then darken the whole thing.
        self._paint_screenshot(ctx)
        ctx.set_source_rgba(0.0, 0.0, 0.0, 0.55)
        ctx.paint()
        if self.drawing:
            x, y, ww, hh = self._sel_rect()
            if ww > 0 and hh > 0:
                # Reveal the selected region at full brightness.
                ctx.save()
                ctx.rectangle(x, y, ww, hh)
                ctx.clip()
                self._paint_screenshot(ctx)
                ctx.restore()
                ctx.set_source_rgba(0.2, 0.6, 1.0, 1.0)
                ctx.set_line_width(2)
                ctx.rectangle(x, y, ww, hh)
                ctx.stroke()
        return False
