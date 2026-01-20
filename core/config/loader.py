import configparser
import os
from pathlib import Path

class ConfigLoader:
    def __init__(self):
        # 自动定位项目根目录 (core/config/*)
        self.project_root = Path(__file__).resolve().parents[2]
        self.config_path = self.project_root / "conf" / "settings.ini"
        
        self.config = configparser.ConfigParser()
        if not self.config_path.exists():
            raise FileNotFoundError(f"❌ 配置文件丢失: {self.config_path}")
        
        self.config.read(self.config_path)

    def get(self, section, key):
        """获取配置值并自动展开用户路径 (~)"""
        val = self.config.get(section, key, fallback=None)
        if val and "~" in val:
            return os.path.expanduser(val)
        return val

# 单例模式：直接导出的实例
wagstaff_config = ConfigLoader()

# === 测试代码 ===
if __name__ == "__main__":
    print(f"Project Root: {wagstaff_config.project_root}")
    print(f"DST Path: {wagstaff_config.get('PATHS', 'DST_ROOT')}")
