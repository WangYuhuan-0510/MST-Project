from PySide6.QtWidgets import QMainWindow, QStackedWidget, QToolBar
from PySide6.QtGui import QAction

from mst.core.app_state import AppState

from .views.project_view import ProjectView
from .views.experiment_setup_view import ExperimentSetupView
from .views.run_view import RunView
from .views.analysis_view import AnalysisView


class MainWindow(QMainWindow):
    """
    应用程序主窗口，负责页面切换和全局菜单/工具栏。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("MST 实验控制平台")
        self.resize(1200, 800)

        self.state = AppState()

        self._stack = QStackedWidget(self)
        self.setCentralWidget(self._stack)

        self._init_views()
        self._init_toolbar()

    def _init_views(self) -> None:
        self.project_view = ProjectView(self)
        self.experiment_view = ExperimentSetupView(self)
        self.run_view = RunView(self)
        self.analysis_view = AnalysisView(self)

        self._stack.addWidget(self.project_view)
        self._stack.addWidget(self.experiment_view)
        self._stack.addWidget(self.run_view)
        self._stack.addWidget(self.analysis_view)

    def _init_toolbar(self) -> None:
        toolbar = QToolBar("导航", self)
        self.addToolBar(toolbar)

        act_project = QAction("项目", self)
        act_project.triggered.connect(lambda: self._stack.setCurrentWidget(self.project_view))
        toolbar.addAction(act_project)

        act_exp = QAction("实验设置", self)
        act_exp.triggered.connect(lambda: self._stack.setCurrentWidget(self.experiment_view))
        toolbar.addAction(act_exp)

        act_run = QAction("运行", self)
        act_run.triggered.connect(lambda: self._stack.setCurrentWidget(self.run_view))
        toolbar.addAction(act_run)

        act_analysis = QAction("分析", self)
        act_analysis.triggered.connect(lambda: self._stack.setCurrentWidget(self.analysis_view))
        toolbar.addAction(act_analysis)

