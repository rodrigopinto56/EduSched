# Overview

This is an academic schedule generation system built with Streamlit. The application helps educational institutions create optimized class schedules by considering various constraints such as teacher availability, classroom capacity, student enrollment, and semester priorities. The system provides an interactive web interface for uploading course data, generating schedules, and exporting results in various formats including PDF reports and visual calendars.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture

**Technology**: Streamlit web framework
- **Rationale**: Provides rapid development of interactive data applications with minimal frontend code
- **Approach**: Single-page application with session state management for maintaining user data across interactions
- **Key Features**: 
  - File upload capabilities for batch data input
  - Interactive data editing with data editors
  - Real-time schedule visualization
  - Export functionality for generated schedules

**Session State Management**
- Stores generated schedules, group data, teacher data, and classroom data
- Maintains edited schedule state to preserve user modifications
- Enables multi-step workflow without data loss

## Backend Architecture

**Processing Logic**: Python-based schedule generation algorithm
- **Core Algorithm**: Constraint-based scheduling with semester prioritization
- **Approach**: Processes groups in order of semester priority (higher semesters scheduled first)
- **Constraints Handled**:
  - Teacher availability conflicts
  - Classroom capacity matching
  - Session distribution across week
  - Time slot availability
  - Duration requirements

**Time Management**
- Operating hours: 7 AM to 9 PM
- Configurable session durations
- Support for multi-hour class blocks

## Data Storage

**In-Memory Storage**: Session-based data persistence
- **Rationale**: Simplifies deployment and eliminates database setup requirements for small-scale use
- **Limitation**: Data is not persisted between sessions
- **Data Structures**: Pandas DataFrames for tabular data manipulation

**Data Models**:
1. **Groups**: Course sections with metadata (semester, teacher, duration, frequency, enrollment)
2. **Teachers**: Instructor information and assigned courses
3. **Classrooms**: Room details including capacity
4. **Schedules**: Generated timetables with day/time slot assignments

## Report Generation

**PDF Export**: ReportLab library
- **Format**: Letter size, landscape orientation for schedule tables
- **Content**: Formatted tables with styling and metadata
- **Rationale**: Provides professional, printable output for administrative use

**Visual Calendar**: Plotly graphs
- **Type**: Interactive Gantt-style timeline visualization
- **Features**: Color-coded by group, hover information, zoomable interface
- **Rationale**: Enables quick visual verification of schedule conflicts and distribution

# External Dependencies

## Core Libraries

1. **Streamlit** - Web application framework
   - Purpose: Primary UI framework for the application
   - Features used: File uploads, data editors, session state, layout components

2. **Pandas** - Data manipulation
   - Purpose: Tabular data processing and CSV handling
   - Use cases: Schedule data structures, import/export operations

3. **ReportLab** - PDF generation
   - Purpose: Professional report creation
   - Components: SimpleDocTemplate, Table layouts, styling

4. **Plotly** - Data visualization
   - Purpose: Interactive schedule timeline visualization
   - Chart type: Gantt/timeline charts for schedule display

## Python Standard Library

- **datetime/time/timedelta**: Time-based calculations and schedule slot management
- **io**: In-memory file handling for PDF generation and downloads

## No External Services

- No database connections (uses in-memory storage)
- No authentication services (single-user application)
- No external APIs or cloud services
- No third-party scheduling services
