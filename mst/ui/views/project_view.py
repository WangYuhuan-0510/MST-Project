from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class ProjectView(QWidget):
    """
    项目管理页面占位实现。
    后续可以在这里添加项目列表、新建/打开项目等功能。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("项目管理（后续实现 SQLite 项目/实验记录）", self))
        layout.addWidget(QLabel("先模拟跑通：请按“实验设置 → 运行 → 分析”的顺序体验闭环。", self))

