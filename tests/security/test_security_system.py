#!/usr/bin/env python3
"""
Basic integration tests for the security system
"""

import pytest
import sys
import os
from pathlib import Path

# Add the scripts directory to the Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))


def test_security_imports():
    """Test that security modules can be imported."""
    try:
        from security.baseline_manager import SecurityBaseline, SecurityBaselineManager
        from security.security_scanner import SecurityScanner, ScanConfiguration
        from security.report_generator import SecurityReportGenerator
        
        # Basic instantiation tests
        baseline = SecurityBaseline(
            timestamp="2024-01-01T00:00:00Z",
            scan_profile="test"
        )
        assert baseline.timestamp == "2024-01-01T00:00:00Z"
        
        config = ScanConfiguration(profile="quick")
        assert config.profile == "quick"
        
        # This confirms the modules are working
        assert True
        
    except ImportError as e:
        pytest.fail(f"Failed to import security modules: {e}")


def test_security_configuration_files():
    """Test that security configuration files exist and are valid."""
    config_dir = Path(__file__).parent.parent.parent / "configs" / "security"
    
    # Check config files exist
    assert (config_dir / "config.yaml").exists(), "Security config.yaml not found"
    assert (config_dir / "thresholds.yaml").exists(), "Security thresholds.yaml not found"
    
    # Basic YAML validity check
    import yaml
    
    with open(config_dir / "config.yaml") as f:
        config_data = yaml.safe_load(f)
    assert "security" in config_data, "Main security section not found in config"
    
    with open(config_dir / "thresholds.yaml") as f:
        thresholds_data = yaml.safe_load(f)
    assert "default" in thresholds_data, "Default thresholds section not found"


def test_security_scripts_exist():
    """Test that security script files exist."""
    scripts_dir = Path(__file__).parent.parent.parent / "scripts" / "security"
    
    assert (scripts_dir / "baseline_manager.py").exists(), "baseline_manager.py not found"
    assert (scripts_dir / "security_scanner.py").exists(), "security_scanner.py not found" 
    assert (scripts_dir / "report_generator.py").exists(), "report_generator.py not found"


if __name__ == "__main__":
    pytest.main([__file__])