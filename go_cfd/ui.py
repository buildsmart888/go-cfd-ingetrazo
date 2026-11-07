"""Minimal functional host panel for the staged GitHub baseline.

The full pre-release CFD case-builder UI is in the accompanying source ZIP.
This staged panel does not attempt to run CFD or claim valid results.
"""
from __future__ import annotations


class CFDDialog:
    def __init__(self, app):
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QLabel, QPushButton, QDialogButtonBox, QTextEdit
        )
        self.app = app
        self.dialog = QDialog(app.window)
        self.dialog.setObjectName("go_cfd_wind_lab")
        self.dialog.setWindowTitle("GO CFD — Wind Lab | 0.1.0-dev")
        self.dialog.resize(560, 340)
        layout = QVBoxLayout(self.dialog)
        layout.addWidget(QLabel("GO CFD | Wind & Structural Aerodynamics"))
        layout.addWidget(QLabel("Research preview — NOT FOR STRUCTURAL DESIGN"))
        self.selection = QLabel()
        layout.addWidget(self.selection)
        self.notes = QTextEdit()
        self.notes.setReadOnly(True)
        self.notes.setPlainText(
            "The repository is being populated with the GO CFD development source.\n"
            "The full pre-release case generator and solver runner are available "
            "in the source archive supplied in the project conversation.\n\n"
            "Do not use this staged UI to claim a CFD solution or design wind load."
        )
        layout.addWidget(self.notes)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.dialog.close)
        layout.addWidget(buttons)

    def refresh_selection(self):
        scene = self.app.scene
        groups = getattr(scene, "groups", [])
        chosen = [g for g in getattr(scene, "selection", [])
                  if any(g is x for x in groups)]
        self.selection.setText(f"Selected BIM groups/components: {len(chosen)}")

    def show(self):
        self.dialog.show()

    def raise_(self):
        self.dialog.raise_()

    def activateWindow(self):
        self.dialog.activateWindow()
