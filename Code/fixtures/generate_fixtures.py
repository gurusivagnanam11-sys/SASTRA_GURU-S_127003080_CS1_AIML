"""Synthetic AUTOSAR HLD Test Fixture Generator.

Generates two controlled synthetic AUTOSAR HLD PDF documents (v1.0 and v2.0)
using PyMuPDF (fitz) or ReportLab.
Includes strict warnings:
[SYNTHETIC TEST DATA / DEMONSTRATION FIXTURE - NOT OFFICIAL OEM SPECIFICATION]
"""

import os
import shutil
from pathlib import Path
import fitz  # PyMuPDF

WARNING_TEXT = "[SYNTHETIC TEST DATA / DEMONSTRATION FIXTURE - NOT OFFICIAL OEM SPECIFICATION]"

def draw_header_and_warning(page, title="AUTOSAR High-Level Design Document"):
    rect = page.rect
    # Warning banner at top
    page.insert_text(
        fitz.Point(50, 30),
        WARNING_TEXT,
        fontsize=8,
        color=(0.8, 0.1, 0.1),
    )
    # Divider line
    shape = page.new_shape()
    shape.draw_line(fitz.Point(50, 40), fitz.Point(rect.width - 50, 40))
    shape.finish(color=(0.7, 0.7, 0.7), width=0.5)
    shape.commit()

def draw_table(page, start_y, headers, rows, col_widths):
    x_start = 50
    row_height = 20
    cur_y = start_y
    
    # Draw header row
    shape = page.new_shape()
    total_width = sum(col_widths)
    shape.draw_rect(fitz.Rect(x_start, cur_y, x_start + total_width, cur_y + row_height))
    shape.finish(fill=(0.2, 0.3, 0.5), color=(0.1, 0.1, 0.1), width=0.5)
    shape.commit()
    
    cur_x = x_start
    for i, h in enumerate(headers):
        page.insert_text(fitz.Point(cur_x + 5, cur_y + 14), str(h), fontsize=9, color=(1, 1, 1))
        cur_x += col_widths[i]
        
    cur_y += row_height
    
    # Draw data rows
    for r_idx, row in enumerate(rows):
        bg_col = (0.95, 0.95, 0.95) if r_idx % 2 == 1 else (1, 1, 1)
        shape = page.new_shape()
        shape.draw_rect(fitz.Rect(x_start, cur_y, x_start + total_width, cur_y + row_height))
        shape.finish(fill=bg_col, color=(0.6, 0.6, 0.6), width=0.5)
        shape.commit()
        
        cur_x = x_start
        for i, val in enumerate(row):
            page.insert_text(fitz.Point(cur_x + 5, cur_y + 14), str(val), fontsize=8.5, color=(0, 0, 0))
            cur_x += col_widths[i]
        cur_y += row_height
        
    return cur_y + 15

