from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QDoubleSpinBox,
    QSpinBox,
    QPushButton,
    QLabel,
    QHBoxLayout,
)


class ExperimentSetupView(QWidget):
    """
    实验参数设置页面（先用于模拟配置）。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)

        title = QLabel("模拟实验参数", self)
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        root.addWidget(title)

        form = QFormLayout()
        root.addLayout(form)

        self.kd = QDoubleSpinBox(self)
        self.kd.setRange(1e-6, 1e6)
        self.kd.setDecimals(6)
        self.kd.setValue(2.0)
        form.addRow("Kd (true)", self.kd)

        self.rmax = QDoubleSpinBox(self)
        self.rmax.setRange(1e-6, 1e6)
        self.rmax.setDecimals(6)
        self.rmax.setValue(5.0)
        form.addRow("Rmax (true)", self.rmax)

        self.noise = QDoubleSpinBox(self)
        self.noise.setRange(0.0, 10.0)
        self.noise.setDecimals(4)
        self.noise.setSingleStep(0.01)
        self.noise.setValue(0.05)
        form.addRow("噪声标准差", self.noise)

        self.n_points = QSpinBox(self)
        self.n_points.setRange(5, 5000)
        self.n_points.setValue(60)
        form.addRow("采样点数", self.n_points)

        self.x_min = QDoubleSpinBox(self)
        self.x_min.setRange(0.0, 1e6)
        self.x_min.setDecimals(6)
        self.x_min.setValue(0.05)
        form.addRow("x_min", self.x_min)

        self.x_max = QDoubleSpinBox(self)
        self.x_max.setRange(1e-6, 1e6)
        self.x_max.setDecimals(6)
        self.x_max.setValue(10.0)
        form.addRow("x_max", self.x_max)

        actions = QHBoxLayout()
        root.addLayout(actions)

        self.btn_apply = QPushButton("应用到模拟器", self)
        self.btn_apply.clicked.connect(self.apply_to_state)
        actions.addWidget(self.btn_apply)

        actions.addStretch(1)

        self.status = QLabel("", self)
        root.addWidget(self.status)

        self._load_from_state()

    def _mw(self):
        return self.window()

    def _load_from_state(self) -> None:
        mw = self._mw()
        if not hasattr(mw, "state"):
            return
        sim = mw.state.sim
        self.kd.setValue(sim.kd_true)
        self.rmax.setValue(sim.r_max_true)
        self.noise.setValue(sim.noise_std)
        self.n_points.setValue(sim.n_points)
        self.x_min.setValue(sim.x_min)
        self.x_max.setValue(sim.x_max)

    def apply_to_state(self) -> None:
        mw = self._mw()
        if not hasattr(mw, "state"):
            self.status.setText("未找到主窗口状态（state）")
            return
        sim = mw.state.sim
        sim.kd_true = float(self.kd.value())
        sim.r_max_true = float(self.rmax.value())
        sim.noise_std = float(self.noise.value())
        sim.n_points = int(self.n_points.value())
        sim.x_min = float(self.x_min.value())
        sim.x_max = float(self.x_max.value())
        self.status.setText("已应用：运行页将按此参数生成模拟数据。")

