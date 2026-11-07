"""IngeTrazo QPainter overlay with animated *illustrative* air particles.

No scene mutations, fake Cp, solver activity or pressure forces.  Installed
only when the user explicitly starts Wind Preview, then reused per window.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QPointF, QRectF, QTimer
from PySide6.QtGui import QBrush, QColor, QPainter, QPen

from .wind_preview import build_preview_lines, point_at_fraction


class WindPreviewController(QObject):
    def __init__(self, app):
        super().__init__(app.window)
        self.app = app
        self.active_scene = None
        self.lines = None
        self.phase = 0.0
        self.animation_speed = 1.0
        self.timer = QTimer(self)
        self.timer.setInterval(40)  # 25 fps; all UI / graphics calls on GUI thread
        self.timer.timeout.connect(self._tick)

    def start(self, scene, lo, hi, direction_to_deg, *, count=24, speed=1.0):
        if speed <= 0 or speed > 10:
            raise ValueError("Preview speed must be 0 < speed <= 10")
        # Build only on demand, never on each selection or timer frame.
        self.lines = build_preview_lines(lo, hi, direction_to_deg, count=count)
        self.active_scene = scene
        self.animation_speed = float(speed)
        self.phase = 0.0
        # IngeTrazo supports several document viewports. A fresh tab may
        # have a different overlay list even though the window is the same.
        overlays = getattr(self.app.viewport, "_ext_overlays", ())
        if self.draw not in overlays:
            self.app.add_overlay(self.draw)
        self.timer.start()
        self.app.viewport.update()

    def stop(self):
        self.timer.stop()
        self.active_scene = None
        self.lines = None
        self.app.viewport.update()

    @property
    def running(self):
        return self.timer.isActive()

    def _tick(self):
        # One UI-driven timer; no solver thread/Qt paint calls off the GUI thread.
        self.phase = (self.phase + 0.008 * self.animation_speed) % 1.0
        self.app.viewport.update()

    def draw(self, viewport, painter):
        if not self.running or viewport.scene is not self.active_scene or not self.lines:
            return
        tracks = self.lines.tracks
        # Project all points in one host API call rather than per-segment.
        flat = [pos for path in tracks for pos in path]
        xs, ys, visible = viewport.world_to_pixels(flat)
        steps = len(tracks[0])
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(QBrush())
        line_pen = QPen(QColor(11, 165, 193, 145), 1.6)
        painter.setPen(line_pen)
        for i in range(len(tracks)):
            start = i * steps
            for j in range(steps-1):
                k = start+j
                if visible[k] and visible[k+1]:
                    painter.drawLine(QPointF(float(xs[k]), float(ys[k])),
                                     QPointF(float(xs[k+1]), float(ys[k+1])))

        # Two bright moving beads per streamline read clearly even in perspective.
        bead_pen = QPen(QColor(255, 230, 157, 235), 1.0)
        painter.setPen(bead_pen)
        painter.setBrush(QColor(255, 189, 88, 225))
        bead_points = [point_at_fraction(track, self.phase + i*.173 + shift)
                       for i, track in enumerate(tracks) for shift in (0.0, 0.49)]
        px, py, front = viewport.world_to_pixels(bead_points)
        for x, y, good in zip(px, py, front):
            if good:
                painter.drawEllipse(QPointF(float(x), float(y)), 3.2, 3.2)

        # Prominent warning on the viewport itself: visual demo != CFD.
        rect = QRectF(14, 14, 358, 51)
        painter.setPen(QPen(QColor(0, 0, 0, 0)))
        painter.setBrush(QColor(20, 30, 35, 205))
        painter.drawRoundedRect(rect, 7, 7)
        painter.setPen(QColor(236, 249, 245))
        painter.drawText(QPointF(26, 34), "GO CFD  |  ANIMATED WIND PREVIEW")
        painter.setPen(QColor(255, 204, 131))
        painter.drawText(QPointF(26, 53), "SNAPSHOT / ILLUSTRATION - NOT CFD OR DESIGN LOADS")


def controller_for(app):
    """Reuse a single overlay for repeated open/close of the CFD dialog."""
    controller = getattr(app.window, "_go_cfd_preview_controller", None)
    if controller is None:
        controller = WindPreviewController(app)
        app.window._go_cfd_preview_controller = controller
    return controller


def stop_preview(app):
    controller = getattr(app.window, "_go_cfd_preview_controller", None)
    if controller is not None:
        controller.stop()
