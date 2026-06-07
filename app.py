import os
import sqlite3
import urllib.parse
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from database import initialize_database, DB_NAME
from engine import run_aegis_flow_engine

app = FastAPI()

if not os.path.exists(DB_NAME):
    initialize_database()

def get_clean_inventory_html():
    """Fetches inventory data and turns it into a human-readable clean table."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, current_stock, critical_threshold, unit FROM inventory")
    rows = cursor.fetchall()
    conn.close()

    html = "<table class='google-table'><thead><tr><th>Medical Item</th><th>Available Amount</th><th>Safety Alert Status</th></tr></thead><tbody>"
    for name, stock, threshold, unit in rows:
        # Determine status flag
        status_badge = "<span class='badge-good'>● Safe Level</span>"
        if stock <= (threshold / 2):
            status_badge = "<span class='badge-alert'>● Critical Shortage</span>"
        elif stock < threshold:
            status_badge = "<span class='badge-warn'>● Running Low</span>"

        html += f"<tr><td><strong>{name}</strong></td><td>{stock} {unit}</td><td>{status_badge}</td></tr>"
    html += "</tbody></table>"
    return html

def get_clean_network_html():
    """Fetches regional network hubs and presents them clearly without technical keys."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Pulling real local hospitals that match the updated database seed
    cursor.execute("SELECT hospital_name, location_hub, distance_km, current_traffic_delay_min FROM neighboring_hospitals LIMIT 4")
    rows = cursor.fetchall()
    conn.close()

    html = "<table class='google-table'><thead><tr><th>Hospital Partner</th><th>Region Hub</th><th>Distance</th><th>Traffic Delay</th></tr></thead><tbody>"
    for name, hub, distance, delay in rows:
        delay_text = f"{delay} mins" if delay > 0 else "Clear Route"
        html += f"<tr><td><strong>{name}</strong></td><td>{hub}</td><td>{distance} km</td><td>{delay_text}</td></tr>"
    html += "</tbody></table>"
    return html

