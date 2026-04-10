from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import h5py
import numpy as np
from mst.core.experiment_schema import default_setup_data, get_experiment_type_config, normalize_experiment_type_id


@dataclass
class Experiment:
    """
    MST 实验数据模型（基于 HDF5 驱动）。
    
    该类负责在内存中存储实验数据，并提供与 UI 界面交互以及 HDF5 文件读写的方法。
    HDF5 文件内部结构组织如下：
      /raw/capillary_i           - 原始毛细管荧光曲线数据
      /processed/capillary_i_fit - 拟合后的平滑数据或处理结果
      /metadata/* - 实验元数据（时间、操作员等）
      /protocol/* - 实验协议参数（功率、时间设置）
      /run/* - 运行时状态（掩码、浓度、选中的毛细管等）
    """

    id: str = field(default_factory=lambda: uuid4().hex)
    name: str = ""
    # 存储原始轨迹：{'capillary_1': [v1, v2, ...], ...}
    raw: Dict[str, List[float]] = field(default_factory=dict)
    # 存储处理后的轨迹或剂量响应曲线拟合点
    processed: Dict[str, List[float]] = field(default_factory=dict)

    # 实验元数据
    metadata: Dict[str, Any] = field(
        default_factory=lambda: {
            "experiment_id": uuid4().hex,
            "temperature": "",    # 实验温度
            "operator": "",       # 操作人员
            "timestamp": datetime.now().isoformat(timespec="seconds"), # 时间戳
            "excitation": "",     # 激发光波长/类型
            "experiment_type": "Pre-test", # 实验类型名称（兼容旧字段）
            "experiment_type_id": "pre_test", # 实验类型 ID（配置驱动）
        }
    )
    
    # 实验设置实例数据（按 schema 保存，不再耦合 UI 控件）
    setup_data: Dict[str, Any] = field(default_factory=lambda: default_setup_data("pre_test"))

    # 实验仪器协议设置
    protocol: Dict[str, Any] = field(
        default_factory=lambda: {
            "led_power": 20,      # LED 激发功率
            "mst_power": "中",     # 红外激光功率（通常设为 低/中/高）
            "time_scheme": "[]",  # 时间序列方案（字符串化存储）
        }
    )

    # 运行数据快照（用于保存当前分析状态，以便回填到结果视图）
    run_data: Dict[str, Any] = field(
        default_factory=lambda: {
            "enabled_mask": [],      # 布尔列表，标记哪些毛细管参与分析
            "t": [],                 # 时间轴数据
            "concentrations": [],    # 样本浓度梯度列表
            "feature_y": [],         # 计算出的响应值（如 Fnorm）
            "selected_capillary": 0, # 当前视图选中的毛细管索引
            "t1_s": 2.0,             # MST 分析的时间点设置
            "mst_t_by_ch": [],       # 串口模式每个毛细管的独立时间轴
            "scan_x_raw": [],        # 串口扫描原始 x
            "scan_y_raw": [],        # 串口扫描原始 y
        }
    )

    def __post_init__(self) -> None:
        metadata_id = str(self.metadata.get("experiment_id") or "").strip()
        if metadata_id:
            self.id = metadata_id
        else:
            self.metadata["experiment_id"] = self.id

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        """安全转换浮点数，失败时返回默认值"""
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def from_ui(
        cls,
        *,
        name: str,
        setup_params: Dict[str, Any],
        excitation: str,
        experiment_type: str,
        experiment_type_id: str | None = None,
        experiment_id: str | None = None,
    ) -> "Experiment":
        """工厂方法：根据 UI 层参数创建 Experiment。"""
        exp = cls(id=str(experiment_id).strip() if experiment_id else uuid4().hex, name=name)
        exp.metadata["experiment_id"] = exp.id

        type_id = normalize_experiment_type_id(experiment_type_id or experiment_type)
        type_cfg = get_experiment_type_config(type_id)

        # 先用 schema 默认值初始化实例数据，再覆盖 UI 输入
        exp.setup_data = default_setup_data(type_id)
        exp.setup_data.update(setup_params or {})

        # 填充元数据：管理、识别、复现实验
        exp.metadata["temperature"] = str(exp.setup_data.get("temperature", "") or "")
        exp.metadata["operator"] = str(exp.setup_data.get("operator", "") or "")
        exp.metadata["timestamp"] = datetime.now().isoformat(timespec="seconds")
        exp.metadata["excitation"] = excitation or ""
        exp.metadata["experiment_type_id"] = type_id
        exp.metadata["experiment_type"] = type_cfg.get("name", experiment_type or "Pre-test")

        # 填充协议设置：控制设备采集、运行的参数
        exp.protocol["led_power"] = int(exp.setup_data.get("excitation_pct", 20) or 20)
        exp.protocol["mst_power"] = str(exp.setup_data.get("mst_power", "中") or "中")
        exp.protocol["time_scheme"] = str(exp.setup_data.get("time_scheme", "[]") or "[]")
        exp.metadata["display_name"] = str(name or "experiment")
        exp.name = str(name or "experiment")

        return exp

    def capture_from_run_view(self, run_view: Any) -> None:
        """从运行分析视图 (RunView) 中捕获实时数据到本模型中"""
        if run_view is None:
            return

        mode = getattr(run_view, "_mode", "sim")

        # 串口模式：从 _SerialBuffer 捕获（纯串口场景必须走这里）
        if mode == "serial":
            serial_buf = getattr(run_view, "_serial_buf", None)
            if serial_buf is None:
                return

            t = [float(v) for v in serial_buf.time_list()]
            t_by_ch = [[float(v) for v in ts] for ts in serial_buf.mst_times_per_channel()]
            scan_x_raw, scan_y_raw, _ = serial_buf.scan_raw_points()
            mat = serial_buf.trace_matrix()
            mask = getattr(serial_buf, "enabled_mask", []) or []

            self.raw = {
                f"capillary_{i + 1}": [float(v) for v in trace]
                for i, trace in enumerate(mat)
                if trace
            }
            self.processed = {
                f"capillary_{i + 1}_fit": [float(v) for v in trace]
                for i, trace in enumerate(mat)
                if trace
            }

            # 串口模式下没有固定浓度，给一个占位索引
            concentrations = list(range(len(mat)))
            t1 = 2.0
            if hasattr(run_view, "spin_t1_ser"):
                try:
                    t1 = float(run_view.spin_t1_ser.value())
                except Exception:
                    t1 = 2.0
            feature_y = [float(v) for v in serial_buf.dose_y_at_t1(t1)] if mat else []

            self.run_data = {
                "enabled_mask": [bool(v) for v in mask],
                "t": t,
                "concentrations": [float(v) for v in concentrations],
                "feature_y": feature_y,
                "selected_capillary": int(getattr(getattr(run_view, "vm", None), "selected_capillary", 0) or 0),
                "highlighted_capillary": int(getattr(getattr(run_view, "vm", None), "selected_capillary", 0) or 0),
                "t1_s": float(t1),
                "mst_t_by_ch": t_by_ch,
                "scan_x_raw": [float(v) for v in scan_x_raw],
                "scan_y_raw": [float(v) for v in scan_y_raw],
            }
            return

        # 模拟模式：从 ViewModel 捕获
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
            "highlighted_capillary": int(getattr(vm, "selected_capillary", 0) or 0),
            "t1_s": float(getattr(vm, "t1_s", 2.0) or 2.0),
        }

    def apply_to_setup_view(self, setup_view: Any) -> None:
        """将模型中的配置与协议参数应用回设置界面。"""
        if setup_view is None:
            return

        setup_data = dict(default_setup_data(self.metadata.get("experiment_type_id", "pre_test")))
        setup_data.update(self.setup_data or {})

        if hasattr(setup_view, "set_data"):
            setup_view.set_data(setup_data)

        led = int(self.protocol.get("led_power", setup_data.get("excitation_pct", 20)) or 20)
        mst = str(self.protocol.get("mst_power", setup_data.get("mst_power", "中")) or "中")

        if hasattr(setup_view, "spin_excitation"):
            setup_view.spin_excitation.setValue(max(10, min(100, led)))
        if hasattr(setup_view, "cmb_mst"):
            idx = setup_view.cmb_mst.findText(mst)
            if idx >= 0:
                setup_view.cmb_mst.setCurrentIndex(idx)

    def apply_to_run_view(self, run_view: Any) -> None:
        """将加载的实验数据还原到运行/分析界面 (RunView) 中进行重现"""
        if run_view is None:
            return

        vm = getattr(run_view, "vm", None)
        if vm is None:
            return

        vm.stop() # 停止当前可能正在运行的任务

        # 获取保存的数据
        t = self.run_data.get("t", []) or []
        caps = self.run_data.get("enabled_mask", []) or []
        concentrations = self.run_data.get("concentrations", []) or []
        feature_y = self.run_data.get("feature_y", []) or []

        # 还原时间轴和原始曲线
        vm.t = [float(v) for v in t]
        vm.traces = [
            [float(v) for v in self.raw.get(f"capillary_{i + 1}", [])]
            for i in range(vm.n_capillaries)
        ]
        # 根据曲线最后一点还原扫描中心参考值
        vm.scan_center = [trace[-1] if trace else 0.0 for trace in vm.traces]

        # 还原有效性掩码
        if caps and len(caps) == vm.n_capillaries:
            vm.enabled_mask = [bool(v) for v in caps]
        else:
            vm.enabled_mask = [True] * vm.n_capillaries

        # 还原分析状态
        highlighted = int(self.run_data.get("highlighted_capillary", self.run_data.get("selected_capillary", 0)) or 0)
        vm.selected_capillary = highlighted
        vm.t1_s = float(self.run_data.get("t1_s", 2.0) or 2.0)
        vm.concentrations = [float(v) for v in concentrations]
        vm.feature_y = [float(v) for v in feature_y]

        # 还原剂量响应拟合对象
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

        # 更新 UI 上的数值输入框
        if hasattr(run_view, "spin_t1"):
            run_view.spin_t1.blockSignals(True) # 阻止信号以防触发重复计算
            run_view.spin_t1.setValue(vm.t1_s)
            run_view.spin_t1.blockSignals(False)

        # 触发界面重新渲染
        if hasattr(run_view, "_render"):
            run_view._render()

    def save_h5(self, path: str | Path) -> None:
        """将当前的 Experiment 对象保存到 HDF5 文件中"""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self.metadata["experiment_id"] = self.id

        with h5py.File(p, "w") as f:
            utf8_dtype = h5py.string_dtype(encoding="utf-8")

            # 保存原始轨迹数据
            g_raw = f.create_group("raw")
            for name, values in self.raw.items():
                g_raw.create_dataset(name, data=np.asarray(values, dtype=np.float64))

            # 保存处理后的数据
            g_processed = f.create_group("processed")
            for name, values in self.processed.items():
                g_processed.create_dataset(name, data=np.asarray(values, dtype=np.float64))

            # 保存元数据（UTF-8）
            g_meta = f.create_group("metadata")
            for k, v in self.metadata.items():
                g_meta.create_dataset(k, data=str(v), dtype=utf8_dtype)

            # 保存协议数据（UTF-8）
            g_protocol = f.create_group("protocol")
            for k, v in self.protocol.items():
                g_protocol.create_dataset(k, data=str(v), dtype=utf8_dtype)

            # 保存实验实例配置（Schema-driven setup data）
            g_setup = f.create_group("setup")
            for k, v in (self.setup_data or {}).items():
                g_setup.create_dataset(k, data=str(v), dtype=utf8_dtype)

            # 保存分析运行数据
            g_run = f.create_group("run")
            g_run.create_dataset("enabled_mask", data=np.asarray(self.run_data.get("enabled_mask", []), dtype=np.int8))
            g_run.create_dataset("t", data=np.asarray(self.run_data.get("t", []), dtype=np.float64))
            g_run.create_dataset("concentrations", data=np.asarray(self.run_data.get("concentrations", []), dtype=np.float64))
            g_run.create_dataset("feature_y", data=np.asarray(self.run_data.get("feature_y", []), dtype=np.float64))
            g_run.create_dataset("selected_capillary", data=np.asarray([self.run_data.get("selected_capillary", 0)], dtype=np.int32))
            g_run.create_dataset("highlighted_capillary", data=np.asarray([self.run_data.get("highlighted_capillary", self.run_data.get("selected_capillary", 0))], dtype=np.int32))
            g_run.create_dataset("t1_s", data=np.asarray([self.run_data.get("t1_s", 2.0)], dtype=np.float64))
            g_run.create_dataset("scan_x_raw", data=np.asarray(self.run_data.get("scan_x_raw", []), dtype=np.float64))
            g_run.create_dataset("scan_y_raw", data=np.asarray(self.run_data.get("scan_y_raw", []), dtype=np.float64))
            mst_t_by_ch = self.run_data.get("mst_t_by_ch", []) or []
            if mst_t_by_ch:
                max_len = max((len(ts) for ts in mst_t_by_ch), default=0)
                if max_len > 0:
                    arr = np.full((len(mst_t_by_ch), max_len), np.nan, dtype=np.float64)
                    for i, ts in enumerate(mst_t_by_ch):
                        if not ts:
                            continue
                        n = min(len(ts), max_len)
                        arr[i, :n] = np.asarray(ts[:n], dtype=np.float64)
                    g_run.create_dataset("mst_t_by_ch", data=arr)

    @classmethod
    def load_h5(cls, path: str | Path) -> "Experiment":
        """从指定的 HDF5 文件加载 Experiment 对象"""
        p = Path(path)
        exp = cls(name=p.stem) # 默认使用文件名作为实验名

        if not p.exists():
            return exp

        with h5py.File(p, "r") as f:
            # 加载原始数据
            if "raw" in f:
                exp.raw = {
                    k: np.asarray(f["raw"][k], dtype=float).reshape(-1).tolist()
                    for k in f["raw"].keys()
                }
            # 加载处理数据
            if "processed" in f:
                exp.processed = {
                    k: np.asarray(f["processed"][k], dtype=float).reshape(-1).tolist()
                    for k in f["processed"].keys()
                }
            # 加载元数据并解码字节
            if "metadata" in f:
                exp.metadata = {
                    k: f["metadata"][k][()].decode("utf-8") if isinstance(f["metadata"][k][()], (bytes, np.bytes_)) else str(f["metadata"][k][()])
                    for k in f["metadata"].keys()
                }
                exp.metadata["experiment_type_id"] = normalize_experiment_type_id(
                    str(exp.metadata.get("experiment_type_id") or exp.metadata.get("experiment_type") or "pre_test")
                )
                exp.id = str(exp.metadata.get("experiment_id") or exp.id)
                exp.metadata["experiment_id"] = exp.id
                exp.name = str(exp.metadata.get("display_name") or exp.name)
            # 加载协议并转换特定字段类型
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

            # 加载 setup 实例数据（配置驱动 UI 的数据层）
            type_id = normalize_experiment_type_id(
                str(exp.metadata.get("experiment_type_id") or exp.metadata.get("experiment_type") or "pre_test")
            )
            exp.setup_data = default_setup_data(type_id)
            if "setup" in f:
                for k in f["setup"].keys():
                    v = f["setup"][k][()]
                    exp.setup_data[k] = v.decode("utf-8") if isinstance(v, (bytes, np.bytes_)) else v

            # 加载运行状态数据
            if "run" in f:
                g = f["run"]
                exp.run_data = {
                    "enabled_mask": [bool(v) for v in np.asarray(g.get("enabled_mask", []), dtype=np.int8).reshape(-1).tolist()],
                    "t": np.asarray(g.get("t", []), dtype=float).reshape(-1).tolist(),
                    "concentrations": np.asarray(g.get("concentrations", []), dtype=float).reshape(-1).tolist(),
                    "feature_y": np.asarray(g.get("feature_y", []), dtype=float).reshape(-1).tolist(),
                    "selected_capillary": int(np.asarray(g.get("selected_capillary", [0]), dtype=np.int32).reshape(-1)[0]),
                    "t1_s": float(np.asarray(g.get("t1_s", [2.0]), dtype=np.float64).reshape(-1)[0]),
                    "mst_t_by_ch": [],
                    "scan_x_raw": np.asarray(g.get("scan_x_raw", []), dtype=np.float64).reshape(-1).tolist(),
                    "scan_y_raw": np.asarray(g.get("scan_y_raw", []), dtype=np.float64).reshape(-1).tolist(),
                }
                if "mst_t_by_ch" in g:
                    arr = np.asarray(g["mst_t_by_ch"], dtype=np.float64)
                    t_by_ch: List[List[float]] = []
                    for row in arr:
                        vals = [float(v) for v in row.tolist() if np.isfinite(v)]
                        t_by_ch.append(vals)
                    exp.run_data["mst_t_by_ch"] = t_by_ch

        exp.metadata.setdefault("experiment_id", exp.id)
        return exp