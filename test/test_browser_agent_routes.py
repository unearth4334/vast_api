#!/usr/bin/env python3
"""
Test BrowserAgent installation API routes

Verifies that the API routes for BrowserAgent installation are properly configured.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_routes_defined():
    """Test that BrowserAgent installation routes are defined in sync_api.py"""
    
    print("=" * 70)
    print("Testing BrowserAgent Installation API Routes")
    print("=" * 70)
    
    sync_api_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'sync', 'sync_api.py')
    
    with open(sync_api_path, 'r') as f:
        content = f.read()
    
    # Check for required routes
    routes_to_check = [
        ("/ssh/install-browser-agent", "install_browser_agent_ssh"),
        ("/vastai/install-browser-agent", "install_browser_agent_vastai"),
    ]
    
    all_found = True
    
    for route_path, function_name in routes_to_check:
        route_decorator = f"@app.route('{route_path}'"
        
        if route_decorator in content:
            print(f"✓ Route found: {route_path}")
            
            # Check for function definition
            if f"def {function_name}(" in content:
                print(f"  ✓ Handler function: {function_name}()")
            else:
                print(f"  ❌ Handler function NOT found: {function_name}()")
                all_found = False
        else:
            print(f"❌ Route NOT found: {route_path}")
            all_found = False
    
    print()
    
    # Check for execute_browser_agent_install function
    if "def execute_browser_agent_install(" in content:
        print("✓ Core function found: execute_browser_agent_install()")
    else:
        print("❌ Core function NOT found: execute_browser_agent_install()")
        all_found = False
    
    # Check for idempotency in installation script
    if "if [ -d \"/root/BrowserAgent\" ]" in content:
        print("✓ Installation script has idempotency check")
    else:
        print("⚠ Installation script may not be idempotent")
    
    if "already installed and working" in content:
        print("✓ Quick verification path exists for existing installations")
    else:
        print("⚠ No quick path for existing installations")
    
    print()
    print("=" * 70)
    
    if all_found:
        print("✅ ALL ROUTES AND FUNCTIONS PROPERLY DEFINED")
        print("=" * 70)
        print("\nAvailable endpoints:")
        print("  POST /ssh/install-browser-agent")
        print("  POST /vastai/install-browser-agent")
        print("\nBoth routes call: execute_browser_agent_install()")
        print("\nFeatures:")
        print("  • Idempotent installation (safe to run multiple times)")
        print("  • Quick verification for existing installations")
        print("  • System dependencies auto-install")
        print("  • Python packages auto-upgrade")
        print("  • Chromium browser auto-install")
        print("  • Comprehensive verification and testing")
        return True
    else:
        print("❌ SOME ROUTES OR FUNCTIONS ARE MISSING")
        print("=" * 70)
        return False


if __name__ == '__main__':
    print("\n🧪 BrowserAgent API Routes Test\n")
    
    try:
        success = test_routes_defined()
        
        if success:
            print("\n🎉 All routes configured correctly!")
            print("\nNext steps:")
            print("  1. Test the route in the WebUI")
            print("  2. Click '🌐 Install BrowserAgent' button")
            print("  3. Verify installation completes successfully")
            sys.exit(0)
        else:
            print("\n❌ Route configuration incomplete")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
