# 企业资产管理后台系统

基于 FastAPI + Vue 3 + MySQL + AI 智能问答的企业级资产管理系统。

---

## 快速启动

### 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | >= 3.12 | 后端运行环境 |
| Node.js | >= 18 | 前端构建工具 |
| MySQL | >= 5.7 | 数据库 |
| uv | 最新 | Python 包管理器（[安装指南](https://docs.astral.sh/uv/getting-started/installation/)） |

### 一键启动（推荐）

**第一步：配置数据库**

复制 `.env.example` 为 `.env`，修改数据库连接信息：

```env
DATABASE_URL=mysql+pymysql://用户名:密码@localhost:3306/asset_management?charset=utf8mb4
SECRET_KEY=替换为一个随机长字符串
```

**第二步：安装依赖**

双击运行 `setup.bat`，等待安装完成。

**第三步：启动服务**

双击运行 `start.bat`，等待服务启动。

启动成功后：

| 地址 | 说明 |
|------|------|
| http://localhost:5173 | 前端页面 |
| http://localhost:8000/docs | API 文档（Swagger） |

**默认账号：** 用户名 `root`，密码 `101704`

---

### 手动启动

```bash
# 1. 安装后端依赖
uv sync

# 2. 安装前端依赖
cd frontend
npm install
cd ..

# 3. 启动后端（新终端）
uvicorn app.main:app --reload --port 8000

# 4. 启动前端（新终端）
cd frontend
npm run dev
```

---

## 功能模块

### 1. 用户认证与权限

- **登录/退出**：JWT Token 认证，24小时有效期
- **角色区分**：管理员（admin）拥有全部权限，普通员工（employee）仅可查看
- **用户管理**：管理员可创建、编辑、禁用用户账号

| 权限 | 管理员 | 普通员工 |
|------|--------|----------|
| 员工管理 | 全部操作 | 仅查看 |
| 资产管理 | 全部操作 | 仅查看 |
| 流转记录 | 全部操作 | 查看自己的 |
| 云盘 | 全部操作 | 上传/下载自己的 |
| 知识库 | 全部操作 | 仅查看 |
| AI 配置 | 仅管理员 | - |
| AI 问答 | 全部 | 全部 |

### 2. 员工管理

- 员工档案管理（工号、姓名、部门、职位、电话、入职日期）
- 在职/离职状态切换
- 关键字搜索、按部门/状态筛选
- Excel 导出

### 3. 资产管理

- 资产台账管理（编号、名称、类型、品牌、型号、序列号、价格、位置）
- 资产类型：电脑、手机、显示器、外设、办公家具、其他
- 资产状态：闲置、使用中、维修中、报废
- 关键字搜索、按类型/状态筛选
- Excel 导出

### 4. 资产流转记录

完整的资产生命周期追溯：

| 操作 | 说明 | 前置状态 |
|------|------|----------|
| 领用 | 员工领取资产 | 闲置 |
| 归还 | 员工归还资产 | 使用中 |
| 送修 | 资产送修 | 闲置/使用中 |
| 修好 | 资产修好 | 维修中 |
| 报废 | 资产报废 | 任意状态 |

- 自动校验流转规则（如：使用中的资产不能直接送修）
- 按员工、操作类型筛选
- Excel 导出

### 5. 数据看板

首页仪表盘展示：
- 员工总数、资产总数
- 各状态资产数量（使用中/闲置/维修中/报废）
- 最近 10 条流转记录

### 6. 操作日志

自动记录所有关键操作（创建、编辑、删除、上传、下载、共享等），支持：
- 按操作类型、目标类型筛选
- 按日期范围筛选
- 操作人、操作时间、IP 地址追溯

### 7. 云盘

- 文件上传（支持图片、PDF、Word、Excel、PPT、文本、压缩包，最大 50MB）
- 文件下载
- 文件删除
- 文件共享（可共享给指定用户）
- 取消共享

### 8. 知识库（AI 问答的数据源）

- 上传文档（PDF、Word、Excel、TXT、Markdown）
- 自动解析文档内容 → 智能分块 → 向量化存储
- 文档管理（编辑标题、重新处理、删除）
- 分块预览
- 语义搜索测试

### 9. AI 智能问答

基于 RAG（检索增强生成）的智能问答系统：

- **自然语言查询**：用中文提问，AI 自动查询数据库回答
- **知识库检索**：自动检索相关文档作为参考
- **工具调用**：AI 可调用内置函数查询员工、资产、流转记录
- **MCP 服务器**：可配置外部数据库，AI 直接查询
- **流式输出**：实时显示 AI 回答（逐字输出）
- **对话历史**：自动保存最近 3 轮对话，刷新页面不丢失

示例问题：
```
公司有多少台电脑？
张三领用了哪些资产？
最近一个月有哪些资产报废了？
研发部有哪些员工？
```

### 10. AI 配置（仅管理员）

| 配置项 | 说明 |
|--------|------|
| API Key | LLM 服务密钥 |
| API 地址 | OpenAI 兼容格式地址，默认 `https://llm.goaichat.top/v1` |
| 模型 | 支持 GLM、DeepSeek、Kimi、Qwen、MiniMax 等 |
| 本地模型 | 可配置本地部署的 LLM 端点 |
| MCP 服务器 | 配置外部数据库连接，AI 可直接查询 |
| RAG 参数 | 检索文档块数量、最大上下文长度 |

---

## 项目结构

```
├── app/                          # 后端应用
│   ├── main.py                   # 入口文件（FastAPI 应用）
│   ├── config.py                 # 配置管理（从 .env 读取）
│   ├── database.py               # 数据库连接
│   ├── models.py                 # 数据库表定义
│   ├── schemas.py                # API 请求/响应模型
│   ├── security.py               # 密码加密、JWT 生成
│   ├── dependencies.py           # 权限验证依赖
│   ├── crud.py                   # 数据库增删改查
│   ├── routers/                  # API 路由
│   │   ├── auth.py               # 认证（登录/注册/用户管理）
│   │   ├── employees.py          # 员工管理
│   │   ├── assets.py             # 资产管理
│   │   ├── asset_logs.py         # 流转记录
│   │   ├── dashboard.py          # 数据看板
│   │   ├── operation_logs.py     # 操作日志
│   │   ├── cloud_files.py        # 云盘
│   │   ├── knowledge.py          # 知识库
│   │   ├── ai_config.py          # AI 配置
│   │   └── chat.py               # AI 问答
│   ├── services/                 # 业务服务
│   │   ├── llm_client.py         # LLM 调用客户端
│   │   ├── rag_engine.py         # RAG 检索增强引擎
│   │   ├── mcp_client.py         # MCP 外部数据库客户端
│   │   ├── vector_store.py       # ChromaDB 向量存储
│   │   ├── embedding.py          # 文本向量化
│   │   ├── text_chunker.py       # 文档分块
│   │   ├── file_parser.py        # 文档解析（PDF/Word/Excel）
│   │   └── encryption.py         # 加密工具（已弃用）
│   └── utils/                    # 工具函数
│       ├── response.py           # 统一响应格式
│       ├── operation_log.py      # 操作日志记录
│       └── file_storage.py       # 文件存储
├── frontend/                     # 前端应用
│   ├── src/
│   │   ├── views/                # 页面组件
│   │   ├── api/                  # 接口封装
│   │   ├── router/               # 路由配置
│   │   ├── stores/               # 状态管理（Pinia）
│   │   ├── layout/               # 布局组件
│   │   └── constants/            # 常量定义
│   └── package.json
├── .env.example                  # 环境变量模板
├── .env                          # 环境变量（需自行创建）
├── setup.bat                     # 依赖安装脚本
├── start.bat                     # 启动脚本
├── pyproject.toml                # Python 项目配置
└── requirements.txt              # Python 依赖清单
```

---

## 配置说明

### 数据库配置（.env）

```env
# MySQL 连接（修改用户名、密码、数据库名）
DATABASE_URL=mysql+pymysql://root:你的密码@localhost:3306/asset_management?charset=utf8mb4

# JWT 密钥（生产环境务必替换为随机字符串）
SECRET_KEY=你的随机密钥

# Token 有效期（分钟），默认 24 小时
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 调试模式（生产环境设为 False）
DEBUG=True
```

### AI 配置（通过管理页面设置）

1. 以管理员登录
2. 进入「AI 配置」页面
3. 在「API 配置」标签页填写：
   - API Key：你的 LLM 服务密钥
   - API 地址：`https://llm.goaichat.top/v1`（默认）
   - 模型：选择可用模型
4. 点击「测试连接」验证
5. 点击「保存配置」

---

## 调试方式

### 后端调试

**查看 API 文档**

启动后访问 http://localhost:8000/docs，可在线测试所有接口。

**查看日志**

后端日志输出到终端窗口，包含：
- 请求路径和状态码
- 数据库查询错误
- LLM 调用错误
- MCP 工具调用日志

**常见问题排查**

| 问题 | 排查方法 |
|------|----------|
| 启动报错 `ModuleNotFoundError` | 运行 `uv sync` 重新安装依赖 |
| 数据库连接失败 | 检查 `.env` 中 `DATABASE_URL` 配置 |
| 401 未授权 | Token 过期，重新登录 |
| AI 问答无响应 | 检查 AI 配置中的 API Key 和地址 |

**Python 语法检查**

```bash
.venv\Scripts\python.exe -m py_compile app/main.py
```

### 前端调试

**浏览器开发者工具**

按 F12 打开开发者工具：
- **Console**：查看 JavaScript 错误
- **Network**：查看 API 请求和响应
- **Elements**：检查页面元素

**前端构建检查**

```bash
cd frontend
npm run build
```

### 数据库调试

**连接数据库**

```bash
mysql -u root -p asset_management
```

**常用 SQL**

```sql
-- 查看所有表
SHOW TABLES;

-- 查看用户
SELECT id, username, role, is_active FROM users;

-- 查看资产统计
SELECT status, COUNT(*) FROM assets GROUP BY status;

-- 查看 AI 配置
SELECT config_key, LEFT(config_value, 20) FROM ai_configs;
```

---

## 常见问题

### Q: 如何修改管理员密码？

管理员登录后，通过 API 修改：

```bash
# 获取 Token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"root","password":"101704"}'

# 修改密码（需用管理员 Token）
curl -X PUT http://localhost:8000/api/auth/users/1 \
  -H "Authorization: Bearer 你的Token" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@company.com"}'
```

### Q: 如何添加新的管理员？

以管理员登录后，在「员工管理」页面添加员工时会自动创建用户账号。或通过 API：

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Authorization: Bearer 管理员Token" \
  -H "Content-Type: application/json" \
  -d '{"username":"newadmin","password":"123456","role":"admin"}'
```

### Q: 如何配置 MCP 外部数据库？

1. 管理员进入「AI 配置」→「MCP 服务器」标签
2. 点击「新增」，填写外部数据库连接信息
3. 保存后 AI 问答即可查询该数据库

### Q: 知识库文档支持哪些格式？

支持 PDF、Word（.docx）、Excel（.xlsx）、纯文本（.txt）、Markdown（.md），单个文件最大 50MB。

### Q: 如何备份数据？

```bash
mysqldump -u root -p asset_management > backup.sql
```

### Q: 生产环境部署注意事项

1. 修改 `.env` 中的 `SECRET_KEY` 为随机强密钥
2. 设置 `DEBUG=False`
3. 修改 `main.py` 第 22 行的 CORS 白名单
4. 使用 HTTPS（建议通过 Nginx 反向代理）
5. 修改默认管理员密码

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| ORM | SQLAlchemy |
| 数据库 | MySQL + PyMySQL |
| 认证 | JWT (python-jose) |
| 密码加密 | bcrypt (passlib) |
| 前端框架 | Vue 3 |
| UI 组件库 | Element Plus |
| 构建工具 | Vite |
| 状态管理 | Pinia |
| HTTP 客户端 | Axios |
| AI/LLM | OpenAI 兼容 API |
| 向量数据库 | ChromaDB |
| 嵌入模型 | text2vec-base-chinese |

---

## 许可证

内部项目，仅供参考学习。
