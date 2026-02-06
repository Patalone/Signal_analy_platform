import importlib
import pkgutil
import processors
from core.interface import SignalProcessor

def get_processor(class_name):
    """
    工厂函数：根据类名（字符串）动态加载并返回算法实例。
    例如：传入 "TimeDomainStats"，返回 processors.basic.TimeDomainStats 的实例
    """
    found_class = None

    # 1. 动态扫描 processors 包下的所有模块 (.py 文件)
    # 这步操作会自动 import processors.basic, processors.spectral 等
    for _, module_name, _ in pkgutil.iter_modules(processors.__path__):
        try:
            module = importlib.import_module(f'processors.{module_name}')
            
            # 2. 在模块中查找类
            if hasattr(module, class_name):
                cls = getattr(module, class_name)
                # 确保它确实是 SignalProcessor 的子类，且不是基类本身
                if issubclass(cls, SignalProcessor) and cls is not SignalProcessor:
                    found_class = cls
                    break
        except Exception as e:
            print(f"Warning: Failed to import module {module_name}: {e}")
            continue

    # 3. 如果没找到，尝试在已加载的子类中查找（兜底方案）
    if found_class is None:
        for cls in SignalProcessor.__subclasses__():
            if cls.__name__ == class_name:
                found_class = cls
                break
    
    if found_class:
        print(f"[Factory] Loaded processor: {class_name}")
        return found_class()
    
    raise ValueError(f"Processor '{class_name}' not found. Please check if the class exists in 'processors/' folder.")