# from dataclasses import dataclass, field
# from typing import List


# @dataclass
# class RunPoint:
#     time_s: float
#     signal: float


# @dataclass
# class RunViewModel:
#     """
#     运行视图模型，占位实现。
#     """

#     running: bool = False
#     points: List[RunPoint] = field(default_factory=list)

#     def start(self) -> None:
#         self.running = True
#         self.points.clear()

#     def stop(self) -> None:
#         self.running = False

