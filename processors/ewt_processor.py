import numpy as np
from scipy.signal import find_peaks, butter, filtfilt
from core.interface import SignalProcessor

class EWTProcessor(SignalProcessor):
    """
    经验小波变换 (EWT) - 简化版实现
    基于频谱峰值自动划分频带，进行自适应分解
    """

    @classmethod
    def get_metadata(cls):
        return {
            "id": cls.__name__,
            "name": "EWT 模态分解",
            "description": "将信号自适应分解为多个模态(Mode)",
            "params": {
                "num_modes": {
                    "type": "number",
                    "label": "模态数量 (N)",
                    "default": 3,
                    "description": "希望分解出几个分量"
                },
                "use_envelope": {
                    "type": "select",
                    "label": "计算包络",
                    "options": ["No", "Yes"],
                    "default": "No"
                }
            }
        }

    def process(self, data: np.ndarray, params: dict) -> dict:
        try:
            fs = params.get('fs', 1.0)
            N = int(params.get('num_modes', 3))
            
            # 1. 预处理：去直流
            data = data - np.mean(data)
            n_samples = len(data)
            
            # 2. 计算频谱
            fft_val = np.fft.fft(data)
            freqs = np.fft.fftfreq(n_samples, d=1/fs)
            
            # 取正半轴
            half_n = n_samples // 2
            pos_freqs = freqs[:half_n]
            pos_amp = np.abs(fft_val[:half_n])
            
            # 3. 寻找频谱边界 (Boundaries)
            # 策略：找到最高的 N 个峰值，取它们中间的极小值作为边界
            # 为了平滑，先做一点高斯模糊或简单平滑，防止噪点干扰找峰
            # 这里简单处理：直接找前 N 个最大峰
            peaks, _ = find_peaks(pos_amp, distance=len(pos_amp)//50)
            if len(peaks) < N:
                # 峰值不够，强行均分
                boundaries = np.linspace(0, fs/2, N+1)
            else:
                # 取最高的 N 个峰
                peak_heights = pos_amp[peaks]
                sorted_indices = np.argsort(peak_heights)[::-1][:N]
                top_peaks = np.sort(peaks[sorted_indices])
                
                # 计算边界：两个峰之间的中点
                boundaries = [0] # 包含直流0
                for i in range(len(top_peaks) - 1):
                    mid_idx = (top_peaks[i] + top_peaks[i+1]) // 2
                    boundaries.append(pos_freqs[mid_idx])
                boundaries.append(fs/2) # 包含奈奎斯特频率
            
            # 4. 构建滤波器组并分解
            modes = []
            
            # 降采样设置 (绘图用)
            target_points = 2000
            step = max(1, n_samples // target_points)
            t_axis = np.linspace(0, n_samples/fs, n_samples)
            
            for i in range(len(boundaries) - 1):
                low_cut = boundaries[i]
                high_cut = boundaries[i+1]
                
                # 防止边界过于接近
                if high_cut - low_cut < 1.0: 
                    continue

                # 使用巴特沃斯带通滤波模拟 EWT 的小波滤波器组
                # (真实的 EWT 需要构建 Littlewood-Paley 小波，这里用 IIR 近似，效果在工程上类似)
                order = 3
                # Nyquist limit check
                if high_cut >= fs/2: high_cut = fs/2 - 0.1
                if low_cut <= 0: low_cut = 0.1
                
                b, a = butter(order, [low_cut, high_cut], btype='bandpass', fs=fs)
                mode_data = filtfilt(b, a, data)
                
                modes.append({
                    "name": f"Mode {i+1} ({low_cut:.1f}-{high_cut:.1f} Hz)",
                    "x": t_axis[::step].tolist(),
                    "y": mode_data[::step].tolist()
                })

            # 5. 返回特殊结构：EWT分解结果
            return {
                "type": "decomposition", # 告诉前端这是分解类结果，需要特殊渲染
                "title": "EWT 模态分解",
                "spectrum_data": {
                    "freqs": pos_freqs[::step].tolist(),
                    "amp": pos_amp[::step].tolist(),
                    "boundaries": boundaries # 传回边界，用于在频谱图上画竖线
                },
                "modes": modes
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}