def build_pdf_v1_fitz(filepath: Path):
    doc = fitz.open()
    
    # Page 1: Title Page
    p1 = doc.new_page(width=595, height=842)
    draw_header_and_warning(p1)
    p1.insert_text(fitz.Point(50, 180), "AUTOSAR High-Level Design Document", fontsize=20, color=(0.1, 0.2, 0.4))
    p1.insert_text(fitz.Point(50, 215), "Vehicle Control System - HLD Specification", fontsize=14, color=(0.3, 0.3, 0.3))
    p1.insert_text(fitz.Point(50, 280), "Version: 1.0", fontsize=11, color=(0, 0, 0))
    p1.insert_text(fitz.Point(50, 305), "Date: 2024-01-15", fontsize=11, color=(0, 0, 0))
    p1.insert_text(fitz.Point(50, 330), "Project: ADAS Vehicle Platform", fontsize=11, color=(0, 0, 0))
    p1.insert_text(fitz.Point(50, 355), "Document ID: AUTOSAR_HLD_v1.0", fontsize=11, color=(0, 0, 0))
    p1.insert_text(fitz.Point(50, 380), "Status: Approved Baseline", fontsize=11, color=(0, 0, 0))
    
    # Page 2: Introduction
    p2 = doc.new_page(width=595, height=842)
    draw_header_and_warning(p2)
    p2.insert_text(fitz.Point(50, 70), "1. Introduction", fontsize=16, color=(0.1, 0.2, 0.4))
    p2.insert_text(fitz.Point(50, 95), "1.1 Purpose and Scope", fontsize=12, color=(0.2, 0.2, 0.2))
    p2.insert_textbox(
        fitz.Rect(50, 105, 545, 200),
        "This High-Level Design (HLD) document defines the software architecture of the Vehicle Control System "
        "following the classic AUTOSAR software architecture standard. The scope encompasses the core control components, "
        "standardized interfaces, software ports, signal routing, and subsystem dependencies.",
        fontsize=10,
    )
    p2.insert_text(fitz.Point(50, 220), "1.2 References and Standards", fontsize=12, color=(0.2, 0.2, 0.2))
    p2.insert_textbox(
        fitz.Rect(50, 230, 545, 300),
        "References include AUTOSAR Classic Platform Release 4.4.0, ISO 26262 Road Vehicles Functional Safety, "
        "and corporate powertrain electronic control guidelines.",
        fontsize=10,
    )

    # Page 3: System Architecture Overview
    p3 = doc.new_page(width=595, height=842)
    draw_header_and_warning(p3)
    p3.insert_text(fitz.Point(50, 70), "2. System Architecture Overview", fontsize=16, color=(0.1, 0.2, 0.4))
    p3.insert_text(fitz.Point(50, 95), "2.1 Architecture Layers", fontsize=12, color=(0.2, 0.2, 0.2))
    p3.insert_textbox(
        fitz.Rect(50, 105, 545, 175),
        "The software architecture follows the standard three-tier AUTOSAR layer model consisting of the Application Layer "
        "containing Software Components (SWCs), the Runtime Environment (RTE) handling communication abstractions, "
        "and the Basic Software (BSW) managing low-level hardware abstraction and microcontroller drivers.",
        fontsize=10,
    )
    p3.insert_text(fitz.Point(50, 195), "2.2 Component Overview", fontsize=12, color=(0.2, 0.2, 0.2))
    p3.insert_textbox(
        fitz.Rect(50, 205, 545, 300),
        "The system consists of four primary software components:\n"
        "1. VehicleControl: Central application component computing motion control requests.\n"
        "2. SensorManager: Acquires, filters, and broadcasts vehicle telemetry and dynamics.\n"
        "3. DiagnosticManager: Manages DTCs and external diagnostic protocol services.\n"
        "4. CommunicationManager: Manages gateway communication across CAN and V2X networks.",
        fontsize=10,
    )

    # Page 4: Software Components - VehicleControl & SensorManager
    p4 = doc.new_page(width=595, height=842)
    draw_header_and_warning(p4)
    p4.insert_text(fitz.Point(50, 70), "3. Software Components", fontsize=16, color=(0.1, 0.2, 0.4))
    p4.insert_text(fitz.Point(50, 95), "3.1 VehicleControl", fontsize=13, color=(0.2, 0.2, 0.2))
    p4.insert_textbox(
        fitz.Rect(50, 105, 545, 230),
        "VehicleControl is the central application software component responsible for processing sensor data "
        "and generating vehicle control commands. It consumes vehicle speed and engine RPM signals from SensorManager "
        "through VehicleDataInterface.\n"
        "Purpose: Controls vehicle motion based on sensor input.\n"
        "Input Ports: VehicleSpeedIn, EngineRPMIn\n"
        "Output Ports: ControlCommandOut, VehicleStateOut\n"
        "Used Interfaces: VehicleDataInterface\n"
        "Dependencies: SensorManager, DiagnosticManager\n"
        "VehicleControl depends on SensorManager for real-time sensor data acquisition.",
        fontsize=10,
    )
    p4.insert_text(fitz.Point(50, 255), "3.2 SensorManager", fontsize=13, color=(0.2, 0.2, 0.2))
    p4.insert_textbox(
        fitz.Rect(50, 265, 545, 390),
        "SensorManager is responsible for acquiring, filtering, and distributing sensor data from physical sensors. "
        "It produces VehicleSpeed as a float32 signal and EngineRPM as a uint16 signal through VehicleDataInterface.\n"
        "Purpose: Sensor data acquisition and distribution.\n"
        "Input Ports: RawSensorIn\n"
        "Output Ports: VehicleSpeedOut, EngineRPMOut\n"
        "Provided Interfaces: VehicleDataInterface\n"
        "SensorManager produces VehicleSpeed which is consumed by VehicleControl.",
        fontsize=10,
    )

    # Page 5: Components - DiagnosticManager & CommunicationManager
    p5 = doc.new_page(width=595, height=842)
    draw_header_and_warning(p5)
    p5.insert_text(fitz.Point(50, 70), "3.3 DiagnosticManager", fontsize=13, color=(0.2, 0.2, 0.2))
    p5.insert_textbox(
        fitz.Rect(50, 80, 545, 195),
        "DiagnosticManager handles on-board diagnostic (OBD) operations, DTC management, and diagnostic service requests. "
        "It provides diagnostic information through DiagnosticInterface.\n"
        "Purpose: Diagnostic services and DTC management.\n"
        "Ports: DiagnosticRequestIn, DiagnosticResponseOut, DiagnosticStatusOut\n"
        "Provided Interfaces: DiagnosticInterface\n"
        "Dependencies: None (standalone diagnostic provider).",
        fontsize=10,
    )
    p5.insert_text(fitz.Point(50, 220), "3.4 CommunicationManager", fontsize=13, color=(0.2, 0.2, 0.2))
    p5.insert_textbox(
        fitz.Rect(50, 230, 545, 345),
        "CommunicationManager manages external vehicle communication including CAN bus messages and V2X data exchange. "
        "It exchanges vehicle state information through CommunicationInterface.\n"
        "Purpose: External communication management.\n"
        "Ports: CommDataIn, CommDataOut, VehicleStateIn\n"
        "Used Interfaces: CommunicationInterface\n"
        "Dependencies: VehicleControl (receives state data).",
        fontsize=10,
    )

    # Page 6: Interfaces
    p6 = doc.new_page(width=595, height=842)
    draw_header_and_warning(p6)
    p6.insert_text(fitz.Point(50, 70), "4. Interfaces", fontsize=16, color=(0.1, 0.2, 0.4))
    p6.insert_text(fitz.Point(50, 95), "4.1 VehicleDataInterface", fontsize=13, color=(0.2, 0.2, 0.2))
    p6.insert_textbox(
        fitz.Rect(50, 105, 545, 175),
        "Type: Sender-Receiver Interface\n"
        "VehicleDataInterface is a Sender-Receiver interface that carries vehicle sensor data between SensorManager and "
        "consuming components. Signals include VehicleSpeed (float32) and EngineRPM (uint16).\n"
        "Provider: SensorManager\n"
        "Consumer: VehicleControl\n"
        "Signals: VehicleSpeed, EngineRPM",
        fontsize=10,
    )
    next_y = draw_table(
        p6, 185,
        ["Signal", "Data Type", "Unit", "Producer", "Consumer"],
        [
            ["VehicleSpeed", "float32", "km/h", "SensorManager", "VehicleControl"],
            ["EngineRPM", "uint16", "rpm", "SensorManager", "VehicleControl"],
        ],
        [100, 80, 60, 120, 135],
    )
    
    p6.insert_text(fitz.Point(50, next_y + 10), "4.2 DiagnosticInterface", fontsize=13, color=(0.2, 0.2, 0.2))
    p6.insert_textbox(
        fitz.Rect(50, next_y + 20, 545, next_y + 80),
        "Type: Client-Server Interface\n"
        "DiagnosticInterface is a Client-Server interface providing diagnostic services. DiagnosticManager acts as the server.\n"
        "Operations: ReadDTC, ClearDTC, ReadDataByIdentifier",
        fontsize=10,
    )
    p6.insert_text(fitz.Point(50, next_y + 95), "4.3 CommunicationInterface", fontsize=13, color=(0.2, 0.2, 0.2))
    p6.insert_textbox(
        fitz.Rect(50, next_y + 105, 545, next_y + 165),
        "Type: Sender-Receiver Interface\n"
        "CommunicationInterface handles V2X and internal vehicle state communication.\n"
        "Signals: VehicleState, CommStatus",
        fontsize=10,
    )

    # Page 7: Signals and Port Definitions
    p7 = doc.new_page(width=595, height=842)
    draw_header_and_warning(p7)
    p7.insert_text(fitz.Point(50, 70), "5. Signals", fontsize=16, color=(0.1, 0.2, 0.4))
    next_y = draw_table(
        p7, 85,
        ["Signal Name", "Type", "Unit", "Source", "Destination", "Interface"],
        [
            ["VehicleSpeed", "float32", "km/h", "SensorManager", "VehicleControl", "VehicleDataInterface"],
            ["EngineRPM", "uint16", "rpm", "SensorManager", "VehicleControl", "VehicleDataInterface"],
            ["VehicleState", "enum", "-", "VehicleControl", "CommunicationManager", "CommunicationInterface"],
            ["DiagnosticStatus", "uint8", "-", "DiagnosticManager", "VehicleControl", "DiagnosticInterface"],
            ["ControlCommand", "struct", "-", "VehicleControl", "Actuators", "-"],
        ],
        [95, 60, 45, 95, 100, 100],
    )
    
    p7.insert_text(fitz.Point(50, next_y + 10), "6. Port Definitions", fontsize=16, color=(0.1, 0.2, 0.4))
    draw_table(
        p7, next_y + 25,
        ["Port Name", "Component", "Direction", "Interface", "Signals"],
        [
            ["VehicleSpeedIn", "VehicleControl", "Input", "VehicleDataInterface", "VehicleSpeed"],
            ["EngineRPMIn", "VehicleControl", "Input", "VehicleDataInterface", "EngineRPM"],
            ["ControlCommandOut", "VehicleControl", "Output", "-", "ControlCommand"],
            ["VehicleSpeedOut", "SensorManager", "Output", "VehicleDataInterface", "VehicleSpeed"],
            ["DiagnosticRequestIn", "DiagnosticManager", "Input", "DiagnosticInterface", "-"],
            ["DiagnosticResponseOut", "DiagnosticManager", "Output", "DiagnosticInterface", "-"],
        ],
        [110, 95, 60, 115, 115],
    )

    # Page 8: Dependencies and Functional Flows
    p8 = doc.new_page(width=595, height=842)
    draw_header_and_warning(p8)
    p8.insert_text(fitz.Point(50, 70), "7. Dependencies", fontsize=16, color=(0.1, 0.2, 0.4))
    p8.insert_text(fitz.Point(50, 95), "7.1 Component Dependencies", fontsize=13, color=(0.2, 0.2, 0.2))
    p8.insert_textbox(
        fitz.Rect(50, 105, 545, 160),
        "VehicleControl depends on SensorManager for sensor data input.\n"
        "VehicleControl depends on DiagnosticManager for system health monitoring.\n"
        "CommunicationManager depends on VehicleControl for vehicle state information.",
        fontsize=10,
    )
    next_y = draw_table(
        p8, 170,
        ["Source", "Depends On", "Relationship", "Description"],
        [
            ["VehicleControl", "SensorManager", "consumes data", "Receives VehicleSpeed and EngineRPM"],
            ["VehicleControl", "DiagnosticManager", "monitors health", "Receives DiagnosticStatus"],
            ["CommunicationManager", "VehicleControl", "receives state", "Gets vehicle state for V2X broadcast"],
        ],
        [110, 100, 90, 195],
    )
    
    p8.insert_text(fitz.Point(50, next_y + 10), "8. Functional Flows", fontsize=16, color=(0.1, 0.2, 0.4))
    p8.insert_text(fitz.Point(50, next_y + 30), "8.1 Sensor Data Flow", fontsize=12, color=(0.2, 0.2, 0.2))
    p8.insert_textbox(
        fitz.Rect(50, next_y + 40, 545, next_y + 75),
        "Physical sensors -> SensorManager -> VehicleDataInterface -> VehicleControl -> ControlCommand -> Actuators",
        fontsize=10,
    )
    p8.insert_text(fitz.Point(50, next_y + 85), "8.2 Diagnostic Flow", fontsize=12, color=(0.2, 0.2, 0.2))
    p8.insert_textbox(
        fitz.Rect(50, next_y + 95, 545, next_y + 130),
        "External tester -> DiagnosticManager -> DiagnosticInterface -> VehicleControl",
        fontsize=10,
    )
    
    doc.save(str(filepath))
    doc.close()

