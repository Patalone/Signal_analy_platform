import numpy as np
from core.interface import SignalProcessor

class StitchProcessor(SignalProcessor):
    """
    拼接视图处理器
    这只是一个“传递者”，它返回原始波形数据。
    真正的拼接魔法发生在前端 charts.js 中。
    """
    
    @classmethod
    def get_metadata(cls):
        return {
            "id": cls.__name__,
            "name": "多信号拼接视图 (Concat)",
            "description": "【甲方专用】将多个信号首尾相接显示",
            "params": {} # 不需要参数
        }

    def process(self, data: np.ndarray, params: dict) -> dict:
        fs = params.get('fs', 1.0)
        n = len(data)
        
        # 为了拼接流畅，这里进行适度降采样，防止拼接后总点数过大导致浏览器崩溃
        target_points = 1000 
        step = max(1, n // target_points)
        
        # 生成相对时间轴（这就是每段信号内部的时间）
        t_axis = np.linspace(0, n/fs, n)
        
        return {
            "type": "chart",
            "chart_type": "line",
            "title": "多信号拼接视图",
            "x_label": "Time (s) - Continuous",
            "y_label": "Amplitude",
            # 注意：这里我们返回 data，前端会负责把不同文件的 data 拼起来
            "data": {
                "x": np.round(t_axis[::step], 4).tolist(),
                "y": np.round(data[::step], 4).tolist()
            }
        }