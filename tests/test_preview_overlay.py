"""Headless API-harness test of the IngeTrazo-style QPainter overlay lifecycle.

Uses minimal fake Qt classes; this is NOT a real IngeTrazo/Qt screenshot test.
"""
import importlib
import sys
import types


def test_overlay_registers_once_and_draws_without_scene_mutation(monkeypatch):
    qt = types.ModuleType('PySide6')
    core = types.ModuleType('PySide6.QtCore')
    gui = types.ModuleType('PySide6.QtGui')

    class QObject:
        def __init__(self, parent=None): self.parent = parent

    class Timer:
        def __init__(self, parent):
            self.started = False
            self.timeout = self
        def setInterval(self, millis): self.interval = millis
        def connect(self, callback): self.tick = callback
        def start(self): self.started = True
        def stop(self): self.started = False
        def isActive(self): return self.started

    class Point:
        def __init__(self, *args): self.coords = args

    class Pen:
        def __init__(self, *args): pass

    class Color:
        def __init__(self, *args): pass

    class Brush:
        def __init__(self, *args): pass

    class Paint:
        Antialiasing = 1
        def __init__(self): self.lines = []; self.beads = []; self.labels = []
        def setRenderHint(self, *args): pass
        def setBrush(self, *args): pass
        def setPen(self, *args): pass
        def drawLine(self, *args): self.lines.append(args)
        def drawEllipse(self, *args): self.beads.append(args)
        def drawRoundedRect(self, *args): pass
        def drawText(self, *args): self.labels.append(args)

    core.QObject = QObject
    core.QTimer = Timer
    core.QPointF = Point
    core.QRectF = Point
    gui.QColor = Color
    gui.QPen = Pen
    gui.QBrush = Brush
    gui.QPainter = Paint

    monkeypatch.setitem(sys.modules, 'PySide6', qt)
    monkeypatch.setitem(sys.modules, 'PySide6.QtCore', core)
    monkeypatch.setitem(sys.modules, 'PySide6.QtGui', gui)
    sys.modules.pop('go_cfd.preview_overlay', None)
    module = importlib.import_module('go_cfd.preview_overlay')

    class VP:
        def __init__(self, scene):
            self.scene = scene
            self.updates = 0
            self._ext_overlays = []
        def update(self): self.updates += 1
        def world_to_pixels(self, points):
            return ([x * 10.0 for x, _, _ in points],
                    [y * 10.0 for _, y, _ in points],
                    [True] * len(points))

    class App:
        def __init__(self):
            self.window = types.SimpleNamespace()
            self.viewport = VP(object())
            self.overlays = []
        def add_overlay(self, cb):
            self.overlays.append(cb)
            self.viewport._ext_overlays.append(cb)

    app = App()
    controller = module.controller_for(app)
    a, b = (0, 0, 0), (2, 3, 4)
    controller.start(app.viewport.scene, a, b, 45, count=8)
    assert len(app.overlays) == 1
    before = controller.phase
    controller._tick()
    assert controller.phase != before
    paint = Paint()
    app.overlays[0](app.viewport, paint)
    assert len(paint.lines) > 100
    assert len(paint.beads) == 16
    assert len(paint.labels) == 2
    assert app.viewport.updates >= 2

    controller.start(app.viewport.scene, a, b, 90, count=12)
    assert len(app.overlays) == 1  # Don't leak duplicate callbacks per restart.
    original_viewport = app.viewport
    other_scene = VP(object())
    app.viewport = other_scene
    controller.start(other_scene.scene, a, b, 180, count=12)
    assert len(app.overlays) == 2  # Register on newly active viewport.
    paint_other = Paint()
    controller.draw(original_viewport, paint_other)
    assert not paint_other.lines  # Previous project's overlay is suppressed.
    paint_new = Paint()
    controller.draw(other_scene, paint_new)
    assert paint_new.lines

    controller.stop()
    paint_stopped = Paint()
    controller.draw(app.viewport, paint_stopped)
    assert not paint_stopped.lines
    # Keep fake modules from leaking into any real Qt tests.
    sys.modules.pop('go_cfd.preview_overlay', None)
