"""Optional native VTK 3D viewer inside an IngeTrazo Qt dialog.

All rendered fields originate from foamToVTK output; no preview proxy is used.
"""
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox,
    QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QSpinBox,
    QVBoxLayout)

from .vtk_results import (_vtk, CFDFieldError, load_cfd_results, read_boundary,
    horizontal_slice, streamlines, with_speed, with_pressure_pa, with_cp)

import vtkmodules.qt
vtkmodules.qt.PyQtImpl = "PySide6"
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor


class CFDVTKViewer(QDialog):
    MODES = (
        ("Velocity streamlines (m/s)", "streamlines"),
        ("Velocity horizontal slice (m/s)", "velocity_slice"),
        ("Pressure horizontal slice (Pa)", "pressure_slice"),
        ("Surface pressure (Pa)", "surface_pressure"),
        ("Surface Cp (dimensionless)", "surface_cp"),
    )

    def __init__(self, parent, case_dir: Path):
        super().__init__(parent)
        self.case = Path(case_dir).resolve()
        self.data = load_cfd_results(self.case)
        self.vtk = _vtk()
        self.setWindowTitle("GO CFD | Actual OpenFOAM Fields — UNVERIFIED")
        self.resize(1120, 740)
        self._tracks = []
        self._moving_points = None
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(65)
        self.timer.timeout.connect(self._animate)
        root = QVBoxLayout(self)
        note = QLabel("REAL OPENFOAM FIELD | STEADY RANS — NOT CFD-VALIDATED OR DESIGN LOADS")
        note.setStyleSheet("color: #99510e; font-weight: bold; padding: 5px")
        root.addWidget(note)
        root.addWidget(QLabel(f"Case: {self.case.name} | time dataset: {self.data.files.time_label}"))
        if not self.data.is_solver_completed:
            caution = QLabel("CAUTION: Solver did not complete all stages; field may be partial")
            caution.setStyleSheet("color: #af2020")
            root.addWidget(caution)

        row = QHBoxLayout()
        self.mode = QComboBox()
        for label, value in self.MODES:
            self.mode.addItem(label, value)
        self.mode.currentIndexChanged.connect(self._options)
        row.addWidget(self.mode, 3)
        self.seeds = QSpinBox()
        self.seeds.setRange(4, 300)
        self.seeds.setValue(80)
        row.addWidget(QLabel("Seeds"))
        row.addWidget(self.seeds)
        self.elevation = QDoubleSpinBox()
        self.elevation.setSuffix(" m")
        self.elevation.setDecimals(2)
        b = self.data.volume.GetBounds()
        self.elevation.setRange(b[4], b[5])
        self.elevation.setValue(min(b[5], max(b[4], self.data.ground_z_m + 1.5)))
        row.addWidget(QLabel("Z"))
        row.addWidget(self.elevation)
        self.patch = QComboBox()
        self.patch.addItem("All building surfaces", "all")
        self.patch.addItem("Ground", "ground")
        for path in self.data.boundary_paths:
            if path.stem not in {"ground", "inlet", "outlet", "top", "sideMin", "sideMax"}:
                self.patch.addItem(path.stem, path.stem)
        row.addWidget(self.patch, 2)
        self.animate = QCheckBox("Moving particles")
        self.animate.setChecked(True)
        row.addWidget(self.animate)
        root.addLayout(row)

        self.widget = QVTKRenderWindowInteractor(self)
        root.addWidget(self.widget, 1)
        self.renderer = self.vtk.vtkRenderer()
        self.renderer.SetBackground(0.94, 0.95, 0.97)
        self.widget.GetRenderWindow().AddRenderer(self.renderer)
        self.widget.GetRenderWindow().GetInteractor().Initialize()
        bottom = QHBoxLayout()
        render = QPushButton("Render actual CFD field")
        render.clicked.connect(self.render_field)
        bottom.addWidget(render)
        save = QPushButton("Save PNG")
        save.clicked.connect(self.save_png)
        bottom.addWidget(save)
        self.message = QLabel("Fields come exclusively from OpenFOAM foamToVTK")
        bottom.addWidget(self.message, 1)
        root.addLayout(bottom)
        self._options()
        QTimer.singleShot(0, self.render_field)

    def _options(self, *_):
        mode = self.mode.currentData()
        self.seeds.setEnabled(mode == "streamlines")
        self.elevation.setEnabled(mode.endswith("_slice"))
        self.patch.setEnabled(mode.startswith("surface_"))
        self.animate.setEnabled(mode == "streamlines")

    def _actor(self, mesh, field=None, legend=None, width=None):
        mapper = self.vtk.vtkPolyDataMapper()
        mapper.SetInputData(mesh)
        if field:
            array = mesh.GetPointData().GetArray(field)
            if array is None:
                raise CFDFieldError(f"Field missing in actual VTK data: {field}")
            lo, hi = array.GetRange()
            if hi <= lo:
                hi = lo + 1e-8
            lut = self.vtk.vtkLookupTable()
            lut.SetNumberOfTableValues(256)
            lut.SetHueRange(.67, 0)
            lut.SetTableRange(lo, hi)
            lut.Build()
            mapper.SetScalarModeToUsePointFieldData()
            mapper.SelectColorArray(field)
            mapper.SetScalarRange(lo, hi)
            mapper.SetLookupTable(lut)
            bar = self.vtk.vtkScalarBarActor()
            bar.SetTitle(legend or field)
            bar.SetLookupTable(lut)
            bar.SetNumberOfLabels(5)
            bar.SetWidth(.1)
            bar.SetHeight(.5)
            bar.SetPosition(.87, .17)
            self.renderer.AddActor2D(bar)
        else:
            mapper.ScalarVisibilityOff()
        actor = self.vtk.vtkActor()
        actor.SetMapper(mapper)
        if not field:
            actor.GetProperty().SetColor(.66, .66, .69)
            actor.GetProperty().SetOpacity(.82)
        if width:
            actor.GetProperty().SetLineWidth(width)
        self.renderer.AddActor(actor)
        return actor

    def _add_buildings(self):
        for path in self.data.boundary_paths[:300]:
            if path.stem in {"ground", "inlet", "outlet", "top", "sideMin", "sideMax"}:
                continue
            reader = self.vtk.vtkXMLPolyDataReader()
            reader.SetFileName(str(path))
            reader.Update()
            self._actor(reader.GetOutput())

    def _selected_surface(self):
        requested = self.patch.currentData()
        excluded = {"ground", "inlet", "outlet", "top", "sideMin", "sideMax"}
        chosen = [p for p in self.data.boundary_paths
                  if ((requested == "all" and p.stem not in excluded)
                      or (requested != "all" and p.stem == requested))]
        if not chosen:
            raise CFDFieldError("No matching boundary surface VTP found in real CFD export")
        append = self.vtk.vtkAppendPolyData()
        for path in chosen:
            append.AddInputData(read_boundary(path))
        append.Update()
        return append.GetOutput()

    def render_field(self):
        try:
            self.timer.stop()
            self._tracks = []
            self._moving_points = None
            self.renderer.RemoveAllViewProps()
            mode = self.mode.currentData()
            if mode == "streamlines":
                self._add_buildings()
                paths = streamlines(self.data.volume, seed_count=self.seeds.value())
                self._actor(paths, "Velocity_m_s", "U magnitude (m/s)", width=1.7)
                if self.animate.isChecked():
                    self._start_animation(paths)
                self.message.setText("Steady U: particles illustrate travel, NOT changing gusts")
            elif mode == "velocity_slice":
                section = with_speed(horizontal_slice(self.data.volume, self.elevation.value()))
                self._actor(section, "Velocity_m_s", "U magnitude (m/s)")
                self._add_buildings()
                self.message.setText("Horizontal velocity from computed CFD field")
            elif mode == "pressure_slice":
                section = with_pressure_pa(horizontal_slice(self.data.volume, self.elevation.value()),
                                           self.data.density_kgm3)
                self._actor(section, "Pressure_Pa", "Gauge pressure (Pa)")
                self._add_buildings()
                self.message.setText("Incompressible kinematic p x rho = pressure (Pa)")
            else:
                surf = self._selected_surface()
                if mode == "surface_pressure":
                    view = with_pressure_pa(surf, self.data.density_kgm3)
                    field, label = "Pressure_Pa", "Gauge pressure (Pa)"
                else:
                    view = with_cp(surf, self.data.reference_speed_ms)
                    field, label = "Cp", "Cp: p_ref = 0"
                self._actor(view, field, label)
                self.message.setText("Actual boundary field; outlet pressure reference assumed 0")
            self.renderer.ResetCamera()
            self.widget.GetRenderWindow().Render()
        except Exception as exc:
            self.message.setText(f"Render error: {exc}")
            QMessageBox.warning(self, "GO CFD VTK", str(exc))

    def _start_animation(self, traces):
        lines = traces.GetLines()
        lines.InitTraversal()
        ids = self.vtk.vtkIdList()
        tracks = []
        while lines.GetNextCell(ids) and len(tracks) < 200:
            if ids.GetNumberOfIds() >= 3:
                tracks.append(tuple(traces.GetPoint(ids.GetId(j))
                                    for j in range(ids.GetNumberOfIds())))
        if not tracks:
            return
        points = self.vtk.vtkPoints()
        verts = self.vtk.vtkCellArray()
        for track in tracks:
            idx = points.InsertNextPoint(track[0])
            verts.InsertNextCell(1)
            verts.InsertCellPoint(idx)
        cloud = self.vtk.vtkPolyData()
        cloud.SetPoints(points)
        cloud.SetVerts(verts)
        mapper = self.vtk.vtkPolyDataMapper()
        mapper.SetInputData(cloud)
        mapper.ScalarVisibilityOff()
        actor = self.vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(1, .76, .15)
        actor.GetProperty().SetPointSize(6)
        self.renderer.AddActor(actor)
        self._tracks = tracks
        self._moving_points = points
        self.phase = 0.0
        self.timer.start()

    def _animate(self):
        if self._moving_points is None:
            return
        self.phase = (self.phase + 0.008) % 1.0
        for i, track in enumerate(self._tracks):
            t = ((self.phase + i*.13) % 1.0) * (len(track)-1)
            j = int(t)
            a, b = track[j], track[min(j+1, len(track)-1)]
            f = t-j
            self._moving_points.SetPoint(i, *(a[d]*(1-f)+b[d]*f for d in range(3)))
        self._moving_points.Modified()
        self.widget.GetRenderWindow().Render()

    def save_png(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save CFD image",
            str(self.case / "GO_CFD_Results_UNVERIFIED.png"), "PNG images (*.png)")
        if filename:
            capture = self.vtk.vtkWindowToImageFilter()
            capture.SetInput(self.widget.GetRenderWindow())
            capture.Update()
            writer = self.vtk.vtkPNGWriter()
            writer.SetFileName(filename)
            writer.SetInputConnection(capture.GetOutputPort())
            writer.Write()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)