def build_pdf_v2_fitz(filepath: Path):
    doc = fitz.open()
    
    # Page 1: Title Page
    p1 = doc.new_page(width=595, height=842)
    draw_header_and_warning(p1)
    p1.insert_text(fitz.Point(50, 180), "AUTOSAR High-Level Design Document", fontsize=20, color=(0.1, 0.2, 0.4))
    p1.insert_text(fitz.Point(50, 215), "Vehicle Control System - HLD Specification", fontsize=14, color=(0.3, 0.3, 0.3))
    p1.insert_text(fitz.Point(50, 280), "Version: 2.0", fontsize=11, color=(0, 0, 0))
    p1.insert_text(fitz.Point(50, 305), "Date: 2024-06-20", fontsize=11, color=(0, 0, 0))
    p1.insert_text(fitz.Point(50, 330), "Project: ADAS Vehicle Platform", fontsize=11, color=(0, 0, 0))
    p1.insert_text(fitz.Point(50, 355), "Document ID: AUTOSAR_HLD_v2.0", fontsize=11, color=(0, 0, 0))
    p1.insert_text(fitz.Point(50, 380), "Status: Approved Revision", fontsize=11, color=(0, 0, 0))
    
    # Page 2: Introduction
    p2 = doc.new_page(width=595, height=842)
    draw_header_and_warning(p2)
    p2.insert_text(fitz.Point(50, 70), "1. Introduction", fontsize=16, color=(0.1, 0.2, 0.4))
    p2.insert_text(fitz.Point(50, 95), "1.1 Purpose and Scope", fontsize=12, color=(0.2, 0.2, 0.2))
    p2.insert_textbox(
        fitz.Rect(50, 105, 545, 200),
        "This High-Level Design (HLD) document defines the software architecture of the Vehicle Control System "
        "following the classic AUTOSAR software architecture standard.\n"
        "Version 2.0 adds functional safety monitoring (SafetyManager) and updates signal precision specifications.",
        fontsize=10,
    )
    p2.insert_text(fitz.Point(50, 220), "1.2 References and Standards", fontsize=12, color=(0.2, 0.2, 0.2))
    p2.insert_textbox(
        fitz.Rect(50, 230, 545, 300),
        "References include AUTOSAR Classic Platform Release 4.4.0, ISO 26262 ASIL-D Functional Safety Requirements, "
        "and corporate powertrain electronic control guidelines.",
        fontsize=10,
    )

    # Page 3: System Architecture Overview
    p3 = doc.new_page(width=595, height=842)
    draw_header_and_warning(p3)
    p3.insert_text(fitz.Point(50, 70), "2. System Architecture Overview", fontsize=16, color=(0.1, 0.2, 0.4))
    p3.insert_text(fitz.Point(50, 95), "2.1 Architecture Layers", fontsize=12, color=(0.2, 0.2, 0.2))
    p3.insert_textbox(
        fitz.Rect(50, 105, 545, 175),
        "The software architecture follows the standard three-tier AUTOSAR layer model consisting of the Application Layer "
        "containing Software Components (SWCs), the Runtime Environment (RTE) handling communication abstractions, "
        "and the Basic Software (BSW) managing low-level hardware abstraction and microcontroller drivers.",
        fontsize=10,
    )
    p3.insert_text(fitz.Point(50, 195), "2.2 Component Overview", fontsize=12, color=(0.2, 0.2, 0.2))
    p3.insert_textbox(
        fitz.Rect(50, 205, 545, 310),
        "The system consists of five primary software components:\n"
        "1. VehicleControl: Central application component computing motion control requests.\n"
        "2. SensorManager: Acquires, filters, and broadcasts vehicle telemetry and dynamics.\n"
        "3. DiagnosticManager: Manages DTCs and external diagnostic protocol services.\n"
        "4. CommunicationManager: Manages gateway communication across CAN and V2X networks.\n"
        "5. SafetyManager: Responsible for functional safety monitoring (ISO 26262 ASIL-D) and emergency override.",
        fontsize=10,
    )

    # Page 4: Software Components - VehicleControl & SensorManager
    p4 = doc.new_page(width=595, height=842)
    draw_header_and_warning(p4)
    p4.insert_text(fitz.Point(50, 70), "3. Software Components", fontsize=16, color=(0.1, 0.2, 0.4))
    p4.insert_text(fitz.Point(50, 95), "3.1 VehicleControl", fontsize=13, color=(0.2, 0.2, 0.2))
    p4.insert_textbox(
        fitz.Rect(50, 105, 545, 240),
        "VehicleControl is the central application software component responsible for processing sensor data "
        "and generating vehicle control commands. It consumes vehicle speed and engine RPM signals from SensorManager "
        "through VehicleDataInterface.\n"
        "Purpose: Controls vehicle motion based on sensor input.\n"
        "Input Ports: VehicleSpeedIn, EngineRPMIn, SafetyStatusIn\n"
        "Output Ports: ControlCommandOut, VehicleStateOut\n"
        "Used Interfaces: VehicleDataInterface\n"
        "Dependencies: SensorManager, DiagnosticManager, SafetyManager\n"
        "VehicleControl depends on SensorManager for real-time sensor data acquisition.\n"
        "VehicleControl depends on SafetyManager for safety override commands.",
        fontsize=10,
    )
    p4.insert_text(fitz.Point(50, 260), "3.2 SensorManager", fontsize=13, color=(0.2, 0.2, 0.2))
    p4.insert_textbox(
        fitz.Rect(50, 270, 545, 400),
        "SensorManager is responsible for acquiring, filtering, and distributing sensor data from physical sensors. "
        "It produces VehicleSpeed as a float64 signal, EngineRPM as a uint16 signal, and EngineTemperature as a float32 signal through VehicleDataInterface.\n"
        "Purpose: Sensor data acquisition and distribution.\n"
        "Input Ports: RawSensorIn\n"
        "Output Ports: VehicleSpeedOut, EngineRPMOut\n"
        "Provided Interfaces: VehicleDataInterface\n"
        "SensorManager produces VehicleSpeed which is consumed by VehicleControl.",
        fontsize=10,
    )

    # Page 5: Components - DiagnosticManager, CommunicationManager & SafetyManager
    p5 = doc.new_page(width=595, height=842)
    draw_header_and_warning(p5)
    p5.insert_text(fitz.Point(50, 70), "3.3 DiagnosticManager", fontsize=13, color=(0.2, 0.2, 0.2))
    p5.insert_textbox(
        fitz.Rect(50, 80, 545, 175),
        "DiagnosticManager handles on-board diagnostic (OBD) operations, DTC management, and diagnostic service requests. "
        "It provides diagnostic information through DiagnosticInterface.\n"
        "Purpose: Diagnostic services and DTC management.\n"
        "Ports: DiagnosticRequestIn, DiagnosticResponseOut, DiagnosticStatusOut\n"
        "Provided Interfaces: DiagnosticInterface\n"
        "Dependencies: None (standalone diagnostic provider).",
        fontsize=10,
    )
    p5.insert_text(fitz.Point(50, 195), "3.4 CommunicationManager", fontsize=13, color=(0.2, 0.2, 0.2))
    p5.insert_textbox(
        fitz.Rect(50, 205, 545, 305),
        "CommunicationManager manages external vehicle communication including CAN bus messages and V2X data exchange. "
        "It exchanges vehicle state information through V2XCommunicationInterface.\n"
        "Purpose: External communication management.\n"
        "Ports: CommDataIn, CommDataOut, VehicleStateIn\n"
        "Used Interfaces: V2XCommunicationInterface\n"
        "Dependencies: VehicleControl (receives state data).",
        fontsize=10,
    )
    p5.insert_text(fitz.Point(50, 325), "3.5 SafetyManager", fontsize=13, color=(0.2, 0.2, 0.2))
    p5.insert_textbox(
        fitz.Rect(50, 335, 545, 435),
        "SafetyManager is a newly added component responsible for functional safety monitoring (ISO 26262). "
        "It monitors system integrity and can override control commands if safety violations are detected.\n"
        "Ports: SafetyStatusOut, SystemHealthIn\n"
        "Interfaces: SafetyMonitorInterface",
        fontsize=10,
    )

    # Page 6: Interfaces
    p6 = doc.new_page(width=595, height=842)
    draw_header_and_warning(p6)
    p6.insert_text(fitz.Point(50, 70), "4. Interfaces", fontsize=16, color=(0.1, 0.2, 0.4))
    p6.insert_text(fitz.Point(50, 95), "4.1 VehicleDataInterface", fontsize=13, color=(0.2, 0.2, 0.2))
    p6.insert_textbox(
        fitz.Rect(50, 105, 545, 185),
        "Type: Sender-Receiver Interface\n"
        "VehicleDataInterface is a Sender-Receiver interface that carries vehicle sensor data between SensorManager and "
        "consuming components. Signals include VehicleSpeed (float64), EngineRPM (uint16), and EngineTemperature (float32).\n"
        "Provider: SensorManager\n"
        "Consumer: VehicleControl\n"
        "Signals: VehicleSpeed, EngineRPM, EngineTemperature",
        fontsize=10,
    )
    next_y = draw_table(
        p6, 195,
        ["Signal", "Data Type", "Unit", "Producer", "Consumer"],
        [
            ["VehicleSpeed", "float64", "km/h", "SensorManager", "VehicleControl"],
            ["EngineRPM", "uint16", "rpm", "SensorManager", "VehicleControl"],
            ["EngineTemperature", "float32", "degC", "SensorManager", "VehicleControl"],
        ],
        [100, 80, 60, 120, 135],
    )
    
    p6.insert_text(fitz.Point(50, next_y + 10), "4.2 DiagnosticInterface", fontsize=13, color=(0.2, 0.2, 0.2))
    p6.insert_textbox(
        fitz.Rect(50, next_y + 20, 545, next_y + 70),
        "Type: Client-Server Interface\n"
        "DiagnosticInterface is a Client-Server interface providing diagnostic services. DiagnosticManager acts as the server.\n"
        "Operations: ReadDTC, ClearDTC, ReadDataByIdentifier",
        fontsize=10,
    )
    p6.insert_text(fitz.Point(50, next_y + 80), "4.3 V2XCommunicationInterface", fontsize=13, color=(0.2, 0.2, 0.2))
    p6.insert_textbox(
        fitz.Rect(50, next_y + 90, 545, next_y + 135),
        "Type: Sender-Receiver Interface\n"
        "V2XCommunicationInterface handles V2X and internal vehicle state communication.\n"
        "Signals: VehicleState, CommStatus",
        fontsize=10,
    )
    p6.insert_text(fitz.Point(50, next_y + 145), "4.4 SafetyMonitorInterface", fontsize=13, color=(0.2, 0.2, 0.2))
    p6.insert_textbox(
        fitz.Rect(50, next_y + 155, 545, next_y + 200),
        "Type: Client-Server Interface\n"
        "Signals: SafetyStatus, SystemHealth",
        fontsize=10,
    )

    # Page 7: Signals and Port Definitions
    p7 = doc.new_page(width=595, height=842)
    draw_header_and_warning(p7)
    p7.insert_text(fitz.Point(50, 70), "5. Signals", fontsize=16, color=(0.1, 0.2, 0.4))
    next_y = draw_table(
        p7, 85,
        ["Signal Name", "Type", "Unit", "Source", "Destination", "Interface"],
        [
            ["VehicleSpeed", "float64", "km/h", "SensorManager", "VehicleControl", "VehicleDataInterface"],
            ["EngineRPM", "uint16", "rpm", "SensorManager", "VehicleControl", "VehicleDataInterface"],
            ["EngineTemperature", "float32", "degC", "SensorManager", "VehicleControl", "VehicleDataInterface"],
            ["VehicleState", "enum", "-", "VehicleControl", "CommunicationManager", "V2XCommunicationInterface"],
            ["DiagnosticStatus", "uint8", "-", "DiagnosticManager", "VehicleControl", "DiagnosticInterface"],
            ["ControlCommand", "struct", "-", "VehicleControl", "Actuators", "-"],
        ],
        [95, 60, 45, 95, 100, 100],
    )
    
    p7.insert_text(fitz.Point(50, next_y + 10), "6. Port Definitions", fontsize=16, color=(0.1, 0.2, 0.4))
    draw_table(
        p7, next_y + 25,
        ["Port Name", "Component", "Direction", "Interface", "Signals"],
        [
            ["VehicleSpeedIn", "VehicleControl", "Input", "VehicleDataInterface", "VehicleSpeed"],
            ["EngineRPMIn", "VehicleControl", "Input", "VehicleDataInterface", "EngineRPM"],
            ["SafetyStatusIn", "VehicleControl", "Input", "SafetyMonitorInterface", "SafetyStatus"],
            ["ControlCommandOut", "VehicleControl", "Output", "-", "ControlCommand"],
            ["VehicleSpeedOut", "SensorManager", "Output", "VehicleDataInterface", "VehicleSpeed"],
            ["DiagnosticRequestIn", "DiagnosticManager", "Input", "DiagnosticInterface", "-"],
            ["DiagnosticResponseOut", "DiagnosticManager", "Output", "DiagnosticInterface", "-"],
            ["SafetyStatusOut", "SafetyManager", "Output", "SafetyMonitorInterface", "SafetyStatus"],
        ],
        [110, 95, 60, 115, 115],
    )

    # Page 8: Dependencies and Functional Flows
    p8 = doc.new_page(width=595, height=842)
    draw_header_and_warning(p8)
    p8.insert_text(fitz.Point(50, 70), "7. Dependencies", fontsize=16, color=(0.1, 0.2, 0.4))
    p8.insert_text(fitz.Point(50, 95), "7.1 Component Dependencies", fontsize=13, color=(0.2, 0.2, 0.2))
    p8.insert_textbox(
        fitz.Rect(50, 105, 545, 175),
        "VehicleControl depends on SensorManager for sensor data input.\n"
        "VehicleControl depends on DiagnosticManager for system health monitoring.\n"
        "VehicleControl depends on SafetyManager for safety override commands.\n"
        "CommunicationManager depends on VehicleControl for vehicle state information.",
        fontsize=10,
    )
    next_y = draw_table(
        p8, 185,
        ["Source", "Depends On", "Relationship", "Description"],
        [
            ["VehicleControl", "SensorManager", "consumes data", "Receives VehicleSpeed and EngineRPM"],
            ["VehicleControl", "DiagnosticManager", "monitors health", "Receives DiagnosticStatus"],
            ["VehicleControl", "SafetyManager", "safety override", "Receives SafetyStatus"],
            ["CommunicationManager", "VehicleControl", "receives state", "Gets vehicle state for V2X broadcast"],
        ],
        [110, 100, 90, 195],
    )
    
    p8.insert_text(fitz.Point(50, next_y + 10), "8. Functional Flows", fontsize=16, color=(0.1, 0.2, 0.4))
    p8.insert_text(fitz.Point(50, next_y + 30), "8.1 Sensor Data Flow", fontsize=12, color=(0.2, 0.2, 0.2))
    p8.insert_textbox(
        fitz.Rect(50, next_y + 40, 545, next_y + 75),
        "Physical sensors -> SensorManager -> VehicleDataInterface -> VehicleControl -> ControlCommand -> Actuators",
        fontsize=10,
    )
    p8.insert_text(fitz.Point(50, next_y + 85), "8.2 Diagnostic Flow", fontsize=12, color=(0.2, 0.2, 0.2))
    p8.insert_textbox(
        fitz.Rect(50, next_y + 95, 545, next_y + 130),
        "External tester -> DiagnosticManager -> DiagnosticInterface -> VehicleControl",
        fontsize=10,
    )
    
    doc.save(str(filepath))
    doc.close()

