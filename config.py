import configparser
import os
from typing import List

class ConfigLoader:
    def __init__(self, config_path: str = "config.ini"):
        # 初始化配置解析器并检查配置文件
        self.config = configparser.ConfigParser()
        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"配置文件 {config_path} 不存在！\n"
                f"请在项目根目录创建config.ini，并参考模板配置"
            )
        self.config.read(config_path, encoding="utf-8")
        
        # 加载各模块配置
        self.db_path = self._load_db_config()
        self.api_keys = self._load_api_auth_config()
        self.service_host, self.service_port = self._load_service_config()

    def _load_db_config(self) -> str:
        """加载数据库路径，含文件存在性、路径类型检查"""
        try:
            db_path = self.config.get("DATABASE", "db_path").strip()
            # 相对路径转项目根目录绝对路径
            if not os.path.isabs(db_path):
                project_root = os.path.dirname(os.path.abspath(__file__))
                db_path = os.path.join(project_root, db_path)
            
            # 检查数据库文件是否存在
            if not os.path.exists(db_path):
                raise FileNotFoundError(
                    f"数据库文件不存在！\n"
                    f"当前配置路径：{db_path}\n"
                    f"请检查[DATABASE]章节db_path或确认文件存在"
                )
            
            # 检查路径是否为文件（避免配置成目录）
            if os.path.isdir(db_path):
                raise IsADirectoryError(
                    f"db_path是目录而非文件！\n"
                    f"当前配置：{db_path}\n"
                    f"请指定具体SQLite文件（如./data/game_db.db）"
                )
            
            return db_path
        except configparser.NoSectionError:
            raise Exception("配置文件缺少 [DATABASE] 章节")
        except configparser.NoOptionError:
            raise Exception("配置文件[DATABASE]章节缺少 db_path 配置项")

    def _load_api_auth_config(self) -> List[str]:
        """加载API Key列表，去重去空"""
        try:
            api_keys_str = self.config.get("API_AUTH", "api_keys").strip()
            if not api_keys_str:
                raise Exception("配置文件[API_AUTH]章节的api_keys不能为空")
            
            api_keys = [key.strip() for key in api_keys_str.split(",") if key.strip()]
            return list(set(api_keys))  # 去重
        except configparser.NoSectionError:
            raise Exception("配置文件缺少 [API_AUTH] 章节")
        except configparser.NoOptionError:
            raise Exception("配置文件[API_AUTH]章节缺少 api_keys 配置项")

    def _load_service_config(self) -> tuple:
        """加载服务地址和端口，校验有效性"""
        try:
            host = self.config.get("SERVICE", "host").strip() or "0.0.0.0"
            port = self.config.getint("SERVICE", "port")
            
            if not (1 <= port <= 65535):
                raise ValueError(f"服务端口 {port} 无效（需1-65535）")
            
            return host, port
        except configparser.NoSectionError:
            raise Exception("配置文件缺少 [SERVICE] 章节")
        except configparser.NoOptionError:
            raise Exception("配置文件[SERVICE]章节缺少 host 或 port")
        except ValueError:
            raise Exception("配置文件[SERVICE]章节的 port 必须为整数")

# 延迟初始化配置，避免循环导入
config = None

def get_config() -> ConfigLoader:
    """获取配置单例（延迟初始化）"""
    global config
    if config is None:
        config = ConfigLoader()
    return config
