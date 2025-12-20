# 使用 Miniconda3 作为基础镜像，支持 conda 命令
FROM continuumio/miniconda3:latest

# 设置工作目录
WORKDIR /app

# 1. 安装系统级依赖
# build-essential: 编译 Python C 扩展 (如 psutil, cryptography)
# git: 用于 pip 安装 git 依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. 复制依赖文件
COPY requirements.txt .

# 3. 安装 Python 依赖
# 使用 base 环境直接安装，简化开发流程
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 4. 暴露端口
EXPOSE 8000

# 5. 启动命令
# 使用 uvicorn 命令行启动以支持 --reload (热重载)
# main:app 指向 main.py 中的 app 对象
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
