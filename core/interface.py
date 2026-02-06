from abc import ABC, abstractmethod
import numpy as np

class SignalProcessor(ABC):
    """
    所有信号处理算法的基类
    """
    
    @abstractmethod
    def process(self, data: np.ndarray, params: dict) -> dict:
        """
        执行具体的信号处理逻辑
        :param data: 输入的一维信号数组 (numpy array)
        :param params: 前端传递的参数字典
        :return: 标准化的结果字典
        """
        pass

    @classmethod
    def get_metadata(cls) -> dict:
        """
        向前端返回该工具的元数据（名称、描述、所需参数）
        用于动态生成网页上的配置表单
        """
        return {
            "id": cls.__name__,
            "name": "未命名工具",
            "description": "无描述",
            "params": {} 
            # 示例: 
            # "params": {
            #    "cutoff": {"type": "number", "default": 100, "label": "截止频率"}
            # }
        }