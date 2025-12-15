#!/usr/bin/env python3
"""
Test Run Workflow Button (WebUI) with Playwright

Tests the "▶️ Run Workflow" button functionality in the Create tab:
1. UI interaction and button states
2. Form validation
3. SSH connection requirement
4. API call to /create/queue-workflow
5. Success/error message display
6. ExecutionQueue integration

Prerequisites:
    pip install playwright
    playwright install chromium

Usage:
    python3 test/test_run_workflow_button.py
"""

import sys
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright, expect
import time

# Configuration
BASE_URL = "http://localhost:5000"
TEST_SSH_CONNECTION = "ssh -p 12345 root@192.168.1.100"


class TestRunWorkflowButton:
    """Test the Run Workflow button in Create tab"""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.passed = 0
        self.failed = 0
        
    async def setup(self):
        """Set up browser and page"""
        print("🌐 Launching browser...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
        # Set up mock API responses
        await self.page.route("**/create/workflows/list", self.mock_workflows_list)
        await self.page.route("**/create/workflow/*", self.mock_workflow_details)
        
        print("✅ Browser ready")
    
    async def teardown(self):
        """Clean up browser"""
        if self.browser:
            await self.browser.close()
            print("🔒 Browser closed")
    
    async def mock_workflows_list(self, route):
        """Mock workflows list endpoint"""
        await route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "success": True,
                "workflows": [
                    {
                        "id": "IMG_to_VIDEO_canvas",
                        "name": "IMG to VIDEO (Canvas)",
                        "description": "Generate video from image",
                        "category": "video",
                        "icon": "🎬",
                        "vram_estimate": "24GB",
                        "tags": ["image-to-video", "wan-2.2"]
                    }
                ]
            })
        )
    
    async def mock_workflow_details(self, route):
        """Mock workflow details endpoint"""
        await route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "success": True,
                "workflow": {
                    "id": "IMG_to_VIDEO_canvas",
                    "name": "IMG to VIDEO (Canvas)",
                    "description": "Generate video from image",
                    "inputs": [
                        {
                            "id": "input_image",
                            "section": "basic",
                            "type": "image",
                            "label": "Input Image",
                            "required": True
                        },
                        {
                            "id": "positive_prompt",
                            "section": "basic",
                            "type": "textarea",
                            "label": "Positive Prompt",
                            "required": True,
                            "default": "A beautiful scene"
                        },
                        {
                            "id": "cfg",
                            "section": "generation",
                            "type": "slider",
                            "label": "CFG Scale",
                            "required": False,
                            "min": 1.0,
                            "max": 10.0,
                            "default": 3.5
                        }
                    ],
                    "outputs": [],
                    "helper_tools": []
                }
            })
        )
    
    async def navigate_to_create_tab(self):
        """Navigate to the Create tab"""
        print("\n📍 Navigating to Create tab...")
        await self.page.goto(BASE_URL)
        
        # Wait for page load
        await self.page.wait_for_load_state("networkidle")
        
        # Click on Create tab
        await self.page.click('a[href="#create"]')
        await self.page.wait_for_selector('#create', state='visible')
        
        print("✅ Navigated to Create tab")
    
    async def select_workflow(self):
        """Select a workflow"""
        print("\n📍 Selecting workflow...")
        
        # Wait for workflow grid
        await self.page.wait_for_selector('.workflow-card')
        
        # Click on first workflow
        await self.page.click('.workflow-card')
        
        # Wait for form to load
        await self.page.wait_for_selector('.create-form', state='visible')
        
        print("✅ Workflow selected and form loaded")
    
    async def test_button_exists(self):
        """Test 1: Run Workflow button exists"""
        print("\n" + "=" * 60)
        print("Test 1: Run Workflow button exists")
        print("=" * 60)
        
        try:
            await self.navigate_to_create_tab()
            await self.select_workflow()
            
            # Check button exists
            button = await self.page.wait_for_selector('#create-execute-button')
            button_text = await button.inner_text()
            
            assert "▶️" in button_text or "Run Workflow" in button_text, \
                f"Button text unexpected: {button_text}"
            
            print("✅ PASS: Run Workflow button exists with correct text")
            self.passed += 1
            
        except Exception as e:
            print(f"❌ FAIL: {e}")
            self.failed += 1
    
    async def test_button_disabled_without_ssh(self):
        """Test 2: Button shows error without SSH connection"""
        print("\n" + "=" * 60)
        print("Test 2: Error shown without SSH connection")
        print("=" * 60)
        
        try:
            await self.navigate_to_create_tab()
            await self.select_workflow()
            
            # Fill in required fields
            await self.page.fill('textarea[data-field-id="positive_prompt"]', 'Test prompt')
            
            # Try to click Run Workflow button
            await self.page.click('#create-execute-button')
            
            # Wait for error message
            await self.page.wait_for_selector('.setup-result.error', state='visible', timeout=2000)
            
            # Check error message
            error = await self.page.text_content('.setup-result.error')
            assert 'connect' in error.lower() or 'instance' in error.lower(), \
                f"Error message unexpected: {error}"
            
            print("✅ PASS: Error shown without SSH connection")
            self.passed += 1
            
        except Exception as e:
            print(f"❌ FAIL: {e}")
            self.failed += 1
    
    async def test_button_validates_required_fields(self):
        """Test 3: Button validates required fields"""
        print("\n" + "=" * 60)
        print("Test 3: Validates required fields")
        print("=" * 60)
        
        try:
            await self.navigate_to_create_tab()
            await self.select_workflow()
            
            # Set SSH connection via toolbar (mock)
            await self.page.evaluate(f'''
                window.sshConnection = "{TEST_SSH_CONNECTION}";
                window.getCurrentSSHConnection = () => "{TEST_SSH_CONNECTION}";
            ''')
            
            # Click button without filling required fields
            await self.page.click('#create-execute-button')
            
            # Wait for error message
            await self.page.wait_for_selector('.setup-result.error', state='visible', timeout=2000)
            
            # Check error message mentions required field
            error = await self.page.text_content('.setup-result.error')
            assert 'required' in error.lower(), f"Error message unexpected: {error}"
            
            print("✅ PASS: Required field validation works")
            self.passed += 1
            
        except Exception as e:
            print(f"❌ FAIL: {e}")
            self.failed += 1
    
    async def test_button_disables_during_execution(self):
        """Test 4: Button disables during execution"""
        print("\n" + "=" * 60)
        print("Test 4: Button disables during execution")
        print("=" * 60)
        
        try:
            await self.navigate_to_create_tab()
            await self.select_workflow()
            
            # Set SSH connection
            await self.page.evaluate(f'''
                window.sshConnection = "{TEST_SSH_CONNECTION}";
                window.getCurrentSSHConnection = () => "{TEST_SSH_CONNECTION}";
            ''')
            
            # Fill required fields
            await self.page.fill('textarea[data-field-id="positive_prompt"]', 'Test prompt')
            
            # Mock the upload (for image input)
            await self.page.evaluate('''
                // Mock image upload
                window.CreateTabState = window.CreateTabState || {{}};
                window.CreateTabState.formValues = window.CreateTabState.formValues || {{}};
                window.CreateTabState.formValues['input_image'] = 'data:image/jpeg;base64,/9j/test';
            ''')
            
            # Mock API response with delay
            await self.page.route("**/create/queue-workflow", lambda route: asyncio.create_task(
                self._delayed_queue_response(route, 1000)
            ))
            
            # Click button
            await self.page.click('#create-execute-button')
            
            # Check button is disabled immediately
            await asyncio.sleep(0.1)  # Small delay for UI update
            button = await self.page.query_selector('#create-execute-button')
            is_disabled = await button.is_disabled()
            button_text = await button.inner_text()
            
            assert is_disabled, "Button should be disabled during execution"
            assert "Executing" in button_text or "⏳" in button_text, \
                f"Button text should show executing state: {button_text}"
            
            print("✅ PASS: Button disables during execution")
            self.passed += 1
            
        except Exception as e:
            print(f"❌ FAIL: {e}")
            self.failed += 1
    
    async def test_successful_workflow_execution(self):
        """Test 5: Successful workflow execution flow"""
        print("\n" + "=" * 60)
        print("Test 5: Successful workflow execution")
        print("=" * 60)
        
        try:
            await self.navigate_to_create_tab()
            await self.select_workflow()
            
            # Set SSH connection
            await self.page.evaluate(f'''
                window.sshConnection = "{TEST_SSH_CONNECTION}";
                window.getCurrentSSHConnection = () => "{TEST_SSH_CONNECTION}";
            ''')
            
            # Fill required fields
            await self.page.fill('textarea[data-field-id="positive_prompt"]', 'Test prompt')
            
            # Mock image upload
            await self.page.evaluate('''
                window.CreateTabState = window.CreateTabState || {{}};
                window.CreateTabState.formValues = window.CreateTabState.formValues || {{}};
                window.CreateTabState.formValues['input_image'] = 'data:image/jpeg;base64,/9j/test';
            ''')
            
            # Mock successful API response
            await self.page.route("**/create/queue-workflow", lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "success": True,
                    "prompt_id": "abc-123-def-456",
                    "message": "Workflow queued successfully!"
                })
            ))
            
            # Click button
            await self.page.click('#create-execute-button')
            
            # Wait for success message
            await self.page.wait_for_selector('.setup-result.success', state='visible', timeout=3000)
            
            # Check success message
            success = await self.page.text_content('.setup-result.success')
            assert 'success' in success.lower() or 'queued' in success.lower(), \
                f"Success message unexpected: {success}"
            
            # Check button is re-enabled
            await asyncio.sleep(0.5)
            button = await self.page.query_selector('#create-execute-button')
            is_disabled = await button.is_disabled()
            button_text = await button.inner_text()
            
            assert not is_disabled, "Button should be re-enabled after execution"
            assert "Run Workflow" in button_text or "▶️" in button_text, \
                f"Button should show normal state: {button_text}"
            
            print("✅ PASS: Successful workflow execution")
            self.passed += 1
            
        except Exception as e:
            print(f"❌ FAIL: {e}")
            self.failed += 1
    
    async def test_api_error_handling(self):
        """Test 6: API error handling"""
        print("\n" + "=" * 60)
        print("Test 6: API error handling")
        print("=" * 60)
        
        try:
            await self.navigate_to_create_tab()
            await self.select_workflow()
            
            # Set SSH connection
            await self.page.evaluate(f'''
                window.sshConnection = "{TEST_SSH_CONNECTION}";
                window.getCurrentSSHConnection = () => "{TEST_SSH_CONNECTION}";
            ''')
            
            # Fill required fields
            await self.page.fill('textarea[data-field-id="positive_prompt"]', 'Test prompt')
            
            # Mock image
            await self.page.evaluate('''
                window.CreateTabState = window.CreateTabState || {{}};
                window.CreateTabState.formValues = window.CreateTabState.formValues || {{}};
                window.CreateTabState.formValues['input_image'] = 'data:image/jpeg;base64,/9j/test';
            ''')
            
            # Mock API error response
            await self.page.route("**/create/queue-workflow", lambda route: route.fulfill(
                status=500,
                content_type="application/json",
                body=json.dumps({
                    "success": False,
                    "message": "SSH connection failed"
                })
            ))
            
            # Click button
            await self.page.click('#create-execute-button')
            
            # Wait for error message
            await self.page.wait_for_selector('.setup-result.error', state='visible', timeout=3000)
            
            # Check error message
            error = await self.page.text_content('.setup-result.error')
            assert 'failed' in error.lower() or 'error' in error.lower(), \
                f"Error message unexpected: {error}"
            
            # Check button is re-enabled
            await asyncio.sleep(0.5)
            button = await self.page.query_selector('#create-execute-button')
            is_disabled = await button.is_disabled()
            
            assert not is_disabled, "Button should be re-enabled after error"
            
            print("✅ PASS: API error handling works")
            self.passed += 1
            
        except Exception as e:
            print(f"❌ FAIL: {e}")
            self.failed += 1
    
    async def test_form_values_sent_to_api(self):
        """Test 7: Form values correctly sent to API"""
        print("\n" + "=" * 60)
        print("Test 7: Form values sent to API")
        print("=" * 60)
        
        try:
            await self.navigate_to_create_tab()
            await self.select_workflow()
            
            # Set SSH connection
            await self.page.evaluate(f'''
                window.sshConnection = "{TEST_SSH_CONNECTION}";
                window.getCurrentSSHConnection = () => "{TEST_SSH_CONNECTION}";
            ''')
            
            # Fill form fields
            await self.page.fill('textarea[data-field-id="positive_prompt"]', 'My test prompt')
            
            # Set slider value
            await self.page.evaluate('''
                const slider = document.querySelector('[data-field-id="cfg"]');
                if (slider) {{
                    slider.value = 7.5;
                    slider.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            ''')
            
            # Mock image
            await self.page.evaluate('''
                window.CreateTabState = window.CreateTabState || {{}};
                window.CreateTabState.formValues = window.CreateTabState.formValues || {{}};
                window.CreateTabState.formValues['input_image'] = 'data:image/jpeg;base64,/9j/test';
            ''')
            
            # Capture API request
            api_request = None
            async def capture_request(route):
                nonlocal api_request
                api_request = await route.request.post_data_json()
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "success": True,
                        "prompt_id": "test-123",
                        "message": "Queued"
                    })
                )
            
            await self.page.route("**/create/queue-workflow", capture_request)
            
            # Click button
            await self.page.click('#create-execute-button')
            
            # Wait for request
            await asyncio.sleep(1)
            
            # Verify request payload
            assert api_request is not None, "API request not captured"
            assert api_request['ssh_connection'] == TEST_SSH_CONNECTION, "SSH connection not sent"
            assert api_request['workflow_id'] == 'IMG_to_VIDEO_canvas', "Workflow ID not sent"
            assert 'inputs' in api_request, "Inputs not sent"
            assert 'positive_prompt' in api_request['inputs'], "Prompt not sent"
            assert api_request['inputs']['positive_prompt'] == 'My test prompt', "Prompt value incorrect"
            
            print("✅ PASS: Form values correctly sent to API")
            self.passed += 1
            
        except Exception as e:
            print(f"❌ FAIL: {e}")
            self.failed += 1
    
    async def _delayed_queue_response(self, route, delay_ms):
        """Helper to simulate delayed API response"""
        await asyncio.sleep(delay_ms / 1000)
        await route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "success": True,
                "prompt_id": "delayed-123",
                "message": "Queued"
            })
        )
    
    async def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("Run Workflow Button Tests (Playwright)")
        print("=" * 60)
        
        await self.setup()
        
        try:
            # Run tests
            await self.test_button_exists()
            await self.test_button_disabled_without_ssh()
            await self.test_button_validates_required_fields()
            await self.test_button_disables_during_execution()
            await self.test_successful_workflow_execution()
            await self.test_api_error_handling()
            await self.test_form_values_sent_to_api()
            
        finally:
            await self.teardown()
        
        # Print summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Tests run: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        
        if self.failed == 0:
            print("\n✅ All tests passed!")
            return 0
        else:
            print(f"\n❌ {self.failed} test(s) failed")
            return 1


async def main():
    """Main entry point"""
    tester = TestRunWorkflowButton()
    return await tester.run_all_tests()


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
