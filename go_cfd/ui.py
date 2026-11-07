"""Qt UI for preliminary GO CFD cases; host model is strictly read-only."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QTabWidget, QVBoxLayout, QWidget,
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl, Qt

from .case_model import WindConfig, is_stale
from .case_builder import build_case
from .geometry import cube_patch, geometry_hash, inspect_surface
from .host_adapter import selected_groups, source_patches_from_selection
from .results import load_force_history
from .runner import SolverRunner, RunCancelled


class SolverThread(QThread):
    stage = Signal(str, int, int)
    output = Signal(str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, runner, parent=None):
        super().__init__(parent)
        self.runner = runner

    def run(self):
        try:
            status = self.runner.run(on_log=self.output.emit, on_stage=self.stage.emit)
            self.completed.emit(status)
        except RunCancelled as exc:
            self.failed.emit(f"CANCELLED: {exc}")
        except Exception as exc:  # display worker exception in UI; no scene mutation
            self.failed.emit(str(exc))


class CFDDialog(QDialog):
    def __init__(self, app):
        super().__init__(app.window)
        self.app = app
        self.setWindowTitle("GO CFD | Preliminary Wind Lab (v0.1-dev)")
        self.resize(820, 620)
        self.worker = None
        self.runner = None
        self.current_case = None
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        self.tabs = QTabWidget(self)
        self.model_tab = QWidget()
        self.wind_tab = QWidget()
        self.run_tab = QWidget()
        self.results_tab = QWidget()
        self.tabs.addTab(self.model_tab, "1 Model")
        self.tabs.addTab(self.wind_tab, "2 Wind")
        self.tabs.addTab(self.run_tab, "3 Mesh & Solve")
        self.tabs.addTab(self.results_tab, "4 Results")
        self._build_model_tab()
        self._build_wind_tab()
        self._build_run_tab()
        self._build_results_tab()

        outer = QVBoxLayout(self)
        outer.addWidget(QLabel("PRELIMINARY CFD ONLY - NOT FOR STRUCTURAL DESIGN"))
        outer.addWidget(self.tabs)
        self.refresh_selection()
        self._load_document_settings()

    def _build_model_tab(self):
        layout = QVBoxLayout(self.model_tab)
        self.selection_label = QLabel("No selection")
        self.selection_label.setWordWrap(True)
        layout.addWidget(self.selection_label)
        row = QHBoxLayout()
        refresh = QPushButton("Refresh selection")
        refresh.clicked.connect(self.refresh_selection)
        row.addWidget(refresh)
        layout.addLayout(row)
        model_help = QLabel(
            "Select one or more CLOSED solid Groups / Components in IngeTrazo. "
            "Internal beams and decorative objects may invalidate the CFD envelope. "
            "Your BIM geometry is never modified."
        )
        model_help.setWordWrap(True)
        layout.addWidget(model_help)
        self.model_note = QPlainTextEdit()
        self.model_note.setReadOnly(True)
        self.model_note.setPlainText(
            "W0 geometry checks: world-space transforms, triangular surface export, "
            "degenerate triangles, unmatched and non-manifold edges. "
            "No automatic healing and no assumption of engineering certification."
        )
        layout.addWidget(self.model_note)

    @staticmethod
    def _spin(maximum, suffix, decimals, value=0.0):
        control = QDoubleSpinBox()
        control.setRange(0.0, maximum)
        control.setDecimals(decimals)
        control.setSuffix(suffix)
        control.setValue(value)
        return control

    def _build_wind_tab(self):
        layout = QFormLayout(self.wind_tab)
        self.speed = self._spin(120, " m/s", 2)
        self.speed.setToolTip("Enter explicitly; the extension does not infer code design speed")
        self.direction = self._spin(359.99, " deg", 2)
        self.density = self._spin(3, " kg/m3", 3, 1.225)
        self.height = self._spin(500, " m", 2, 10)
        self.intensity = self._spin(90, " %", 1, 10)
        self.cell = self._spin(50, " m (0 = auto)", 3)
        for name, widget in (
            ("Reference velocity (required)", self.speed),
            ("Wind direction TO (+X=0, +Y=90)", self.direction),
            ("Air density", self.density),
            ("Reference height (metadata)", self.height),
            ("Turbulence intensity", self.intensity),
            ("Background cell size", self.cell),
        ):
            layout.addRow(name, widget)
        layout.addRow(QLabel(
            "Uniform inlet; NO atmospheric boundary layer or code wind-pressure method yet."
        ))

    def _build_run_tab(self):
        layout = QVBoxLayout(self.run_tab)
        form = QFormLayout()
        self.case_root = QLineEdit(str(Path.home() / "Documents" / "GO_CFD_Cases"))
        choose = QPushButton("Browse...")
        choose.clicked.connect(self._choose_folder)
        dir_row = QHBoxLayout()
        dir_row.addWidget(self.case_root)
        dir_row.addWidget(choose)
        form.addRow("Case root folder", dir_row)
        self.backend = QComboBox()
        self.backend.addItem("Native Linux / installed OpenFOAM", "native")
        self.backend.addItem("Windows WSL2", "wsl")
        form.addRow("Solver backend", self.backend)
        self.bashrc = QLineEdit()
        self.bashrc.setPlaceholderText("Optional: e.g. /opt/openfoam2606/etc/bashrc")
        form.addRow("OpenFOAM bashrc (if needed)", self.bashrc)
        layout.addLayout(form)
        row = QHBoxLayout()
        self.build_selection = QPushButton("Build case from selected model")
        self.build_selection.clicked.connect(lambda: self._build_case("model"))
        self.build_cube = QPushButton("Build sample cube case")
        self.build_cube.clicked.connect(lambda: self._build_case("cube"))
        row.addWidget(self.build_selection)
        row.addWidget(self.build_cube)
        layout.addLayout(row)
        self.case_label = QLabel("Case: not generated")
        self.case_label.setWordWrap(True)
        layout.addWidget(self.case_label)
        row2 = QHBoxLayout()
        self.run_button = QPushButton("Run OpenFOAM")
        self.run_button.clicked.connect(self._run_solver)
        self.stop_button = QPushButton("Cancel")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._cancel_solver)
        self.open_button = QPushButton("Open output folder")
        self.open_button.clicked.connect(self._open_case)
        row2.addWidget(self.run_button)
        row2.addWidget(self.stop_button)
        row2.addWidget(self.open_button)
        layout.addLayout(row2)
        self.progress = QProgressBar()
        self.progress.setRange(0, 4)
        layout.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.document().setMaximumBlockCount(500)
        layout.addWidget(self.log)

    def _build_results_tab(self):
        layout = QVBoxLayout(self.results_tab)
        self.result_state = QLabel(
            "No validated result. Even a completed CFD solver is UNVERIFIED until QA."
        )
        self.result_state.setWordWrap(True)
        layout.addWidget(self.result_state)
        buttons = QHBoxLayout()
        btn = QPushButton("Read force history")
        btn.clicked.connect(self._read_forces)
        buttons.addWidget(btn)
        verify = QPushButton("Check if model changed")
        verify.clicked.connect(self._check_stale)
        buttons.addWidget(verify)
        layout.addLayout(buttons)
        self.results_text = QPlainTextEdit()
        self.results_text.setReadOnly(True)
        layout.addWidget(self.results_text)
        layout.addWidget(QLabel(
            "Cp contours, ABL, grid convergence and structural-load export are NOT "
            "implemented in W0. Do not use these values to approve structures."
        ))

    def _choose_folder(self):
        p = QFileDialog.getExistingDirectory(self, "CFD output parent folder", self.case_root.text())
        if p:
            self.case_root.setText(p)

    def refresh_selection(self):
        selected = selected_groups(self.app.scene)
        self.selection_label.setText(
            f"Visible selected solid Groups/Components: {len(selected)}\n" +
            ", ".join(str(getattr(g, "name", "unnamed")) for g in selected[:15])
        )

    def _config(self):
        cfg = WindConfig(
            speed_ms=self.speed.value(), direction_to_deg=self.direction.value(),
            density_kgm3=self.density.value(), reference_height_m=self.height.value(),
            turbulence_intensity=self.intensity.value()/100,
            background_cell_m=self.cell.value() or None,
        )
        cfg.validate()
        return cfg

    def _build_case(self, source):
        try:
            cfg = self._config()
            self.log.appendPlainText("Extracting scene geometry (main UI thread)...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                patches = ((cube_patch(),) if source == "cube"
                           else source_patches_from_selection(self.app.scene))
                screening = inspect_surface(patches)
                self.log.appendPlainText("Geometry screening: " + json.dumps(screening))
                if not screening["watertight_candidate"]:
                    raise ValueError("Selected envelope not watertight; fix geometry before meshing")
                base = Path(self.case_root.text()).expanduser()
                name = ("cube" if source == "cube" else "selected") + "_" + datetime.now().strftime("%Y%m%d_%H%M%S")
                target = base / name
                if target.exists():
                    raise FileExistsError(f"Case folder already exists: {target}")
                manifest = build_case(target, patches, cfg)
                self.current_case = target
                self.case_label.setText(f"Generated: {target}")
                self.log.appendPlainText("Case generated. NOT RUN; NOT VALIDATED.")
                self.app.set_document_data({
                    "schema_version": 1, "last_case": str(target),
                    "source": source, "source_geometry_hash": manifest["source_geometry_hash"],
                })
            finally:
                QApplication.restoreOverrideCursor()
        except Exception as exc:
            self.log.appendPlainText("ERROR: " + str(exc))
            QMessageBox.warning(self, "GO CFD case error", str(exc))

    def _load_document_settings(self):
        data = self.app.document_data(default={})
        if isinstance(data, dict) and data.get("last_case"):
            self.current_case = Path(data["last_case"])
            self.case_label.setText("Last document case: " + str(self.current_case))
            manifest_path = self.current_case / "go_cfd_manifest.json"
            if manifest_path.is_file():
                try:
                    wind = json.loads(manifest_path.read_text(encoding="utf-8")).get("scenario", {})
                    self.speed.setValue(float(wind.get("speed_ms", 0)))
                    self.direction.setValue(float(wind.get("direction_to_deg", 0)))
                    self.density.setValue(float(wind.get("density_kgm3", 1.225)))
                    self.height.setValue(float(wind.get("reference_height_m", 10)))
                    self.intensity.setValue(float(wind.get("turbulence_intensity", 0.1))*100)
                    self.cell.setValue(float(wind.get("background_cell_m") or 0))
                except (OSError, ValueError, TypeError, KeyError):
                    pass

    def _run_solver(self):
        if self.worker is not None and self.worker.isRunning():
            return
        if self.current_case is None or not (self.current_case / "go_cfd_manifest.json").exists():
            QMessageBox.warning(self, "GO CFD", "Build a case before solving")
            return
        self.runner = SolverRunner(self.current_case,
                                   backend=self.backend.currentData(),
                                   foam_bashrc=self.bashrc.text())
        self.worker = SolverThread(self.runner, self)
        self.worker.stage.connect(self._stage)
        self.worker.output.connect(self._solver_log)
        self.worker.completed.connect(self._solved)
        self.worker.failed.connect(self._failed)
        self.build_selection.setEnabled(False)
        self.build_cube.setEnabled(False)
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress.setValue(0)
        self.worker.start()

    def _solver_log(self, msg):
        self.log.appendPlainText(msg)

    def _stage(self, name, number, total):
        self.progress.setRange(0, total)
        self.progress.setValue(number - 1)
        self.log.appendPlainText(f"STAGE {number}/{total}: {name}")

    def _finish(self):
        self.build_selection.setEnabled(True)
        self.build_cube.setEnabled(True)
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def _solved(self, status):
        self.progress.setValue(4)
        self._finish()
        self.result_state.setText(status + " - convergence and mesh QA NOT VERIFIED")
        self.tabs.setCurrentWidget(self.results_tab)
        self._read_forces()

    def _failed(self, reason):
        self._finish()
        self.log.appendPlainText("RUN STOPPED: " + reason)
        self.result_state.setText("CFD run failed/interrupted: " + reason)

    def _cancel_solver(self):
        if self.runner is not None:
            self.runner.cancel()
            self.log.appendPlainText("Cancellation requested...")

    def _open_case(self):
        if self.current_case and self.current_case.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.current_case)))

    def _read_forces(self):
        if not self.current_case:
            return
        try:
            histories = load_force_history(self.current_case)
            lines = ["PRELIMINARY - force history only (not design loads)", ""]
            for name, points in histories.items():
                if points:
                    last = points[-1]
                    lines += [f"Patch: {name} / {len(points)} samples",
                              f"Force [N]: {last.force_total_N}",
                              f"Moment [N.m]: {last.moment_total_Nm}", ""]
            if not histories:
                lines.append("No forces.dat found. Run the solver first.")
            self.results_text.setPlainText("\n".join(lines))
        except Exception as exc:
            self.results_text.setPlainText("Import failed: " + str(exc))

    def _check_stale(self):
        if not self.current_case:
            return
        try:
            manifest = json.loads((self.current_case / "go_cfd_manifest.json").read_text())
            data = self.app.document_data(default={})
            if data.get("source") == "cube":
                patches = (cube_patch(),)
            else:
                patches = source_patches_from_selection(self.app.scene)
            stale = is_stale(manifest, self._config(), geometry_hash(patches))
            self.result_state.setText(
                "STALE - model/settings changed; rerun and discard previous results" if stale
                else "Input fingerprint matches selected geometry/settings; solver QA still required"
            )
        except Exception as exc:
            self.result_state.setText("Unable to verify freshness: " + str(exc))