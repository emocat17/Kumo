# 使用 LTS 版本 Node.js Alpine 镜像
FROM node:20-alpine

# 设置工作目录
WORKDIR /app

# 1. 安装基础工具
RUN apk add --no-cache git

# 2. 复制依赖描述文件 (利用 Docker 缓存层)
COPY package.json package-lock.json* ./

# 3. 安装依赖
RUN npm install

# 4. 暴露 Vite 默认端口
EXPOSE 6677

# 5. 启动开发服务器
# --host 0.0.0.0 允许外部访问容器
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
