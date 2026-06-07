import os
import sqlite3
import json
import math
from typing import Dict, Any, List, TypedDict, Callable

DB_NAME = "hospital_ecosystem.db"

# Center coordinates for each metropolitan hub center
METRO_HUBS = {
    "Hyderabad": (17.3850, 78.4867),
    "Mumbai": (19.0760, 72.8777),
    "Delhi NCR": (28.6139, 77.2090),
    "Bengaluru": (12.9716, 77.5946),
    "Chennai": (13.0827, 80.2707),
    "Kolkata": (22.5726, 88.3639)
}

class AgentWorkflowState(TypedDict):
    raw_query: str
    hub: str
    parsed_intent: str
    target_asset: str
    rag_protocol_context: str
    local_inventory_status: Dict[str, Any]
    routing_alternatives: List[Dict[str, Any]]
    final_orchestrated_brief: str
    execution_logs: List[str]

# --- HAVERSINE DISTANCE MATH ---
def haversine_distance(coord1, coord2):
    """Calculates geographical distance between two coordinate pairs in kilometers."""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    R = 6371.0  # Earth radius in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

# --- SYSTEM OPERATIONAL GUIDELINES (LOCAL RAG SAFETY ENGINE) ---
def retrieve_rag_knowledge_base(query: str, target_asset: str) -> str:
    """
    Retrieves operational safety protocols based on target asset classes.
    """
    protocols = {
        "blood": "Verify universal donor status. Cross-match verification bypass is permitted under Level 1 trauma indicators. Maintain temperature-controlled transport.",
        "epinephrine": "Epinephrine stocks dropping below 25 vials require immediate route optimization matching. Cold chain parameters must maintain 2°C - 8°C throughout transport.",
        "antivenom": "Verify species indicator. Cold-chain storage at 2°C - 8°C must be maintained. Perform rapid hypersensitivity screen prior to administration.",
        "ventilator": "Verify sterile packaging integrity. Ensure compatibility with host ventilator hardware models. Sterile transport container seal required.",
        "surfactant": "Keep refrigerated. Avoid shaking. Warm vial to room temperature gently before intratracheal administration. Rapid transport required under cold chain."
    }
    
    query_lower = target_asset.lower()
    if "blood" in query_lower:
        return protocols["blood"]
    elif "epinephrine" in query_lower:
        return protocols["epinephrine"]
    elif "antivenom" in query_lower:
        return protocols["antivenom"]
    elif "ventilator" in query_lower:
        return protocols["ventilator"]
    elif "surfactant" in query_lower:
        return protocols["surfactant"]
    else:
        return "Evaluate alternative route distribution nodes based on lowest transit latency."

# --- DATABASE QUERY HANDLERS ---
def query_local_inventory(asset_name: str, hub: str) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory WHERE item_name LIKE ? AND location_hub = ?", (f"%{asset_name}%", hub))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {"error": "Asset not discovered."}

