# MediLog Medical Logistics Command Platform: Architecture & Technical Specifications

MediLog is built as an offline-first, high-concurrency clinical dispatch and medical logistics assistant. It operates entirely within a secure Hospital Intranet / Local Area Network (LAN) topology to bypass cloud latencies, protect sensitive patient demand metrics, and guarantee sub-millisecond route evaluations.

Here is the comprehensive breakdown of the system architecture, component details, data pipeline, and operational roles.

---

## 1. High-Level Architecture Overview

The application is structured around a single-node, offline-first paradigm using a **FastAPI Web Server** for API routing and page rendering, an embedded **SQLite Database** running in write-ahead logging (WAL) mode for local data persistence, and a **State-Driven Graph Workflow Engine** for programmatic triage logic.

```mermaid
graph TD
    User([Hospital Dispatcher / Admin]) -->|Selects Triage & Hub| UI[Tailwind CSS Dashboard]
    UI -->|GET / POST requests| AppServer[FastAPI Web Server]
    
    subgraph Data Layer
        DB[(hospital_ecosystem.db)] <-->|PRAGMA journal_mode=WAL| DB_Conn[SQLite Connections]
    end

    AppServer -->|Triggers Pipeline| GraphExec[DirectionalStateGraph]
    
    subgraph State Graph Nodes
        GraphExec -->|Step 1| Classifier[Classifier Node]
        GraphExec -->|Step 2| RAGSafety[RAG Safety Node]
        GraphExec -->|Step 3| LocalScout[Local Scout Node]
        GraphExec -->|Step 4 (Branch)| NeighborScout[Neighbor Scout Node]
        GraphExec -->|Step 5| Planner[Planner Node]
    end

    LocalScout <--> DB_Conn
    NeighborScout <--> DB_Conn
    NeighborScout -->|Haversine Formula| SpatialCalc[Spatial Distance Calculus]
    
    Planner -->|Dynamic Decision Brief & Log Stream| AppServer
    AppServer -->|Re-renders View| UI