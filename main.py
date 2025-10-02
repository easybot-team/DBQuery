import json  # 新增：用于解析JSON字符串
from fastapi import FastAPI, Query, HTTPException, Depends
from typing import List, Optional, Dict, Any
from db_utils import (
    query_single_table, query_related_tables, get_table_count,
    query_player_by_multi_condition, query_group_by_condition,
    get_player_id_by_multi_condition  # 新增：导入获取玩家ID的函数
)
from auth_utils import verify_api_key
from config import get_config  # 用延迟加载的配置

# 初始化FastAPI应用（全局API Key认证）
app = FastAPI(
    title="EasyBot数据库查询接口",
    description="支持API Key认证、全维度查询（玩家/Group表）",
    version="3.2",
    dependencies=[Depends(verify_api_key)]
)

# 获取配置并定义支持的表名
config = get_config()
SUPPORTED_TABLES = [
    "__EFMigrationsHistory", "Player", "ServerInfo",
    "SocialAccount", "PlayerServerInfo", "Group", "sqlite_sequence"
]

# ---------------------- 1. 基础查询接口 ----------------------
@app.get("/api/single-table", summary="单表查询（修复参数解析错误）")
def get_single_table(
    table_name: str = Query(..., description=f"表名，支持：{', '.join(SUPPORTED_TABLES)}"),
    # 关键修复：conditions改为str类型（接收JSON字符串）
    conditions: Optional[str] = Query(None, description="查询条件（JSON字符串，如'{\"Id\":1,\"Name\":\"Slide2_shutdown\"}'，需用单引号包裹）"),
    fields: Optional[List[str]] = Query(None, description="返回字段（如Id,Name,IpString，默认所有字段）")
):
    # 1. 表名校验
    if table_name not in SUPPORTED_TABLES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的表名！仅支持：{', '.join(SUPPORTED_TABLES)}"
        )
    
    # 2. 解析conditions（JSON字符串转字典）
    conditions_dict = None
    if conditions:
        try:
            conditions_dict = json.loads(conditions)
            # 校验解析结果是否为字典
            if not isinstance(conditions_dict, dict):
                raise HTTPException(
                    status_code=400,
                    detail="conditions格式错误！需传入JSON字典（如'{\"Id\":1}'）"
                )
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"conditions解析失败：{str(e)}（检查引号配对/逗号是否多余）"
            )
    
    # 3. 执行查询
    try:
        results = query_single_table(table_name, conditions_dict, fields)
        return {
            "status": "success",
            "table_name": table_name,
            "total_count": len(results),
            "query_conditions": conditions_dict or "无",
            "return_fields": fields or "所有字段",
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")

@app.get("/api/table-count", summary="查询表总记录数")
def get_table_record_count(
    table_name: str = Query(..., description=f"表名，支持：{', '.join(SUPPORTED_TABLES)}")
):
    if table_name not in SUPPORTED_TABLES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的表名！仅支持：{', '.join(SUPPORTED_TABLES)}"
        )
    
    try:
        count = get_table_count(table_name)
        return {
            "status": "success",
            "table_name": table_name,
            "total_record_count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"统计失败：{str(e)}")

@app.get("/api/supported-tables", summary="获取支持的表名列表")
def get_supported_tables():
    return {
        "status": "success",
        "supported_tables": SUPPORTED_TABLES,
        "total_table_count": len(SUPPORTED_TABLES)
    }

# ---------------------- 2. 关联查询接口 ----------------------
@app.get("/api/related-table", summary="玩家-社交账号/服务器关联查询（多维度）")
def get_related_table(
    related_type: str = Query(..., description="关联类型：player_social（玩家-社交账号）、player_server（玩家-服务器）"),
    player_id: Optional[int] = Query(None, description="玩家ID（如1、2，对应Player表的Id）"),
    player_name: Optional[str] = Query(None, description="玩家昵称（模糊匹配，如Slide2）"),
    qq_number: Optional[str] = Query(None, description="QQ号（精确匹配，如2651559189）"),
    ip: Optional[str] = Query(None, description="IP地址（模糊匹配，如114.88）"),
    uuid: Optional[str] = Query(None, description="玩家UUID（精确匹配，如765537e9-af61-3ac2-9ae5-57256eadfed5）")
):
    """
    支持通过玩家ID、名称、QQ号、IP、UUID查询关联数据
    - 若传入player_id，直接查询该ID的关联数据
    - 若传入其他条件，先查询玩家ID列表，再批量查询关联数据
    """
    try:
        # 优先使用player_id查询
        if player_id:
            results = query_related_tables(related_type, player_id)
        else:
            # 否则通过其他条件查询玩家ID列表
            player_ids = get_player_id_by_multi_condition(
                player_name=player_name,
                qq_number=qq_number,
                ip=ip,
                uuid=uuid
            )
            if not player_ids:
                raise HTTPException(status_code=404, detail="未找到匹配的玩家")
            
            # 批量查询每个玩家ID的关联数据
            results_list = []
            for pid in player_ids:
                result = query_related_tables(related_type, pid)
                results_list.append({
                    "player_id": pid,
                    "related_data": result
                })
            results = {"multi_player_results": results_list}
        
        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])
        
        return {
            "status": "success",
            "related_type": related_type,
            "query_conditions": {
                "player_id": player_id,
                "player_name": player_name,
                "qq_number": qq_number,
                "ip": ip,
                "uuid": uuid
            },
            "data": results
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"关联查询失败：{str(e)}")

