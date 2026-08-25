# 企业资产管理后台系统

基于 FastAPI + MySQL + SQLAlchemy 的企业内部资产管理系统。

## 功能特性

- **用户认证与权限控制** - JWT 认证，管理员/普通员工角色区分
- **员工信息管理** - 员工档案、部门、职位、在职状态
- **资产台账管理** - 电脑、手机、显示器、外设、家具等资产分类管理
- **资产流转记录** - 领用、归还、调拨、送修、修好、报废全流程追溯
- **数据导出** - 资产台账、流转记录 Excel 导出
- **数据看板** - 资产统计、流转趋势、部门分布等可视化数据

## 技术栈

- FastAPI 0.109
- SQLAlchemy 2.0
- MySQL (pymysql)
- JWT 认证 (python-jose)
- 密码加密 (passlib + bcrypt)
- Excel 导出 (openpyxl)

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

复制 `.env.example` 为 `.env` 并修改数据库连接信息：

```bash
cp .env.example .env
```

编辑 `.env`：
```env
DATABASE_URL=mysql+pymysql://root:101704@localhost:3306/asset_management?charset=utf8mb4
SECRET_KEY=your-super-secret-key-change-in-production
```

### 3. 创建数据库

在 MySQL 中创建数据库：
```sql
CREATE DATABASE asset_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. 启动服务

```bash
uvicorn app.main:app --reload
```

服务启动后访问：
- API 文档: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 5. 初始化管理员账号

首次启动后，通过 API 创建管理员账号：

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "email": "admin@company.com", "password": "admin123", "role": "admin"}'
```

或直接在数据库中插入（密码需用 bcrypt 加密）。

## API 接口说明

### 认证
- `POST /api/auth/login` - 登录获取 Token
- `GET /api/auth/me` - 获取当前用户信息
- `POST /api/auth/register` - 注册用户（需管理员权限）
- `GET /api/auth/users` - 用户列表（管理员）
- `PUT /api/auth/users/{id}` - 更新用户（管理员）
- `DELETE /api/auth/users/{id}` - 删除用户（管理员）

### 员工管理
- `POST /api/employees` - 创建员工（管理员）
- `GET /api/employees` - 员工列表（分页、筛选）
- `GET /api/employees/me` - 获取我的员工信息
- `GET /api/employees/{id}` - 员工详情
- `PUT /api/employees/{id}` - 更新员工（管理员）
- `DELETE /api/employees/{id}` - 删除员工（管理员）

### 资产管理
- `POST /api/assets` - 创建资产（管理员）
- `GET /api/assets` - 资产列表（分页、筛选）
- `GET /api/assets/stats/summary` - 资产统计概览
- `GET /api/assets/{id}` - 资产详情
- `PUT /api/assets/{id}` - 更新资产（管理员）
- `DELETE /api/assets/{id}` - 删除资产（管理员）
- `GET /api/assets/export/excel` - 导出资产台账（管理员）

### 资产流转记录
- `POST /api/asset-logs` - 创建流转记录（领用/归还/送修等）
- `GET /api/asset-logs` - 流转记录列表（分页、筛选）
- `GET /api/asset-logs/asset/{asset_id}` - 某资产的流转历史
- `GET /api/asset-logs/employee/{employee_id}` - 某员工的资产记录
- `GET /api/asset-logs/{id}` - 记录详情
- `GET /api/asset-logs/export/excel` - 导出流转记录（管理员）

### 数据看板
- `GET /api/dashboard/stats` - 统计概览
- `GET /api/dashboard/charts/assets-by-type` - 按类型统计
- `GET /api/dashboard/charts/assets-by-status` - 按状态统计
- `GET /api/dashboard/charts/logs-by-action` - 按操作类型统计
- `GET /api/dashboard/charts/employees-by-department` - 按部门统计
- `GET /api/dashboard/charts/monthly-checkouts` - 月度领用趋势

## 权限说明

| 接口 | 管理员 | 普通员工 |
|------|--------|----------|
| 用户管理 | ✅ | ❌ |
| 员工增删改 | ✅ | ❌ (仅可看自己) |
| 资产增删改 | ✅ | ❌ (仅可查看) |
| 资产领用/归还 | ✅ | ✅ (仅自己的) |
| 流转记录查看 | ✅ (全部) | ✅ (仅自己的) |
| 数据导出 | ✅ | ❌ |
| 数据看板 | ✅ | ✅ |

## 项目结构

```
app/
├── main.py           # 入口文件
├── config.py         # 配置管理
├── database.py       # 数据库连接
├── models.py         # ORM 模型
├── schemas.py        # Pydantic 模型
├── security.py       # 密码加密、JWT
├── dependencies.py   # 依赖注入（认证、权限）
├── crud.py           # 数据库操作封装
└── routers/          # API 路由
    ├── auth.py       # 认证相关
    ├── employees.py  # 员工管理
    ├── assets.py     # 资产管理
    ├── asset_logs.py # 流转记录
    └── dashboard.py  # 数据看板
```

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| DATABASE_URL | MySQL 连接字符串 | mysql+pymysql://root:101704@localhost:3306/asset_management |
| SECRET_KEY | JWT 签名密钥 | 必须修改 |
| ALGORITHM | JWT 算法 | HS256 |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token 过期时间(分钟) | 1440 |
| DEBUG | 调试模式 | True |

## 部署建议

1. 修改 `SECRET_KEY` 为强随机字符串
2. 设置 `DEBUG=False`
3. 使用 Gunicorn + Uvicorn Worker 生产部署：
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```
4. 配置 Nginx 反向代理
5. 使用 HTTPS
6. 定期备份数据库

## License

MIT