# 后端 Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 Playwright 浏览器（如需浏览器自动化功能）
RUN playwright install chromium --with-deps || true

# 复制项目文件
COPY . .

# 创建必要目录
RUN mkdir -p /opt/app/video /opt/app/video/cookies temp

EXPOSE 5000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
