# DBQuery：EasyBot 数据库 API 查询服务

基于 FastAPI + SQLite 构建，为 EasyBot 项目提供安全、高效的数据库查询接口，支持多表查询、关联分析与精准筛选。


## 一、项目基础信息
### 1. 核心定位
专为 EasyBot 项目设计的轻量化数据库查询服务，通过标准化 API 接口实现 SQLite 数据库的可视化、安全化访问，无需直接操作数据库文件，降低数据泄露与误操作风险。

### 2. 核心功能清单
| 功能模块       | 具体能力                                                                 | 支持表范围                                                                 |
|----------------|--------------------------------------------------------------------------|----------------------------------------------------------------------------|
| 基础查询       | 单表条件筛选、指定字段返回、表记录数统计                                  | __EFMigrationsHistory、Player、ServerInfo、SocialAccount、PlayerServerInfo、Group、sqlite_sequence |
| 关联查询       | 玩家-社交账号绑定关系查询、玩家-关联服务器信息查询                        | Player 与 SocialAccount、Player 与 PlayerServerInfo + ServerInfo 多表关联 |
| 多维度筛选     | 玩家昵称/QQ号/IP/UUID 组合查询、Group 表群名/状态/成员数范围筛选          | Player、SocialAccount、Group 重点表专项优化                                |
| 安全防护       | 全接口 API Key 认证、请求参数格式校验、数据库文件路径双重校验              | 所有接口统一防护                                                           |

### 3. 前置准备步骤
#### （1）环境配置
- **Python 版本**：3.8 及以上
- **依赖安装**：执行以下命令安装项目所需依赖
  ```bash
  # 升级pip（可选，推荐）
  python -m pip install --upgrade pip
  # 安装依赖库
  pip install -r requirements.txt
  ```
- **依赖清单**：`requirements.txt` 包含核心依赖（fastapi==0.111.0、uvicorn==0.30.1、pydantic==2.7.1 等）

#### （2）配置文件修改
打开项目根目录下的 `config.ini`，按实际需求配置以下参数：
  ```ini
  [DATABASE]
  # 数据库文件路径（绝对路径如"D:/EasyBot/db/easybot.db"，相对路径如"./db/easybot.db"）
  db_path = ./db/easybot.db

  [API_AUTH]
  # 有效API Key列表（多个用英文逗号分隔，建议自定义复杂密钥）
  api_keys = easybot_api_key_2025, db_query_auth_888

  [SERVICE]
  # 服务地址（0.0.0.0 支持局域网访问，127.0.0.1 仅本地访问）
  host = 0.0.0.0
  # 服务端口（1-65535之间，避免与其他服务冲突，如8000、8888）
  port = 8000
  ```

#### （3）服务启动与访问
1. 执行启动命令：
   ```bash
   python main.py
   ```
2. 服务启动成功后，通过以下地址访问：
   - **接口文档**：`http://{服务地址}:{端口}/docs`（如 `http://127.0.0.1:8000/docs`），支持在线调试接口
   - **服务状态**：启动日志将打印配置信息（地址、端口、数据库路径等），无报错即正常运行


## 二、通用请求规则
### 1. 认证规则（必看）
所有接口需在 **请求头** 中携带 `X-API-Key` 字段，值为 `config.ini` 中配置的有效 API Key，示例：
```http
GET /api/player/multi-query HTTP/1.1
Host: 127.0.0.1:8000
X-API-Key: easybot_api_key_2025
```
- 未携带 `X-API-Key`：返回 401 未授权，提示“未提供 API Key”
- 密钥无效/不匹配：返回 401 未授权，提示“无效的 API Key”

### 2. 参数传递规范
| 参数类型       | 传递方式                                                                 | 示例                                                                 |
|----------------|--------------------------------------------------------------------------|----------------------------------------------------------------------|
| 简单标量参数   | URL Query 参数直接传入（字符串/整数/布尔值）                              | `player_name=zzh4141`、`group_id=2441192464`、`enabled=1`              |
| 字典类参数     | 传入 JSON 格式字符串（需用单引号包裹，避免与 URL 引号冲突）                | `conditions='{"Id":1,"Name":"zzh4141"}'`                     |
| 列表类参数     | 用英文逗号分隔多个值，FastAPI 自动解析为列表                              | `fields=Id,Name,IpString`（解析为 `["Id", "Name", "IpString"]`）     |

