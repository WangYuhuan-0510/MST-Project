# MST 项目骨架

该仓库为 MST（Microscale Thermophoresis）实验控制/分析软件的 Python 项目骨架，目录结构与模块职责如下：

- `app.py`：程序入口（启动 Qt 主窗口）
- `mst/ui`：UI 层（主窗口 + 页面 + 视图模型）
- `mst/device`：设备通讯（传输层、协议、控制器、模拟设备）
- `mst/core`：核心业务逻辑（实验模型、流程、信号处理、拟合）
- `mst/data`：数据持久化（SQLite + HDF5）
- `mst/reporting`：导出（CSV / PDF）
- `tests`：单元测试

## 安装依赖

建议使用虚拟环境：

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 运行

```bash
python app.py
```

## 先模拟跑通（推荐）

- 打开后先到 `实验设置` 页面，调整 `Kd/Rmax/噪声/点数/x范围`，点击“应用到模拟器”
- 切到 `运行` 页面，点击“开始（模拟）”，等待采样完成或点击“停止”
- 切到 `分析` 页面：
  - 点击“拟合 Kd”得到拟合的 `Kd` 与 `R²`
  - 点击“导出 CSV / PDF”
- 导出文件默认输出到 `exports/` 目录

## 运行测试

```bash
python -m pytest -q
```

