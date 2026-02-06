import pandas as pd
import numpy as np
import io
import datetime
from datetime import timezone

# 常量定义 (源自 signal_processor.py)
CSV_HEADER_INFO = {
    "version_row_idx": 0,
    "data_collect_unit_row_idx": 1,
    "sensor_type_row_idx": 2,
    "timestamp_row_idx": 3,
    "sampling_freq_row_idx": 4,
    "unit_after_scaling_row_idx": 5,
    "scale_data_row_idx": 6,
    "title_row_idx": 9
}

CODE_RAW_DATA_AXIS_X = "X"
CODE_RAW_DATA_AXIS_Y = "Y"
CODE_RAW_DATA_AXIS_Z = "Z"

class ABBParser:
    @staticmethod
    def parse_content(file_bytes: bytes) -> dict:
        """
        从二进制流中解析 ABB CSV 格式
        移植自 signal_processor.py -> parse_data
        """
        try:
            content_str = file_bytes.decode('utf-8')
            csv_data_io = io.StringIO(content_str)

            # 1. 读取配置头 (前10行)
            # 注意：源码中使用 header=None 读取前几行
            csv_data_io.seek(0)
            config_data = pd.read_csv(csv_data_io, sep=';', nrows=CSV_HEADER_INFO["title_row_idx"], header=None)

            # 提取关键元数据
            # 采样率 (Line 5)
            sampling_freq = np.float64(config_data.iloc[CSV_HEADER_INFO["sampling_freq_row_idx"], 1])
            # 单位 (Line 6)
            unit_after_scaling = config_data.iloc[CSV_HEADER_INFO["unit_after_scaling_row_idx"], 1]
            # 时间戳 (Line 4)
            utc_time_str = config_data.iloc[CSV_HEADER_INFO["timestamp_row_idx"], 1]
            
            # 缩放因子 (Line 7)
            scale_data_row_val = np.float64(config_data.iloc[CSV_HEADER_INFO["scale_data_row_idx"], :])
            # 过滤掉 NaN
            scale_valid = scale_data_row_val[~np.isnan(scale_data_row_val)]
            
            # 简单的缩放因子映射逻辑 (简化版，假设三轴一致或取第一个有效值)
            scale_val = 1.0
            if len(scale_valid) > 0:
                scale_val = scale_valid[0]

            scale_map = {
                "X": scale_valid[0] if len(scale_valid) > 0 else 1.0,
                "Y": scale_valid[1] if len(scale_valid) > 1 else (scale_valid[0] if len(scale_valid)>0 else 1.0),
                "Z": scale_valid[2] if len(scale_valid) > 2 else (scale_valid[0] if len(scale_valid)>0 else 1.0),
            }

            # 2. 读取实际数据 (从第 10 行开始)
            csv_data_io.seek(0) # 重置指针
            df = pd.read_csv(
                csv_data_io, 
                sep=';', 
                header=CSV_HEADER_INFO["title_row_idx"],
                engine='c'
            )

            # 3. 数据清洗与缩放
            # 移除空列
            df = df.dropna(axis=1, how='all')
            
            # 仅保留存在的轴
            valid_axes = []
            for axis in [CODE_RAW_DATA_AXIS_X, CODE_RAW_DATA_AXIS_Y, CODE_RAW_DATA_AXIS_Z]:
                if axis in df.columns:
                    valid_axes.append(axis)
                    # 应用缩放因子: Raw * Scale
                    df[axis] = df[axis] * scale_map[axis]

            # 归一化 (参考源码 cal_normalized_signal: 去除均值/直流分量)
            # 注意：源码中 vibration 类型会先积分，这里暂做基础通用处理
            normalized_df = df.copy()
            for col in valid_axes:
                normalized_df[col] = normalized_df[col] - np.mean(normalized_df[col])

            return {
                "df": df[valid_axes],               # 原始物理量数据 (已缩放)
                "df_norm": normalized_df[valid_axes], # 归一化数据 (已去均值)
                "fs": sampling_freq,
                "meta": {
                    "unit": unit_after_scaling,
                    "time": utc_time_str,
                    "scale_factors": scale_map
                }
            }

        except Exception as e:
            print(f"Parsing Error: {e}")
            raise ValueError(f"Failed to parse ABB CSV: {str(e)}")