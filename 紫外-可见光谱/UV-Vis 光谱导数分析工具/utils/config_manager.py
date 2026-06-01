import json
import os
from typing import Dict, Any

PRESETS_FILE = "presets.json"

DEFAULT_CONFIG = {
    "smooth_win": 15,
    "smooth_poly": 3,
    "baseline_enable": False,
    "baseline_lam": 5.0,
    "deriv_win": 21,
    "deriv_win_2nd": 41,
    "deriv_poly": 3,
    "peak_enable": True,
    "peak_source": "基线校正后",
    "peak_mode": "自动",
    "peak_prom": 0.02,
    "peak_dist": 10,
}

class ConfigManager:
    @staticmethod
    def load_presets() -> Dict[str, Dict[str, Any]]:
        """加载所有预设配置"""
        if not os.path.exists(PRESETS_FILE):
            return {"默认配置": DEFAULT_CONFIG.copy()}
        
        try:
            with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                presets = json.load(f)
            # 确保默认配置存在
            if "默认配置" not in presets:
                presets["默认配置"] = DEFAULT_CONFIG.copy()
            return presets
        except Exception:
            return {"默认配置": DEFAULT_CONFIG.copy()}

    @staticmethod
    def save_preset(name: str, config: Dict[str, Any]) -> None:
        """保存新的预设"""
        presets = ConfigManager.load_presets()
        # 过滤掉不需要保存的临时键
        clean_config = {k: v for k, v in config.items() if k in DEFAULT_CONFIG}
        presets[name] = clean_config
        
        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(presets, f, indent=4, ensure_ascii=False)

    @staticmethod
    def delete_preset(name: str) -> None:
        """删除预设"""
        if name == "默认配置":
            return # 禁止删除默认配置
            
        presets = ConfigManager.load_presets()
        if name in presets:
            del presets[name]
            with open(PRESETS_FILE, "w", encoding="utf-8") as f:
                json.dump(presets, f, indent=4, ensure_ascii=False)

    @staticmethod
    def get_default_keys() -> list:
        """获取受管参数列表"""
        return list(DEFAULT_CONFIG.keys())
