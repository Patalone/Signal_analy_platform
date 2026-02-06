import uvicorn
import yaml

if __name__ == "__main__":
    # 读取配置端口
    try:
        with open("config/system.yaml", "r", encoding='utf-8') as f:
            config = yaml.safe_load(f)
        port = config['service']['port']
        host = config['service']['host']
    except:
        port = 8899
        host = "0.0.0.0"

    print(f"Starting server on {host}:{port}...")
    uvicorn.run("api.app:app", host=host, port=port, reload=True)