def main():
    base_dir = Path(__file__).resolve().parent.parent
    
    fixtures_v1 = base_dir / "fixtures" / "v1"
    fixtures_v2 = base_dir / "fixtures" / "v2"
    data_raw = base_dir / "data" / "raw"
    
    fixtures_v1.mkdir(parents=True, exist_ok=True)
    fixtures_v2.mkdir(parents=True, exist_ok=True)
    data_raw.mkdir(parents=True, exist_ok=True)
    
    pdf_v1_path = fixtures_v1 / "AUTOSAR_HLD_v1.0.pdf"
    pdf_v2_path = fixtures_v2 / "AUTOSAR_HLD_v2.0.pdf"
    
    build_pdf_v1_fitz(pdf_v1_path)
    build_pdf_v2_fitz(pdf_v2_path)
    
    shutil.copy2(pdf_v1_path, data_raw / "AUTOSAR_HLD_v1.0.pdf")
    shutil.copy2(pdf_v2_path, data_raw / "AUTOSAR_HLD_v2.0.pdf")
    
    print(f"Generated {pdf_v1_path} ({pdf_v1_path.stat().st_size} bytes)")
    print(f"Generated {pdf_v2_path} ({pdf_v2_path.stat().st_size} bytes)")
    print(f"Copied to {data_raw}")

if __name__ == "__main__":
    main()
