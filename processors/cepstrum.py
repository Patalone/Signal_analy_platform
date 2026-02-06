import numpy as np
from core.interface import SignalProcessor

class CepstrumProcessor(SignalProcessor):
    """
    倒频谱分析 (Cepstrum)
    算法：IFFT( log( |FFT(x)| ) )
    用途：识别周期性的频谱结构（如齿轮故障、回声监测）。
    """

    @classmethod
    def get_metadata(cls):
        return {
            "id": cls.__name__,
            "name": "倒频谱分析 (Cepstrum)",
            "description": "检测频谱中的周期性分量(倒频率)",
            "params": {
                "window": {
                    "type": "select",
                    "label": "窗函数",
                    "options": ["None", "Hanning", "Hamming"],
                    "default": "Hanning"
                },
                "show_limit": {
                    "type": "number",
                    "label": "显示范围(s)",
                    "default": 0.5,
                    "description": "倒频率通常只需看前半段"
                }
            }
        }

    def process(self, data: np.ndarray, params: dict) -> dict:
        try:
            fs = params.get('fs', 1.0)
            window_type = params.get('window', 'Hanning')
            limit = float(params.get('show_limit', 0.5))
            n = len(data)

            # 1. 加窗
            if window_type == "Hanning":
                data = data * np.hanning(n)
            elif window_type == "Hamming":
                data = data * np.hamming(n)

            # 2. 实倒频谱计算
            # 这里的 +1e-10 是为了防止 log(0)
            spectrum = np.fft.fft(data)
            log_spectrum = np.log(np.abs(spectrum) + 1e-10)
            cepstrum = np.abs(np.fft.ifft(log_spectrum))
            
            # 3. 构建坐标轴 (倒频率 Quefrency, 单位为秒)
            quefrency = np.linspace(0, n/fs, n)

            # 4. 截取数据
            # 倒频谱第0点通常是巨大的直流分量，需要避开 (start_idx=5)
            # 另外只取前半部分或者用户指定的范围
            start_idx = 5
            mask = (quefrency > 0) & (quefrency <= limit)
            
            # 确保 mask 在 start_idx 之后
            mask[:start_idx] = False
            
            plot_x = quefrency[mask]
            plot_y = cepstrum[mask]

            # 5. 降采样优化
            target_points = 2000
            if len(plot_x) > target_points:
                step = len(plot_x) // target_points
                plot_x = plot_x[::step]
                plot_y = plot_y[::step]

            return {
                "type": "chart",
                "chart_type": "line",
                "title": "倒频谱 (Cepstrum)",
                "x_label": "Quefrency (s)",
                "y_label": "Amplitude",
                "data": {
                    "x": np.round(plot_x, 5).tolist(),
                    "y": np.round(plot_y, 5).tolist()
                },
                "kpi": {
                    "Max Peak": f"{np.max(plot_y):.4f}"
                }
            }
        except Exception as e:
            return {"error": str(e)}