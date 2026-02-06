import numpy as np
from scipy.stats import kurtosis, skew
from core.interface import SignalProcessor

class TimeDomainStats(SignalProcessor):
    """
    计算基础时域特征 + 时域波形 (支持降采样绘图)
    """
    
    @classmethod
    def get_metadata(cls):
        return {
            "id": cls.__name__,
            "name": "时域分析 (Waveform)",
            "description": "显示时域波形及统计指标",
            "params": {} 
        }

    def process(self, data: np.ndarray, params: dict) -> dict:
        try:
            fs = params.get('fs', 1.0)
            n = len(data)

            # 1. 基础统计指标
            rms = np.sqrt(np.mean(data ** 2))
            peak = np.max(np.abs(data))
            p2p = np.max(data) - np.min(data)
            
            # 2. 【新增】时域波形降采样 (防止前端卡死)
            # 生成时间轴
            t_axis = np.linspace(0, n/fs, n)
            
            target_points = 2000
            if n > target_points:
                step = n // target_points
                plot_x = t_axis[::step]
                plot_y = data[::step]
            else:
                plot_x = t_axis
                plot_y = data

            # 3. 返回混合结果 (既有图表数据，又有KPI表格)
            return {
                "type": "hybrid",  # 混合类型
                "chart_type": "line",
                "title": "时域波形",
                "x_label": "Time (s)",
                "y_label": "Amplitude",
                "data": {
                    "x": np.round(plot_x, 4).tolist(),
                    "y": np.round(plot_y, 4).tolist()
                },
                "kpi": {
                    "RMS": float(f"{rms:.4f}"),
                    "Peak-Peak": float(f"{p2p:.4f}"),
                    "Kurtosis": float(f"{kurtosis(data):.4f}"),
                    "Crest Factor": float(f"{peak/(rms+1e-9):.4f}")
                }
            }
        except Exception as e:
            return {"error": str(e)}