# 前端部署与运行指南

本项目前端位于 `front` 目录，基于 Vue 3 + Vite + TypeScript 构建。

## 1. 环境要求

- **Node.js**: 版本需 >= 18.0.0 (推荐使用 LTS 版本)
- **npm**: 版本需 >= 9.0.0

## 2. 安装与启动 (开发模式)

### 2.1 进入前端目录

打开终端，进入项目的 `front` 文件夹：

```bash
cd front
```

### 2.2 安装依赖

首次运行前需要安装项目依赖：

```bash
npm install
```

### 2.3 启动开发服务器

启动本地开发环境，支持热更新：

```bash
npm run dev
```

启动成功后，终端将显示访问地址（默认为 `http://localhost:6677/`）。

> **注意**: 如果遇到端口占用或安全端口错误（如 ERR_UNSAFE_PORT），请查看下方配置说明修改端口。

## 3. 构建与部署 (生产模式)

### 3.1 构建生产代码

构建用于生产环境的静态文件：

```bash
npm run build
```

构建完成后，生成的文件将位于 `front/dist` 目录下。

### 3.2 本地预览生产构建

在本地模拟生产环境运行：

```bash
npm run preview
```

### 3.3 部署

将 `front/dist` 目录下的所有文件上传至您的 Web 服务器（如 Nginx, Apache, Vercel 等）的根目录即可。

**Nginx 配置示例:**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /path/to/your/project/front/dist;
        index index.html;
        try_files $uri $uri/ /index.html; # 必须配置，支持 Vue Router History 模式
    }

    # 如果有后端 API 代理
    location /api/ {
        proxy_pass http://localhost:8000/;
    }
}
```

## 4. 项目配置

### 4.1 修改运行端口

编辑 `front/vite.config.ts` 文件：

```typescript
export default defineConfig(({ mode }) => {
  // ...
  const port = 6677 // 在此处修改端口号，避免使用 6666 (非安全端口)
  // ...
})
```

### 4.2 环境变量

项目支持 `.env` 文件配置。在 `front` 目录下创建 `.env.local` (本地开发) 或 `.env.production` (生产) 文件：

```env
# 指定后端 API 地址
VITE_API_BASE_URL=http://localhost:8000
```

## 5. 常见命令速查

| 命令 | 说明 |
|Str |Str |
| `npm run dev` | 启动开发服务器 |
| `npm run build` | 构建生产版本 |
| `npm run preview` | 预览生产构建 |
| `npm run type-check` | 运行 TypeScript 类型检查 |
| `npm run lint` | 运行 ESLint 代码检查 |
| `npm run format` | 运行 Prettier 代码格式化 |
