"""IngeTrazo plugin-loader registration without a GUI dependency."""
from go_cfd import setup


class FakeMenu:
    def __init__(self):
        self.actions = []

    def addAction(self, title, callback):
        self.actions.append((title, callback))


class FakeApp:
    def __init__(self):
        self.menu = FakeMenu()
        self.actions = []

    def add_menu(self, title):
        self.title = title
        return self.menu

    def add_menu_action(self, title, callback, **kwargs):
        self.actions.append(title)


def test_plugin_registers_menu_without_qt():
    app = FakeApp()
    setup(app)
    assert app.title == "GO CFD"
    assert app.menu.actions[0][0] == "Open GO CFD Wind Lab..."
    assert app.actions
