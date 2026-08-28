**#快速启动+文件说明**
运行环境：X86架构windows系统
操作说明：数据库服务器在.env中进行配置，启动后再执行后面的操作
启动setup.bat会自动检索配置依赖环境，启动start会自动启动前后端服务，输入任意按键停止服务


# 企业资产管理后台系统

基于 FastAPI + Vue 3 + MySQL 的企业内部资产管理系统。

## 功能特性

- **用户认证与权限控制** - JWT 认证，管理员/普通员工角色区分
- **员工信息管理** - 员工档案、部门、职位、在职状态
- **资产台账管理** - 电脑、手机、显示器、外设、家具等资产分类管理
- **资产流转记录** - 领用、归还、调拨、送修、修好、报废全流程追溯
- **数据导出** - 资产台账、流转记录 Excel 导出
- **数据看板** - 资产统计、流转趋势、部门分布等可视化数据

## 技术栈

- **后端**: FastAPI + SQLAlchemy + MySQL
- **前端**: Vue 3 + Element Plus + Vite
- **认证**: JWT (python-jose)
- **包管理**: uv (Python) / npm (前端)

## 快速开始

### 环境要求

- Python >= 3.12
- Node.js >= 18
- MySQL
- Windows 系统

### 方式一：一键启动（推荐）

1. 配置环境变量，复制 `.env.example` 为 `.env` 并修改数据库连接信息

2. 安装依赖

```bash
setup.bat
```

3. 启动服务

```bash
start.bat
```

启动后访问：
- 前端页面: http://localhost:5173
- API 文档: http://localhost:8000/docs

### 方式二：手动启动

1. 安装 Python 依赖

```bash
uv sync
```

2. 安装前端依赖

```bash
cd frontend
npm install
```

3. 启动后端

```bash
uvicorn app.main:app --reload
```

4. 启动前端

```bash
cd frontend
npm run dev
```

## 项目结构

```
├── app/                    # 后端应用
│   ├── main.py            # 入口文件
│   ├── config.py          # 配置管理
│   ├── database.py        # 数据库连接
│   ├── models.py          # ORM 模型
│   ├── schemas.py         # Pydantic 模型
│   ├── security.py        # 密码加密、JWT
│   ├── dependencies.py    # 依赖注入
│   ├── crud.py            # 数据库操作
│   └── routers/           # API 路由
│       ├── auth.py        # 认证
│       ├── employees.py   # 员工管理
│       ├── assets.py      # 资产管理
│       ├── asset_logs.py  # 流转记录
│       └── dashboard.py   # 数据看板
├── frontend/              # 前端应用
│   ├── src/
│   │   ├── views/         # 页面组件
│   │   ├── router/        # 路由配置
│   │   ├── stores/        # 状态管理
│   │   └── api/           # 接口封装
│   └── package.json
├── .env.example           # 环境变量模板
├── setup.bat              # 依赖安装脚本
├── start.bat              # 启动脚本
└── requirements.txt
```

## 默认账号

| 用户名 | 密码 |
|--------|------|
| root | 101704 |

## 修改管理员账号

### 方式一：通过 API 注册

```bash
curl -X POST "http://localhost:8000/api/auth/register" ^
  -H "Content-Type: application/json" ^
  -d "{\"username\": \"admin\", \"email\": \"admin@company.com\", \"password\": \"your-password\", \"role\": \"admin\"}"
```

### 方式二：直接修改数据库

```sql
-- 使用 bcrypt 加密密码后更新
UPDATE users SET hashed_password = '加密后的密码' WHERE username = 'root';
```
