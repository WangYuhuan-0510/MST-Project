from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import h5py
import numpy as np


@dataclass
class Experiment:
    """
    MST 实验数据模型（HDF5 驱动）。

    HDF5 结构：
      /raw/capillary_i
      /processed/capillary_i_fit
      /metadata/*
      /protocol/*
    """

    name: str = ""
    raw: Dict[str, List[float]] = field(default_factory=dict)
    processed: Dict[str, List[float]] = field(default_factory=dict)

    metadata: Dict[str, Any] = field(
        default_factory=lambda: {
            "temperature": "",
            "operator": "",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "excitation": "",
            "experiment_type": "",
        }
    )
    protocol: Dict[str, Any] = field(
        default_factory=lambda: {
            "led_power": 20,
            "mst_power": "中",
            "time_scheme": "[]",
        }
    )

    # 运行数据快照（用于回填 Results）
    run_data: Dict[str, Any] = field(
        default_factory=lambda: {
            "enabled_mask": [],
            "t": [],
            "concentrations": [],
            "feature_y": [],
            "selected_capillary": 0,
            "t1_s": 2.0,
        }
    )

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def from_ui(cls, *, name: str, setup_params: Dict[str, Any], excitation: str, experiment_type: str) -> "Experiment":
        exp = cls(name=name)

        exp.metadata["temperature"] = setup_params.get("temperature", "")
        exp.metadata["operator"] = setup_params.get("operator", "")
        exp.metadata["timestamp"] = datetime.now().isoformat(timespec="seconds")
        exp.metadata["excitation"] = excitation or ""
        exp.metadata["experiment_type"] = experiment_type or ""

        exp.protocol["led_power"] = int(setup_params.get("excitation_pct", 20) or 20)
        exp.protocol["mst_power"] = setup_params.get("mst_power", "中") or "中"
        exp.protocol["time_scheme"] = setup_params.get("time_scheme", "[]") or "[]"

        return exp

    def capture_from_run_view(self, run_view: Any) -> None:
        if run_view is None:
            return

        vm = getattr(run_view, "vm", None)
        if vm is None:
            return

        traces = getattr(vm, "traces", []) or []
        self.raw = {
            f"capillary_{i + 1}": [float(v) for v in trace]
            for i, trace in enumerate(traces)
            if trace
        }

        self.processed = {
            f"capillary_{i + 1}_fit": [float(v) for v in trace]
            for i, trace in enumerate(traces)
            if trace
        }

        fit = getattr(vm, "fit", None)
        if fit is not None:
            self.processed["dose_response_x_fit"] = [float(v) for v in getattr(fit, "x_fit", [])]
            self.processed["dose_response_y_fit"] = [float(v) for v in getattr(fit, "y_fit", [])]

        self.run_data = {
            "enabled_mask": [bool(v) for v in (getattr(vm, "enabled_mask", []) or [])],
            "t": [float(v) for v in (getattr(vm, "t", []) or [])],
            "concentrations": [float(v) for v in (getattr(vm, "concentrations", []) or [])],
            "feature_y": [float(v) for v in (getattr(vm, "feature_y", []) or [])],
            "selected_capillary": int(getattr(vm, "selected_capillary", 0) or 0),
            "t1_s": float(getattr(vm, "t1_s", 2.0) or 2.0),
        }

    def apply_to_setup_view(self, setup_view: Any) -> None:
        if setup_view is None:
            return

        led = int(self.protocol.get("led_power", 20) or 20)
        mst = str(self.protocol.get("mst_power", "中") or "中")

        if hasattr(setup_view, "spin_excitation"):
            setup_view.spin_excitation.setValue(max(10, min(100, led)))
        if hasattr(setup_view, "cmb_mst"):
            idx = setup_view.cmb_mst.findText(mst)
            if idx >= 0:
                setup_view.cmb_mst.setCurrentIndex(idx)

    def apply_to_run_view(self, run_view: Any) -> None:
        if run_view is None:
            return

        vm = getattr(run_view, "vm", None)
        if vm is None:
            return

        vm.stop()

        t = self.run_data.get("t", []) or []
        caps = self.run_data.get("enabled_mask", []) or []
        concentrations = self.run_data.get("concentrations", []) or []
        feature_y = self.run_data.get("feature_y", []) or []

        vm.t = [float(v) for v in t]
        vm.traces = [
            [float(v) for v in self.raw.get(f"capillary_{i + 1}", [])]
            for i in range(vm.n_capillaries)
        ]
        vm.scan_center = [trace[-1] if trace else 0.0 for trace in vm.traces]

        if caps and len(caps) == vm.n_capillaries:
            vm.enabled_mask = [bool(v) for v in caps]
        else:
            vm.enabled_mask = [True] * vm.n_capillaries

        vm.selected_capillary = int(self.run_data.get("selected_capillary", 0) or 0)
        vm.t1_s = float(self.run_data.get("t1_s", 2.0) or 2.0)
        vm.concentrations = [float(v) for v in concentrations]
        vm.feature_y = [float(v) for v in feature_y]

        fit_x = self.processed.get("dose_response_x_fit", [])
        fit_y = self.processed.get("dose_response_y_fit", [])
        if fit_x and fit_y and len(fit_x) == len(fit_y):
            from mst.ui.viewmodels.run_analysis_vm import DoseFit

            vm.fit = DoseFit(
                x_fit=[float(v) for v in fit_x],
                y_fit=[float(v) for v in fit_y],
                text="Loaded from experiment.h5",
            )
        else:
            vm.fit = None

        if hasattr(run_view, "spin_t1"):
            run_view.spin_t1.blockSignals(True)
            run_view.spin_t1.setValue(vm.t1_s)
            run_view.spin_t1.blockSignals(False)

        if hasattr(run_view, "_render"):
            run_view._render()

    def save_h5(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        with h5py.File(p, "w") as f:
            g_raw = f.create_group("raw")
            for name, values in self.raw.items():
                g_raw.create_dataset(name, data=np.asarray(values, dtype=np.float64))

            g_processed = f.create_group("processed")
            for name, values in self.processed.items():
                g_processed.create_dataset(name, data=np.asarray(values, dtype=np.float64))

            g_meta = f.create_group("metadata")
            for k, v in self.metadata.items():
                g_meta.create_dataset(k, data=np.bytes_(str(v)))

            g_protocol = f.create_group("protocol")
            for k, v in self.protocol.items():
                g_protocol.create_dataset(k, data=np.bytes_(str(v)))

            g_run = f.create_group("run")
            g_run.create_dataset("enabled_mask", data=np.asarray(self.run_data.get("enabled_mask", []), dtype=np.int8))
            g_run.create_dataset("t", data=np.asarray(self.run_data.get("t", []), dtype=np.float64))
            g_run.create_dataset("concentrations", data=np.asarray(self.run_data.get("concentrations", []), dtype=np.float64))
            g_run.create_dataset("feature_y", data=np.asarray(self.run_data.get("feature_y", []), dtype=np.float64))
            g_run.create_dataset("selected_capillary", data=np.asarray([self.run_data.get("selected_capillary", 0)], dtype=np.int32))
            g_run.create_dataset("t1_s", data=np.asarray([self.run_data.get("t1_s", 2.0)], dtype=np.float64))

    @classmethod
    def load_h5(cls, path: str | Path) -> "Experiment":
        p = Path(path)
        exp = cls(name=p.stem)

        if not p.exists():
            return exp

        with h5py.File(p, "r") as f:
            if "raw" in f:
                exp.raw = {
                    k: np.asarray(f["raw"][k], dtype=float).reshape(-1).tolist()
                    for k in f["raw"].keys()
                }
            if "processed" in f:
                exp.processed = {
                    k: np.asarray(f["processed"][k], dtype=float).reshape(-1).tolist()
                    for k in f["processed"].keys()
                }
            if "metadata" in f:
                exp.metadata = {
                    k: f["metadata"][k][()].decode("utf-8") if isinstance(f["metadata"][k][()], (bytes, np.bytes_)) else str(f["metadata"][k][()])
                    for k in f["metadata"].keys()
                }
            if "protocol" in f:
                protocol: Dict[str, Any] = {}
                for k in f["protocol"].keys():
                    v = f["protocol"][k][()]
                    text = v.decode("utf-8") if isinstance(v, (bytes, np.bytes_)) else str(v)
                    if k == "led_power":
                        protocol[k] = int(cls._safe_float(text, 20.0))
                    else:
                        protocol[k] = text
                exp.protocol = protocol

            if "run" in f:
                g = f["run"]
                exp.run_data = {
                    "enabled_mask": [bool(v) for v in np.asarray(g.get("enabled_mask", []), dtype=np.int8).reshape(-1).tolist()],
                    "t": np.asarray(g.get("t", []), dtype=float).reshape(-1).tolist(),
                    "concentrations": np.asarray(g.get("concentrations", []), dtype=float).reshape(-1).tolist(),
                    "feature_y": np.asarray(g.get("feature_y", []), dtype=float).reshape(-1).tolist(),
                    "selected_capillary": int(np.asarray(g.get("selected_capillary", [0]), dtype=np.int32).reshape(-1)[0]),
                    "t1_s": float(np.asarray(g.get("t1_s", [2.0]), dtype=np.float64).reshape(-1)[0]),
                }

        return exp
