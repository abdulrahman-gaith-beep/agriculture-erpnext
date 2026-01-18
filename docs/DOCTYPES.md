# DocType Reference

This document provides detailed documentation for all DocTypes (data models) in the Agriculture module.

## Table of Contents

- [Overview](#overview)
- [Master Data DocTypes](#master-data-doctypes)
  - [Crop](#crop)
  - [Disease](#disease)
  - [Fertilizer](#fertilizer)
  - [Agriculture Analysis Criteria](#agriculture-analysis-criteria)
- [Transactional DocTypes](#transactional-doctypes)
  - [Crop Cycle](#crop-cycle)
  - [Soil Analysis](#soil-analysis)
  - [Water Analysis](#water-analysis)
  - [Plant Analysis](#plant-analysis)
  - [Soil Texture](#soil-texture)
  - [Weather](#weather)
- [Child Table DocTypes](#child-table-doctypes)
  - [Agriculture Task](#agriculture-task)
  - [Linked Location](#linked-location)
  - [Detected Disease](#detected-disease)
  - [Fertilizer Content](#fertilizer-content)
  - [Analysis Criteria Tables](#analysis-criteria-tables)

## Overview

The Agriculture module contains **23 DocTypes** organized into three categories:

| Category | Count | Purpose |
|----------|-------|---------|
| Master Data | 4 | Configuration and reference data |
| Transactional | 6 | Operational records |
| Child Tables | 13 | Supporting data for parent DocTypes |

### Naming Conventions

| DocType | Naming Method | Example |
|---------|---------------|---------|
| Crop | field:title | "Tomato" |
| Disease | field:common_name | "Powdery Mildew" |
| Fertilizer | field:fertilizer_name | "NPK 10-10-10" |
| Crop Cycle | autoname | "CYCLE-00001" |
| Weather | location-date | "WEA-2024-01-15-Field A" |
| Analysis types | autoname | "SA-00001" |

---

## Master Data DocTypes

### Crop

**Purpose**: Defines crop templates with cultivation tasks, spacing requirements, and material specifications.

**File**: `agriculture/agriculture/doctype/crop/crop.py`

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | Data | Yes | Unique identifier/name for the crop |
| `crop_name` | Data | Yes | Common name of the crop |
| `scientific_name` | Data | No | Botanical/Latin name |
| `type` | Select | No | Annual, Perennial, or Biennial |
| `category` | Data | No | Classification category |
| `period` | Int | No | Total cultivation period in days |
| `crop_spacing` | Float | No | Distance between plants |
| `crop_spacing_uom` | Link (UOM) | No | Unit for crop spacing |
| `row_spacing` | Float | No | Distance between rows |
| `row_spacing_uom` | Link (UOM) | No | Unit for row spacing |
| `target_warehouse` | Link (Warehouse) | No | Storage location for produce |
| `planting_uom` | Link (UOM) | No | Unit for planting measurement |
| `planting_area` | Data | No | Area specification |
| `yield_uom` | Link (UOM) | No | Unit for yield measurement |
| `agriculture_task` | Table (Agriculture Task) | Yes | Cultivation task definitions |
| `materials_required` | Table (BOM Item) | No | Input materials needed |
| `produce` | Table (BOM Item) | No | Expected primary outputs |
| `byproducts` | Table (BOM Item) | No | Secondary outputs |

#### Business Logic

```python
class Crop(Document):
    def validate(self):
        self.validate_crop_tasks()

    def validate_crop_tasks(self):
        # Ensure start_day <= end_day for all tasks
        for task in self.agriculture_task:
            if task.start_day > task.end_day:
                frappe.throw(_("Start day is greater than end day in task '{0}'")
                    .format(task.task_name))

        # Auto-calculate period from task end days
        max_crop_period = max([task.end_day for task in self.agriculture_task])
        self.period = max(self.period, max_crop_period)

        # Sort tasks by start day
        self.agriculture_task.sort(key=lambda task: task.start_day)
```

#### Dashboard Links

- Shows linked Crop Cycles

#### Example

```python
crop = frappe.get_doc({
    "doctype": "Crop",
    "title": "Cherry Tomato",
    "crop_name": "Cherry Tomato",
    "scientific_name": "Solanum lycopersicum var. cerasiforme",
    "type": "Annual",
    "period": 90,
    "crop_spacing": 45,
    "crop_spacing_uom": "Centimeter",
    "row_spacing": 90,
    "row_spacing_uom": "Centimeter",
    "agriculture_task": [
        {"task_name": "Prepare soil", "priority": "High", "start_day": 1, "end_day": 3},
        {"task_name": "Sow seeds", "priority": "High", "start_day": 4, "end_day": 4},
        {"task_name": "First watering", "priority": "Medium", "start_day": 4, "end_day": 4},
        {"task_name": "Transplant seedlings", "priority": "High", "start_day": 21, "end_day": 25},
        {"task_name": "Apply fertilizer", "priority": "Medium", "start_day": 35, "end_day": 35},
        {"task_name": "Harvest", "priority": "High", "start_day": 75, "end_day": 90}
    ]
}).insert()
```

---

### Disease

**Purpose**: Documents crop diseases with treatment protocols and tasks.

**File**: `agriculture/agriculture/doctype/disease/disease.py`

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `common_name` | Data | Yes | Common name (used as primary key) |
| `scientific_name` | Data | No | Scientific/pathogen name |
| `treatment_task` | Table (Agriculture Task) | No | Treatment steps |
| `treatment_period` | Int | No | Duration of treatment in days |
| `description` | Long Text | No | Detailed description |

#### Integration with Crop Cycle

When a disease is detected in a Crop Cycle:
1. Disease is added to `detected_disease` table
2. Treatment tasks are automatically created as Project Tasks
3. Tasks are scheduled from the disease detection date

#### Example

```python
disease = frappe.get_doc({
    "doctype": "Disease",
    "common_name": "Powdery Mildew",
    "scientific_name": "Erysiphales",
    "description": "Fungal disease causing white powdery spots on leaves",
    "treatment_period": 14,
    "treatment_task": [
        {"task_name": "Remove infected leaves", "priority": "High", "start_day": 1, "end_day": 1},
        {"task_name": "Apply fungicide", "priority": "High", "start_day": 1, "end_day": 1},
        {"task_name": "Improve air circulation", "priority": "Medium", "start_day": 1, "end_day": 14},
        {"task_name": "Second fungicide application", "priority": "Medium", "start_day": 7, "end_day": 7},
        {"task_name": "Monitor for recurrence", "priority": "Low", "start_day": 8, "end_day": 14}
    ]
}).insert()
```

---

### Fertilizer

**Purpose**: Tracks fertilizer products with detailed nutrient composition.

**File**: `agriculture/agriculture/doctype/fertilizer/fertilizer.py`

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `fertilizer_name` | Data | Yes | Name (used as primary key) |
| `item` | Link (Item) | Yes | ERPNext Item reference |
| `density` | Data | No | Density for liquid fertilizers |
| `fertilizer_contents` | Table (Fertilizer Content) | No | Nutrient composition |

#### ERPNext Integration

- Links to Item master for inventory tracking
- Uses Item's stock UOM and valuation rate
- Can be used in Crop's `materials_required` via BOM Item

#### Example

```python
fertilizer = frappe.get_doc({
    "doctype": "Fertilizer",
    "fertilizer_name": "Complete NPK 15-15-15",
    "item": "FERT-NPK-151515",
    "fertilizer_contents": [
        {"content": "Nitrogen Content", "value": 15.0},
        {"content": "Phosphorous Content", "value": 15.0},
        {"content": "Potassium Content", "value": 15.0},
        {"content": "Calcium Content", "value": 2.5},
        {"content": "Sulphur Content", "value": 1.0}
    ]
}).insert()
```

---

### Agriculture Analysis Criteria

**Purpose**: Configures analysis parameters for all analysis DocTypes.

**File**: `agriculture/agriculture/doctype/agriculture_analysis_criteria/`

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | Data | Yes | Criteria name |
| `standard` | Check | No | Include in default templates |
| `linked_doctype` | Select | No | Associated analysis type |

#### Linked DocType Options

- Fertilizer
- Plant Analysis
- Soil Analysis
- Water Analysis
- Soil Texture
- Weather

#### Standard Criteria (Created at Installation)

**Fertilizer Content** (18 criteria):
- Nitrogen, Phosphorous, Potassium, Calcium, Sulphur, Magnesium
- Iron, Copper, Zinc, Boron, Manganese, Chlorine, Molybdenum, Sodium
- Humic Acid, Fulvic Acid, Inert, Others

**Plant Analysis** (11 criteria):
- Nitrogen, Phosphorous, Potassium, Calcium, Magnesium
- Sulphur, Boron, Copper, Iron, Manganese, Zinc

**Soil Analysis** (21 criteria):
- Depth, pH, Salt Concentration, Organic Matter, CEC
- Saturation percentages (K, Ca, Mn)
- Nutrient levels in ppm (N, P, K, Ca, Mg, S, Cu, Fe, Mn, Zn, Al)

**Water Analysis** (17 criteria):
- pH, Conductivity, Hardness, Turbidity, Odor, Color
- Chemical content (Nitrate, Nitrite, Ca, Mg, Sulphate, B, Cu, Fe, Mn, Zn, Cl)

**Soil Texture** (5 criteria):
- Bulk Density, Field Capacity, Wilting Point, Hydraulic Conductivity, Organic Matter

**Weather** (9 criteria):
- Temperature (High, Low, Average), Dew Point
- Precipitation, Humidity, Pressure, PAR, Degree Days

---

## Transactional DocTypes

### Crop Cycle

**Purpose**: Manages active crop cultivation with automated project generation.

**File**: `agriculture/agriculture/doctype/crop_cycle/crop_cycle.py`

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | Data | Yes | Descriptive name |
| `crop` | Link (Crop) | Yes | Crop template reference |
| `start_date` | Date | Yes | Cultivation start date |
| `project` | Link (Project) | No | Auto-generated project |
| `crop_spacing` | Float | No | Inherited from Crop |
| `crop_spacing_uom` | Link (UOM) | No | Inherited from Crop |
| `row_spacing` | Float | No | Inherited from Crop |
| `row_spacing_uom` | Link (UOM) | No | Inherited from Crop |
| `linked_location` | Table (Linked Location) | No | Field locations |
| `detected_disease` | Table (Detected Disease) | No | Disease tracking |
| `linked_plant_analysis` | Table (Linked Plant Analysis) | No | Analysis links |
| `linked_soil_analysis` | Table (Linked Soil Analysis) | No | Analysis links |

#### Lifecycle Events

```python
class CropCycle(Document):
    def validate(self):
        self.set_missing_values()  # Copy spacing from Crop

    def after_insert(self):
        self.create_crop_cycle_project()  # Create Project + Tasks
        self.create_tasks_for_diseases()

    def on_update(self):
        self.create_tasks_for_diseases()  # Handle new diseases
```

#### Auto-Generated Project

When a Crop Cycle is created:
1. Project created with crop cycle title
2. Start/end dates calculated from crop period
3. All crop tasks converted to Project Tasks
4. Task dates calculated from start_date + task.start_day

#### Whitelisted Methods

```python
@frappe.whitelist()
def reload_linked_analysis(self):
    """Publishes linked analysis data for real-time UI updates."""

@frappe.whitelist()
def append_to_child(self, obj_to_append):
    """Bulk append documents to child tables."""
```

#### Example

```python
crop_cycle = frappe.get_doc({
    "doctype": "Crop Cycle",
    "title": "Spring Tomatoes 2024",
    "crop": "Cherry Tomato",
    "start_date": "2024-03-15",
    "linked_location": [
        {"location": "Field A - North Section"},
        {"location": "Field A - South Section"}
    ]
}).insert()

# Access auto-generated project
print(f"Project created: {crop_cycle.project}")
```

---

### Soil Analysis

**Purpose**: Records soil composition and nutrient analysis results.

**File**: `agriculture/agriculture/doctype/soil_analysis/soil_analysis.py`

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `location` | Link (Location) | No | Sample collection point |
| `collection_datetime` | Datetime | No | When sample was collected |
| `result_datetime` | Datetime | No | When results were received |
| `soil_analysis_criteria` | Table | No | Analysis parameter values |

#### Whitelisted Methods

```python
@frappe.whitelist()
def load_contents(self):
    """Loads standard soil analysis criteria into the criteria table."""
    criteria = frappe.get_all(
        'Agriculture Analysis Criteria',
        filters={'linked_doctype': 'Soil Analysis', 'standard': 1}
    )
    for c in criteria:
        self.append('soil_analysis_criteria', {'criteria': c.name})
```

---

### Water Analysis

**Purpose**: Records water quality testing with datetime validation.

**File**: `agriculture/agriculture/doctype/water_analysis/water_analysis.py`

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `location` | Link (Location) | No | Water source location |
| `collection_datetime` | Datetime | No | Sample collection time |
| `laboratory_testing_datetime` | Datetime | No | Lab testing time |
| `result_datetime` | Datetime | No | Results received time |
| `water_analysis_criteria` | Table | No | Analysis parameter values |

#### Validation Logic

```python
def validate(self):
    # Ensures: collection < testing < result
    if self.collection_datetime > self.laboratory_testing_datetime:
        frappe.throw(_("Collection datetime must be before lab testing"))
    if self.laboratory_testing_datetime > self.result_datetime:
        frappe.throw(_("Lab testing must be before result datetime"))
```

---

### Plant Analysis

**Purpose**: Records plant tissue nutrient analysis.

**File**: `agriculture/agriculture/doctype/plant_analysis/plant_analysis.py`

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `location` | Link (Location) | No | Sample location |
| `collection_datetime` | Datetime | No | Sample collection time |
| `result_datetime` | Datetime | No | Results received time |
| `plant_analysis_criteria` | Table | No | Analysis parameter values |

---

### Soil Texture

**Purpose**: Records physical soil properties.

**File**: `agriculture/agriculture/doctype/soil_texture/soil_texture.py`

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `location` | Link (Location) | No | Sample location |
| `soil_texture_criteria` | Table | No | Property measurements |

#### Standard Criteria

- Bulk Density
- Field Capacity
- Wilting Point
- Hydraulic Conductivity
- Organic Matter

---

### Weather

**Purpose**: Daily weather data recording.

**File**: `agriculture/agriculture/doctype/weather/weather.py`

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `location` | Link (Location) | Yes | Weather station/location |
| `weather_date` | Date | Yes | Recording date |
| `source` | Data | No | Data source (station, API, etc.) |
| `weather_parameter` | Table (Weather Parameter) | No | Measurements |

#### Naming Format

Auto-named as: `WEA-{date}-{location}`

---

## Child Table DocTypes

### Agriculture Task

**Purpose**: Defines tasks for Crop and Disease DocTypes.

**Parent DocTypes**: Crop, Disease

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_name` | Data | Yes | Task description |
| `priority` | Select | No | Low, Medium, High |
| `start_day` | Int | Yes | Start day (1 = first day) |
| `end_day` | Int | Yes | End day |

#### Priority Options

- Low
- Medium
- High

---

### Linked Location

**Purpose**: Associates locations with Crop Cycles.

**Parent DocType**: Crop Cycle

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `location` | Link (Location) | Yes | ERPNext Location reference |

---

### Detected Disease

**Purpose**: Tracks diseases found in Crop Cycles.

**Parent DocType**: Crop Cycle

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `disease` | Link (Disease) | Yes | Disease reference |
| `start_date` | Date | Yes | Detection date |
| `tasks_created` | Check | No | Flag for task generation |

---

### Fertilizer Content

**Purpose**: Nutrient composition entries for fertilizers.

**Parent DocType**: Fertilizer

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | Link (Agriculture Analysis Criteria) | Yes | Nutrient type |
| `value` | Float | No | Percentage or amount |

---

### Analysis Criteria Tables

Child tables for analysis DocTypes share a common structure:

**DocTypes**:
- Soil Analysis Criteria
- Water Analysis Criteria
- Plant Analysis Criteria
- Soil Texture Criteria
- Weather Parameter

#### Common Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `criteria` | Link (Agriculture Analysis Criteria) | Yes | Parameter reference |
| `value` | Float/Data | No | Measured value |

---

## Permission Summary

All DocTypes use consistent role-based permissions:

### Agriculture Manager

| Permission | Crop | Disease | Fertilizer | Analysis | Criteria |
|------------|------|---------|------------|----------|----------|
| Create | Yes | Yes | Yes | Yes | Yes |
| Read | Yes | Yes | Yes | Yes | Yes |
| Write | Yes | Yes | Yes | Yes | Yes |
| Delete | Yes | Yes | Yes | Yes | Yes |
| Export | Yes | Yes | Yes | Yes | Yes |
| Report | Yes | Yes | Yes | Yes | Yes |

### Agriculture User

| Permission | Crop | Disease | Fertilizer | Analysis | Criteria |
|------------|------|---------|------------|----------|----------|
| Create | No | No | No | No | No |
| Read | Yes | Yes | Yes | Yes | Yes |
| Write | Yes | Yes | Yes | Yes | Yes |
| Delete | No | No | No | No | No |
| Export | Yes | Yes | Yes | Yes | Yes |
| Report | Yes | Yes | Yes | Yes | Yes |

---

## API Examples

### REST API

```bash
# List all crops
GET /api/resource/Crop

# Get specific crop
GET /api/resource/Crop/Cherry%20Tomato

# Create crop cycle
POST /api/resource/Crop%20Cycle
Content-Type: application/json
{
    "title": "Spring Planting",
    "crop": "Cherry Tomato",
    "start_date": "2024-03-01"
}

# Update with linked locations
PUT /api/resource/Crop%20Cycle/CYCLE-00001
Content-Type: application/json
{
    "linked_location": [
        {"location": "Field A"}
    ]
}
```

### Python API

```python
import frappe

# Get all crops of a specific type
annual_crops = frappe.get_all(
    'Crop',
    filters={'type': 'Annual'},
    fields=['name', 'crop_name', 'period']
)

# Get crop cycle with child tables
cycle = frappe.get_doc('Crop Cycle', 'CYCLE-00001')
for location in cycle.linked_location:
    print(f"Location: {location.location}")

# Load analysis criteria
analysis = frappe.get_doc('Soil Analysis', 'SA-00001')
analysis.load_contents()
analysis.save()
```

---

For architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md).
For development setup, see [DEVELOPMENT.md](DEVELOPMENT.md).
