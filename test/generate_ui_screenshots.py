#!/usr/bin/env python3
"""
UI Screenshot Generator for Resource Manager

Generates screenshots of the Resource Manager UI to showcase functionality.
"""

import sys
import os
import time
import subprocess
from pathlib import Path

# Check if playwright is available
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Note: Playwright not available. Install with: pip install playwright && playwright install")


def start_server(port=5556):
    """Start the Flask development server"""
    print(f"Starting Flask server on port {port}...")
    
    env = os.environ.copy()
    env['FLASK_APP'] = 'app.sync.sync_api'
    env['FLASK_ENV'] = 'development'
    
    process = subprocess.Popen(
        ['python3', '-m', 'flask', 'run', '--port', str(port), '--host', '0.0.0.0'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=os.path.dirname(os.path.dirname(__file__))
    )
    
    # Wait for server to start
    import requests
    max_attempts = 30
    for i in range(max_attempts):
        try:
            response = requests.get(f"http://localhost:{port}/status", timeout=1)
            if response.status_code == 200:
                print(f"✓ Server started successfully")
                return process
        except:
            time.sleep(0.5)
    
    print("✗ Failed to start server")
    process.terminate()
    return None


def capture_screenshots_playwright(port=5556):
    """Capture screenshots using Playwright"""
    if not PLAYWRIGHT_AVAILABLE:
        print("Playwright not available, skipping screenshot capture")
        return False
    
    screenshots_dir = Path("docs/screenshots")
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    url = f"http://localhost:{port}"
    
    print("\nCapturing screenshots with Playwright...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        try:
            # Screenshot 1: Main UI with Sync tab
            print("  1. Capturing main UI...")
            page.goto(url)
            page.wait_for_load_state('networkidle')
            time.sleep(1)
            page.screenshot(path=str(screenshots_dir / "01_main_ui.png"))
            
            # Screenshot 2: Resource Manager tab (empty state)
            print("  2. Capturing Resource Manager tab...")
            page.click('button:has-text("Resource Manager")')
            page.wait_for_timeout(2000)  # Wait for initialization
            page.screenshot(path=str(screenshots_dir / "02_resource_manager_tab.png"))
            
            # Screenshot 3: Resource grid loaded
            print("  3. Capturing resource grid...")
            page.wait_for_selector('.resource-card', timeout=5000)
            page.screenshot(path=str(screenshots_dir / "03_resource_grid.png"))
            
            # Screenshot 4: Filter by ecosystem
            print("  4. Capturing ecosystem filter...")
            page.select_option('#filter-ecosystem', 'sdxl')
            page.wait_for_timeout(1000)
            page.screenshot(path=str(screenshots_dir / "04_ecosystem_filter.png"))
            
            # Screenshot 5: Search functionality
            print("  5. Capturing search...")
            page.fill('#filter-search', 'workflow')
            page.wait_for_timeout(1000)
            page.screenshot(path=str(screenshots_dir / "05_search_results.png"))
            
            # Screenshot 6: Resource selection
            print("  6. Capturing resource selection...")
            page.click('.btn-select >> nth=0')
            page.click('.btn-select >> nth=1')
            page.wait_for_timeout(500)
            page.screenshot(path=str(screenshots_dir / "06_resource_selection.png"))
            
            # Screenshot 7: Selected resources footer
            print("  7. Capturing selection footer...")
            page.evaluate("document.querySelector('.resource-footer').scrollIntoView()")
            page.wait_for_timeout(500)
            page.screenshot(path=str(screenshots_dir / "07_selection_footer.png"))
            
            print(f"\n✓ Screenshots saved to {screenshots_dir}")
            return True
            
        except Exception as e:
            print(f"\n✗ Error capturing screenshots: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            browser.close()


def generate_html_screenshot_fallback(port=5556):
    """Generate HTML documentation with embedded images as fallback"""
    print("\nGenerating HTML documentation...")
    
    docs_dir = Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resource Manager UI Showcase</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 40px;
        }}
        .feature {{
            background: white;
            padding: 30px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .feature h3 {{
            color: #007bff;
            margin-top: 0;
        }}
        .feature ul {{
            line-height: 1.8;
        }}
        .note {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        .button {{
            display: inline-block;
            background: #007bff;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 5px;
            margin: 10px 10px 10px 0;
        }}
        .button:hover {{
            background: #0056b3;
        }}
    </style>
</head>
<body>
    <h1>🎨 Resource Manager UI Showcase</h1>
    
    <div class="note">
        <strong>Note:</strong> To view the Resource Manager in action, start the application and navigate to 
        <code>http://localhost:{port}</code> and click on the "📦 Resource Manager" tab.
    </div>
    
    <h2>Key Features</h2>
    
    <div class="feature">
        <h3>📦 Resource Library</h3>
        <ul>
            <li>Browse 10+ curated resources in a visual grid layout</li>
            <li>View resource cards with thumbnails, tags, and metadata</li>
            <li>See resource type badges (workflow, lora, checkpoint, etc.)</li>
            <li>Quick access to download commands and dependencies</li>
        </ul>
    </div>
    
    <div class="feature">
        <h3>🔍 Smart Filtering</h3>
        <ul>
            <li><strong>Ecosystem Filter:</strong> FLUX, SDXL, WAN, SD 1.5, RealESRGAN</li>
            <li><strong>Type Filter:</strong> Workflows, LoRAs, Checkpoints, VAEs, Upscalers</li>
            <li><strong>Search:</strong> Full-text search across titles and descriptions</li>
            <li><strong>Clear Filters:</strong> Reset all filters with one click</li>
        </ul>
    </div>
    
    <div class="feature">
        <h3>✨ Resource Cards</h3>
        <ul>
            <li>Preview images with 16:9 aspect ratio</li>
            <li>Ecosystem and type tags with color coding</li>
            <li>File size display (when available)</li>
            <li>Dependency warnings</li>
            <li>"View Details" button for full description</li>
            <li>"Select" button for batch operations</li>
        </ul>
    </div>
    
    <div class="feature">
        <h3>⚡ Quick Installation</h3>
        <ul>
            <li>Multi-select resources for batch installation</li>
            <li>Selection counter with total size calculation</li>
            <li>SSH connection string input</li>
            <li>"Install Selected" button for deployment</li>
            <li>Real-time feedback on installation status</li>
        </ul>
    </div>
    
    <div class="feature">
        <h3>🎨 Modern Design</h3>
        <ul>
            <li>Responsive grid layout (auto-adjusts to screen size)</li>
            <li>Card hover effects with elevation</li>
            <li>Clean, minimalist interface</li>
            <li>Color-coded tags for easy identification</li>
            <li>Mobile-friendly design</li>
        </ul>
    </div>
    
    <h2>Sample Resources Available</h2>
    
    <div class="feature">
        <h3>Workflows (3)</h3>
        <ul>
            <li><strong>WAN 2.2 I2V:</strong> Image-to-Video workflow for WAN 2.2</li>
            <li><strong>FLUX Schnell T2I:</strong> Fast text-to-image with FLUX</li>
            <li><strong>SD 1.5 Img2Img:</strong> Classic image-to-image workflow</li>
        </ul>
    </div>
    
    <div class="feature">
        <h3>LoRAs (3)</h3>
        <ul>
            <li><strong>WAN FusionX:</strong> Style LoRA for WAN 2.1</li>
            <li><strong>FLUX Realism:</strong> Photorealistic enhancement</li>
            <li><strong>SDXL Anime:</strong> Anime style for SDXL</li>
        </ul>
    </div>
    
    <div class="feature">
        <h3>Upscalers (2)</h3>
        <ul>
            <li><strong>RealESRGAN x4plus:</strong> General 4x upscaling</li>
            <li><strong>RealESRGAN Anime:</strong> Anime-optimized upscaling</li>
        </ul>
    </div>
    
    <div class="feature">
        <h3>Models (2)</h3>
        <ul>
            <li><strong>SDXL Base 1.0:</strong> Official SDXL checkpoint</li>
            <li><strong>SDXL VAE:</strong> High-quality VAE encoder</li>
        </ul>
    </div>
    
    <h2>Quick Start Guide</h2>
    
    <div class="feature">
        <ol>
            <li>Start the application: <code>docker-compose up -d</code></li>
            <li>Navigate to <code>http://localhost:5000</code></li>
            <li>Click the "📦 Resource Manager" tab</li>
            <li>Browse resources using filters or search</li>
            <li>Select desired resources</li>
            <li>Enter SSH connection string (e.g., <code>root@host:port</code>)</li>
            <li>Click "Install Selected" to deploy</li>
        </ol>
    </div>
    
    <h2>API Endpoints</h2>
    
    <div class="feature">
        <h3>Available Endpoints:</h3>
        <ul>
            <li><code>GET /resources/list</code> - List all resources with filtering</li>
            <li><code>GET /resources/get/&lt;path&gt;</code> - Get specific resource details</li>
            <li><code>POST /resources/install</code> - Install resources to remote instance</li>
            <li><code>GET /resources/ecosystems</code> - List all ecosystems</li>
            <li><code>GET /resources/types</code> - List all resource types</li>
            <li><code>GET /resources/tags</code> - List all tags</li>
            <li><code>GET /resources/search?q=query</code> - Search resources</li>
        </ul>
    </div>
    
    <div style="text-align: center; margin: 40px 0;">
        <a href="http://localhost:{port}" class="button">🚀 Open Resource Manager</a>
        <a href="../README.md" class="button">📖 Read Documentation</a>
    </div>
    
    <hr style="margin: 40px 0; border: none; border-top: 1px solid #ddd;">
    
    <p style="text-align: center; color: #888;">
        Resource Manager v1.0 | Built with Flask + JavaScript
    </p>
</body>
</html>
"""
    
    with open(docs_dir / "resource_manager_showcase.html", 'w') as f:
        f.write(html_content)
    
    print(f"✓ HTML showcase saved to {docs_dir}/resource_manager_showcase.html")
    return True


def main():
    """Main function to generate UI screenshots"""
    print("=" * 70)
    print("RESOURCE MANAGER UI SCREENSHOT GENERATOR")
    print("=" * 70)
    
    port = 5556
    server_process = None
    
    try:
        # Start server
        server_process = start_server(port)
        if not server_process:
            print("\n✗ Could not start server, aborting screenshot generation")
            return 1
        
        time.sleep(2)  # Give server time to fully initialize
        
        # Try to capture screenshots with Playwright
        if PLAYWRIGHT_AVAILABLE:
            success = capture_screenshots_playwright(port)
            if not success:
                print("\nFalling back to HTML documentation...")
                generate_html_screenshot_fallback(port)
        else:
            print("\nPlaywright not available, generating HTML documentation...")
            generate_html_screenshot_fallback(port)
        
        print("\n" + "=" * 70)
        print("SCREENSHOT GENERATION COMPLETE")
        print("=" * 70)
        print(f"\nTo view the Resource Manager:")
        print(f"1. Ensure the server is running")
        print(f"2. Navigate to http://localhost:5000")
        print(f"3. Click the '📦 Resource Manager' tab")
        print("=" * 70)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if server_process:
            server_process.terminate()
            server_process.wait(timeout=5)
            print("\n✓ Server stopped")


if __name__ == '__main__':
    sys.exit(main())
