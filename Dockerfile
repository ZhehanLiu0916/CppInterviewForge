# 阶段1：builder（构建依赖）
FROM python:3.11-slim AS builder

WORKDIR /app

# 复制依赖文件
COPY pyproject.toml .

# 安装构建依赖
RUN pip install --no-cache-dir poetry-core && \
    pip install --no-cache-dir -r <(poetry export --without-hashes --format=requirements.txt 2>/dev/null || cat requirements.txt)

# 阶段2：runtime（运行环境）
FROM python:3.11-slim

WORKDIR /app

# 复制构建的依赖
COPY --from=builder /usr/local/lib/python3.11/site-packages ./usr/local/lib/python3.11/site-packages

# 复制应用代码
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY static/ ./static/ 2>/dev/null || true
COPY .env.example ./
COPY books/ ./books/ 2>/dev/null || true

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODEMARK=1

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
