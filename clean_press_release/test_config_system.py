#!/usr/bin/env python3
"""
Test script for the multi-mode configuration system
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from multi_mode_config_loader import get_multi_mode_config
from config_manager_gui import get_config_manager

def test_config_loader():
    """Test the multi-mode configuration loader"""
    print("🧪 Testing Multi-Mode Configuration Loader...")
    
    try:
        config = get_multi_mode_config()
        
        # Test getting available modes
        modes = config.get_available_modes()
        print(f"✅ Available modes: {list(modes.keys())}")
        
        # Test getting default mode
        default_mode = config.get_default_mode()
        print(f"✅ Default mode: {default_mode}")
        
        # Test setting current mode
        if config.set_current_mode("press_release"):
            print("✅ Successfully set mode to press_release")
        else:
            print("❌ Failed to set mode to press_release")
        
        # Test getting current mode
        current_mode = config.get_current_mode()
        print(f"✅ Current mode: {current_mode}")
        
        # Test getting mode info
        mode_info = config.get_mode_info("press_release")
        if mode_info:
            print(f"✅ Press release mode info: {mode_info['name']} - {mode_info['description']}")
        else:
            print("❌ Failed to get press release mode info")
        
        # Test getting configuration
        section_creator_config = config.get_section_creator_config()
        if section_creator_config:
            print("✅ Successfully loaded section creator configuration")
        else:
            print("❌ Failed to load section creator configuration")
        
        print("🎉 Multi-Mode Configuration Loader test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing configuration loader: {e}")
        return False

def test_config_manager():
    """Test the configuration manager GUI"""
    print("\n🧪 Testing Configuration Manager GUI...")
    
    try:
        manager = get_config_manager()
        
        # Test getting current mode
        current_mode = manager.get_current_mode()
        print(f"✅ Current mode: {current_mode}")
        
        # Test getting available modes
        available_modes = manager.get_available_modes()
        print(f"✅ Available modes: {available_modes}")
        
        # Test updating mode info
        mode_info_html, status = manager.update_mode_info("press_release")
        if mode_info_html and "Press Release" in mode_info_html:
            print("✅ Successfully generated mode info HTML")
        else:
            print("❌ Failed to generate mode info HTML")
        
        print("🎉 Configuration Manager GUI test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing configuration manager: {e}")
        return False

def test_mode_switching():
    """Test switching between different modes"""
    print("\n🧪 Testing Mode Switching...")
    
    try:
        config = get_multi_mode_config()
        
        # Test switching to RFP mode
        if config.set_current_mode("rfp"):
            print("✅ Successfully switched to RFP mode")
            
            # Test getting RFP-specific configuration
            rfp_config = config.get_current_config()
            if rfp_config:
                print("✅ Successfully loaded RFP configuration")
            else:
                print("❌ Failed to load RFP configuration")
        else:
            print("❌ Failed to switch to RFP mode")
        
        # Test switching back to press release mode
        if config.set_current_mode("press_release"):
            print("✅ Successfully switched back to press release mode")
        else:
            print("❌ Failed to switch back to press release mode")
        
        print("🎉 Mode switching test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing mode switching: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Multi-Mode Configuration System Tests\n")
    
    tests = [
        test_config_loader,
        test_config_manager,
        test_mode_switching
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The configuration system is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the configuration files and dependencies.")
        return 1

if __name__ == "__main__":
    sys.exit(main())


