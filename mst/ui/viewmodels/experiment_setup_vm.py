from dataclasses import dataclass


@dataclass
class ExperimentSetupViewModel:
    """
    实验设置视图模型，占位实现。
    """

    temperature: float = 25.0
    buffer: str = ""

