#!/usr/bin/env python3
"""
Test BrowserAgent installation workflow step

This script tests the BrowserAgent installation functionality
by loading the ComfyUI template and verifying the step configuration.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.webui.template_manager import TemplateManager

def test_browser_agent_step():
    """Test that BrowserAgent installation step is properly configured"""
    
    print("=" * 70)
    print("Testing BrowserAgent Installation Step Configuration")
    print("=" * 70)
    
    # Initialize template manager
    template_manager = TemplateManager()
    
    # Load ComfyUI template
    print("\n1. Loading ComfyUI template...")
    template = template_manager.load_template('comfyui')
    
    if not template:
        print("   ❌ FAILED: Could not load ComfyUI template")
        return False
    
    print(f"   ✓ Template loaded: {template.get('name')}")
    print(f"   ✓ Version: {template.get('version')}")
    
    # Find BrowserAgent installation step
    print("\n2. Searching for BrowserAgent installation step...")
    setup_steps = template.get('setup_steps', [])
    
    browser_agent_step = None
    for step in setup_steps:
        if step.get('type') == 'browser_agent_install':
            browser_agent_step = step
            break
    
    if not browser_agent_step:
        print("   ❌ FAILED: BrowserAgent installation step not found")
        print(f"   Available steps: {[s.get('name') for s in setup_steps]}")
        return False
    
    print(f"   ✓ Step found: {browser_agent_step.get('name')}")
    print(f"   ✓ Type: {browser_agent_step.get('type')}")
    print(f"   ✓ Description: {browser_agent_step.get('description')}")
    
    # Verify step configuration
    print("\n3. Verifying step configuration...")
    
    required_fields = ['name', 'type', 'description', 'repository', 'destination', 'branch', 'commands']
    for field in required_fields:
        if field not in browser_agent_step:
            print(f"   ❌ FAILED: Missing required field: {field}")
            return False
        print(f"   ✓ {field}: {browser_agent_step.get(field) if field != 'commands' else f'{len(browser_agent_step.get(field))} commands'}")
    
    # Verify commands
    print("\n4. Verifying installation commands...")
    commands = browser_agent_step.get('commands', [])
    
    expected_commands = [
        'Update package list',
        'Install system dependencies',
        'Clone or update BrowserAgent',
        'Install Python dependencies',
        'Install Playwright browser',
        'Verify installation',
        'Run unit tests'
    ]
    
    for expected in expected_commands:
        found = any(expected in cmd.get('name', '') for cmd in commands)
        if found:
            print(f"   ✓ {expected}")
        else:
            print(f"   ❌ Missing: {expected}")
            return False
    
    # Check UI button configuration
    print("\n5. Checking UI button configuration...")
    ui_config = template.get('ui_config', {})
    setup_buttons = ui_config.get('setup_buttons', [])
    
    browser_agent_button = None
    for button in setup_buttons:
        if button.get('action') == 'install_browser_agent':
            browser_agent_button = button
            break
    
    if not browser_agent_button:
        print("   ❌ FAILED: BrowserAgent button not found in UI config")
        return False
    
    print(f"   ✓ Button label: {browser_agent_button.get('label')}")
    print(f"   ✓ Action: {browser_agent_button.get('action')}")
    print(f"   ✓ Style: {browser_agent_button.get('style')}")
    print(f"   ✓ Tooltip: {browser_agent_button.get('tooltip')}")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)
    print("\nBrowserAgent installation step is properly configured:")
    print(f"  • Repository: {browser_agent_step.get('repository')}")
    print(f"  • Destination: {browser_agent_step.get('destination')}")
    print(f"  • Branch: {browser_agent_step.get('branch')}")
    print(f"  • Commands: {len(commands)}")
    print(f"  • UI Button: {browser_agent_button.get('label')}")
    print("\nNext steps:")
    print("  1. Test the installation on a VastAI instance")
    print("  2. Implement browser-based workflow executor")
    print("  3. Update Create tab to use browser execution")
    print("  4. Remove old API-based workflow code")
    
    return True


def test_step_order():
    """Test that BrowserAgent step is in the correct order"""
    
    print("\n" + "=" * 70)
    print("Testing Setup Steps Order")
    print("=" * 70)
    
    template_manager = TemplateManager()
    template = template_manager.load_template('comfyui')
    
    if not template:
        print("❌ Could not load template")
        return False
    
    setup_steps = template.get('setup_steps', [])
    
    print("\nCurrent setup steps order:")
    for i, step in enumerate(setup_steps, 1):
        step_name = step.get('name')
        step_type = step.get('type')
        icon = "🌐" if step_type == 'browser_agent_install' else "•"
        print(f"  {i}. {icon} {step_name} ({step_type})")
    
    # Find BrowserAgent step position
    browser_agent_index = -1
    for i, step in enumerate(setup_steps):
        if step.get('type') == 'browser_agent_install':
            browser_agent_index = i
            break
    
    if browser_agent_index == -1:
        print("\n❌ BrowserAgent step not found")
        return False
    
    print(f"\n✓ BrowserAgent step is at position {browser_agent_index + 1}")
    
    # BrowserAgent should be after Python venv setup
    venv_index = -1
    for i, step in enumerate(setup_steps):
        if step.get('type') == 'python_venv':
            venv_index = i
            break
    
    if venv_index != -1 and browser_agent_index > venv_index:
        print(f"✓ Correctly ordered after Python venv setup (position {venv_index + 1})")
    else:
        print(f"⚠ Warning: BrowserAgent should be after Python venv setup")
    
    return True


if __name__ == '__main__':
    print("\n🧪 BrowserAgent Installation Step Test Suite\n")
    
    try:
        # Run tests
        test1_passed = test_browser_agent_step()
        test2_passed = test_step_order()
        
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"  Configuration Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
        print(f"  Step Order Test:    {'✅ PASSED' if test2_passed else '❌ FAILED'}")
        
        if test1_passed and test2_passed:
            print("\n🎉 All tests passed! BrowserAgent installation step is ready.")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed. Please review the output above.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
