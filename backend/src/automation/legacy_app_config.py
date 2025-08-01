# Legacy Application Configuration
# Configuration settings for handling legacy enterprise applications

# Browser and Navigation Settings
LEGACY_APP_CONFIG = {
    # Navigation and Loading
    "legacy_wait_time": 600,  # 10 minutes - Time to wait for legacy app to fully load
    "navigation_timeout": 600000,  # 10 minutes for initial page load
    "dom_load_timeout": 600000,   # 10 minutes for DOM content to load
    
    # Progress reporting
    "progress_interval": 30,  # Show progress every 30 seconds during long waits
    
    # Browser settings optimized for legacy apps
    "browser_settings": {
        "headless": False,
        "slow_mo": 1000,
        "timeout": 600000,  # 5 minutes default timeout
        "viewport": {"width": 1920, "height": 1080}
    },
    
    # Application-specific settings
    "cisco_catalyst_center": {
        "legacy_wait_time": 600,  # 10 minutes for Cisco Catalyst Center
        "requires_extra_auth_time": True,
        "expected_console_errors": [
            "401 unauthorized",
            "cors",
            "mixed content",
            "invalid contribution"
        ]
    }
}

def get_wait_time_for_app(url: str) -> int:
    """Get appropriate wait time based on application URL"""
    
    # Cisco applications typically need more time
    if any(domain in url.lower() for domain in ["cisco", "catalyst", "dna"]):
        return LEGACY_APP_CONFIG["cisco_catalyst_center"]["legacy_wait_time"]
    
    # Default wait time for other legacy apps
    return LEGACY_APP_CONFIG["legacy_wait_time"]

def get_browser_config_for_legacy_apps() -> dict:
    """Get browser configuration optimized for legacy applications"""
    
    config = LEGACY_APP_CONFIG["browser_settings"].copy()
    config["legacy_wait_time"] = LEGACY_APP_CONFIG["legacy_wait_time"]
    
    return config
