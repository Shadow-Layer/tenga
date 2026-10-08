"""Simplified custom Swagger UI with quick start guide."""

from fastapi.responses import HTMLResponse

def get_swagger_ui_with_guide(app) -> HTMLResponse:
    """Return simplified Swagger UI with quick start guide."""
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tenga Inventory POS - API</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f8f9fa;
        }
        
        .page {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            background: linear-gradient(135deg, #0066cc 0%, #0052a3 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 28px;
            margin-bottom: 8px;
        }
        
        .header p {
            font-size: 14px;
            opacity: 0.9;
        }
        
        .intro {
            background: white;
            padding: 30px;
            margin: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .intro h2 {
            color: #333;
            margin-bottom: 12px;
            font-size: 18px;
        }
        
        .intro p {
            color: #666;
            line-height: 1.6;
            margin-bottom: 12px;
        }
        
        .creds {
            background: #f0f4f8;
            border-left: 4px solid #0066cc;
            padding: 12px;
            border-radius: 4px;
            font-size: 13px;
            font-family: monospace;
            color: #333;
            margin-top: 12px;
        }
        
        .steps-container {
            padding: 20px;
        }
        
        .step {
            background: white;
            margin-bottom: 16px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            overflow: hidden;
            transition: transform 0.2s;
        }
        
        .step:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .step-header {
            background: #f5f5f5;
            padding: 16px 20px;
            border-left: 4px solid #0066cc;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .step-header:hover {
            background: #ebebeb;
        }
        
        .step-title {
            font-weight: 600;
            color: #333;
            font-size: 15px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .step-number {
            display: inline-block;
            width: 28px;
            height: 28px;
            line-height: 28px;
            text-align: center;
            background: #0066cc;
            color: white;
            border-radius: 50%;
            font-weight: bold;
            font-size: 13px;
        }
        
        .step-content {
            display: none;
            padding: 20px;
            border-top: 1px solid #e0e0e0;
        }
        
        .step.open .step-content {
            display: block;
        }
        
        .step-body {
            color: #555;
            line-height: 1.6;
            font-size: 14px;
        }
        
        .step-body p {
            margin-bottom: 12px;
        }
        
        .endpoint {
            background: #f0f4f8;
            border-left: 4px solid #0066cc;
            padding: 12px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 13px;
            color: #333;
            margin: 12px 0;
        }
        
        .json-box {
            background: #282c34;
            color: #abb2bf;
            padding: 16px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 12px;
            overflow-x: auto;
            line-height: 1.5;
            margin: 12px 0;
        }
        
        .try-button {
            display: inline-block;
            background: #0066cc;
            color: white;
            padding: 10px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            font-size: 14px;
            margin-top: 12px;
            transition: background 0.2s;
        }
        
        .try-button:hover {
            background: #0052a3;
        }
        
        .swagger-container {
            margin: 40px 20px 20px 20px;
        }
        
        .tip {
            background: #fffbee;
            border-left: 4px solid #ffa500;
            padding: 12px;
            border-radius: 4px;
            font-size: 13px;
            color: #333;
            margin: 12px 0;
        }
        
        .tip strong {
            color: #ff8c00;
        }
        
        .toggle-all {
            text-align: center;
            padding: 20px;
        }
        
        .toggle-button {
            background: #0066cc;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            font-size: 14px;
        }
        
        .toggle-button:hover {
            background: #0052a3;
        }
        
        #swagger-ui {
            margin: 0;
        }
    </style>
</head>
<body>
    <div class="page">
        <!-- Header -->
        <div class="header">
            <h1>🏪 Tenga Inventory POS - API Setup</h1>
            <p>Complete 8-step workflow to get up and running</p>
        </div>
        
        <!-- Introduction -->
        <div class="intro">
            <h2>Getting Started</h2>
            <p>Follow these 8 simple steps to test the complete POS workflow. Each step includes an API endpoint and example request.</p>
            <div class="creds">
Email: admin@teststore.com<br>
Password: Admin123!
            </div>
        </div>
        
        <!-- Steps -->
        <div class="steps-container">
            <div class="toggle-all">
                <button class="toggle-button" onclick="toggleAll()">Expand All Steps</button>
            </div>
            
            <!-- Step 1 -->
            <div class="step">
                <div class="step-header" onclick="this.parentElement.classList.toggle('open')">
                    <div class="step-title">
                        <span class="step-number">1</span>
                        <span>Create a Location</span>
                    </div>
                    <span>▼</span>
                </div>
                <div class="step-content">
                    <div class="step-body">
                        <p>A location is a physical store where you manage inventory and tills.</p>
                        <div class="endpoint">POST /api/v1/locations</div>
                        <div class="json-box">{
  "name": "Downtown Store",
  "code": "LOC001",
  "description": "Main location",
  "organization_id": 1
}</div>
                        <div class="tip"><strong>Tip:</strong> Save the location_id returned - you'll need it for stock and till steps.</div>
                    </div>
                </div>
            </div>
            
            <!-- Step 2 -->
            <div class="step">
                <div class="step-header" onclick="this.parentElement.classList.toggle('open')">
                    <div class="step-title">
                        <span class="step-number">2</span>
                        <span>Create a Product</span>
                    </div>
                    <span>▼</span>
                </div>
                <div class="step-content">
                    <div class="step-body">
                        <p>Add items you want to sell.</p>
                        <div class="endpoint">POST /api/v1/products</div>
                        <div class="json-box">{
  "name": "Coffee",
  "sku": "COFFEE-001",
  "category": "Beverages",
  "price": 450,
  "cost": 200,
  "organization_id": 1
}</div>
                        <div class="tip"><strong>Tip:</strong> Price is in cents (450 = $4.50). Save the product_id.</div>
                    </div>
                </div>
            </div>
            
            <!-- Step 3 -->
            <div class="step">
                <div class="step-header" onclick="this.parentElement.classList.toggle('open')">
                    <div class="step-title">
                        <span class="step-number">3</span>
                        <span>Add Stock</span>
                    </div>
                    <span>▼</span>
                </div>
                <div class="step-content">
                    <div class="step-body">
                        <p>Set inventory levels at your location.</p>
                        <div class="endpoint">POST /api/v1/stock/stock/adjust?organization_id=1</div>
                        <div class="json-box">{
  "product_id": 1,
  "location_id": 1,
  "quantity": 100,
  "reason": "PHYSICAL_COUNT_DISCREPANCY",
  "recorded_by_id": 2
}</div>
                        <div class="tip"><strong>Tip:</strong> Include organization_id in the URL query parameter.</div>
                    </div>
                </div>
            </div>
            
            <!-- Step 4 -->
            <div class="step">
                <div class="step-header" onclick="this.parentElement.classList.toggle('open')">
                    <div class="step-title">
                        <span class="step-number">4</span>
                        <span>Create a Till</span>
                    </div>
                    <span>▼</span>
                </div>
                <div class="step-content">
                    <div class="step-body">
                        <p>Set up a cash register at your location.</p>
                        <div class="endpoint">POST /api/v1/tills</div>
                        <div class="json-box">{
  "organization_id": 1,
  "location_id": 1,
  "code": "TILL001",
  "name": "Front Register"
}</div>
                        <div class="tip"><strong>Tip:</strong> Save the till_id for session management.</div>
                    </div>
                </div>
            </div>
            
            <!-- Step 5 -->
            <div class="step">
                <div class="step-header" onclick="this.parentElement.classList.toggle('open')">
                    <div class="step-title">
                        <span class="step-number">5</span>
                        <span>Open Till Session</span>
                    </div>
                    <span>▼</span>
                </div>
                <div class="step-content">
                    <div class="step-body">
                        <p>Start a till session with opening cash balance.</p>
                        <div class="endpoint">POST /api/v1/tills/{till_id}/open</div>
                        <div class="json-box">{
  "user_id": 2,
  "opening_balance_cents": 50000
}</div>
                        <div class="tip"><strong>Tip:</strong> Opening balance in cents (50000 = $500.00). Replace {till_id} with your ID.</div>
                    </div>
                </div>
            </div>
            
            <!-- Step 6 -->
            <div class="step">
                <div class="step-header" onclick="this.parentElement.classList.toggle('open')">
                    <div class="step-title">
                        <span class="step-number">6</span>
                        <span>Process a Sale</span>
                    </div>
                    <span>▼</span>
                </div>
                <div class="step-content">
                    <div class="step-body">
                        <p>Record a transaction. Stock automatically deducts.</p>
                        <div class="endpoint">POST /api/v1/sales</div>
                        <div class="json-box">{
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
  "is_offline": false
}</div>
                        <div class="tip"><strong>Tip:</strong> Stock deducts automatically. Save the sale_id.</div>
                    </div>
                </div>
            </div>
            
            <!-- Step 7 -->
            <div class="step">
                <div class="step-header" onclick="this.parentElement.classList.toggle('open')">
                    <div class="step-title">
                        <span class="step-number">7</span>
                        <span>Verify Stock</span>
                    </div>
                    <span>▼</span>
                </div>
                <div class="step-content">
                    <div class="step-body">
                        <p>Check that inventory was deducted correctly.</p>
                        <div class="endpoint">GET /api/v1/stock/locations/{location_id}/stock</div>
                        <p style="margin-top: 12px;">Replace {location_id} with your ID. You should see reduced quantity (100 - 2 = 98).</p>
                        <div class="tip"><strong>Tip:</strong> This verifies the sale correctly updated inventory.</div>
                    </div>
                </div>
            </div>
            
            <!-- Step 8 -->
            <div class="step">
                <div class="step-header" onclick="this.parentElement.classList.toggle('open')">
                    <div class="step-title">
                        <span class="step-number">8</span>
                        <span>Close Till Session</span>
                    </div>
                    <span>▼</span>
                </div>
                <div class="step-content">
                    <div class="step-body">
                        <p>Finalize the till session with closing cash amount.</p>
                        <div class="endpoint">POST /api/v1/tills/{till_id}/close</div>
                        <div class="json-box">{
  "user_id": 2,
  "closing_amount_cents": 51250,
  "notes": "End of shift"
}</div>
                        <div class="tip"><strong>Tip:</strong> Closing amount should be opening ($500) + sales ($9) = $509. Replace {till_id} with your ID.</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Swagger UI -->
        <div class="swagger-container">
            <h2 style="color: #333; margin-bottom: 20px; text-align: center;">📚 Full API Documentation</h2>
            <div id="swagger-ui"></div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-bundle.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@3/swagger-ui-standalone-preset.js"></script>
    
    <script>
        function toggleAll() {
            const steps = document.querySelectorAll('.step');
            const allOpen = Array.from(steps).every(step => step.classList.contains('open'));
            
            steps.forEach(step => {
                if (allOpen) {
                    step.classList.remove('open');
                } else {
                    step.classList.add('open');
                }
            });
        }
        
        window.addEventListener('load', function() {
            SwaggerUIBundle({
                url: "/openapi.json",
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                layout: "StandaloneLayout"
            });
        });
    </script>
</body>
</html>
""")