@app.get("/", response_class=HTMLResponse)
async def render_dashboard(result: str = None, error: str = None):
    inventory_table = get_clean_inventory_html()
    network_table = get_clean_network_html()

    output_panel_html = ""
    if result:
        try:
            data = eval(urllib.parse.unquote(result))
            
            # Translate technical execution logs to human-friendly checklist items
            friendly_steps = ""
            for log in data['execution_logs']:
                if "Intent" in log:
                    friendly_steps += "<div class='step-item'>🔍 Identified target item requirement from incoming request.</div>"
                elif "RAG" in log or "Protocol" in log:
                    friendly_steps += "<div class='step-item'>📖 Checked medical guidelines and regional delivery protocol rules.</div>"
                elif "Scout" in log or "deficit" in log:
                    friendly_steps += "<div class='step-item'>🏥 Evaluated stock levels across local Hyderabad database records.</div>"
                elif "Orchestrator" in log:
                    friendly_steps += "<div class='step-item'>✨ Calculated best emergency delivery routes based on current traffic.</div>"

            output_panel_html = f"""
            <div class="bento-card col-span-2">
                <div class="card-header">📋 System Assessment Steps</div>
                <div style="margin-bottom: 24px;">{friendly_steps}</div>
                
                <div class="card-header">🛡️ Smart Emergency Dispatch Recommendation</div>
                <div class="brief-container">{data['final_orchestrated_brief'].replace('\n', '<br>')}</div>
            </div>
            """
        except Exception:
            output_panel_html = "<div class='bento-card' style='color:#EA4335;'>Could not process the emergency routing response details.</div>"
    else:
        output_panel_html = """
        <div class="bento-card col-span-2 empty-state">
            <div style="font-size: 2.5rem; margin-bottom: 12px;">🏥</div>
            <h3>System Status: Monitoring Live Networks</h3>
            <p>Select an emergency scenario on the left panel and click 'Check Availability' to see immediate transfer solutions.</p>
        </div>
        """

    html_layout = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Aegis-Flow | Medical Logistics Control Hub</title>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-main: #F8FAFC;
                --bg-card: #FFFFFF;
                --text-primary: #202124;
                --text-secondary: #5F6368;
                --google-blue: #1A73E8;
                --border-color: #DADCE0;
            }}
            body {{
                background-color: var(--bg-main);
                color: var(--text-primary);
                font-family: 'Roboto', sans-serif;
                margin: 0; padding: 24px;
                -webkit-font-smoothing: antialiased;
            }}
            .dashboard-grid {{
                display: grid;
                grid-template-columns: 360px 1fr;
                gap: 24px;
                max-width: 1440px;
                margin: 0 auto;
            }}
            .control-panel {{
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 24px;
                box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3);
                height: fit-content;
            }}
            .main-workspace {{
                display: flex;
                flex-direction: column;
                gap: 24px;
            }}
            .hero-banner {{
                background: #FFFFFF;
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 24px;
                box-shadow: 0 1px 2px 0 rgba(60,64,67,0.15);
            }}
            .hero-banner h1 {{ margin: 0 0 6px 0; font-size: 1.5rem; font-weight: 500; color: #1A73E8; }}
            .hero-banner p {{ margin: 0; color: var(--text-secondary); font-size: 0.95rem; line-height: 1.4; }}
            
            .bento-layout {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 24px;
            }}
            .bento-card {{
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 24px;
                box-shadow: 0 1px 2px 0 rgba(60,64,67,0.15);
            }}
            .col-span-2 {{ grid-column: span 2; }}
            .card-header {{
                font-size: 1.1rem;
                font-weight: 500;
                color: var(--text-primary);
                margin-bottom: 16px;
                padding-bottom: 8px;
                border-bottom: 1px solid var(--border-color);
            }}
            label {{
                font-weight: 500;
                font-size: 0.9rem;
                color: var(--text-primary);
                display: block;
                margin-bottom: 6px;
            }}
            select, input[type="password"] {{
                width: 100%; padding: 10px; margin-bottom: 20px;
                border: 1px solid var(--border-color); border-radius: 4px;
                background: #FFFFFF; color: var(--text-primary);
                box-sizing: border-box; font-size: 0.9rem; font-family: inherit;
            }}
            select:focus, input[type="password"]:focus {{
                border-color: var(--google-blue);
                outline: none;
            }}
            button {{
                background-color: var(--google-blue);
                color: white; border: none; padding: 12px 24px;
                border-radius: 4px; font-weight: 500; cursor: pointer; width: 100%;
                font-size: 0.95rem;
                box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3);
                transition: background-color 0.2s;
            }}
            button:hover {{ background-color: #1557B0; }}
            .btn-sync {{ background: #FFFFFF; color: var(--google-blue); border: 1px solid var(--border-color); box-shadow: none; margin-top: 8px; }}
            .btn-sync:hover {{ background: #F8FAFC; }}
            
            /* Clean Google Material styled tables */
            .google-table {{ width: 100%; border-collapse: collapse; margin-top: 4px; font-size: 0.9rem; }}
            .google-table th {{ color: var(--text-secondary); font-weight: 500; padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border-color); background: #F8FAFC; }}
            .google-table td {{ padding: 14px 16px; border-bottom: 1px solid var(--border-color); color: var(--text-primary); }}
            
            /* Status Indicators */
            .badge-good {{ color: #137333; background: #E6F4EA; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 500; }}
            .badge-warn {{ color: #B06000; background: #FEF7E0; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 500; }}
            .badge-alert {{ color: #C5221F; background: #FCE8E6; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 500; }}
            
            .step-item {{ font-size: 0.95rem; margin-bottom: 8px; color: #137333; display: flex; align-items: center; gap: 8px; }}
            .brief-container {{
                background: #E8F0FE; border-left: 4px solid var(--google-blue);
                padding: 16px; border-radius: 4px; color: #1C3D5A;
                font-size: 0.95rem; line-height: 1.6;
            }}
            .empty-state {{ text-align: center; padding: 40px 20px; color: var(--text-secondary); }}
            .empty-state h3 {{ margin: 0 0 6px 0; color: var(--text-primary); font-weight: 400; }}
        </style>
    </head>
    <body>
        <div class="dashboard-grid">
            <!-- LEFT CONTROL PANEL -->
            <div class="control-panel">
                <div style="font-size: 1rem; font-weight: 500; margin-bottom: 20px; color: var(--google-blue); letter-spacing: 0.5px;">🏥 MANAGEMENT CENTER</div>
                
                <form action="/run-analytics" method="post">
                    <label for="scenario">Select Emergency Scenario</label>
                    <select name="user_query" id="scenario">
                        <option value="TRAUMA ROOM 1 EMERGENCY: Patient experiencing massive blood loss, urgent demand for 4 units of O-Negative Blood. Check asset bank balance immediately.">Hyderabad Trauma Center: 4 Units O-Neg Blood Required</option>
                        <option value="AUTOMATED REPORT: Local stock of Epinephrine 1mg/mL is running dangerously low. Predict depletion curve and scan routing networks for supply dispatch.">Secunderabad Hub: Epinephrine Stock Level Running Low</option>
                    </select>
                    
                    <label for="token">OpenAI Key Overlay (Optional)</label>
                    <input type="password" name="api_key_override" placeholder="Enter proxy token key if needed..." id="token">

                    <button type="submit">Check Partner Hospital Availability</button>
                </form>

                <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 20px 0;">
                
                <form action="/sync-db" method="post">
                    <button type="submit" class="btn-sync">Reset & Refresh Database Info</button>
                </form>
            </div>

            <!-- RIGHT WORKSPACE MAIN CANVAS -->
            <div class="main-workspace">
                <div class="hero-banner">
                    <h1>Aegis-Flow Logistics Command</h1>
                    <p>Live regional monitoring portal coordinating backup supply lines and medical logistics for critical care items across Hyderabad networks.</p>
                </div>

                {f"<div style='background: #FCE8E6; border: 1px solid #FAD2CF; padding: 12px; border-radius: 4px; color: #C5221F; font-size: 0.9rem; margin-bottom: 4px;'>{error}</div>" if error else ""}

                <div class="bento-layout">
                    <!-- DYNAMIC AGENT RESULT SECTORS -->
                    {output_panel_html}

                    <!-- STOCK PROFILE CARD -->
                    <div class="bento-card">
                        <div class="card-header">📍 Local Stock Inventory (Hyderabad Hub)</div>
                        <div style="overflow-x: auto;">{inventory_table}</div>
                    </div>

                    <!-- ROUTING INTERFACES CARD -->
                    <div class="bento-card">
                        <div class="card-header">🌐 Connected Regional Medical Centers</div>
                        <div style="overflow-x: auto;">{network_table}</div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html_layout

@app.post("/run-analytics")
async def handle_pipeline(user_query: str = Form(...), api_key_override: str = Form(None)):
    if api_key_override and api_key_override.strip() != "":
        os.environ["OPENAI_API_KEY"] = api_key_override.strip()
    
    if not os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") == "mock-key-for-ui":
        err_msg = urllib.parse.quote("Please enter your OpenAI API Key token in the form field on the left to activate routing analysis.")
        return RedirectResponse(url=f"/?error={err_msg}", status_code=303)

    output_state = run_aegis_flow_engine(user_query)
    stringified_payload = urllib.parse.quote(str(output_state))
    return RedirectResponse(url=f"/?result={stringified_payload}", status_code=303)

@app.post("/sync-db")
async def sync_database():
    initialize_database()
    return RedirectResponse(url="/", status_code=303)