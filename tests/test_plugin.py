"""Host registration smoke tests for staged GO CFD plugin."""
from go_cfd import setup


class FakeMenu:
    def __init__(self):
        self.actions = []
    def addAction(self, name, callback):
        self.actions.append((name, callback))


class FakeApp:
    def __init__(self):
        self.menu = FakeMenu()
        self.actions = []
    def add_menu(self, title):
        self.title = title
        return self.menu
    def add_menu_action(self, text, callback, **kwargs):
        self.actions.append(text)


def test_plugin_registers_actions():
    app = FakeApp()
    setup(app)
    assert app.title == "GO CFD"
    assert app.menu.actions[0][0] == "Open GO CFD Wind Lab..."
    assert app.actions
