# 项目上下文与学习实践规则 (agy / cline / cl / goose)

## 1. 核心定位与工作区边界
- **动手学习工作区**：本目录（`~/az2`）是用户的**核心演练与代码实践环境**，允许在此新建、修改、调试代码与运行测试。
- **官方参考对照源**：上游官方完整示例位于 `~/zero-to-tech-demos`（只读目录）。如遇到实现疑问或需要对比官方标准写法，可读取该目录中的对应章节代码，但**严禁修改该目录**。

## 2. 运行环境与 Web 服务规范 (WSL Linux)
- **严禁使用 `file://` 协议**：学习 Web 服务与前端交互时，严禁指导用户通过浏览器直接以本地文件协议打开 HTML 文件。
- **本地服务启动规范**：
  - 纯静态页面：可使用 `python3 -m http.server 3000` 或 `npx serve`。
  - Vite / Node 项目：使用 `npm run dev` 启动开发服务器，在 `http://localhost:<端口>` 调试；预览使用 `npm run build && npm run preview`。
- **依赖隔离**：严禁向全局安装 npm 模块或 Python 包，所有依赖仅在项目本地目录管理（`npm install <pkg>`）。

## 3. 教学辅导与交互偏好
- **结对教学模式**：
  - 给出清晰、可执行的修改与命令，注重指出关键机制（如 DOM 树、事件循环、CSS 盒模型、状态更新、API 异步交互等）。
  - 先分析核心逻辑，代码修改力求精简准确。
- **排查与文件定位**：
  - 默认以当前核心文件（如根目录的 `index.html`、`script.js`、`style.css`，或 `src/` 下对应组件）为首要分析对象，避免无目的的大范围文件遍历。

## 4. 远程腾讯云主机 (tx) 部署与 Nginx 规范
- **Nginx 配置文件注意点**：
  - 腾讯云上实际生效的配置文件为 `/etc/nginx/sites-enabled/default`（注意：与 `sites-available/default` 并非软链接，修改必须直接针对 `/etc/nginx/sites-enabled/default`，切勿改在 `sites-available` 导致不生效）。
  - 该配置内同时运行有其他服务的反向代理（如 7860 端口的 `/docs-chat/`），切勿整文件覆写。
- **React / SPA 部署修改方式（在腾讯云 tx 执行）**：
  - 代码同步后先执行安装与打包：`npm install && npm run build`。
  - 直接修改正在生效的 `/etc/nginx/sites-enabled/default`（指向 `dist` 并配置单页应用回退）：
    ```bash
    sudo sed -i 's|root /home/ubuntu/yoiy;|root /home/ubuntu/yoiy/dist;|g' /etc/nginx/sites-enabled/default
    sudo sed -i 's|try_files $uri $uri/ =404;|try_files $uri $uri/ /index.html;|g' /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo nginx -s reload
    ```

