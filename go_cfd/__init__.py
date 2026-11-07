"""GO CFD: IngeTrazo 0.6.0 extension entry point.

Host and Qt imports are deliberately deferred.
"""
from __future__ import annotations
from .constants import VERSION, PROJECT_NAME


def setup(app):
    """Register extension commands without mutating the model on startup."""
    def open_dialog():
        from .ui import CFDDialog
        dialog = getattr(app.window, "_go_cfd_dialog", None)
        if dialog is None:
            dialog = CFDDialog(app)
            app.window._go_cfd_dialog = dialog
        dialog.refresh_selection()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    menu = app.add_menu("GO CFD")
    menu.addAction("Open GO CFD Wind Lab...", open_dialog)
    app.add_menu_action("GO CFD - Wind Lab...", open_dialog,
                        tip="Create preliminary CFD cases from selected solid groups.")
    try:
        from PySide6.QtWidgets import QToolBar
        from PySide6.QtGui import QIcon
        from pathlib import Path
        toolbar = QToolBar("GO CFD", app.window)
        toolbar.setObjectName("go_cfd_toolbar")
        icon = QIcon(str(Path(__file__).parent / "assets" / "go_cfd.svg"))
        action = toolbar.addAction(icon, "GO CFD", open_dialog)
        action.setToolTip("GO CFD - Wind & Structural Aerodynamics")
        app.window.addToolBar(toolbar)
    except (ImportError, AttributeError, RuntimeError, TypeError):
        pass
