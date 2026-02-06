# --- START OF FILE core/mysql_connector.py ---
import pymysql
import yaml
from pathlib import Path

# 尝试加载配置
try:
    with open("config/system.yaml", "r", encoding='utf-8') as f:
        CONFIG = yaml.safe_load(f)
        DB_CONF = CONFIG.get('database', {})
except:
    # 默认回退配置 (源自你的 backend.py)
    DB_CONF = {
        "host": "192.168.112.133",
        "port": 3306,
        "user": "root",
        "password": "bangding123",
        "db": "aisinglewell"
    }

class MySQLClient:
    def get_connection(self):
        return pymysql.connect(
            host=DB_CONF.get("host"),
            port=DB_CONF.get("port"),
            user=DB_CONF.get("user"),
            password=DB_CONF.get("password"),
            database=DB_CONF.get("db"),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

mysql_conn = MySQLClient()