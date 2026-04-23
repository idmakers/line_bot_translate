# 使用官方的 Python 基礎映像
FROM python:3.9-slim

# 設置工作目錄
WORKDIR /app

# Install system dependencies first to leverage cache
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app

# 暴露 Flask 應用程式運行的端口
EXPOSE 5000

# 設置環境變數
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# 運行 Flask 應用程式
CMD ["flask", "run"]