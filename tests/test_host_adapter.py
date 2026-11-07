"""Offline contract test; does not claim installed IngeTrazo compatibility."""
import sys
import types
from go_cfd import setup
from go_cfd.host_adapter import source_patches_from_selection


class _Vec:
    def __init__(self, x, y, z):
        self.v = x, y, z

    def x(self): return self.v[0]
    def y(self): return self.v[1]
    def z(self): return self.v[2]


class _Face:
    def triangulate(self):
        return [(_Vec(0, 0, 0), _Vec(1, 0, 0), _Vec(0, 1, 0))]


class _Group:
    def __init__(self):
        self.uid = 'group123'
        self.name = 'Exterior Roof'
        self.mesh = types.SimpleNamespace(faces=[_Face()])


class _Scene:
    def __init__(self):
        self.groups = [_Group()]
        self.selection = {self.groups[0]}

    def entity_visible(self, _):
        return True


def test_selected_world_faces_contract(monkeypatch):
    core = types.ModuleType('core')
    core_group = types.ModuleType('core.group')
    core_group.world_mesh = lambda group: group.mesh
    formats = types.ModuleType('formats')
    meshexport = types.ModuleType('formats.meshexport')
    meshexport.export_triangles = lambda face: face.triangulate()
    for key, val in [('core', core), ('core.group', core_group),
                     ('formats', formats), ('formats.meshexport', meshexport)]:
        monkeypatch.setitem(sys.modules, key, val)
    patches = source_patches_from_selection(_Scene())
    assert len(patches) == 1
    assert patches[0].name == 'surface_001_Exterior_Roof'
    assert patches[0].source_id == 'group123'
    assert patches[0].triangles[0][1] == (1, 0, 0)


def test_plugin_setup_registers_commands_without_qt(monkeypatch):
    class _Menu:
        def __init__(self): self.actions = []
        def addAction(self, name, func): self.actions.append((name, func))

    class _App:
        def __init__(self):
            self.window = object()
            self.menu = _Menu()
            self.entries = []
        def add_menu(self, _): return self.menu
        def add_menu_action(self, *args, **kwargs): self.entries.append(args)

    # If Qt is installed in the test runner, keep the mock host read-only.
    monkeypatch.setitem(sys.modules, 'PySide6', types.ModuleType('PySide6'))
    monkeypatch.delitem(sys.modules, 'PySide6.QtWidgets', raising=False)
    app = _App()
    setup(app)
    assert len(app.menu.actions) == 1
    assert len(app.entries) == 1
