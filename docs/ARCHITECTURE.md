# Architecture Overview

This document describes the system architecture, design patterns, and technical decisions of the Agriculture module for ERPNext.

## Table of Contents

- [System Overview](#system-overview)
- [Technology Stack](#technology-stack)
- [Module Structure](#module-structure)
- [Data Model](#data-model)
- [Key Design Patterns](#key-design-patterns)
- [Integration Points](#integration-points)
- [Security Model](#security-model)
- [Extension Points](#extension-points)

## System Overview

The Agriculture module is built as a Frappe application that extends ERPNext with domain-specific functionality for agricultural management.

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Desk UI    │  │  Workspace   │  │   Forms & Lists      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                     Agriculture Module                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    DocTypes (23)                        │   │
│  │  ┌─────────┐ ┌────────────┐ ┌─────────────┐ ┌────────┐ │   │
│  │  │  Crop   │ │ Crop Cycle │ │  Analysis   │ │Disease │ │   │
│  │  └─────────┘ └────────────┘ └─────────────┘ └────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                        Frappe Framework                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐    │
│  │   ORM    │  │   REST   │  │  Hooks   │  │  Real-time  │    │
│  └──────────┘  └──────────┘  └──────────┘  └─────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                          ERPNext                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐    │
│  │ Projects │  │  Items   │  │Warehouse │  │  Location   │    │
│  └──────────┘  └──────────┘  └──────────┘  └─────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                        Data Layer                               │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐  │
│  │   MariaDB / PostgreSQL  │  │          Redis              │  │
│  └─────────────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Relationships

```
Crop ──────────────┐
                   │
                   ▼
             Crop Cycle ──────────► Project (ERPNext)
                   │                      │
                   │                      ▼
                   │                   Tasks (ERPNext)
                   │
    ┌──────────────┼──────────────┬──────────────┐
    │              │              │              │
    ▼              ▼              ▼              ▼
Location      Detected       Linked         Weather
              Disease       Analysis        Data
                   │              │
                   ▼              ▼
              Treatment     Soil/Water/
                Tasks      Plant Analysis
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Frappe Desk | Admin interface, forms, lists |
| **Framework** | Frappe | Low-code platform, ORM, API |
| **Backend** | Python 3.8+ | Server-side logic |
| **Database** | MariaDB/PostgreSQL | Data persistence |
| **Cache** | Redis | Sessions, real-time, queues |
| **Web Server** | Nginx + Gunicorn | HTTP serving |
| **Task Queue** | Redis Queue (RQ) | Background jobs |

## Module Structure

### Directory Layout

```
agriculture/
├── __init__.py              # Package init, version
├── hooks.py                 # App configuration
├── modules.txt              # Module registration
├── patches.txt              # Migration patches
│
├── agriculture/             # Core module
│   ├── __init__.py
│   ├── setup.py             # Installation logic
│   │
│   ├── doctype/             # Data models
│   │   ├── crop/
│   │   │   ├── crop.json    # Schema definition
│   │   │   ├── crop.py      # Business logic
│   │   │   ├── crop.js      # Client scripts
│   │   │   └── test_crop.py # Unit tests
│   │   └── ...
│   │
│   └── workspace/           # UI workspace
│       └── agriculture/
│           └── agriculture.json
│
├── config/                  # Configuration
│   ├── desktop.py           # Sidebar config
│   └── docs.py              # Documentation config
│
└── templates/               # Web templates
```

### Module Registration

**modules.txt**
```
Agriculture
```

**hooks.py** (Key configurations)
```python
# App dependency
required_apps = ["erpnext"]

# Installation hooks
after_install = "agriculture.agriculture.setup.setup_agriculture"
after_uninstall = "agriculture.agriculture.setup.cleanup_role_and_permissions"

# Domain-based feature gating
domains = {
    'Agriculture': 'agriculture.agriculture.agriculture',
}

# Global search
global_search_doctypes = {
    "Agriculture": [
        {'doctype': 'Crop', 'index': 8},
        {'doctype': 'Crop Cycle', 'index': 10},
        # ...
    ]
}
```

## Data Model

### Entity Relationship Diagram

```
                    ┌──────────────────────┐
                    │  Agriculture         │
                    │  Analysis Criteria   │
                    │  ──────────────────  │
                    │  title               │
                    │  standard            │
                    │  linked_doctype      │
                    └──────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ Soil Analysis │    │Water Analysis │    │Plant Analysis │
│ ───────────── │    │ ───────────── │    │ ───────────── │
│ location      │    │ collection_dt │    │ location      │
│ collection_dt │    │ lab_result_dt │    │ collection_dt │
│ result_dt     │    │ result_dt     │    │ result_dt     │
│ *criteria[]   │    │ *criteria[]   │    │ *criteria[]   │
└───────────────┘    └───────────────┘    └───────────────┘

┌───────────────┐                         ┌───────────────┐
│    Disease    │                         │  Fertilizer   │
│ ───────────── │                         │ ───────────── │
│ common_name   │                         │ name          │
│ scientific    │                         │ item          │
│ treatment_pd  │                         │ density       │
│ *tasks[]      │                         │ *contents[]   │
└───────────────┘                         └───────────────┘
        │                                         │
        └────────────────┬────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                        Crop                                  │
│ ──────────────────────────────────────────────────────────── │
│ title, crop_name, scientific_name, type                      │
│ crop_spacing, crop_spacing_uom, row_spacing, row_spacing_uom │
│ period, *agriculture_task[], *materials_required[]           │
│ *produce[], *byproducts[]                                    │
└─────────────────────────────────────────────────────────────┘
                         │
                         │ creates
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     Crop Cycle                               │
│ ──────────────────────────────────────────────────────────── │
│ title, crop, start_date, project                             │
│ crop_spacing, row_spacing + UOMs                             │
│ *linked_location[], *detected_disease[]                      │
│ *linked_plant_analysis[], *linked_soil_analysis[]            │
└─────────────────────────────────────────────────────────────┘
        │                                         │
        │ generates                               │ links to
        ▼                                         ▼
┌───────────────┐                         ┌───────────────┐
│    Project    │                         │   Location    │
│   (ERPNext)   │                         │   (ERPNext)   │
│ ───────────── │                         │ ───────────── │
│ project_name  │                         │ name          │
│ start_date    │                         │ location      │
│ end_date      │                         │ (geojson)     │
└───────────────┘                         └───────────────┘
        │
        ▼
┌───────────────┐
│     Task      │
│   (ERPNext)   │
│ ───────────── │
│ subject       │
│ priority      │
│ start_date    │
│ end_date      │
└───────────────┘
```

### DocType Categories

#### Master Data (Configuration)

| DocType | Primary Key | Description |
|---------|-------------|-------------|
| Crop | Name (title) | Crop templates with tasks and materials |
| Disease | Name | Disease definitions with treatments |
| Fertilizer | Name | Fertilizer products with composition |
| Agriculture Analysis Criteria | Name | Analysis parameters configuration |

#### Transactional Data

| DocType | Primary Key | Description |
|---------|-------------|-------------|
| Crop Cycle | Auto-named | Active crop cultivation records |
| Soil Analysis | Auto-named | Soil test results |
| Water Analysis | Auto-named | Water quality results |
| Plant Analysis | Auto-named | Plant nutrient analysis |
| Weather | Location+Date | Daily weather data |
| Soil Texture | Name | Soil physical properties |

#### Child Tables (Table Fields)

| DocType | Parent(s) | Purpose |
|---------|-----------|---------|
| Agriculture Task | Crop, Disease | Task definitions |
| Linked Location | Crop Cycle | Location associations |
| Detected Disease | Crop Cycle | Disease tracking |
| Fertilizer Content | Fertilizer | Nutrient entries |
| Soil Analysis Criteria | Soil Analysis | Analysis values |
| Water Analysis Criteria | Water Analysis | Analysis values |
| Plant Analysis Criteria | Plant Analysis | Analysis values |
| Soil Texture Criteria | Soil Texture | Property values |
| Weather Parameter | Weather | Weather measurements |

## Key Design Patterns

### 1. Template-Instance Pattern (Crop → Crop Cycle)

Crops serve as templates, while Crop Cycles are instances:

```python
# Crop defines the template
class Crop(Document):
    def validate_crop_tasks(self):
        # Sort and validate task definitions
        self.agriculture_task.sort(key=lambda task: task.start_day)

# Crop Cycle creates instances from template
class CropCycle(Document):
    def set_missing_values(self):
        crop = frappe.get_doc('Crop', self.crop)
        # Copy template values
        if not self.crop_spacing_uom:
            self.crop_spacing_uom = crop.crop_spacing_uom
```

### 2. Automatic Project Generation

Crop cycles automatically generate ERPNext Projects and Tasks:

```python
class CropCycle(Document):
    def after_insert(self):
        self.create_crop_cycle_project()
        self.create_tasks_for_diseases()

    def create_project(self, period, crop_tasks):
        project = frappe.get_doc({
            "doctype": "Project",
            "project_name": self.title,
            "expected_start_date": self.start_date,
            "expected_end_date": add_days(self.start_date, period - 1)
        }).insert()
        return project.name

    def create_task(self, crop_tasks, project_name, start_date):
        for crop_task in crop_tasks:
            frappe.get_doc({
                "doctype": "Task",
                "subject": crop_task.get("task_name"),
                "priority": crop_task.get("priority"),
                "project": project_name,
                "exp_start_date": add_days(start_date, crop_task.get("start_day") - 1),
                "exp_end_date": add_days(start_date, crop_task.get("end_day") - 1)
            }).insert()
```

### 3. Dynamic Criteria Loading

Analysis documents dynamically load criteria based on configuration:

```python
class SoilAnalysis(Document):
    @frappe.whitelist()
    def load_contents(self):
        # Load all standard criteria for this DocType
        criteria = frappe.get_all(
            'Agriculture Analysis Criteria',
            filters={'linked_doctype': 'Soil Analysis', 'standard': 1},
            fields=['name', 'title']
        )
        for criterion in criteria:
            self.append('soil_analysis_criteria', {
                'criteria': criterion.name,
                'title': criterion.title
            })
```

### 4. Real-Time Data Publishing

Crop cycles publish updates for real-time UI refresh:

```python
@frappe.whitelist()
def reload_linked_analysis(self):
    linked_doctypes = ['Soil Texture', 'Soil Analysis', 'Plant Analysis']
    output = {}

    for doctype in linked_doctypes:
        output[doctype] = frappe.get_all(doctype, fields=required_fields)

    # Publish to connected clients
    frappe.publish_realtime(
        "List of Linked Docs",
        output,
        user=frappe.session.user
    )
```

### 5. Geospatial Point-in-Polygon Detection

The module includes utilities for geospatial calculations:

```python
def get_coordinates(doc):
    """Extract coordinates from GeoJSON location data."""
    return ast.literal_eval(doc.location).get('features')[0] \
        .get('geometry').get('coordinates')

def is_in_location(point, vs):
    """Ray-casting algorithm for point-in-polygon detection."""
    x, y = point
    inside = False
    j = len(vs) - 1
    for i in range(len(vs)):
        xi, yi = vs[i]
        xj, yj = vs[j]
        intersect = ((yi > y) != (yj > y)) and \
            (x < (xj - xi) * (y - yi) / (yj - yi) + xi)
        if intersect:
            inside = not inside
        j = i
    return inside
```

## Integration Points

### ERPNext Modules

| Module | Integration |
|--------|-------------|
| **Projects** | Crop cycles create Projects; tasks become Project Tasks |
| **Stock** | Fertilizers link to Items; warehouses for produce |
| **Assets** | Locations can represent land assets |
| **Setup** | Uses Item Groups, UOMs, Locations |

### External Integration Opportunities

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Weather APIs   │    │   IoT Sensors   │    │   GIS Systems   │
│  ─────────────  │    │  ─────────────  │    │  ─────────────  │
│  OpenWeather    │    │  Soil moisture  │    │  Satellite      │
│  AccuWeather    │    │  Weather        │    │  Field maps     │
│  Local services │    │  stations       │    │  Crop imagery   │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │  Agriculture Module │
                    └─────────────────────┘
```

### API Endpoints

All DocType operations available via REST API:

```bash
# Create a crop
POST /api/resource/Crop
{
    "title": "Tomato",
    "crop_name": "Tomato",
    "scientific_name": "Solanum lycopersicum"
}

# List crop cycles
GET /api/resource/Crop Cycle?filters=[["crop","=","Tomato"]]

# Execute whitelisted methods
POST /api/method/frappe.client.get
{
    "doctype": "Crop Cycle",
    "name": "CYCLE-00001"
}
```

## Security Model

### Role-Based Access Control

```
┌─────────────────────────────────────────────────────────────┐
│                   Agriculture Manager                        │
│  ─────────────────────────────────────────────────────────  │
│  Full CRUD on all Agriculture DocTypes                       │
│  Configure analysis criteria                                 │
│  Manage locations                                            │
│  Export, print, share all data                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ inherits
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agriculture User                          │
│  ─────────────────────────────────────────────────────────  │
│  Read/Write (no Create/Delete)                               │
│  View reports and dashboards                                 │
│  Export and print data                                       │
│  Limited location access                                     │
└─────────────────────────────────────────────────────────────┘
```

### Permission Matrix

| DocType | Manager | User |
|---------|---------|------|
| Crop | CRUD | RU |
| Crop Cycle | CRUD | RU |
| Disease | CRUD | RU |
| Fertilizer | CRUD | RU |
| Soil Analysis | CRUD | RU |
| Water Analysis | CRUD | RU |
| Plant Analysis | CRUD | RU |
| Weather | CRUD | RU |
| Location | CRUD | RU |
| Analysis Criteria | CRUD | R |

### Domain-Based Feature Gating

The module restricts visibility to users with the "Agriculture" domain enabled:

```python
# hooks.py
domains = {
    'Agriculture': 'agriculture.agriculture.agriculture',
}
```

## Extension Points

### Adding New Analysis Types

1. Create new DocType with criteria child table
2. Add criteria records in setup.py
3. Register in workspace JSON
4. Add to global search configuration

### Custom Hooks

Extend behavior without modifying core code:

```python
# In your custom app's hooks.py
doc_events = {
    "Crop Cycle": {
        "after_insert": "my_app.handlers.on_crop_cycle_created",
        "on_update": "my_app.handlers.on_crop_cycle_updated"
    }
}
```

### Custom Fields

Add fields via Customize Form without modifying DocType JSON:

```python
# Programmatic custom field
frappe.get_doc({
    "doctype": "Custom Field",
    "dt": "Crop Cycle",
    "fieldname": "custom_irrigation_schedule",
    "fieldtype": "Link",
    "options": "Irrigation Schedule"
}).insert()
```

### Scheduled Tasks

Add background processing:

```python
# hooks.py
scheduler_events = {
    "daily": [
        "agriculture.tasks.check_weather_alerts"
    ],
    "hourly": [
        "agriculture.tasks.sync_iot_data"
    ]
}
```

## Performance Considerations

### Database Indexes

Key fields are indexed for query performance:
- Foreign keys (crop in Crop Cycle)
- Date fields (start_date, collection_datetime)
- Status fields

### Caching Strategy

- DocType metadata cached by Frappe
- Analysis criteria can be cached for form load
- Real-time updates reduce polling overhead

### Batch Operations

For large-scale operations:

```python
# Use frappe.enqueue for background processing
frappe.enqueue(
    'agriculture.tasks.bulk_create_analysis',
    queue='long',
    locations=location_list
)
```

## Monitoring and Logging

### Standard Frappe Logging

```python
import frappe

# Info logging
frappe.log("Crop cycle created: {0}".format(self.name))

# Error logging
frappe.log_error(
    message=frappe.get_traceback(),
    title="Crop Cycle Creation Failed"
)
```

### Error Tracking

Errors logged to Error Log DocType, accessible via:
- **Help > Error Log** in desk
- API: `GET /api/resource/Error Log`

---

For development setup and contribution guidelines, see [DEVELOPMENT.md](DEVELOPMENT.md).
