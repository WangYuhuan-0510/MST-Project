from dataclasses import dataclass, field
from typing import List


@dataclass
class ProjectInfo:
    name: str
    path: str


@dataclass
class ProjectViewModel:
    """
    项目视图模型，占位实现。
    后续可以扩展为信号/槽或使用 Qt 的模型视图框架。
    """

    projects: List[ProjectInfo] = field(default_factory=list)

    def load_projects(self) -> None:
        self.projects.clear()

