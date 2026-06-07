import os
import sqlite3
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.requests import Request
from database import initialize_database, DB_NAME
from engine import run_aegis_flow_engine, METRO_HUBS, haversine_distance

app = FastAPI()

# =====================================================================
# Helper Database Query Handlers for UI Tables
# =====================================================================

def get_alert_count(hub: str) -> int:
    """Calculates the number of items currently below safety threshold in the active hub."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM inventory WHERE current_stock < critical_threshold AND location_hub = ?", (hub,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_clean_inventory_html(hub: str) -> str:
    """Fetches local stock inventory for the selected hub and generates a clean table."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, current_stock, critical_threshold, unit FROM inventory WHERE location_hub = ?", (hub,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return '<div class="text-slate-400 py-6 text-center text-xs">No local ledger records discovered.</div>'

    html = """
    <table class="w-full text-left border-collapse text-xs">
        <thead>
            <tr class="border-b border-outline-variant text-on-surface-variant uppercase tracking-wider text-[10px]">
                <th class="pb-2.5 font-semibold px-2">Supply Item</th>
                <th class="pb-2.5 font-semibold px-2">Stock</th>
                <th class="pb-2.5 font-semibold text-right px-2">Status</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-outline-variant text-on-surface">
    """
    for name, stock, threshold, unit in rows:
        if stock <= (threshold / 2):
            status_badge = '<span class="px-1.5 py-0.5 text-[10px] rounded bg-rose-50 text-rose-700 font-bold border border-rose-100 shrink-0">Critical</span>'
        elif stock < threshold:
            status_badge = '<span class="px-1.5 py-0.5 text-[10px] rounded bg-amber-50 text-amber-700 font-bold border border-amber-100 shrink-0">Low</span>'
        else:
            status_badge = '<span class="px-1.5 py-0.5 text-[10px] rounded bg-emerald-50 text-emerald-700 font-bold border border-emerald-100 shrink-0">Safe</span>'

        html += f"""
        <tr class="hover:bg-surface-container transition-colors duration-150">
            <td class="py-2.5 px-2">
                <span class="font-semibold text-on-surface text-[11px]">{name}</span>
            </td>
            <td class="py-2.5 px-2 font-mono text-on-surface-variant font-medium text-[11px]">{stock} {unit}</td>
            <td class="py-2.5 px-2 text-right">{status_badge}</td>
        </tr>
        """
    html += "</tbody></table>"
    return html

def get_clean_network_html(hub: str) -> str:
    """Fetches regional network hubs relative to the active hub and presents them clearly."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT hospital_name, city, latitude, longitude, current_traffic_delay_min FROM neighboring_hospitals")
    rows = cursor.fetchall()
    conn.close()

    hub_coords = METRO_HUBS.get(hub, (17.3850, 78.4867))
    results = []
    for name, city, lat, lon, delay in rows:
        dist = haversine_distance(hub_coords, (lat, lon))
        results.append({
            "name": name,
            "city": city,
            "distance_km": round(dist, 1),
            "delay": delay
        })
        
    # Sort closest hospitals first
    results.sort(key=lambda x: x["distance_km"])
    
    html = """
    <table class="w-full text-left border-collapse text-xs">
        <thead>
            <tr class="border-b border-outline-variant text-on-surface-variant uppercase tracking-wider text-[10px]">
                <th class="pb-2.5 font-semibold">Hospital Partner</th>
                <th class="pb-2.5 font-semibold">Hub City</th>
                <th class="pb-2.5 font-semibold">Distance</th>
                <th class="pb-2.5 font-semibold text-right">Route Status</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-outline-variant text-on-surface">
    """
    # Show top 5 closest partners
    for item in results[:5]:
        name = item["name"]
        city = item["city"]
        dist = item["distance_km"]
        delay = item["delay"]
        
        if dist < 0.1:
            dist_text = "Host Hub"
            route_status = '<span class="px-2 py-0.5 text-[10px] rounded font-semibold bg-blue-50 text-blue-600 border border-blue-100">Local Facility</span>'
        elif city == hub:
            dist_text = f"{dist} km"
            # Latency Alert logic: Red/Amber based on traffic delay
            if delay >= 18:
                route_status = f'<span class="px-2 py-1 text-[10px] rounded font-bold bg-rose-50 text-rose-700 border border-rose-200 flex items-center justify-end gap-1"><span class="material-symbols-outlined text-xs shrink-0 font-bold">emergency</span>Road ({delay}m delay) 🚨 Siren Advised</span>'
            elif delay >= 12:
                route_status = f'<span class="px-2 py-1 text-[10px] rounded font-bold bg-amber-50 text-amber-700 border border-amber-200 flex items-center justify-end gap-1"><span class="material-symbols-outlined text-xs shrink-0 font-bold">warning</span>Road ({delay}m delay) ⚠️ Heavy</span>'
            else:
                route_status = f'<span class="px-2 py-0.5 text-[10px] rounded font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100">Road (Clear)</span>'
        else:
            dist_text = f"{dist} km"
            route_status = '<span class="px-2 py-0.5 text-[10px] rounded font-semibold bg-purple-50 text-purple-600 border border-purple-100">Express Air Cargo</span>'
            
        html += f"""
        <tr class="hover:bg-surface-container transition-colors duration-150">
            <td class="py-3 px-2">
                <span class="font-semibold text-on-surface">{name}</span>
            </td>
            <td class="py-3 px-2 text-on-surface-variant font-medium">{city}</td>
            <td class="py-3 px-2 font-mono text-on-surface-variant font-medium">{dist_text}</td>
            <td class="py-3 px-2 text-right">{route_status}</td>
        </tr>
        """
    html += "</tbody></table>"
    return html

def add_active_transfer(item_name: str, quantity: int, from_hospital: str, to_hub: str, eta: int, mode: str):
    """Inserts a new active shipment record into the tracking database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM active_transfers")
    count = cursor.fetchone()[0]
    transfer_id = f"TRF-{100 + count + 1}"
    
    cursor.execute(
        "INSERT INTO active_transfers VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (transfer_id, item_name, quantity, from_hospital, to_hub, "In Transit", eta, mode)
    )
    conn.commit()
    conn.close()

def get_active_transfers_html(hub: str) -> str:
    """Generates a clean HTML table of current active transfers destined for this metropolitan hub."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM active_transfers WHERE to_hub = ? OR from_hospital IN (SELECT hospital_name FROM neighboring_hospitals WHERE city = ?) ORDER BY transfer_id DESC", (hub, hub))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return '<div class="text-slate-400 py-12 text-center text-xs font-semibold">No active shipments currently registered for this hub.</div>'

    html = f"""
    <div class="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden shadow-sm">
        <div class="px-6 py-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-low/30">
            <h3 class="font-headline-sm text-headline-sm text-on-surface flex items-center gap-2">
                <span class="material-symbols-outlined text-primary">local_shipping</span>
                Active Medical Shipments & Transfers ({hub})
            </h3>
            <span class="text-[10px] font-semibold bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded border border-emerald-100 uppercase tracking-wider">Live Tracker</span>
        </div>
        <div class="overflow-x-auto">
            <table class="w-full text-left">
                <thead>
                    <tr class="bg-surface-container-low text-on-surface-variant uppercase text-[10px] tracking-wider border-b border-outline-variant">
                        <th class="px-3 py-2.5 font-semibold">Shipment ID</th>
                        <th class="px-3 py-2.5 font-semibold">Supply Item & Qty</th>
                        <th class="px-3 py-2.5 font-semibold">Origin Facility</th>
                        <th class="px-3 py-2.5 font-semibold">Destination / Route</th>
                        <th class="px-3 py-2.5 font-semibold">ETA / Duration</th>
                        <th class="px-3 py-2.5 font-semibold text-right">Status</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-outline-variant text-on-surface">
    """
    for trf_id, name, qty, origin, destination, status, eta, mode in rows:
        mode_icon = "local_shipping" if mode == "Road" else "flight"
        mode_badge = f'<span class="flex items-center gap-1.5 text-[11px] font-semibold text-on-surface-variant"><span class="material-symbols-outlined text-sm shrink-0">{mode_icon}</span>{mode}</span>'
        
        eta_text = f"{eta} mins" if eta > 0 else "Arrived"
        
        if status == "Delivered":
            status_badge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-100 uppercase">Delivered</span>'
        elif status == "Pending Departure":
            status_badge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-100 uppercase">Pending</span>'
        else:
            status_badge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-100 uppercase animate-pulse">In Transit</span>'
            
        html += f"""
        <tr class="hover:bg-surface-container transition-colors duration-150">
            <td class="px-3 py-3 font-mono-data text-mono-data text-primary font-bold">{trf_id}</td>
            <td class="px-3 py-3">
                <div class="font-body-md text-body-md font-semibold text-on-surface">{name}</div>
                <div class="text-[11px] text-on-surface-variant font-medium">Quantity: {qty} units</div>
            </td>
            <td class="px-3 py-3 font-body-md text-body-md text-on-surface-variant">{origin}</td>
            <td class="px-3 py-3 font-body-md text-body-md text-on-surface-variant">
                <div class="font-semibold">{destination} Hub</div>
                <div>{mode_badge}</div>
            </td>
            <td class="px-3 py-3 font-mono-data text-mono-data text-on-surface font-semibold">{eta_text}</td>
            <td class="px-3 py-3 text-right">{status_badge}</td>
        </tr>
        """
    html += "</tbody></table></div></div>"
    return html

# =====================================================================
# FRAME: GOOGLE STITCH DASHBOARD ENVIRONMENT HTML (REALIGNED LAYOUT)
# =====================================================================
DASHBOARD_FRAME_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1.0" name="viewport"/>
    <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #f6f9ff;
        }}
        .material-symbols-outlined {{
            font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        }}
        .custom-scrollbar::-webkit-scrollbar {{
            width: 4px;
        }}
        .custom-scrollbar::-webkit-scrollbar-track {{
            background: transparent;
        }}
        .custom-scrollbar::-webkit-scrollbar-thumb {{
            background: #e5e7eb;
            border-radius: 10px;
        }}
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {{
            background: #d1d5db;
        }}
    </style>
    <script id="tailwind-config">
        tailwind.config = {{
            darkMode: "class",
            theme: {{
                extend: {{
                    "colors": {{
                        "on-tertiary-fixed-variant": "#5f4100",
                        "on-primary-fixed": "#001b3d",
                        "surface-container": "#e0f0ff",
                        "on-tertiary": "#ffffff",
                        "on-error-container": "#93000a",
                        "inverse-on-surface": "#e6f2ff",
                        "on-secondary-fixed": "#00210a",
                        "primary-fixed": "#d6e3ff",
                        "on-secondary": "#ffffff",
                        "tertiary-container": "#7e5800",
                        "tertiary": "#604200",
                        "tertiary-fixed-dim": "#ffba2c",
                        "secondary-fixed": "#90f9a6",
                        "outline": "#727783",
                        "error": "#ba1a1a",
                        "on-primary": "#ffffff",
                        "outline-variant": "#c2c6d4",
                        "secondary-container": "#90f9a6",
                        "primary-container": "#005eb8",
                        "surface": "#f6f9ff",
                        "error-container": "#ffdad6",
                        "surface-variant": "#d4e5f5",
                        "on-secondary-fixed-variant": "#005224",
                        "on-primary-fixed-variant": "#00468c",
                        "on-primary-container": "#c8daff",
                        "surface-dim": "#cbdcec",
                        "secondary-fixed-dim": "#75dc8c",
                        "secondary": "#006d32",
                        "inverse-primary": "#a9c7ff",
                        "on-tertiary-container": "#ffd38a",
                        "surface-container-highest": "#d4e5f5",
                        "primary": "#00478d",
                        "on-error": "#ffffff",
                        "surface-tint": "#005db6",
                        "on-surface": "#0d1d29",
                        "on-surface-variant": "#424752",
                        "on-background": "#0d1d29",
                        "surface-bright": "#f6f9ff",
                        "surface-container-low": "#ebf5ff",
                        "on-secondary-container": "#007435",
                        "on-tertiary-fixed": "#271900",
                        "surface-container-high": "#d9eafa",
                        "tertiary-fixed": "#ffdeaa",
                        "inverse-surface": "#22323e",
                        "background": "#f6f9ff",
                        "primary-fixed-dim": "#a9c7ff",
                        "surface-container-lowest": "#ffffff"
                    }},
                    "borderRadius": {{
                        "DEFAULT": "0.125rem",
                        "lg": "0.25rem",
                        "xl": "0.5rem",
                        "full": "0.75rem"
                    }},
                    "spacing": {{
                        "stack-sm": "8px",
                        "stack-lg": "24px",
                        "stack-md": "16px",
                        "container-padding": "24px",
                        "gutter": "16px",
                        "unit": "4px"
                    }},
                    "fontFamily": {{
                        "body-lg": ["Inter"],
                        "headline-sm": ["Inter"],
                        "body-sm": ["Inter"],
                        "body-md": ["Inter"],
                        "label-sm": ["Inter"],
                        "headline-md": ["Inter"],
                        "headline-lg": ["Inter"],
                        "label-md": ["Inter"],
                        "mono-data": ["Inter"]
                    }},
                    "fontSize": {{
                        "body-lg": ["16px", {{"lineHeight": "24px", "fontWeight": "400"}}],
                        "headline-sm": ["20px", {{"lineHeight": "28px", "fontWeight": "600"}}],
                        "body-sm": ["13px", {{"lineHeight": "18px", "fontWeight": "400"}}],
                        "body-md": ["14px", {{"lineHeight": "20px", "fontWeight": "400"}}],
                        "label-sm": ["11px", {{"lineHeight": "14px", "fontWeight": "500"}}],
                        "headline-md": ["24px", {{"lineHeight": "32px", "letterSpacing": "-0.01em", "fontWeight": "600"}}],
                        "headline-lg": ["32px", {{"lineHeight": "40px", "letterSpacing": "-0.02em", "fontWeight": "600"}}],
                        "label-md": ["12px", {{"lineHeight": "16px", "letterSpacing": "0.05em", "fontWeight": "600"}}],
                        "mono-data": ["13px", {{"lineHeight": "18px", "letterSpacing": "-0.01em", "fontWeight": "500"}}]
                    }}
                }},
            }},
        }}
    </script>
</head>
<body class="bg-surface text-on-surface overflow-hidden h-screen flex flex-col">
<!-- TopAppBar Shell -->
<header class="bg-surface-container-lowest border-b border-outline-variant flex justify-between items-center w-full px-container-padding h-14 z-50">
<div class="flex items-center gap-6">
<span class="font-headline-sm text-headline-sm font-bold text-primary">MedLog Command</span>
<div class="hidden md:flex items-center gap-4">
<div class="flex items-center gap-2 px-3 py-1 bg-surface-container rounded-full">
<span class="w-2 h-2 rounded-full bg-secondary"></span>
<span class="font-label-md text-label-md text-on-surface">Active Hub: {selected_hub}</span>
</div>
<div class="flex items-center gap-2 px-3 py-1 bg-surface-container-low rounded-full">
<span class="w-2 h-2 rounded-full bg-tertiary"></span>
<span class="font-label-md text-label-md text-on-surface">Offline Engine Active</span>
</div>
<div class="flex items-center gap-2 px-3 py-1 bg-error-container rounded-full">
<span class="w-2 h-2 rounded-full bg-error"></span>
<span class="font-label-md text-label-md text-on-error-container">Shortage Alerts: {alert_count}</span>
</div>
</div>
</div>
<div class="flex items-center gap-3">
<div class="flex items-center gap-1">
<button class="p-2 hover:bg-surface-container-low transition-colors rounded-full cursor-pointer active:opacity-80">
<span class="material-symbols-outlined text-on-surface-variant">notifications</span>
</button>
<button class="p-2 hover:bg-surface-container-low transition-colors rounded-full cursor-pointer active:opacity-80">
<span class="material-symbols-outlined text-on-surface-variant">settings</span>
</button>
<button class="p-2 hover:bg-surface-container-low transition-colors rounded-full cursor-pointer active:opacity-80">
<span class="material-symbols-outlined text-on-surface-variant">help</span>
</button>
</div>
<div class="w-8 h-8 rounded-full bg-surface-variant border border-outline-variant flex items-center justify-center overflow-hidden">
<img alt="User Profile" class="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCpkEbDPVgb65ghtzOmkr6MkOLNMfCjhw5ydHoInEuxUChB0bGl0X7hAHk0C1XcLKq7ODapqZCvkuccM3HTztIkPWvGKqayes7MHPnTk11c5Ak3jDowtrOr1N03C3AWKR9dZg18vFv_CW0YKUwhwiaQE_0-dBwtvYidxoFEJlHxKi-kpaU5LKS0Kq_g3qQ6RynQARLih-DXFDDfuptVOR-_qbgFp_2HhidWBgCy9z15hP02k_mykfQ2och3L0m6WHdzt-naliyXi1p1"/>
</div>
</div>
</header>
<div class="flex flex-1 overflow-hidden">
<!-- SideNavBar Shell (Setup & Configuration) -->
<aside class="w-64 bg-surface-container-lowest border-r border-outline-variant flex flex-col p-stack-md shrink-0">
<div class="mb-6">
<div class="flex items-center gap-3 mb-4">
<div class="w-10 h-10 bg-primary-container rounded flex items-center justify-center">
<span class="material-symbols-outlined text-on-primary">hub</span>
</div>
<div>
<h2 class="font-label-md text-label-md text-primary font-bold">Central Command</h2>
<p class="text-[10px] text-on-surface-variant uppercase tracking-wider">Logistics Node v4.2</p>
</div>
</div>

<!-- METROPOLITAN HUB SELECTOR -->
<form id="hub-form" action="/" method="get" class="mb-4">
    <input type="hidden" name="view" value="{selected_view}">
    <label class="block text-[11px] font-bold text-outline uppercase tracking-widest px-2 mb-1.5">Metropolitan Hub</label>
    <select name="hub" onchange="document.getElementById('hub-form').submit()" class="w-full border border-outline-variant rounded-lg p-2 text-xs bg-surface-container-lowest focus:border-primary focus:ring-1 focus:ring-primary font-semibold text-on-surface">
        {hub_options}
    </select>
</form>

<hr class="border-outline-variant my-4">

<!-- ROUTING DISPATCH INITIATION -->
<form action="/?view=dashboard" method="post" class="space-y-4">
    <input type="hidden" name="active_hub" value="{selected_hub}">
    <div>
        <label class="block text-[11px] font-bold text-outline uppercase tracking-widest px-2 mb-1.5">Triage Scenario</label>
        <select name="user_input" class="w-full border border-outline-variant rounded-lg p-2 text-xs bg-surface-container-lowest focus:border-primary focus:ring-1 focus:ring-primary text-on-surface font-semibold">
            <option value="TRAUMA ROOM 1 EMERGENCY: Patient experiencing massive blood loss, urgent demand for 4 units of O-Negative Blood. Check asset bank balance immediately.">Trauma Triage: O-Neg Blood</option>
            <option value="AUTOMATED REPORT: Local stock of Epinephrine 1mg/mL is running dangerously low. Predict depletion curve and scan routing networks for supply dispatch.">Med Alert: Epinephrine Low</option>
            <option value="CRITICAL VENOM INJURY: Triage reports multiple snakebite admissions. Demand for 15 vials of Polyvalent Antivenom. Verify local levels and scan nearest partner hubs.">Snakebite: Antivenom Triage</option>
            <option value="ICU SYSTEM ALERT: Surge in respiratory admissions has depleted local stock of Ventilator Circuits. 10 units required immediately to maintain life support nodes.">ICU Alert: Ventilator Shortage</option>
            <option value="NEONATAL UNIT URGENT: Preterm infant in respiratory distress requires 5 vials of Surfactant. Local supply depleted. Search regional cold-chain transport networks.">Neonatal: Surfactant Crisis</option>
        </select>
    </div>

    <button type="submit" class="w-full bg-primary-container text-white py-2 px-4 rounded font-label-md text-label-md hover:opacity-90 transition-all active:scale-95 duration-150 flex items-center justify-center gap-2">
        <span class="material-symbols-outlined text-[18px]">bolt</span>
        Analyze Route
    </button>
</form>

</div>
<nav class="flex-1 space-y-1">
<div class="text-[11px] font-bold text-outline uppercase tracking-widest px-2 mb-2">Navigation</div>
<a class="flex items-center gap-3 px-3 py-2 {dashboard_active_classes} rounded-lg group cursor-pointer active:scale-95 duration-150" href="/?hub={selected_hub}&view=dashboard">
<span class="material-symbols-outlined">dashboard</span>
<span class="font-label-md text-label-md">Dashboard</span>
</a>
<a class="flex items-center gap-3 px-3 py-2 {transfers_active_classes} rounded-lg group cursor-pointer active:scale-95 duration-150 transition-all" href="/?hub={selected_hub}&view=transfers">
<span class="material-symbols-outlined">local_shipping</span>
<span class="font-label-md text-label-md">Active Transfers</span>
</a>
</nav>

<div class="mt-auto pt-6 border-t border-outline-variant space-y-2">
<form action="/sync-db" method="post">
    <button type="submit" class="w-full text-center py-2 border border-outline-variant rounded bg-surface-container-lowest text-on-surface-variant font-label-md text-label-md hover:bg-surface-container-low transition-colors text-xs">
        🔄 Reset Ledger DB
    </button>
</form>
<div class="text-[10px] text-center font-medium text-outline">Offline Local Policy Engine</div>
</div>
</aside>

<!-- Center Main Area -->
<main class="flex-1 overflow-y-auto p-container-padding custom-scrollbar">
<div class="max-w-[1200px] mx-auto space-y-6">
    {warning_banner}
    {main_workspace_content}
</div>
</main>

<!-- Right Sidebar (Active Data Stream) -->
<aside class="w-80 bg-surface-container-lowest border-l border-outline-variant flex flex-col shrink-0">
<div class="p-4 border-b border-outline-variant flex items-center justify-between shrink-0">
<h3 class="font-label-md text-label-md text-on-surface uppercase font-bold flex items-center gap-2">
<span class="material-symbols-outlined text-[18px] text-secondary">sensors</span>
                    Dynamic Progress Logs
                </h3>
<span class="text-[10px] text-on-surface-variant px-2 py-0.5 bg-surface-container rounded-full">REALTIME</span>
</div>
<div class="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
    {telemetry_logs}
</div>
</aside>
</div>
<script>
        // Active state navigation logic
        document.querySelectorAll('nav a').forEach(link => {{
            link.addEventListener('click', (e) => {{
                document.querySelectorAll('nav a').forEach(l => {{
                    l.classList.remove('bg-surface-container', 'text-primary', 'font-bold');
                    l.classList.add('text-on-surface-variant');
                }});
                link.classList.add('bg-surface-container', 'text-primary', 'font-bold');
                link.classList.remove('text-on-surface-variant');
            }});
        }});
    </script>
</body></html>
"""

# =====================================================================
# SYSTEM CORE ROUTING CONTROLLERS
# =====================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    if not os.path.exists(DB_NAME):
        initialize_database()
    hub = request.query_params.get("hub", "Hyderabad")
    view = request.query_params.get("view", "dashboard")
    
    idle_brief = """
    <strong>Ready for Dispatch Evaluation</strong><br><br>
    Please select an emergency care scenario on the left panel, and click <strong>'Analyze Route'</strong>. 
    The local routing coordinator will check the offline safety guidelines, current inventories, and coordinates distance parameters to calculate backup transfer recommendations instantly.
    """
    
    # Subagent logic overlay (horizontal visual flowchart)
    idle_logs = """
    <div class="mb-4 text-center font-bold text-[10px] text-outline bg-surface-container py-2 rounded-lg border border-outline-variant/30 uppercase tracking-widest">
        🔍 Classifier ──► 📖 Safety ──► 🏪 Scout ──► ✨ Planner
    </div>
    <div class="flex items-center gap-2.5 p-3 rounded-lg border border-slate-100 bg-slate-50 text-slate-400 text-xs">
        <span class="material-symbols-outlined text-sm shrink-0">hourglass_empty</span>
        <div>Waiting for emergency dispatch scenario...</div>
    </div>
    """
    
    inventory_table = get_clean_inventory_html(hub)
    network_table = get_clean_network_html(hub)
    hub_options = "".join([f'<option value="{h}" {"selected" if h == hub else ""}>{h}</option>' for h in METRO_HUBS])
    alert_count = get_alert_count(hub)
    
    # Visual Alert Warning Banner if low stocks exist
    warning_banner = ""
    if alert_count > 0:
        warning_banner = f"""
        <div class="flex items-center justify-between p-4 bg-error-container/20 text-error border border-error/20 rounded-xl mb-2">
            <div class="flex items-center gap-3">
                <span class="material-symbols-outlined text-[24px]">warning</span>
                <div>
                    <p class="text-xs font-bold uppercase tracking-wider">Critical Stock Shortage Alert</p>
                    <p class="text-[11px] text-on-surface-variant mt-0.5">Safety parameters breached for {alert_count} critical medical items at the {hub} Hub. Dispatch checks are strongly advised.</p>
                </div>
            </div>
            <span class="text-[10px] font-bold bg-error/10 px-2.5 py-1 rounded border border-error/20 uppercase tracking-widest">Action Advised</span>
        </div>
        """
    
    # Active navigation link highlights
    if view == "transfers":
        dashboard_active_classes = "text-on-surface-variant hover:text-primary hover:bg-surface-container-low"
        transfers_active_classes = "text-primary font-bold bg-surface-container"
        main_workspace_content = get_active_transfers_html(hub)
    else:
        dashboard_active_classes = "text-primary font-bold bg-surface-container"
        transfers_active_classes = "text-on-surface-variant hover:text-primary hover:bg-surface-container-low"
        main_workspace_content = f"""
        <!-- Bento Style Stats Grid -->
        <div class="grid grid-cols-12 gap-gutter">
            <!-- DISPATCH BRIEF (Colspan 7) -->
            <div class="col-span-12 md:col-span-7 bg-surface-container-lowest border border-outline-variant p-4 flex flex-col h-[320px]">
                <div class="flex justify-between items-center mb-4 shrink-0">
                    <h3 class="font-headline-sm text-headline-sm text-on-surface flex items-center gap-2">
                        <span class="material-symbols-outlined text-primary">medical_services</span>
                        Dynamic Dispatch Recommendation Brief
                    </h3>
                </div>
                <div class="flex-1 overflow-y-auto custom-scrollbar p-4 bg-surface-container-low rounded-xl border border-outline-variant/30 text-xs text-on-surface leading-relaxed font-normal">
                    {idle_brief}
                </div>
            </div>

            <!-- LOCAL LEDGER (Colspan 5) -->
            <div class="col-span-12 md:col-span-5 bg-surface-container-lowest border border-outline-variant p-4 flex flex-col h-[320px]">
                <h3 class="font-headline-sm text-headline-sm text-on-surface mb-3 flex items-center gap-2 shrink-0">
                    <span class="material-symbols-outlined text-primary">inventory_2</span>
                    Local Stock Ledger ({hub})
                </h3>
                <div class="flex-1 overflow-y-auto custom-scrollbar">
                    {inventory_table}
                </div>
            </div>
        </div>

        <!-- CONNECTED NETWORKS TABLE -->
        <div class="bg-surface-container-lowest border border-outline-variant">
            <div class="px-6 py-4 border-b border-outline-variant flex justify-between items-center">
                <h3 class="font-headline-sm text-headline-sm text-on-surface flex items-center gap-2">
                    <span class="material-symbols-outlined text-primary">lan</span>
                    Connected Regional Partner Networks
                </h3>
                <span class="text-[10px] font-semibold bg-primary-container/10 text-primary px-2.5 py-1 rounded border border-primary-container/20">Live Coordinate Tables</span>
            </div>
            <div class="overflow-x-auto p-4">
                {network_table}
            </div>
        </div>

        <!-- Footer Section Info -->
        <div class="flex flex-col md:flex-row gap-gutter">
            <div class="flex-1 bg-surface-container-low p-stack-md border border-outline-variant flex items-center gap-4">
                <div class="w-12 h-12 rounded-full bg-white flex items-center justify-center border border-outline-variant shrink-0">
                    <span class="material-symbols-outlined text-primary">explore</span>
                </div>
                <div>
                    <p class="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Active Coordinates Hub</p>
                    <p class="font-headline-sm text-headline-sm text-on-surface">{hub} Node</p>
                </div>
            </div>
            <div class="flex-1 bg-surface-container-low p-stack-md border border-outline-variant flex items-center gap-4">
                <div class="w-12 h-12 rounded-full bg-white flex items-center justify-center border border-outline-variant shrink-0">
                    <span class="material-symbols-outlined text-primary">security</span>
                </div>
                <div>
                    <p class="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Privacy & Compliance</p>
                    <p class="font-headline-sm text-headline-sm text-on-surface">100% HIPAA Offline</p>
                </div>
            </div>
            <div class="flex-1 bg-surface-container-low p-stack-md border border-outline-variant flex items-center gap-4">
                <div class="w-12 h-12 rounded-full bg-white flex items-center justify-center border border-outline-variant shrink-0">
                    <span class="material-symbols-outlined text-primary">speed</span>
                </div>
                <div>
                    <p class="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Rules Latency Score</p>
                    <p class="font-headline-sm text-headline-sm text-on-surface">&lt; 1ms Execution</p>
                </div>
            </div>
        </div>
        """

    return DASHBOARD_FRAME_HTML.format(
        selected_hub=hub,
        selected_view=view,
        inventory_table=inventory_table,
        network_table=network_table,
        telemetry_logs=idle_logs,
        hub_options=hub_options,
        alert_count=alert_count,
        warning_banner=warning_banner,
        dashboard_active_classes=dashboard_active_classes,
        transfers_active_classes=transfers_active_classes,
        main_workspace_content=main_workspace_content
    )

@app.post("/", response_class=HTMLResponse)
async def execute_engine_pipeline(request: Request, user_input: str = Form(...), active_hub: str = Form("Hyderabad")):
    if not os.path.exists(DB_NAME):
        initialize_database()
        
    # Run our local rules block
    output_state = run_aegis_flow_engine(user_input, hub=active_hub)
    
    # Check if a dispatch source was found, and insert an active shipment
    if output_state.get("routing_alternatives"):
        best = output_state["routing_alternatives"][0]
        qty = 4
        local_stock = output_state.get("local_inventory_status", {})
        if isinstance(local_stock, dict) and "current_stock" in local_stock:
            qty = max(1, local_stock["critical_threshold"] - local_stock["current_stock"])
            
        mode = "Road" if best["city"] == active_hub else "Air"
        eta = best["current_traffic_delay_min"] + 15 if mode == "Road" else 180
        
        add_active_transfer(
            item_name=output_state["target_asset"],
            quantity=qty,
            from_hospital=best["hospital_name"],
            to_hub=active_hub,
            eta=eta,
            mode=mode
        )
    
    # Subagent logic overlay (horizontal visual flowchart highlighted)
    flowchart_html = """
    <div class="mb-4 text-center font-bold text-[10px] text-primary bg-primary-container/15 py-2 rounded-lg border border-primary-container/30 uppercase tracking-widest flex items-center justify-center gap-1.5 animate-pulse">
        <span class="material-symbols-outlined text-sm font-bold">route</span>
        🔍 Classifier ──► 📖 Safety ──► 🏪 Scout ──► ✨ Planner
    </div>
    """
    
    # 1. Parse Live Agent Logs into color-coded system badges
    log_blocks = flowchart_html
    for log in output_state.get("execution_logs", []):
        if "Alert" in log or "⚠️" in log:
            log_blocks += f'<div class="flex items-start gap-2.5 p-2.5 rounded-lg border border-rose-100 bg-rose-50 text-rose-700 text-xs font-medium"><span class="material-symbols-outlined text-sm shrink-0 mt-0.5">warning</span><div>{log}</div></div>'
        elif "✅" in log or "🟢" in log or "🚚" in log or "📦" in log:
            log_blocks += f'<div class="flex items-start gap-2.5 p-2.5 rounded-lg border border-emerald-100 bg-emerald-50 text-emerald-700 text-xs font-medium"><span class="material-symbols-outlined text-sm shrink-0 mt-0.5">check_circle</span><div>{log}</div></div>'
        else:
            log_blocks += f'<div class="flex items-start gap-2.5 p-2.5 rounded-lg border border-blue-100 bg-blue-50 text-blue-700 text-xs font-medium"><span class="material-symbols-outlined text-sm shrink-0 mt-0.5">info</span><div>{log}</div></div>'

    inventory_table = get_clean_inventory_html(active_hub)
    network_table = get_clean_network_html(active_hub)
    hub_options = "".join([f'<option value="{h}" {"selected" if h == active_hub else ""}>{h}</option>' for h in METRO_HUBS])
    alert_count = get_alert_count(active_hub)

    # Visual Alert Warning Banner if low stocks exist
    warning_banner = ""
    if alert_count > 0:
        warning_banner = f"""
        <div class="flex items-center justify-between p-4 bg-error-container/20 text-error border border-error/20 rounded-xl mb-2">
            <div class="flex items-center gap-3">
                <span class="material-symbols-outlined text-[24px]">warning</span>
                <div>
                    <p class="text-xs font-bold uppercase tracking-wider">Critical Stock Shortage Alert</p>
                    <p class="text-[11px] text-on-surface-variant mt-0.5">Safety parameters breached for {alert_count} critical medical items at the {active_hub} Hub. Dispatch checks are strongly advised.</p>
                </div>
            </div>
            <span class="text-[10px] font-bold bg-error/10 px-2.5 py-1 rounded border border-error/20 uppercase tracking-widest">Action Advised</span>
        </div>
        """

    brief = output_state.get("final_orchestrated_brief", "Pipeline ran with empty outputs.").replace('\n', '<br>')

    # Standard dashboard content with the simulated brief output
    dashboard_active_classes = "text-primary font-bold bg-surface-container"
    transfers_active_classes = "text-on-surface-variant hover:text-primary hover:bg-surface-container-low"
    main_workspace_content = f"""
    <!-- Bento Style Stats Grid -->
    <div class="grid grid-cols-12 gap-gutter">
        <!-- DISPATCH BRIEF (Colspan 7) -->
        <div class="col-span-12 md:col-span-7 bg-surface-container-lowest border border-outline-variant p-4 flex flex-col h-[320px]">
            <div class="flex justify-between items-center mb-4 shrink-0">
                <h3 class="font-headline-sm text-headline-sm text-on-surface flex items-center gap-2">
                    <span class="material-symbols-outlined text-primary">medical_services</span>
                    Dynamic Dispatch Recommendation Brief
                </h3>
            </div>
            <div class="flex-1 overflow-y-auto custom-scrollbar p-4 bg-surface-container-low rounded-xl border border-outline-variant/30 text-xs text-on-surface leading-relaxed font-normal">
                {brief}
            </div>
        </div>

        <!-- LOCAL LEDGER (Colspan 5) -->
        <div class="col-span-12 md:col-span-5 bg-surface-container-lowest border border-outline-variant p-4 flex flex-col h-[320px]">
            <h3 class="font-headline-sm text-headline-sm text-on-surface mb-3 flex items-center gap-2 shrink-0">
                <span class="material-symbols-outlined text-primary">inventory_2</span>
                Local Stock Ledger ({active_hub})
            </h3>
            <div class="flex-1 overflow-y-auto custom-scrollbar">
                {inventory_table}
            </div>
        </div>
    </div>

    <!-- CONNECTED NETWORKS TABLE -->
    <div class="bg-surface-container-lowest border border-outline-variant">
        <div class="px-6 py-4 border-b border-outline-variant flex justify-between items-center">
            <h3 class="font-headline-sm text-headline-sm text-on-surface flex items-center gap-2">
                <span class="material-symbols-outlined text-primary">lan</span>
                Connected Regional Partner Networks
            </h3>
            <span class="text-[10px] font-semibold bg-primary-container/10 text-primary px-2.5 py-1 rounded border border-primary-container/20">Live Coordinate Tables</span>
        </div>
        <div class="overflow-x-auto p-4">
            {network_table}
        </div>
    </div>

    <!-- Footer Section Info -->
    <div class="flex flex-col md:flex-row gap-gutter">
        <div class="flex-1 bg-surface-container-low p-stack-md border border-outline-variant flex items-center gap-4">
            <div class="w-12 h-12 rounded-full bg-white flex items-center justify-center border border-outline-variant shrink-0">
                <span class="material-symbols-outlined text-primary">explore</span>
            </div>
            <div>
                <p class="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Active Coordinates Hub</p>
                <p class="font-headline-sm text-headline-sm text-on-surface">{active_hub} Node</p>
            </div>
        </div>
        <div class="flex-1 bg-surface-container-low p-stack-md border border-outline-variant flex items-center gap-4">
            <div class="w-12 h-12 rounded-full bg-white flex items-center justify-center border border-outline-variant shrink-0">
                <span class="material-symbols-outlined text-primary">security</span>
            </div>
            <div>
                <p class="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Privacy & Compliance</p>
                <p class="font-headline-sm text-headline-sm text-on-surface">100% HIPAA Offline</p>
            </div>
        </div>
        <div class="flex-1 bg-surface-container-low p-stack-md border border-outline-variant flex items-center gap-4">
            <div class="w-12 h-12 rounded-full bg-white flex items-center justify-center border border-outline-variant shrink-0">
                <span class="material-symbols-outlined text-primary">speed</span>
            </div>
            <div>
                <p class="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Rules Latency Score</p>
                <p class="font-headline-sm text-headline-sm text-on-surface">&lt; 1ms Execution</p>
            </div>
        </div>
    </div>
    """

    return DASHBOARD_FRAME_HTML.format(
        selected_hub=active_hub,
        selected_view="dashboard",
        inventory_table=inventory_table,
        network_table=network_table,
        telemetry_logs=log_blocks,
        hub_options=hub_options,
        alert_count=alert_count,
        warning_banner=warning_banner,
        dashboard_active_classes=dashboard_active_classes,
        transfers_active_classes=transfers_active_classes,
        main_workspace_content=main_workspace_content
    )

@app.post("/sync-db")
async def sync_database():
    initialize_database()
    return RedirectResponse(url="/", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)