### 3. 统一响应格式
所有接口返回 JSON 格式数据，结构统一，便于前端解析：
#### （1）成功响应（status: success）
```json
{
  "status": "success",
  "query_conditions": {
    "player_name": "zzh4141",
    "qq_number": "2441192464"
  },
  "total_count": 1,
  "data": [
    {
      "player_info": {"Id": 1, "Name": "zzh4141"},
      "social_info": {"qq_number": "2441192464", "qq_name": "zzh4141"}
    }
  ]
}
```
#### （2）错误响应（status: error）
```json
{
  "status": "error",
  "detail": "数据库文件不存在！当前配置路径：./db/easybot.db",
  "code": 500
}
```


## 三、常见问题与注意事项
### 1. 启动与连接类问题
| 问题现象                     | 可能原因                                                                 | 解决方案                                                                 |
|------------------------------|--------------------------------------------------------------------------|--------------------------------------------------------------------------|
| 启动报错“数据库文件不存在”   | 1. `config.ini` 的 `db_path` 配置错误；2. 数据库文件被删除/移动；3. 路径权限不足 | 1. 核对 `db_path` 路径（相对路径基于项目根目录）；2. 恢复数据库文件到指定路径；3. 赋予文件读写权限（Windows 右键→属性→安全，Linux `chmod 644 文件名`） |
| 启动报错“API Key 配置为空”   | `config.ini` 的 `[API_AUTH]` 章节 `api_keys` 未配置或为空                  | 在 `api_keys` 后添加至少一个密钥（如 `api_keys=easybot_key_001`）         |
| 无法访问接口文档（404）      | 1. 服务未启动；2. 服务地址/端口错误；3. 防火墙拦截                        | 1. 确认 `main.py` 正常运行；2. 核对启动日志中的 `host` 和 `port`；3. 关闭防火墙或添加端口例外 |

### 2. 接口调用类问题
| 问题现象                     | 可能原因                                                                 | 解决方案                                                                 |
|------------------------------|--------------------------------------------------------------------------|--------------------------------------------------------------------------|
| 调用接口返回“参数解析失败”   | 1. 字典参数 JSON 格式错误（如引号不配对、多余逗号）；2. 列表参数格式错误   | 1. 检查 JSON 格式（推荐用 [JSON 校验工具](https://json.cn/) 验证）；2. 列表参数用逗号分隔（如 `fields=Id,Name`） |
| 关联查询无结果               | 1. 查询条件错误（如玩家昵称拼写错误、QQ号不匹配）；2. 无关联数据          | 1. 核对数据库中实际数据（如通过单表查询确认玩家是否存在）；2. 检查关联表是否有数据（如 Player 的 `SocialAccountId` 是否为空） |
| Group 表查询语法错误         | 未处理 `Group` 为 SQL 关键字的冲突（旧版本代码问题）                     | 确保 `db_utils.py` 中 Group 表查询语句用双引号包裹（如 `FROM "Group"`）   |

### 3. 生产环境优化建议
1. **关闭调试模式**：将 `main.py` 中 `uvicorn.run` 的 `reload=True` 改为 `reload=False`（避免代码修改自动重启，节省资源）
   ```python
   # 生产环境启动配置
   uvicorn.run(
       "main.py:app",
       host=config.service_host,
       port=config.service_port,
       reload=False  # 关键修改：关闭热重载
   )
   ```
2. **添加日志记录**：引入 `logging` 模块，记录接口调用日志、错误日志，便于问题排查
   ```python
   # main.py 顶部导入
   import logging
   # 日志配置
   logging.basicConfig(
       level=logging.INFO,
       format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
       handlers=[logging.FileHandler("db_query.log"), logging.StreamHandler()]
   )
   logger = logging.getLogger(__name__)
   # 接口中添加日志
   @app.get("/api/single-table")
   def get_single_table(...):
       logger.info(f"单表查询请求：table_name={table_name}, conditions={conditions}")
       try:
           # 业务逻辑
       except Exception as e:
           logger.error(f"单表查询失败：{str(e)}", exc_info=True)
           raise
   ```
3. **限制接口请求频率**：使用 `slowapi` 库添加接口限流，防止恶意请求（如每分钟最多 60 次请求）
   ```bash
   # 安装依赖
   pip install slowapi
   ```
   ```python
   # main.py 配置限流
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address

   limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
   app.state.limiter = limiter
   app.add_exception_handler(_rate_limit_exceeded_handler)
   # 接口添加限流装饰器
   @app.get("/api/single-table")
   @limiter.limit("60/minute")
   def get_single_table(...):
       # 业务逻辑
   ```
