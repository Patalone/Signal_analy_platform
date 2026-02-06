import numpy as np
from scipy.signal import hilbert, butter, filtfilt
from core.interface import SignalProcessor

class EnvelopeProcessor(SignalProcessor):
    """
    包络分析 (Envelope Analysis) - 双域版
    同时输出：包络时域波形 + 包络频谱
    """

    @classmethod
    def get_metadata(cls):
        return {
            "id": cls.__name__,
            "name": "包络分析 (Envelope)",
            "description": "输出包络波形及包络谱，用于诊断冲击故障",
            "params": {
                "low_cut": {
                    "type": "number",
                    "label": "高通滤波(Hz)",
                    "default": 0, 
                    "description": "建议设为1000Hz以上以避开低频干扰"
                },
                "high_cut": {
                    "type": "number",
                    "label": "低通滤波(Hz)",
                    "default": 0,
                    "description": "0表示不限制"
                }
            }
        }

    def process(self, data: np.ndarray, params: dict) -> dict:
        try:
            fs = params.get('fs', 1.0)
            low_cut = float(params.get('low_cut', 0))
            high_cut = float(params.get('high_cut', 0))
            n = len(data)

            # 1. 带通滤波
            filtered_data = data
            if low_cut > 0 or high_cut > 0:
                nyq = 0.5 * fs
                low = low_cut if low_cut > 0 else 10
                high = high_cut if (high_cut > 0 and high_cut < nyq) else (nyq - 1)
                if low < high:
                    b, a = butter(4, [low/nyq, high/nyq], btype='bandpass')
                    filtered_data = filtfilt(b, a, data)

            # 2. 希尔伯特变换 -> 包络 (时域)
            analytic_signal = hilbert(filtered_data)
            envelope = np.abs(analytic_signal)
            envelope = envelope - np.mean(envelope) # 去直流

            # --- 准备时域数据 (降采样) ---
            target_points = 2000
            t_axis = np.linspace(0, n/fs, n)
            
            if n > target_points:
                step = n // target_points
                time_x = t_axis[::step]
                time_y = envelope[::step]
            else:
                time_x = t_axis
                time_y = envelope

            # 3. FFT -> 包络谱 (频域)
            fft_val = np.fft.fft(envelope)
            amplitude = np.abs(fft_val) / n
            amplitude[1:] *= 2
            freqs = np.fft.fftfreq(n, d=1/fs)
            
            half_n = n // 2
            valid_freqs = freqs[:half_n]
            valid_amp = amplitude[:half_n]
            
            # --- 准备频域数据 (降采样) ---
            if len(valid_freqs) > target_points:
                step_f = len(valid_freqs) // target_points
                freq_x = valid_freqs[::step_f]
                freq_y = valid_amp[::step_f]
            else:
                freq_x = valid_freqs
                freq_y = valid_amp

            # 4. 计算 KPI
            peak_idx = np.argmax(valid_amp)
            main_freq = valid_freqs[peak_idx]

            # 5. 返回复合结构
            return {
                "type": "dual_domain", # 标记为双域数据
                "kpi": {
                    "包络主频": f"{main_freq:.2f} Hz",
                    "最大冲击": f"{np.max(envelope):.4f}"
                },
                # 包络时域数据
                "time_data": {
                    "x": np.round(time_x, 4).tolist(),
                    "y": np.round(time_y, 4).tolist(),
                    "x_label": "Time (s)",
                    "y_label": "Envelope Amp"
                },
                # 包络频域数据
                "freq_data": {
                    "x": np.round(freq_x, 2).tolist(),
                    "y": np.round(freq_y, 5).tolist(),
                    "x_label": "Frequency (Hz)",
                    "y_label": "Spectrum Amp"
                }
            }

        except Exception as e:
            return {"error": str(e)}