"""GO CFD: IngeTrazo 0.6.0 extension entry point.

The plugin remains importable without Qt/OpenFOAM. Host imports are deferred.
"""
from __future__ import annotations
from .constants import VERSION, PROJECT_NAME


def setup(app):
    """Register extension commands. Never mutate the model on setup."""
    def open_dialog(wind_tab=False):
        from .ui import CFDDialog
        dialog = getattr(app.window, "_go_cfd_dialog", None)
        if dialog is None:
            dialog = CFDDialog(app)
            app.window._go_cfd_dialog = dialog
        dialog.refresh_selection()
        if wind_tab:
            dialog.tabs.setCurrentWidget(dialog.wind_tab)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    menu = app.add_menu("GO CFD")
    menu.addAction("Open GO CFD Wind Lab...", lambda: open_dialog())
    menu.addAction("Animated Wind Preview Settings...", lambda: open_dialog(True))

    def stop_preview():
        from .preview_overlay import stop_preview as stop
        stop(app)

    menu.addAction("Stop Animated Wind Preview", stop_preview)
    app.add_menu_action("GO CFD - Wind Lab...", lambda: open_dialog(),
                        tip="Create preliminary CFD cases from selected solid groups.")
    try:
        from PySide6.QtWidgets import QToolBar
        from PySide6.QtGui import QIcon
        from pathlib import Path
        toolbar = QToolBar("GO CFD", app.window)
        toolbar.setObjectName("go_cfd_toolbar")
        icon = QIcon(str(Path(__file__).parent / "assets" / "go_cfd.svg"))
        action = toolbar.addAction(icon, "GO CFD", lambda: open_dialog())
        action.setToolTip("GO CFD - Wind & Structural Aerodynamics")
        toolbar.addAction("Stop Wind", stop_preview)
        app.window.addToolBar(toolbar)
    except (ImportError, AttributeError, RuntimeError, TypeError):
        # The menu remains usable even in a host build without toolbar hooks.
        pass