# ---------------------- 3. 玩家专项查询接口 ----------------------
@app.get("/api/player/multi-query", summary="玩家多维度查询（名称/QQ/IP/UUID）")
def player_multi_query(
    player_name: Optional[str] = Query(None, description="玩家昵称（模糊匹配，如Slide2）"),
    qq_number: Optional[str] = Query(None, description="QQ号（精确匹配，如2651559189）"),
    qq_name: Optional[str] = Query(None, description="QQ昵称（模糊匹配，如歪优）"),
    ip: Optional[str] = Query(None, description="IP地址（模糊匹配，如114.88）"),
    uuid: Optional[str] = Query(None, description="玩家UUID（精确匹配，如765537e9-af61-3ac2-9ae5-57256eadfed5）"),
    fields: Optional[List[str]] = Query(None, description="返回字段（如Id,Name,IpString）")
):
    try:
        results = query_player_by_multi_condition(
            player_name=player_name,
            qq_number=qq_number,
            qq_name=qq_name,
            ip=ip,
            uuid=uuid,
            fields=fields
        )
        return {
            "status": "success",
            "query_conditions": {
                "player_name": player_name or "未传入",
                "qq_number": qq_number or "未传入",
                "qq_name": qq_name or "未传入",
                "ip": ip or "未传入",
                "uuid": uuid or "未传入"
            },
            "total_matched_count": len(results),
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"玩家查询失败：{str(e)}")

@app.get("/api/player/ip-uuid-query", summary="玩家IP/UUID专项查询")
def player_ip_uuid_query(
    ip: Optional[str] = Query(None, description="IP地址（模糊/精确匹配，如114.88或127.0.0.1）"),
    uuid: Optional[str] = Query(None, description="玩家UUID（精确匹配，如765537e9-af61-3ac2-9ae5-57256eadfed5）"),
    fields: Optional[List[str]] = Query(None, description="返回字段（如Id,Name,Ip,IpString）")
):
    if not (ip or uuid):
        raise HTTPException(
            status_code=400,
            detail="至少需传入一个查询条件：ip 或 uuid"
        )
    
    try:
        results = query_player_by_multi_condition(
            ip=ip,
            uuid=uuid,
            fields=fields
        )
        return {
            "status": "success",
            "query_conditions": {
                "ip": ip or "未传入",
                "uuid": uuid or "未传入"
            },
            "total_matched_count": len(results),
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IP/UUID查询失败：{str(e)}")

# ---------------------- 4. Group表专项查询接口 ----------------------
@app.get("/api/group/single-group", summary="Group表单群精确查询（按群号）")
def get_single_group(
    group_id: int = Query(..., description="QQ群号（精确匹配，如665661136）"),
    fields: Optional[List[str]] = Query(None, description="返回字段（如GroupId,Name,Enabled,MemberCount）")
):
    try:
        results = query_group_by_condition(
            group_id=group_id,
            fields=fields
        )
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"未找到群号为 {group_id} 的群组"
            )
        
        return {
            "status": "success",
            "query_condition": f"GroupId = {group_id}",
            "data": results[0]
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"单群查询失败：{str(e)}")

@app.get("/api/group/multi-query", summary="Group表多条件筛选")
def group_multi_query(
    group_name: Optional[str] = Query(None, description="群名称（模糊匹配，如EasyBot）"),
    enabled: Optional[int] = Query(None, description="启用状态（0=未启用，1=启用）"),
    min_member: Optional[int] = Query(None, description="最小成员数（如200，筛选≥200人的群）"),
    max_member: Optional[int] = Query(None, description="最大成员数（如500，筛选≤500人的群）"),
    fields: Optional[List[str]] = Query(None, description="返回字段（如GroupId,Name,Enabled,MemberCount）")
):
    try:
        results = query_group_by_condition(
            group_name=group_name,
            enabled=enabled,
            min_member=min_member,
            max_member=max_member,
            fields=fields
        )
        return {
            "status": "success",
            "query_conditions": {
                "group_name": group_name or "未传入",
                "enabled": enabled if enabled is not None else "未传入",
                "min_member": min_member or "未传入",
                "max_member": max_member or "未传入"
            },
            "total_matched_count": len(results),
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Group表筛选失败：{str(e)}")

# ---------------------- 服务启动入口 ----------------------
if __name__ == "__main__":
    import uvicorn
    from datetime import datetime  # 新增：用于显示启动时间
    
    # 格式化启动时间
    startup_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 结构化启动日志（分模块展示关键信息）
    print(f"\n{'='*80}")
    print(f"[启动成功] EasyBot数据库查询接口 v{app.version} | 启动时间: {startup_time}")
    print(f"{'='*80}")
    print(f"[服务配置]")
    print(f"  访问地址: http://{config.service_host}:{config.service_port}")
    print(f"  文档地址: http://{config.service_host}:{config.service_port}/docs (推荐通过文档测试接口)")
    print(f"\n[数据库配置]")
    print(f"  文件路径: {config.db_path}")
    print(f"\n[API安全]")
    # 修复：直接使用列表遍历，移除split(',')调用
    masked_keys = [f"{k[:5]}***" for k in config.api_keys]
    print(f"  有效API Key数量: {len(masked_keys)} | 示例: {masked_keys[0]} (实际使用时需完整传递)")
    print(f"\n[支持表列表]")
    print(f"  {', '.join(SUPPORTED_TABLES)} (可通过/api/supported-tables接口获取最新列表)")
    print(f"{'='*80}\n")
    
    # 启动服务（生产环境建议关闭reload=True）
    uvicorn.run(
        "main:app",
        host=config.service_host,
        port=config.service_port,
        reload=True
    )