def scan_neighboring_networks(asset_name: str, hub: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query_lower = asset_name.lower()
    if "blood" in query_lower:
        col = "available_o_neg_units"
    elif "epinephrine" in query_lower:
        col = "available_epinephrine_vials"
    elif "antivenom" in query_lower:
        col = "available_antivenom_vials"
    elif "ventilator" in query_lower:
        col = "available_ventilators"
    elif "surfactant" in query_lower:
        col = "available_surfactant_vials"
    else:
        col = "available_o_neg_units"
        
    query = f"""
        SELECT hospital_name, city, latitude, longitude, current_traffic_delay_min, {col} as available_units, contact_secure_rpc 
        FROM neighboring_hospitals 
        WHERE {col} > 0
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    hub_coords = METRO_HUBS.get(hub, (17.3850, 78.4867))
    results = []
    for r in rows:
        d = dict(r)
        hosp_coords = (d["latitude"], d["longitude"])
        dist = haversine_distance(hub_coords, hosp_coords)
        d["distance_km"] = round(dist, 1)
        results.append(d)
        
    # Sort closest hospitals first
    results.sort(key=lambda x: x["distance_km"])
    return results

# --- DIRECTIONAL STATE GRAPH ROUTER ENGINE ---
class DirectionalStateGraph:
    def __init__(self):
        self.nodes: Dict[str, Callable[[AgentWorkflowState], AgentWorkflowState]] = {}
        # transitions is dict mapping from_node to list of (to_node, condition_fn)
        self.transitions: Dict[str, List[tuple]] = {}

    def add_node(self, name: str, func: Callable[[AgentWorkflowState], AgentWorkflowState]):
        self.nodes[name] = func

    def add_transition(self, from_node: str, to_node: str, condition: Callable[[AgentWorkflowState], bool] = None):
        if from_node not in self.transitions:
            self.transitions[from_node] = []
        self.transitions[from_node].append((to_node, condition))

    def run(self, initial_state: AgentWorkflowState) -> AgentWorkflowState:
        state = initial_state
        current_node = "START"
        
        while current_node != "END":
            # Search for transitions
            next_node = None
            if current_node in self.transitions:
                for candidate, condition in self.transitions[current_node]:
                    if condition is None or condition(state):
                        next_node = candidate
                        break
            
            if not next_node:
                # Default safety transition if no conditions matched
                break
                
            current_node = next_node
            if current_node in self.nodes:
                state = self.nodes[current_node](state)
                
        return state

# --- GRAPH WORKFLOW NODES ---
def intent_classifier_node(state: AgentWorkflowState) -> AgentWorkflowState:
    state["execution_logs"].append("🔍 [Classifier Node] Analyzing request details to identify target medical supplies...")
    
    query = state["raw_query"].lower()
    if "blood" in query or "o-neg" in query or "trauma" in query:
        state["target_asset"] = "O-Negative Blood"
    elif "epinephrine" in query or "epi" in query or "medication" in query:
        state["target_asset"] = "Epinephrine 1mg/mL"
    elif "antivenom" in query or "bite" in query or "venom" in query:
        state["target_asset"] = "Polyvalent Antivenom"
    elif "ventilator" in query or "icu" in query or "circuit" in query:
        state["target_asset"] = "Ventilator Circuits"
    elif "surfactant" in query or "neonatal" in query or "infant" in query:
        state["target_asset"] = "Surfactant 25mg/mL"
    else:
        state["target_asset"] = "O-Negative Blood"
        
    state["execution_logs"].append(f"📦 [Classifier Node] Locked target item: {state['target_asset']}")
    return state

def rag_knowledge_injector_node(state: AgentWorkflowState) -> AgentWorkflowState:
    state["execution_logs"].append("📖 [RAG Safety Node] Injecting operational guidelines and transport limits...")
    context = retrieve_rag_knowledge_base(state["raw_query"], state["target_asset"])
    state["rag_protocol_context"] = context
    state["execution_logs"].append("✅ [RAG Safety Node] Safety protocols and regulations successfully loaded.")
    return state

def local_scout_node(state: AgentWorkflowState) -> AgentWorkflowState:
    state["execution_logs"].append(f"🏪 [Local Scout Node] Scanning stock levels at the {state['hub']} Hub ledger...")
    local = query_local_inventory(state["target_asset"], state["hub"])
    state["local_inventory_status"] = local
    
    if "error" in local:
        state["execution_logs"].append("❌ [Local Scout Node] Asset not discovered in the local inventory ledger.")
    else:
        stock = local["current_stock"]
        threshold = local["critical_threshold"]
        state["execution_logs"].append(f"📊 [Local Scout Node] Stock check: {stock} units available (Critical threshold: {threshold} units)")
        
    return state

def neighbor_scout_node(state: AgentWorkflowState) -> AgentWorkflowState:
    state["execution_logs"].append(f"⚠️ [Neighbor Scout Node] Stock below safety limit! Initiating regional coordinate search...")
    state["execution_logs"].append(f"🌐 [Neighbor Scout Node] Executing dynamic Haversine formulas against hospital ledger database...")
    state["routing_alternatives"] = scan_neighboring_networks(state["target_asset"], state["hub"])
    
    routes_found = len(state["routing_alternatives"])
    state["execution_logs"].append(f"✅ [Neighbor Scout Node] Spatial scan complete. Discovered {routes_found} potential delivery partners.")
    return state

def synthesis_orchestrator_node(state: AgentWorkflowState) -> AgentWorkflowState:
    state["execution_logs"].append("✨ [Planner Node] Formulating optimized transit options...")
    
    hub = state["hub"]
    asset = state["target_asset"]
    local_stock = state["local_inventory_status"]
    alternatives = state["routing_alternatives"]
    
    # 1. Analyze Situation
    if "error" in local_stock:
        situation = f"Asset '{asset}' was not found in the local inventory ledger."
    else:
        stock = local_stock["current_stock"]
        threshold = local_stock["critical_threshold"]
        unit = local_stock["unit"]
        burn = local_stock["daily_burn_rate"]
        deficit = threshold - stock
        
        depletion_text = f"{round(stock/burn, 1)} days" if burn > 0 else "Indefinite"
        situation = f"Local stock of {asset} at the **{hub} Hub** is currently at **{stock} {unit}**, which falls below the safety threshold of **{threshold} {unit}** (a deficit of **{deficit} {unit}**). Based on the daily burn rate of **{burn} {unit}/day**, the estimated local depletion window is **{depletion_text}**."

    # 2. Select Dispatch Source
    if not alternatives:
        if "error" not in local_stock and local_stock["current_stock"] >= local_stock["critical_threshold"]:
            source = f"Local inventory levels are fully sufficient at **{hub} Hub**. No regional dispatch request is required at this time."
        else:
            source = "No regional partner facilities currently report available stock for this item. Please escalate this request to the national medical asset command."
    else:
        best = alternatives[0]
        name = best["hospital_name"]
        city = best["city"]
        dist = best["distance_km"]
        avail = best["available_units"]
        rpc = best["contact_secure_rpc"]
        delay = best["current_traffic_delay_min"]
        
        if city == hub:
            source = f"**{name} ({city})**\n- **Route Transit:** Local Road Dispatch ({dist} km distance)\n- **Available Inventory:** {avail} units ready for immediate transfer\n- **Traffic Latency:** {delay} minutes expected delay\n- **Secure Contact:** {rpc}"
        else:
            source = f"**{name} ({city})**\n- **Route Transit:** Inter-City Express Air Cargo ({dist} km distance)\n- **Available Inventory:** {avail} units ready for transfer\n- **Transit Mode:** Flight Cargo Connection Required\n- **Secure Contact:** {rpc}"

    # 3. Transport Protocols
    protocol = state["rag_protocol_context"]

    # Build final orchestrated brief
    brief = f"""### EMERGENCY DISPATCH DECISION BRIEF

**1. CURRENT SITUATION**
{situation}

**2. RECOMMENDED DISPATCH SOURCE**
{source}

**3. TRANSPORT & SAFETY PROTOCOLS**
- **Safety Directive:** {protocol}
- **Required Transport Actions:** Ensure transport container seals are verified. Log transit dispatch times via the secure communication channel.
"""
    state["final_orchestrated_brief"] = brief.strip()
    state["execution_logs"].append("🚚 [Planner Node] Dispatch recommendations successfully finalized via local rules engine.")
    return state

# --- GRAPH CONVERTER WORKFLOW BOOTSTRAP ---
def run_aegis_flow_engine(user_query: str, hub: str = "Hyderabad") -> Dict[str, Any]:
    state: AgentWorkflowState = {
        "raw_query": user_query,
        "hub": hub,
        "parsed_intent": "",
        "target_asset": "",
        "rag_protocol_context": "",
        "local_inventory_status": {},
        "routing_alternatives": [],
        "final_orchestrated_brief": "",
        "execution_logs": ["🚀 Initializing emergency dispatch check..."]
    }
    
    # Define our state graph workflow
    graph = DirectionalStateGraph()
    
    # Add nodes
    graph.add_node("classifier", intent_classifier_node)
    graph.add_node("rag_safety", rag_knowledge_injector_node)
    graph.add_node("local_scout", local_scout_node)
    graph.add_node("neighbor_scout", neighbor_scout_node)
    graph.add_node("synthesis_planner", synthesis_orchestrator_node)
    
    # Define conditions for transition
    def is_local_stock_deficient(s: AgentWorkflowState) -> bool:
        local = s.get("local_inventory_status", {})
        if "error" in local:
            return False
        return local.get("current_stock", 0) < local.get("critical_threshold", 0)
        
    def is_local_stock_safe(s: AgentWorkflowState) -> bool:
        return not is_local_stock_deficient(s)
    
    # Establish directional transitions
    graph.add_transition("START", "classifier")
    graph.add_transition("classifier", "rag_safety")
    graph.add_transition("rag_safety", "local_scout")
    
    # Branching: If local inventory is deficient, transition to neighbor scout. Otherwise skip directly to synthesis planner.
    graph.add_transition("local_scout", "neighbor_scout", is_local_stock_deficient)
    graph.add_transition("local_scout", "synthesis_planner", is_local_stock_safe)
    
    graph.add_transition("neighbor_scout", "synthesis_planner")
    graph.add_transition("synthesis_planner", "END")
    
    # Run graph execution
    final_state = graph.run(state)
    return final_state