# ===================================
# AI News Digest - Docker 镜像
# ===================================

FROM python:3.11-slim-bookworm

WORKDIR /app

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装系统依赖（wkhtmltopdf 含 wkhtmltoimage，用于 Markdown 转图片）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    wkhtmltopdf \
    fontconfig \
    libjpeg62-turbo \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY *.py ./
COPY api/ ./api/
COPY src/ ./src/

# 创建必要目录
RUN mkdir -p /app/logs /app/reports

# 设置环境变量默认值
ENV PYTHONUNBUFFERED=1
ENV LOG_DIR=/app/logs

# 暴露 API 端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || python -c "import sys; sys.exit(0)"

# 默认命令
CMD ["python", "main.py", "--schedule"]
