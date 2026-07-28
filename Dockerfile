# ============================================
# Autonomous Agent - Docker Image
# ============================================
FROM python:3.11-slim

LABEL org.opencontainers.image.title="Autonomous Agent"
LABEL org.opencontainers.image.description="Self-Growing AI Agent Platform"
LABEL org.opencontainers.image.version="5.0"

WORKDIR /app

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 暴露 API 端口
EXPOSE 8000

# 默认以 API 模式启动
CMD ["python", "run.py", "api"]
