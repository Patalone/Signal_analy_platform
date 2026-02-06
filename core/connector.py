from minio import Minio
import yaml
import json
import os
from datetime import datetime
from core.lib.data_parser import ABBParser

# 1. 加载配置
with open("config/system.yaml", "r", encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

# 2. 获取历史记录路径（带容错默认值）
history_conf = CONFIG.get('history', {})
HISTORY_FILE = history_conf.get('file_path', "data/analysis_history.json")

class MinioClient:
    def __init__(self):
        self.client = Minio(
            CONFIG['minio']['endpoint'],
            access_key=CONFIG['minio']['access_key'],
            secret_key=CONFIG['minio']['secret_key'],
            secure=CONFIG['minio']['secure']
        )
        self.bucket = CONFIG['minio']['data_bucket']
        
        # 确保本地数据目录存在
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

    def list_objects(self, prefix=""):
            """列出文件（带调试日志版）"""
            print(f"\n--- DEBUG: 正在请求 Minio ---")
            print(f"Endpoint: {self.client._base_url}")
            print(f"Bucket:   {self.bucket}")
            print(f"Prefix:   '{prefix}'")
            
            try:
                # 1. 先检查桶是否存在
                if not self.client.bucket_exists(self.bucket):
                    print(f"!!! 严重错误: 桶 '{self.bucket}' 不存在！")
                    return []

                # 2. 尝试获取对象
                # recursive=False 模拟文件夹模式
                objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=False)
                
                results = []
                count = 0
                for obj in objects:
                    count += 1
                    print(f"Found: {obj.object_name} (Dir: {obj.is_dir})") # 打印每一个找到的东西
                    results.append({
                        "name": obj.object_name,
                        "is_dir": obj.is_dir,
                        "size": obj.size if not obj.is_dir else 0
                    })
                
                print(f"--- DEBUG: 总共找到 {count} 个对象 ---\n")
                
                if count == 0 and prefix == "":
                    # 如果根目录也是空的，尝试一次 recursive=True 看看是不是路径层级问题
                    print("根目录为空，尝试深度扫描测试...")
                    deep_objs = self.client.list_objects(self.bucket, prefix="", recursive=True)
                    for x in deep_objs:
                        print(f"深度扫描发现文件: {x.object_name}")
                        break # 只看第一个
                
                return results

            except Exception as e:
                print(f"!!! Minio Error: {str(e)}")
                import traceback
                traceback.print_exc() # 打印完整报错堆栈
                return []

    def get_file_data(self, object_name):
        """下载并解析文件"""
        response = None
        try:
            response = self.client.get_object(self.bucket, object_name)
            raw_bytes = response.read()
            # 调用 core/lib/data_parser.py 中的解析器
            return ABBParser.parse_content(raw_bytes)
        except Exception as e:
            raise e
        finally:
            if response:
                response.close()
                response.release_conn()

    def save_analysis_history(self, object_name, analysis_type):
        """保存分析历史"""
        record = {
            "file": object_name,
            "type": analysis_type,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                pass
        
        # 去重并插入头部
        history = [h for h in history if h['file'] != object_name]
        history.insert(0, record)
        
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history[:50], f, indent=2, ensure_ascii=False)

    def get_analysis_history(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

# 实例化单例
minio_conn = MinioClient()