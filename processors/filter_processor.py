import numpy as np
from scipy.signal import butter, filtfilt, sosfilt
from core.interface import SignalProcessor

class BandStopProcessor(SignalProcessor):
    """
    带阻滤波 (Band-Stop / Notch Filter)
    用于去除特定的频率成分，观察剩余信号特征
    """

    @classmethod
    def get_metadata(cls):
        return {
            "id": cls.__name__,
            "name": "指定频段去除 (Band Stop)",
            "description": "滤除指定频率范围，观察剩余波形",
            "params": {
                "low_freq": {"type": "number", "default": 0, "label": "起始频率(Hz)"},
                "high_freq": {"type": "number", "default": 0, "label": "终止频率(Hz)"},
                "order": {"type": "number", "default": 4, "label": "滤波器阶数"}
            }
        }

    def process(self, data: np.ndarray, params: dict) -> dict:
        try:
            fs = params.get('fs', 1.0)
            low = float(params.get('low_freq', 0))
            high = float(params.get('high_freq', 0))
            order = int(params.get('order', 4))
            n = len(data)

            # 简单的参数校验
            if low >= high or low <= 0 or high >= fs/2:
                # 如果参数无效，直接返回原始数据（或者报错）
                filtered_data = data
                status = "参数无效，未滤波"
            else:
                # 构建巴特沃斯带阻滤波器
                # [low, high] 是要滤除的频带
                nyq = 0.5 * fs
                sos = butter(order, [low/nyq, high/nyq], btype='bandstop', output='sos')
                filtered_data = sosfilt(sos, data)
                status = f"已滤除 {low:.1f} - {high:.1f} Hz"

            # --- 准备时域数据 (降采样) ---
            target_points = 2000
            t_axis = np.linspace(0, n/fs, n)
            
            if n > target_points:
                step = n // target_points
                plot_x = t_axis[::step]
                plot_y = filtered_data[::step]
            else:
                plot_x = t_axis
                plot_y = filtered_data

            # 计算滤除后的 RMS 对比
            original_rms = np.sqrt(np.mean(data**2))
            filtered_rms = np.sqrt(np.mean(filtered_data**2))
            reduction = (1 - filtered_rms/original_rms) * 100

            return {
                "type": "chart",
                "chart_type": "line",
                "title": f"滤除后波形 ({low:.0f}-{high:.0f}Hz)",
                "x_label": "Time (s)",
                "y_label": "Amplitude",
                "data": {
                    "x": np.round(plot_x, 4).tolist(),
                    "y": np.round(plot_y, 4).tolist()
                },
                "kpi": {
                    "状态": status,
                    "原始RMS": f"{original_rms:.4f}",
                    "当前RMS": f"{filtered_rms:.4f}",
                    "能量下降": f"{reduction:.2f}%"
                }
            }

        except Exception as e:
            return {"error": str(e)}