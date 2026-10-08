"""Custom Swagger UI with integrated quick start guide."""

from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

def get_swagger_ui_with_guide(app: FastAPI) -> HTMLResponse:
    """Return custom Swagger UI HTML with integrated quick start guide."""
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tenga Inventory POS - API Documentation</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
        }
        
        .container {
            display: grid;
            grid-template-columns: 350px 1fr;
            height: 100vh;
            overflow: hidden;
        }
        
        .sidebar {
            background: white;
            border-right: 1px solid #e0e0e0;
            overflow-y: auto;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .sidebar-header {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #333;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .sidebar-header::before {
            content: "📚";
            font-size: 20px;
        }
        
        .guide-section {
            margin-bottom: 16px;
        }
        
        .step-item {
            padding: 12px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            border-left: 3px solid #ddd;
            margin-bottom: 8px;
            font-size: 14px;
        }
        
        .step-item:hover {
            background: #f0f0f0;
            border-left-color: #0066cc;
        }
        
        .step-item.active {
            background: #e3f2fd;
            border-left-color: #0066cc;
            font-weight: 600;
        }
        
        .step-number {
            display: inline-block;
            width: 24px;
            height: 24px;
            line-height: 24px;
            text-align: center;
            background: #0066cc;
            color: white;
            border-radius: 50%;
            font-size: 12px;
            font-weight: bold;
            margin-right: 8px;
        }
        
        .main-content {
            display: grid;
            grid-template-rows: auto 1fr;
            overflow: hidden;
        }
        
        .tabs-header {
            background: white;
            border-bottom: 2px solid #e0e0e0;
            display: flex;
            padding: 0;
            overflow-x: auto;
        }
        
        .tab-button {
            padding: 16px 24px;
            border: none;
            background: none;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            color: #666;
            border-bottom: 3px solid transparent;
            transition: all 0.2s;
            white-space: nowrap;
        }
        
        .tab-button:hover {
            color: #333;
            background: #f9f9f9;
        }
        
        .tab-button.active {
            color: #0066cc;
            border-bottom-color: #0066cc;
        }
        
        .tabs-content {
            overflow: auto;
            background: white;
        }
        
        .tab-pane {
            display: none;
            padding: 20px;
            height: 100%;
        }
        
        .tab-pane.active {
            display: block;
        }
        
        #swagger-ui {
            max-width: 100%;
        }
        
        .guide-content {
            max-width: 900px;
            margin: 0 auto;
        }
        
        .step-detail {
            background: #f9f9f9;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .step-detail h3 {
            color: #0066cc;
            margin-bottom: 12px;
            font-size: 18px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .step-detail p {
            color: #555;
            line-height: 1.6;
            margin-bottom: 12px;
        }
        
        .api-info {
            background: #f0f4f8;
            border-left: 4px solid #0066cc;
            padding: 12px;
            border-radius: 4px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            color: #333;
            margin: 12px 0;
            overflow-x: auto;
        }
        
        .code-block {
            background: #282c34;
            color: #abb2bf;
            padding: 16px;
            border-radius: 6px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            margin: 12px 0;
            overflow-x: auto;
            line-height: 1.5;
        }
        
        .code-block .keyword { color: #c678dd; }
        .code-block .string { color: #98c379; }
        .code-block .number { color: #d19a66; }
        
        .example-request {
            background: white;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 12px;
            margin: 12px 0;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 12px;
            overflow-x: auto;
        }
        
        .try-it-button {
            display: inline-block;
            background: #0066cc;
            color: white;
            padding: 10px 16px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 500;
            margin-top: 12px;
            transition: background 0.2s;
        }
        
        .try-it-button:hover {
            background: #0052a3;
        }
        
        .checklist {
            background: white;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 16px;
            margin: 20px 0;
        }
        
        .checklist h4 {
            margin-bottom: 12px;
            color: #333;
        }
        
        .checklist-item {
            display: flex;
            align-items: center;
            padding: 8px 0;
            color: #555;
            font-size: 14px;
        }
        
        .checklist-item::before {
            content: "☐";
            margin-right: 8px;
            font-size: 16px;
            color: #0066cc;
            font-weight: bold;
        }
        
        .phase-box {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 16px;
            margin: 12px 0;
        }
        
        .phase-box h5 {
            color: #0066cc;
            margin-bottom: 8px;
            font-size: 14px;
            font-weight: 600;
        }
        
        .phase-box ul {
            margin-left: 20px;
            font-size: 13px;
            color: #555;
        }
        
        .phase-box li {
            margin: 4px 0;
        }
        
        .info-box {
            background: #e3f2fd;
            border-left: 4px solid #0066cc;
            padding: 12px;
            border-radius: 4px;
            margin: 12px 0;
            font-size: 14px;
            color: #1565c0;
        }
        
        .info-box strong {
            color: #0d47a1;
        }
        
        @media (max-width: 768px) {
            .container {
                grid-template-columns: 1fr;
            }
            
            .sidebar {
                display: none;
            }
        }
        
        @media (max-width: 1024px) {
            .container {
                grid-template-columns: 280px 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Sidebar Navigation -->
        <div class="sidebar">
            <div class="sidebar-header">Quick Start</div>
            <div class="guide-section">
                <div class="step-item active" onclick="showGuide(0)" data-step="0">
                    <span class="step-number">1</span>
                    <span>Create Location</span>
                </div>
                <div class="step-item" onclick="showGuide(1)" data-step="1">
                    <span class="step-number">2</span>
                    <span>Create Product</span>
                </div>
                <div class="step-item" onclick="showGuide(2)" data-step="2">
                    <span class="step-number">3</span>
                    <span>Add Stock</span>
                </div>
                <div class="step-item" onclick="showGuide(3)" data-step="3">
                    <span class="step-number">4</span>
                    <span>Create Till</span>
                </div>
                <div class="step-item" onclick="showGuide(4)" data-step="4">
                    <span class="step-number">5</span>
                    <span>Open Session</span>
                </div>
                <div class="step-item" onclick="showGuide(5)" data-step="5">
                    <span class="step-number">6</span>
                    <span>Process Sale</span>
                </div>
                <div class="step-item" onclick="showGuide(6)" data-step="6">
                    <span class="step-number">7</span>
                    <span>Verify Stock</span>
                </div>
                <div class="step-item" onclick="showGuide(7)" data-step="7">
                    <span class="step-number">8</span>
                    <span>Close Till</span>
                </div>
            </div>
            
            <hr style="margin: 20px 0; border: none; border-top: 1px solid #e0e0e0;">
            
            <div style="font-size: 12px; color: #666; line-height: 1.6;">
                <p style="font-weight: 600; margin-bottom: 8px;">Demo Credentials</p>
                <p><strong>Admin:</strong></p>
                <p style="font-size: 11px; margin-bottom: 8px;">admin@teststore.com<br>Admin123!</p>
                <p><strong>Cashier:</strong></p>
                <p style="font-size: 11px;">cashier@teststore.com<br>Cashier123!</p>
            </div>
        </div>
        
        <!-- Main Content -->
        <div class="main-content">
            <div class="tabs-header">
                <button class="tab-button active" onclick="switchTab('guide')">📖 Quick Start</button>
                <button class="tab-button" onclick="switchTab('api')">🔌 API Docs</button>
            </div>
            
            <div class="tabs-content">
                <!-- Quick Start Tab -->
                <div id="guide" class="tab-pane active">
                    <div class="guide-content">
                        <h2 style="margin-bottom: 20px; color: #333;">Tenga Inventory POS - Quick Start Guide</h2>
                        
                        <div id="step-0" class="step-detail" style="display: block;">
                            <h3>📍 Step 1: Create a Location</h3>
                            <p>A location represents a physical store or warehouse where you manage inventory and tills.</p>
                            <div class="api-info">POST /api/v1/locations</div>
                            <div class="example-request">{
  "name": "Downtown Store",
  "code": "LOC001",
  "description": "Main retail location",
  "organization_id": 1
}</div>
                            <a href="javascript:scrollToEndpoint('post-locations')" class="try-it-button">Try it in Swagger →</a>
                            <div class="info-box">💡 <strong>Tip:</strong> You'll use location_id in subsequent steps for stock and till management.</div>
                        </div>
                        
                        <div id="step-1" class="step-detail" style="display: none;">
                            <h3>📦 Step 2: Create a Product</h3>
                            <p>Add items that you want to sell - coffee, tea, snacks, etc.</p>
                            <div class="api-info">POST /api/v1/products</div>
                            <div class="example-request">{
  "name": "Premium Coffee",
  "sku": "COFFEE-001",
  "category": "Beverages",
  "price": 450,
  "cost": 200,
  "organization_id": 1
}</div>
                            <a href="javascript:scrollToEndpoint('post-products')" class="try-it-button">Try it in Swagger →</a>
                            <div class="info-box">💡 <strong>Tip:</strong> Price is in cents (450 = \$4.50). Record the product_id for later steps.</div>
                        </div>
                        
                        <div id="step-2" class="step-detail" style="display: none;">
                            <h3>📊 Step 3: Add Stock to Location</h3>
                            <p>Set initial inventory levels for your products at this location.</p>
                            <div class="api-info">POST /api/v1/stock/stock/adjust?organization_id=1</div>
                            <div class="example-request">{
  "product_id": 1,
  "location_id": 1,
  "quantity": 100,
  "reason": "PHYSICAL_COUNT_DISCREPANCY",
  "recorded_by_id": 2
}</div>
                            <a href="javascript:scrollToEndpoint('post-stock')" class="try-it-button">Try it in Swagger →</a>
                            <div class="info-box">💡 <strong>Tip:</strong> Valid reasons: PHYSICAL_COUNT_DISCREPANCY, DAMAGE, SHRINKAGE, ADJUSTMENT. Include organization_id as query parameter.</div>
                        </div>
                        
                        <div id="step-3" class="step-detail" style="display: none;">
                            <h3>💳 Step 4: Create a Till</h3>
                            <p>Set up a cash register (physical device or terminal) at your location.</p>
                            <div class="api-info">POST /api/v1/tills</div>
                            <div class="example-request">{
  "organization_id": 1,
  "location_id": 1,
  "code": "TILL001",
  "name": "Front Register"
}</div>
                            <a href="javascript:scrollToEndpoint('post-tills')" class="try-it-button">Try it in Swagger →</a>
                            <div class="info-box">💡 <strong>Tip:</strong> Include organization_id in the request body. Record the till_id for session management.</div>
                        </div>
                        
                        <div id="step-4" class="step-detail" style="display: none;">
                            <h3>🔓 Step 5: Open Till Session</h3>
                            <p>Start a till session with an opening cash balance (in cents).</p>
                            <div class="api-info">POST /api/v1/tills/{till_id}/open</div>
                            <div class="example-request">{
  "user_id": 2,
  "opening_balance_cents": 50000
}</div>
                            <a href="javascript:scrollToEndpoint('post-tills-open')" class="try-it-button">Try it in Swagger →</a>
                            <div class="info-box">💡 <strong>Tip:</strong> Opening balance is in cents (50000 = \$500.00). Replace {till_id} with your till ID from step 4.</div>
                        </div>
                        
                        <div id="step-5" class="step-detail" style="display: none;">
                            <h3>💰 Step 6: Process a Sale</h3>
                            <p>Record a transaction with products, quantities, and payment method.</p>
                            <div class="api-info">POST /api/v1/sales</div>
                            <div class="example-request">{
  "till_id": 1,
  "cashier_id": 2,
  "payment_method": "cash",
  "items": [
    {
      "product_id": 1,
      "quantity": 2,
      "unit_price": 450
    }
  ],
  "is_offline": false,
  "notes": "Customer purchase"
}</div>
                            <a href="javascript:scrollToEndpoint('post-sales')" class="try-it-button">Try it in Swagger →</a>
                            <div class="info-box">💡 <strong>Tip:</strong> Stock is automatically deducted when the sale is processed. Total will be calculated automatically.</div>
                        </div>
                        
                        <div id="step-6" class="step-detail" style="display: none;">
                            <h3>✓ Step 7: Verify Stock Deduction</h3>
                            <p>Confirm that inventory was automatically updated after the sale.</p>
                            <div class="api-info">GET /api/v1/stock/locations/{location_id}/stock</div>
                            <p>Replace {location_id} with your location ID from step 1.</p>
                            <a href="javascript:scrollToEndpoint('get-stock')" class="try-it-button">Try it in Swagger →</a>
                            <div class="info-box">💡 <strong>Tip:</strong> If you sold 2 units and started with 100, you should see 98 units remaining.</div>
                        </div>
                        
                        <div id="step-7" class="step-detail" style="display: none;">
                            <h3>🔒 Step 8: Close Till Session</h3>
                            <p>Finalize the till session with closing balance and reconcile cash.</p>
                            <div class="api-info">POST /api/v1/tills/{till_id}/close</div>
                            <div class="example-request">{
  "user_id": 2,
  "closing_amount_cents": 51250,
  "notes": "End of shift"
}</div>
                            <a href="javascript:scrollToEndpoint('post-tills-close')" class="try-it-button">Try it in Swagger →</a>
                            <div class="info-box">💡 <strong>Tip:</strong> Closing amount should include opening balance + sales. Replace {till_id} with your till ID.</div>
                        </div>
                        
                        <div style="margin-top: 40px; padding: 20px; background: #f0f7ff; border-radius: 8px; border-left: 4px solid #0066cc;">
                            <h4 style="color: #0d47a1; margin-bottom: 12px;">✅ Testing Checklist</h4>
                            <div class="phase-box">
                                <h5>Setup Phase</h5>
                                <ul>
                                    <li>Create 1 location</li>
                                    <li>Create 2 products</li>
                                    <li>Add stock to location</li>
                                    <li>Create 1 till</li>
                                </ul>
                            </div>
                            <div class="phase-box">
                                <h5>Operations Phase</h5>
                                <ul>
                                    <li>Open till session</li>
                                    <li>Process multiple sales</li>
                                    <li>Track inventory</li>
                                </ul>
                            </div>
                            <div class="phase-box">
                                <h5>Verification Phase</h5>
                                <ul>
                                    <li>Verify stock deductions</li>
                                    <li>Check till reconciliation</li>
                                    <li>View sale history</li>
                                    <li>Close till session</li>
                                </ul>
                            </div>
                        </div>
                        
                        <div style="margin-top: 30px; text-align: center; color: #999; font-size: 12px;">
                            <p>💡 Click the <strong>"Try it in Swagger"</strong> buttons above to test each endpoint interactively!</p>
                            <p style="margin-top: 8px;">All endpoints require Bearer token authentication (login first).</p>
                        </div>
                    </div>
                </div>
                
                <!-- API Docs Tab -->
                <div id="api" class="tab-pane">
                    <div id="swagger-ui"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-bundle.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-standalone-preset.js"></script>
    
    <script>
        let swaggerUI;
        
        function switchTab(tab) {
            // Hide all tab panes
            document.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.remove('active');
            });
            
            // Deactivate all tab buttons
            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tab).classList.add('active');
            event.target.classList.add('active');
            
            // Initialize Swagger UI on first access
            if (tab === 'api' && !swaggerUI) {
                initSwaggerUI();
            }
        }
        
        function showGuide(stepIndex) {
            // Hide all steps
            document.querySelectorAll('[id^="step-"]').forEach(step => {
                step.style.display = 'none';
            });
            
            // Deactivate all step items
            document.querySelectorAll('.step-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Show selected step
            document.getElementById('step-' + stepIndex).style.display = 'block';
            document.querySelector('[data-step="' + stepIndex + '"]').classList.add('active');
            
            // Scroll to top
            document.querySelector('.tabs-content').scrollTop = 0;
        }
        
        function scrollToEndpoint(endpoint) {
            // Switch to API tab
            switchTab('api');
            
            // Give Swagger UI time to render
            setTimeout(() => {
                const element = document.querySelector('[data-name="' + endpoint + '"]');
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }, 100);
        }
        
        function initSwaggerUI() {
            swaggerUI = SwaggerUIBundle({
                url: "/openapi.json",
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                layout: "StandaloneLayout",
                deepLinking: true,
                onFailure: function(data) {
                    console.error('Failed to load OpenAPI spec:', data);
                }
            });
        }
        
        // Initialize on page load
        window.addEventListener('load', function() {
            console.log('Tenga Inventory POS API Documentation loaded');
        });
    </script>
</body>
</html>
""")
