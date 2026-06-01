from utils.config_manager import ConfigManager, DEFAULT_CONFIG
import os

def test_config_manager():
    print("Testing ConfigManager...")
    
    # 1. Load initial (should be default)
    presets = ConfigManager.load_presets()
    assert "默认配置" in presets
    print("Default config loaded successfully.")
    
    # 2. Save new preset
    new_config = DEFAULT_CONFIG.copy()
    new_config["smooth_win"] = 99
    ConfigManager.save_preset("TestPreset", new_config)
    print("TestPreset saved.")
    
    # 3. Load again to verify
    presets = ConfigManager.load_presets()
    assert "TestPreset" in presets
    assert presets["TestPreset"]["smooth_win"] == 99
    print("TestPreset verification successful.")
    
    # 4. Delete preset
    ConfigManager.delete_preset("TestPreset")
    presets = ConfigManager.load_presets()
    assert "TestPreset" not in presets
    print("TestPreset deleted successfully.")
    
    # Cleanup
    if os.path.exists("presets.json"):
        os.remove("presets.json")
    print("All tests passed.")

if __name__ == "__main__":
    test_config_manager()