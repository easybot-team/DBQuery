# DBQuery
通过API调用获取EasyBot数据库中的信息
## 一、项目基础信息
### 1. 核心功能
支持通过HTTP请求查询SQLite数据库中7张表（__EFMigrationsHistory、Player、ServerInfo、SocialAccount、PlayerServerInfo、Group、sqlite_sequence），包含单表查询、关联查询、多维度筛选，且所有接口需API Key认证，保障访问安全。

### 2. 前置准备
- **环境要求**：Python 3.8+，安装依赖库（执行`pip install -r requirements.txt`，依赖含fastapi、uvicorn、python-dotenv等）。
- **配置文件**：修改`config.ini`，设置`db_path`（数据库文件路径）、`api_keys`（有效API Key列表）、`host`（服务地址）、`port`（服务端口）。
- **服务启动**：执行`python main.py`，启动后访问`http://服务地址:端口/docs`可查看可视化接口文档。


## 二、通用请求规则
1. **API Key认证**：所有接口需在请求头中携带`X-API-Key`，值为`config.ini`中配置的有效API Key（如`X-API-Key: game_api_key_2025`），未携带或无效将返回401未授权。
2. **参数格式**：
   - 字符串参数直接传入（如`player_name=Slide2`）。
   - 字典参数需符合JSON格式（如`conditions={"Id":1,"Name":"Slide2_shutdown"}`）。
   - 列表参数用逗号分隔（如`fields=Id,Name,IpString`）。
3. **响应格式**：所有接口返回JSON格式数据，包含`status`（success/error）、查询条件、数据总数、结果数据（`data`字段）。

## 三、常见问题与注意事项
1. **API Key无效/未携带**：检查`config.ini`中`api_keys`配置，确保请求头`X-API-Key`值在有效列表中，且无空格或拼写错误。
2. **数据库连接失败**：确认`config.ini`的`db_path`配置正确（绝对路径或相对路径），且数据库文件存在、无读写权限问题。
3. **查询无结果**：检查查询条件是否正确（如玩家ID是否存在、IP格式是否正确、群号是否匹配），或该条件下确实无数据。
4. **Group表查询语法错误**：项目中已处理`Group`为SQL关键字的问题（用反引号包裹），无需手动修改SQL，直接使用接口即可。
5. **生产环境优化**：关闭`main.py`中`uvicorn.run`的`reload=True`（避免代码修改自动重启），建议添加日志记录（如用`logging`模块记录接口调用和错误信息）。
