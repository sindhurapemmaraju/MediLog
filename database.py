import sqlite3
import os

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

def initialize_database():
    """Initializes a regional, multi-city medical inventory ledger with multiple asset classes."""
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()

    
    # 1. Local Ledger Table (contains inventories segmented by hub)
    cursor.execute("""
        CREATE TABLE inventory (
            item_id TEXT PRIMARY KEY,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            current_stock INTEGER NOT NULL,
            critical_threshold INTEGER NOT NULL,
            daily_burn_rate REAL NOT NULL,
            unit TEXT NOT NULL,
            location_hub TEXT NOT NULL
        )
    """)
    
    # 2. Inter-Hospital Routing Networks (contains hospital coordinates, traffic delay, and item stocks)
    cursor.execute("""
        CREATE TABLE neighboring_hospitals (
            hospital_id TEXT PRIMARY KEY,
            hospital_name TEXT NOT NULL,
            city TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            current_traffic_delay_min INTEGER NOT NULL,
            available_o_neg_units INTEGER NOT NULL,
            available_epinephrine_vials INTEGER NOT NULL,
            available_antivenom_vials INTEGER NOT NULL,
            available_ventilators INTEGER NOT NULL,
            available_surfactant_vials INTEGER NOT NULL,
            contact_secure_rpc TEXT NOT NULL
        )
    """)
    
    # 3. Active Shipment / Transfers Ledger
    cursor.execute("""
        CREATE TABLE active_transfers (
            transfer_id TEXT PRIMARY KEY,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            from_hospital TEXT NOT NULL,
            to_hub TEXT NOT NULL,
            status TEXT NOT NULL,
            eta_minutes INTEGER NOT NULL,
            transit_mode TEXT NOT NULL
        )
    """)
    
    # Seed Data: Items for each metropolitan hub, showing various stock status (deficit vs safe)
    inventory_data = [
        # Hyderabad Hub
        ("INV-B-001-HYD", "O-Negative Blood", "Blood Assets", 2, 10, 4.5, "Units", "Hyderabad"),
        ("INV-M-102-HYD", "Epinephrine 1mg/mL", "Critical Medications", 3, 25, 8.2, "Vials", "Hyderabad"),
        ("INV-M-103-HYD", "Polyvalent Antivenom", "Antidotes", 1, 15, 3.0, "Vials", "Hyderabad"),
        ("INV-E-201-HYD", "Ventilator Circuits", "ICU Equipments", 18, 10, 2.5, "Units", "Hyderabad"),
        ("INV-M-104-HYD", "Surfactant 25mg/mL", "Neonatal Drugs", 4, 15, 2.0, "Vials", "Hyderabad"),

        # Mumbai Hub
        ("INV-B-001-MUM", "O-Negative Blood", "Blood Assets", 15, 10, 6.0, "Units", "Mumbai"),
        ("INV-M-102-MUM", "Epinephrine 1mg/mL", "Critical Medications", 4, 25, 12.0, "Vials", "Mumbai"),
        ("INV-M-103-MUM", "Polyvalent Antivenom", "Antidotes", 22, 15, 4.0, "Vials", "Mumbai"),
        ("INV-E-201-MUM", "Ventilator Circuits", "ICU Equipments", 2, 10, 3.5, "Units", "Mumbai"),
        ("INV-M-104-MUM", "Surfactant 25mg/mL", "Neonatal Drugs", 18, 15, 3.0, "Vials", "Mumbai"),

        # Delhi NCR Hub
        ("INV-B-001-DEL", "O-Negative Blood", "Blood Assets", 3, 12, 8.0, "Units", "Delhi NCR"),
        ("INV-M-102-DEL", "Epinephrine 1mg/mL", "Critical Medications", 30, 25, 10.5, "Vials", "Delhi NCR"),
        ("INV-M-103-DEL", "Polyvalent Antivenom", "Antidotes", 8, 15, 5.0, "Vials", "Delhi NCR"),
        ("INV-E-201-DEL", "Ventilator Circuits", "ICU Equipments", 14, 10, 4.0, "Units", "Delhi NCR"),
        ("INV-M-104-DEL", "Surfactant 25mg/mL", "Neonatal Drugs", 2, 15, 3.5, "Vials", "Delhi NCR"),

        # Bengaluru Hub
        ("INV-B-001-BLR", "O-Negative Blood", "Blood Assets", 18, 10, 5.5, "Units", "Bengaluru"),
        ("INV-M-102-BLR", "Epinephrine 1mg/mL", "Critical Medications", 2, 25, 9.0, "Vials", "Bengaluru"),
        ("INV-M-103-BLR", "Polyvalent Antivenom", "Antidotes", 20, 15, 3.5, "Vials", "Bengaluru"),
        ("INV-E-201-BLR", "Ventilator Circuits", "ICU Equipments", 25, 10, 5.0, "Units", "Bengaluru"),
        ("INV-M-104-BLR", "Surfactant 25mg/mL", "Neonatal Drugs", 19, 15, 2.5, "Vials", "Bengaluru"),

        # Chennai Hub
        ("INV-B-001-MAA", "O-Negative Blood", "Blood Assets", 8, 10, 5.0, "Units", "Chennai"),
        ("INV-M-102-MAA", "Epinephrine 1mg/mL", "Critical Medications", 28, 25, 8.0, "Vials", "Chennai"),
        ("INV-M-103-MAA", "Polyvalent Antivenom", "Antidotes", 3, 15, 4.5, "Vials", "Chennai"),
        ("INV-E-201-MAA", "Ventilator Circuits", "ICU Equipments", 6, 10, 3.0, "Units", "Chennai"),
        ("INV-M-104-MAA", "Surfactant 25mg/mL", "Neonatal Drugs", 24, 15, 3.0, "Vials", "Chennai"),

        # Kolkata Hub
        ("INV-B-001-CCU", "O-Negative Blood", "Blood Assets", 1, 10, 4.0, "Units", "Kolkata"),
        ("INV-M-102-CCU", "Epinephrine 1mg/mL", "Critical Medications", 1, 25, 7.5, "Vials", "Kolkata"),
        ("INV-M-103-CCU", "Polyvalent Antivenom", "Antidotes", 18, 15, 3.0, "Vials", "Kolkata"),
        ("INV-E-201-CCU", "Ventilator Circuits", "ICU Equipments", 32, 10, 4.0, "Units", "Kolkata"),
        ("INV-M-104-CCU", "Surfactant 25mg/mL", "Neonatal Drugs", 1, 15, 2.0, "Vials", "Kolkata")
    ]
    
    # Hospital network across 6 metropolitan cities with coordinates and stocks
    neighbor_data = [
        # Hyderabad
        ("HOSP-HYD-01", "Apollo Hospitals (Jubilee Hills)", "Hyderabad", 17.4265, 78.4012, 10, 15, 60, 40, 15, 25, "rpc://apollo-jh-secure"),
        ("HOSP-HYD-02", "KIMS Hospitals (Secunderabad)", "Hyderabad", 17.4374, 78.4878, 18, 0, 85, 30, 12, 0, "rpc://kims-sec-secure"),
        ("HOSP-HYD-03", "Yashoda Hospitals (Somajiguda)", "Hyderabad", 17.4211, 78.4593, 12, 8, 30, 20, 8, 35, "rpc://yashoda-sj-secure"),
        ("HOSP-HYD-04", "NIMS (Punjagutta)", "Hyderabad", 17.4215, 78.4534, 15, 12, 40, 0, 5, 20, "rpc://nims-punja-secure"),

        # Mumbai
        ("HOSP-MUM-01", "Kokilaben Dhirubhai Ambani Hospital", "Mumbai", 19.1312, 72.8252, 22, 18, 45, 35, 18, 30, "rpc://kokilaben-mumbai"),
        ("HOSP-MUM-02", "Lilavati Hospital & Research Centre", "Mumbai", 19.0518, 72.8276, 15, 5, 20, 25, 4, 10, "rpc://lilavati-mumbai"),
        ("HOSP-MUM-03", "H. N. Reliance Foundation Hospital", "Mumbai", 18.9568, 72.8202, 25, 12, 50, 45, 12, 22, "rpc://hn-reliance-mumbai"),
        ("HOSP-MUM-04", "Fortis Hospital (Mulund)", "Mumbai", 19.1678, 72.9546, 30, 2, 70, 0, 10, 8, "rpc://fortis-mulund"),

        # Delhi NCR
        ("HOSP-DEL-01", "AIIMS (New Delhi)", "Delhi NCR", 28.5672, 77.2100, 15, 20, 100, 50, 30, 40, "rpc://aiims-delhi"),
        ("HOSP-DEL-02", "Medanta - The Medicity", "Delhi NCR", 28.4230, 77.0396, 35, 14, 80, 45, 15, 30, "rpc://medanta-gurugram"),
        ("HOSP-DEL-03", "Max Super Speciality Hospital (Saket)", "Delhi NCR", 28.5276, 77.2105, 20, 8, 40, 25, 10, 15, "rpc://max-saket"),
        ("HOSP-DEL-04", "Fortis Escorts Heart Institute", "Delhi NCR", 28.5606, 77.2741, 25, 4, 30, 15, 5, 10, "rpc://fortis-okhla"),

        # Bengaluru
        ("HOSP-BLR-01", "Narayana Health City", "Bengaluru", 12.8126, 77.6942, 25, 40, 250, 60, 45, 80, "rpc://narayana-blr"),
        ("HOSP-BLR-02", "Manipal Hospital (Old Airport Road)", "Bengaluru", 12.9576, 77.6482, 15, 15, 90, 40, 22, 50, "rpc://manipal-blr"),
        ("HOSP-BLR-03", "Fortis Hospital (Bannerghatta Road)", "Bengaluru", 12.8943, 77.5976, 20, 10, 60, 30, 14, 35, "rpc://fortis-bannerghatta"),
        ("HOSP-BLR-04", "Aster CMI Hospital (Hebbal)", "Bengaluru", 13.0498, 77.5898, 22, 12, 80, 25, 10, 20, "rpc://aster-hebbal"),

        # Chennai
        ("HOSP-MAA-01", "Apollo Hospitals (Greams Road)", "Chennai", 13.0604, 80.2520, 12, 25, 120, 55, 25, 70, "rpc://apollo-greams"),
        ("HOSP-MAA-02", "Fortis Malar Hospital (Adyar)", "Chennai", 13.0116, 80.2568, 15, 8, 45, 30, 10, 30, "rpc://fortis-malar"),
        ("HOSP-MAA-03", "MIOT International", "Chennai", 13.0215, 80.1834, 20, 12, 75, 40, 15, 40, "rpc://miot-chennai"),
        ("HOSP-MAA-04", "Gleneagles Global Health City", "Chennai", 12.9038, 80.2185, 30, 5, 50, 20, 8, 15, "rpc://gleneagles-perumbakkam"),

        # Kolkata
        ("HOSP-CCU-01", "Apollo Multispecialty Hospital", "Kolkata", 22.5694, 88.4062, 18, 14, 85, 45, 35, 60, "rpc://apollo-kolkata"),
        ("HOSP-CCU-02", "Fortis Hospital (Anandapur)", "Kolkata", 22.5169, 88.4011, 20, 6, 40, 25, 12, 30, "rpc://fortis-anandapur"),
        ("HOSP-CCU-03", "AMRI Hospital (Salt Lake)", "Kolkata", 22.5658, 88.4079, 15, 5, 35, 20, 8, 25, "rpc://amri-saltlake")
    ]
    
    # Active shipments
    transfer_data = [
        ("TRF-101", "O-Negative Blood", 4, "Apollo Hospitals (Jubilee Hills)", "Hyderabad", "In Transit", 8, "Road"),
        ("TRF-102", "Epinephrine 1mg/mL", 50, "Narayana Health City", "Hyderabad", "Pending Departure", 120, "Air"),
        ("TRF-103", "Insulin Regular", 30, "Medanta - The Medicity", "Delhi NCR", "Delivered", 0, "Road"),
        ("TRF-104", "O-Negative Blood", 8, "Lilavati Hospital & Research Centre", "Mumbai", "In Transit", 15, "Road"),
        ("TRF-105", "Epinephrine 1mg/mL", 15, "Fortis Hospital (Bannerghatta Road)", "Bengaluru", "In Transit", 20, "Road"),
        ("TRF-106", "O-Negative Blood", 10, "Apollo Hospitals (Greams Road)", "Chennai", "In Transit", 12, "Road"),
        ("TRF-107", "O-Negative Blood", 6, "Apollo Multispecialty Hospital", "Kolkata", "In Transit", 18, "Road")
    ]
    
    cursor.executemany("INSERT INTO inventory VALUES (?, ?, ?, ?, ?, ?, ?, ?)", inventory_data)
    cursor.executemany("INSERT INTO neighboring_hospitals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", neighbor_data)
    cursor.executemany("INSERT INTO active_transfers VALUES (?, ?, ?, ?, ?, ?, ?, ?)", transfer_data)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    initialize_database()