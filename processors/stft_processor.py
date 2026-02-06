import numpy as np
from scipy.signal import spectrogram
from core.interface import SignalProcessor

class STFTProcessor(SignalProcessor):
    """
    短时傅里叶变换 (STFT) - 声谱图
    展示信号频率随时间的变化情况 (热力图)
    """

    @classmethod
    def get_metadata(cls):
        return {
            "id": cls.__name__,
            "name": "时频声谱图 (STFT)",
            "description": "生成时间-频率-能量热力图，用于分析非平稳信号",
            "params": {
                "nperseg": {
                    "type": "select",
                    "label": "窗口大小",
                    "options": [256, 512, 1024],
                    "default": 256,
                    "description": "窗口越小时间分辨率越高，频率分辨率越低"
                },
                "overlap_ratio": {
                    "type": "select",
                    "label": "重叠率",
                    "options": ["50%", "75%", "90%"],
                    "default": "50%"
                }
            }
        }

    def process(self, data: np.ndarray, params: dict) -> dict:
        try:
            fs = params.get('fs', 1.0)
            nperseg = int(params.get('nperseg', 256))
            overlap_map = {"50%": 0.5, "75%": 0.75, "90%": 0.9}
            overlap_ratio = overlap_map.get(params.get('overlap_ratio'), 0.5)
            noverlap = int(nperseg * overlap_ratio)

            # 1. 计算声谱图
            # f: 频率轴, t: 时间轴, Sxx: 功率谱密度矩阵
            f, t, Sxx = spectrogram(data, fs=fs, nperseg=nperseg, noverlap=noverlap)

            # 2. 转换为 dB (对数标度)，以便看清微弱信号
            Sxx_db = 10 * np.log10(Sxx + 1e-12)

            # 3. 数据压缩 (关键步骤)
            # 热力图数据量极大 (Time x Freq)，前端渲染百万点会卡死
            # 我们将矩阵缩小到例如 100x100 或 200x200 的网格
            target_t_bins = 200
            target_f_bins = 200
            
            # 简单的网格降采样
            t_idx = np.linspace(0, len(t)-1, target_t_bins, dtype=int)
            f_idx = np.linspace(0, len(f)-1, target_f_bins, dtype=int)
            
            sub_t = t[t_idx]
            sub_f = f[f_idx]
            # 使用网格索引提取子矩阵
            sub_Sxx = Sxx_db[np.ix_(f_idx, t_idx)]

            # 4. 转换为 ECharts Heatmap 格式: [[time_idx, freq_idx, value], ...]
            heatmap_data = []
            for i in range(len(sub_f)):      # Y轴: 频率
                for j in range(len(sub_t)):  # X轴: 时间
                    # ECharts Heatmap: [x, y, value]
                    # x对应时间索引，y对应频率索引
                    val = float(f"{sub_Sxx[i, j]:.2f}")
                    heatmap_data.append([j, i, val])

            return {
                "type": "chart",
                "chart_type": "heatmap",
                "title": "时频声谱图 (Spectrogram)",
                "x_label": "Time (s)",
                "y_label": "Frequency (Hz)",
                # 传递轴数据以便前端显示 Label
                "axis_data": {
                    "x_axis": np.round(sub_t, 3).tolist(),
                    "y_axis": np.round(sub_f, 1).tolist()
                },
                "data": heatmap_data, 
                "kpi": {
                    "时间跨度": f"{t[-1]:.2f} s",
                    "频率范围": f"0 - {f[-1]:.0f} Hz"
                }
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e)}