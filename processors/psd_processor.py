import numpy as np
from scipy.signal import welch
from core.interface import SignalProcessor

class PSDProcessor(SignalProcessor):
    """
    功率谱密度分析 (PSD - Welch Method)
    """

    @classmethod
    def get_metadata(cls):
        return {
            "id": cls.__name__,
            "name": "功率谱密度 (PSD)",
            "description": "使用 Welch 方法估计信号的功率谱密度",
            "params": {
                "nperseg": {
                    "type": "select",
                    "label": "窗口长度",
                    "options": [256, 512, 1024, 2048, 4096],
                    "default": 1024
                },
                "scaling": {
                    "type": "select",
                    "label": "单位类型",
                    "options": ["density", "spectrum"],
                    "default": "density",
                    "description": "density(V**2/Hz) 或 spectrum(V**2)"
                }
            }
        }

    def process(self, data: np.ndarray, params: dict) -> dict:
        try:
            fs = params.get('fs', 1.0)
            nperseg = int(params.get('nperseg', 1024))
            scaling = params.get('scaling', 'density')
            
            # 使用 Welch 方法计算 PSD
            # f: 频率轴, Pxx: 功率谱密度
            f, Pxx = welch(data, fs=fs, nperseg=nperseg, scaling=scaling)
            
            # 转换为 dB 刻度 (10*log10) 以便观察
            # 添加微小量防止 log(0)
            Pxx_db = 10 * np.log10(Pxx + 1e-12)

            # 降采样优化绘图
            target_points = 2000
            if len(f) > target_points:
                step = len(f) // target_points
                f = f[::step]
                Pxx_db = Pxx_db[::step]

            return {
                "type": "chart",
                "chart_type": "line",
                "title": "功率谱密度 (PSD)",
                "x_label": "Frequency (Hz)",
                "y_label": "PSD (dB/Hz)",
                "data": {
                    "x": np.round(f, 2).tolist(),
                    "y": np.round(Pxx_db, 4).tolist()
                },
                "kpi": {
                    "Max PSD": f"{np.max(Pxx_db):.2f} dB",
                    "Avg Power": f"{np.mean(Pxx):.4e}"
                }
            }
        except Exception as e:
            return {"error": str(e)}