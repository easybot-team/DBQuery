import sqlite3
import os
from typing import List, Dict, Any, Optional
from config import get_config  # 用延迟加载的配置

def get_db_connection():
    """创建数据库连接，含双重文件检查"""
    try:
        config = get_config()  # 获取配置
        # 双重检查：避免服务运行中文件被删除
        if not os.path.exists(config.db_path):
            raise FileNotFoundError(
                f"数据库文件已丢失！\n"
                f"路径：{config.db_path}\n"
                f"请恢复文件后重启服务"
            )
        
        conn = sqlite3.connect(config.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # 结果以字典格式返回
        return conn
    except Exception as e:
        raise Exception(f"数据库连接失败：{str(e)}（路径：{config.db_path}）")

def query_single_table(
    table_name: str, 
    conditions: Optional[Dict[str, Any]] = None, 
    fields: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """单表查询：支持条件筛选、指定字段（新增参数校验）"""
    conn = None
    try:
        # 新增：参数类型校验
        if conditions is not None and not isinstance(conditions, dict):
            raise Exception(f"conditions必须是字典，当前类型：{type(conditions)}")
        if fields is not None and (not isinstance(fields, list) or len(fields) == 0):
            raise Exception("fields必须是非空列表（如['Id','Name']）")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 处理查询字段
        query_fields = ", ".join(fields) if (fields and len(fields) > 0) else "*"
        # 处理查询条件
        where_clause = ""
        params = []
        if conditions and len(conditions) > 0:
            where_clause = "WHERE " + " AND ".join([f"{k} = ?" for k in conditions.keys()])
            params = list(conditions.values())
        
        # 执行查询
        sql = f"SELECT {query_fields} FROM {table_name} {where_clause}"
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        raise Exception(f"单表查询失败（表：{table_name}）：{str(e)}")
    finally:
        if conn:
            conn.close()

def query_related_tables(related_type: str, main_id: int) -> Dict[str, Any]:
    """关联查询：玩家-社交账号、玩家-服务器"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        result = {}
        
        if related_type == "player_social":
            # 查询玩家信息
            sql_player = "SELECT * FROM Player WHERE Id = ?"
            cursor.execute(sql_player, (main_id,))
            player_row = cursor.fetchone()
            if not player_row:
                return {"error": f"玩家ID {main_id} 不存在"}
            player_data = dict(player_row)
            
            # 查询关联社交账号
            social_id = player_data.get("SocialAccountId")
            social_data = None
            if social_id:
                sql_social = "SELECT * FROM SocialAccount WHERE Id = ?"
                cursor.execute(sql_social, (social_id,))
                social_row = cursor.fetchone()
                social_data = dict(social_row) if social_row else None
            
            result = {
                "player_info": player_data,
                "related_social_account": social_data or "未绑定社交账号"
            }
        
        elif related_type == "player_server":
            # 查询玩家信息
            sql_player = "SELECT * FROM Player WHERE Id = ?"
            cursor.execute(sql_player, (main_id,))
            player_row = cursor.fetchone()
            if not player_row:
                return {"error": f"玩家ID {main_id} 不存在"}
            player_data = dict(player_row)
            
            # 查询关联服务器ID
            sql_relation = "SELECT ServersId FROM PlayerServerInfo WHERE PlayersId = ?"
            cursor.execute(sql_relation, (main_id,))
            server_id_rows = cursor.fetchall()
            server_ids = [row["ServersId"] for row in server_id_rows] if server_id_rows else []
            
            # 查询服务器详情
            server_data = []
            if server_ids:
                sql_servers = f"SELECT * FROM ServerInfo WHERE Id IN ({', '.join(['?']*len(server_ids))})"
                cursor.execute(sql_servers, server_ids)
                server_data = [dict(row) for row in cursor.fetchall()]
            
            result = {
                "player_info": player_data,
                "related_servers": server_data or "未关联任何服务器"
            }
        
        else:
            result = {"error": "仅支持 player_social（玩家-社交账号）、player_server（玩家-服务器）"}
        
        return result
    except Exception as e:
        raise Exception(f"关联查询失败（类型：{related_type}）：{str(e)}")
    finally:
        if conn:
            conn.close()

def query_player_by_multi_condition(
    player_name: Optional[str] = None,
    qq_number: Optional[str] = None,
    qq_name: Optional[str] = None,
    ip: Optional[str] = None,
    uuid: Optional[str] = None,
    fields: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """玩家多维度查询：名称/QQ/IP/UUID"""
    if not (player_name or qq_number or qq_name or ip or uuid):
        raise Exception("至少需传入一个查询条件：player_name/qq_number/qq_name/ip/uuid")
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 处理查询字段
        player_fields = ", ".join(fields) if (fields and len(fields) > 0) else "p.*"
        # 左关联社交账号表
        sql = f"""
            SELECT {player_fields}, 
                   s.Id AS social_id, s.Uuid AS qq_number, 
                   s.Name AS qq_name, s.Platform AS social_platform
            FROM Player p
            LEFT JOIN SocialAccount s ON p.SocialAccountId = s.Id
            WHERE 1=1
        """
        params = []
        
        # 拼接查询条件
        if player_name:
            sql += " AND p.Name LIKE ?"
            params.append(f"%{player_name}%")
        if qq_number:
            sql += " AND s.Uuid = ?"
            params.append(qq_number)
        if qq_name:
            sql += " AND s.Name LIKE ?"
            params.append(f"%{qq_name}%")
        if ip:
            sql += " AND p.Ip LIKE ?"
            params.append(f"%{ip}%")
        if uuid:
            sql += " AND p.Uuid = ?"
            params.append(uuid)
        
        # 执行查询并格式化结果
        cursor.execute(sql, params)
        results = cursor.fetchall()
        formatted_data = []
        for row in results:
            row_dict = dict(row)
            # 分离玩家信息和社交信息
            player_info = {k: v for k, v in row_dict.items() if not k.startswith(("social_", "qq_"))}
            social_info = {
                "social_id": row_dict.get("social_id"),
                "qq_number": row_dict.get("qq_number"),
                "qq_name": row_dict.get("qq_name"),
                "platform": row_dict.get("social_platform")
            }
            social_info = {k: v for k, v in social_info.items() if v is not None}
            
            formatted_data.append({
                "player_info": player_info,
                "social_info": social_info or "未绑定社交账号"
            })
        
        return formatted_data
    except Exception as e:
        raise Exception(f"玩家多维度查询失败：{str(e)}")
    finally:
        if conn:
            conn.close()
# 多维度查询玩家ID的方法
def get_player_id_by_multi_condition(
    player_name: Optional[str] = None,
    qq_number: Optional[str] = None,
    ip: Optional[str] = None,
    uuid: Optional[str] = None
) -> List[int]:
    """通过玩家名称、QQ号、IP、UUID查询玩家ID列表"""
    if not (player_name or qq_number or ip or uuid):
        raise Exception("至少需传入一个查询条件：player_name、qq_number、ip、uuid")
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = """
            SELECT p.Id 
            FROM Player p
            LEFT JOIN SocialAccount s ON p.SocialAccountId = s.Id
            WHERE 1=1
        """
        params = []
        
        if player_name:
            sql += " AND p.Name LIKE ?"
            params.append(f"%{player_name}%")
        if qq_number:
            sql += " AND s.Uuid = ?"
            params.append(qq_number)
        if ip:
            sql += " AND p.Ip LIKE ?"
            params.append(f"%{ip}%")
        if uuid:
            sql += " AND p.Uuid = ?"
            params.append(uuid)
        
        cursor.execute(sql, params)
        return [row["Id"] for row in cursor.fetchall()]
    except Exception as e:
        raise Exception(f"查询玩家ID失败：{str(e)}")
    finally:
        if conn:
            conn.close()

def query_group_by_condition(
    group_id: Optional[int] = None,
    group_name: Optional[str] = None,
    enabled: Optional[int] = None,
    min_member: Optional[int] = None,
    max_member: Optional[int] = None,
    fields: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Group表查询：修复SQL关键字兼容（用双引号包裹表名）"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 处理查询字段
        group_fields = ", ".join(fields) if (fields and len(fields) > 0) else "*"
        # 关键修复：用双引号包裹Group表名，兼容所有SQLite版本
        sql = f"SELECT {group_fields} FROM \"Group\" WHERE 1=1"
        params = []
        
        # 拼接查询条件
        if group_id is not None:
            sql += " AND GroupId = ?"
            params.append(group_id)
        if group_name:
            sql += " AND Name LIKE ?"
            params.append(f"%{group_name}%")
        if enabled is not None:
            sql += " AND Enabled = ?"
            params.append(enabled)
        if min_member is not None:
            sql += " AND MemberCount >= ?"
            params.append(min_member)
        if max_member is not None:
            sql += " AND MemberCount <= ?"
            params.append(max_member)
        
        # 执行查询
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        raise Exception(f"Group表查询失败：{str(e)}")
    finally:
        if conn:
            conn.close()

def get_table_count(table_name: str) -> int:
    """查询表总记录数"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) AS count FROM {table_name}")
        return cursor.fetchone()["count"]
    except Exception as e:
        raise Exception(f"表记录数查询失败（表：{table_name}）：{str(e)}")
    finally:
        if conn:
            conn.close()
