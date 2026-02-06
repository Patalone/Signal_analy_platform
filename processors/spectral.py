import numpy as np
from core.interface import SignalProcessor

class SpectrumAnalyzer(SignalProcessor):
    """
    计算信号频谱 (FFT)
    """

    @classmethod
    def get_metadata(cls):
        return {
            "id": cls.__name__,
            "name": "频谱分析 (FFT)",
            "description": "显示信号的频率分布图",
            "params": {
                "window": {
                    "type": "select",
                    "label": "窗函数",
                    "options": ["None", "Hanning", "Hamming", "Blackman"],
                    "default": "Hanning"
                },
                "max_freq": {
                    "type": "number",
                    "label": "最高显示频率(Hz)",
                    "default": 0, # 0表示自动
                    "description": "0表示显示到奈奎斯特频率"
                }
            }
        }

    def process(self, data: np.ndarray, params: dict) -> dict:
        fs = params.get('fs', 1.0)
        window_type = params.get('window', 'Hanning')
        max_freq_limit = float(params.get('max_freq', 0))

        n = len(data)
        
        # 1. 加窗处理
        if window_type == "Hanning":
            data = data * np.hanning(n)
        elif window_type == "Hamming":
            data = data * np.hamming(n)
        elif window_type == "Blackman":
            data = data * np.blackman(n)
            
        # 2. FFT 计算
        fft_val = np.fft.fft(data)
        amplitude = np.abs(fft_val) / n
        amplitude[1:] *= 2 # 单边谱修正
        
        freqs = np.fft.fftfreq(n, d=1/fs)
        
        # 3. 截取正半轴
        half_n = n // 2
        valid_freqs = freqs[:half_n]
        valid_amp = amplitude[:half_n]

        # 4. 频率范围过滤 (如果有设置 max_freq)
        if max_freq_limit > 0:
            mask = valid_freqs <= max_freq_limit
            valid_freqs = valid_freqs[mask]
            valid_amp = valid_amp[mask]

        # 5. 【关键】数据降采样 (Downsampling)
        # 前端 ECharts 渲染超过 2000 个点会变慢，超过 10000 个点会卡死
        target_points = 2000
        current_points = len(valid_freqs)
        
        if current_points > target_points:
            step = current_points // target_points
            # 使用切片进行降采样 [start:stop:step]
            plot_freqs = valid_freqs[::step]
            plot_amp = valid_amp[::step]
        else:
            plot_freqs = valid_freqs
            plot_amp = valid_amp

        # 6. 计算主频 (用于显示 KPI)
        peak_idx = np.argmax(valid_amp)
        main_freq = valid_freqs[peak_idx]
        max_val = valid_amp[peak_idx]

        return {
            "type": "chart",  # 告诉前端这是图表
            "chart_type": "line", # 折线图
            "title": "频谱图 (FFT)",
            "x_label": "频率 (Hz)",
            "y_label": "幅值",
            "data": {
                "x": np.round(plot_freqs, 2).tolist(),
                "y": np.round(plot_amp, 5).tolist()
            },
            "kpi": {
                "主频": f"{main_freq:.2f} Hz",
                "最大幅值": f"{max_val:.4f}"
            }
        }