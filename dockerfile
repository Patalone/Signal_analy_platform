# 使用官方 Python 轻量镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置时区为上海
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' > /etc/timezone

# 复制依赖文件并安装
# 增加 --no-cache-dir 减小镜像体积
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目代码
COPY . .

# 暴露端口 (对应 system.yaml 里的配置)
EXPOSE 8899

# 启动命令
CMD ["python", "main.py"]