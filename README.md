# Agriculture for ERPNext

A comprehensive agriculture management module for ERPNext that provides crop lifecycle management, land tracking, soil/water/plant analysis, disease management, and fertilizer inventory tracking.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Frappe Framework](https://img.shields.io/badge/Framework-Frappe-blue)](https://frappeframework.com)
[![ERPNext](https://img.shields.io/badge/Requires-ERPNext-green)](https://erpnext.com)

## Overview

The Agriculture module extends ERPNext with domain-specific features for managing agricultural operations. It enables farmers, agricultural businesses, and cooperatives to:

- **Manage Crops**: Define crops with scientific information, spacing requirements, and growth tasks
- **Track Crop Cycles**: Monitor complete crop lifecycles from planting to harvest with automated project management
- **Analyze Resources**: Record and track soil, water, plant, and weather analysis data
- **Manage Diseases**: Document crop diseases and treatment protocols
- **Track Fertilizers**: Maintain fertilizer inventory with detailed nutrient composition

## Key Features

### Crop Management
- Define crops with botanical details (common name, scientific name, type)
- Configure planting specifications (crop spacing, row spacing)
- Set up cultivation tasks with scheduling (start/end days, priorities)
- Track material inputs and expected produce/byproducts

### Crop Cycle Orchestration
- Create crop cycles linked to specific locations
- Automatic project and task generation based on crop templates
- Disease detection and treatment task management
- Real-time data publishing for linked analyses

### Comprehensive Analysis
- **Soil Analysis**: pH, nutrients (N, P, K, Ca, Mg), organic matter, CEC
- **Water Analysis**: pH, conductivity, hardness, turbidity, chemical composition
- **Plant Analysis**: Nutrient levels in plant tissue
- **Soil Texture**: Bulk density, field capacity, hydraulic conductivity
- **Weather Tracking**: Temperature, precipitation, humidity, pressure, PAR

### Disease & Fertilizer Management
- Document diseases with treatment protocols
- Auto-generate treatment tasks when diseases are detected
- Track fertilizer inventory with detailed nutrient composition
- Link fertilizers to ERPNext item management

## Installation

### Prerequisites

- Python 3.8+
- [Frappe Bench](https://github.com/frappe/bench)
- [ERPNext](https://github.com/frappe/erpnext) installed and configured

### Install via Bench

1. **Get the Agriculture app**:
   ```bash
   bench get-app https://github.com/frappe/agriculture
   ```

2. **Install on your site**:
   ```bash
   bench --site your-site.local install-app agriculture
   ```

3. **Enable the Agriculture domain** (optional but recommended):
   - Navigate to **Settings > Domain Settings**
   - Add "Agriculture" to the active domains

### Post-Installation Setup

The app automatically creates:
- **60+ standard analysis criteria** for soil, water, plant, weather, and fertilizer analysis
- **Item groups**: Fertilizer, Seed, By-product, Produce
- **Roles**: Agriculture Manager, Agriculture User
- **Location permissions** for agriculture roles

## Project Structure

```
agriculture-erpnext/
├── agriculture/                    # Main application package
│   ├── __init__.py                # Version: 0.0.1
│   ├── hooks.py                   # Frappe app configuration
│   ├── modules.txt                # Module declaration
│   ├── patches.txt                # Database migration patches
│   │
│   ├── agriculture/               # Core module
│   │   ├── setup.py               # Installation/setup logic
│   │   ├── workspace/             # Workspace UI definitions
│   │   │   └── agriculture/
│   │   │       └── agriculture.json
│   │   │
│   │   └── doctype/               # 23 DocTypes (data models)
│   │       ├── crop/              # Crop master data
│   │       ├── crop_cycle/        # Crop lifecycle management
│   │       ├── disease/           # Disease definitions
│   │       ├── fertilizer/        # Fertilizer inventory
│   │       ├── weather/           # Weather tracking
│   │       ├── plant_analysis/    # Plant nutrient analysis
│   │       ├── soil_analysis/     # Soil composition analysis
│   │       ├── water_analysis/    # Water quality analysis
│   │       ├── soil_texture/      # Soil physical properties
│   │       ├── agriculture_analysis_criteria/  # Analysis parameters
│   │       └── [child doctypes]/  # Supporting link tables
│   │
│   ├── config/                    # Application configuration
│   │   ├── desktop.py             # Desktop/sidebar configuration
│   │   └── docs.py                # Documentation configuration
│   │
│   └── templates/                 # Web templates
│
├── setup.py                       # Python package setup
├── requirements.txt               # Dependencies (frappe)
├── MANIFEST.in                    # Package manifest
├── CONTRIBUTING.md                # Contribution guidelines
├── license.txt                    # GNU GPL V3 license
│
└── docs/                          # Documentation
    ├── ARCHITECTURE.md            # System architecture
    ├── DOCTYPES.md                # DocType reference
    └── DEVELOPMENT.md             # Development guide
```

## DocType Overview

### Master Data

| DocType | Description |
|---------|-------------|
| **Crop** | Defines crop types with botanical info, spacing, tasks, inputs, and outputs |
| **Fertilizer** | Fertilizer products with nutrient composition linked to Items |
| **Disease** | Crop diseases with treatment tasks and protocols |
| **Agriculture Analysis Criteria** | Configurable parameters for all analysis types |

### Workflow Documents

| DocType | Description |
|---------|-------------|
| **Crop Cycle** | Manages complete crop lifecycle with project automation |
| **Weather** | Daily weather data recording with location tracking |

### Analysis Documents

| DocType | Description |
|---------|-------------|
| **Soil Analysis** | Soil composition and nutrient analysis |
| **Water Analysis** | Water quality testing with validation |
| **Plant Analysis** | Plant tissue nutrient analysis |
| **Soil Texture** | Physical soil properties (density, hydraulic conductivity) |

### Child Tables (Supporting DocTypes)

| DocType | Parent | Purpose |
|---------|--------|---------|
| Agriculture Task | Crop, Disease | Task definitions with scheduling |
| Linked Location | Crop Cycle | Associates locations with crop cycles |
| Detected Disease | Crop Cycle | Tracks diseases found in crop cycles |
| Fertilizer Content | Fertilizer | Nutrient composition entries |
| Soil/Water/Plant Analysis Criteria | Analysis docs | Analysis parameter values |

## Roles and Permissions

### Agriculture Manager
Full access to all agriculture features:
- Create, read, update, delete all agriculture DocTypes
- Manage locations and spatial data
- Configure analysis criteria
- Export and share reports

### Agriculture User
Standard operational access:
- Read and update existing records
- Create analysis reports
- View dashboards and reports
- Cannot delete records or modify configuration

## Integration with ERPNext

The Agriculture module integrates with core ERPNext features:

- **Project Management**: Crop cycles automatically create Projects and Tasks
- **Inventory**: Fertilizers link to Items; crop inputs/outputs use Item records
- **Warehouse**: Storage locations for agricultural products
- **Location**: Geospatial data for fields and analysis points

## Usage

### Quick Start

1. **Define a Crop**:
   - Go to **Agriculture > Crop**
   - Enter crop details (name, scientific name, type)
   - Add spacing requirements and cultivation tasks

2. **Create a Crop Cycle**:
   - Go to **Agriculture > Crop Cycle**
   - Select the crop and start date
   - Link field locations
   - Save to auto-generate project and tasks

3. **Record Analysis Data**:
   - Navigate to the appropriate analysis type
   - Select location and dates
   - Load standard criteria and enter values

4. **Track Diseases**:
   - Add detected diseases to crop cycles
   - System auto-generates treatment tasks

### Workspace Navigation

Access the Agriculture workspace from the sidebar:

- **Crops & Lands**: Crop, Crop Cycle, Location
- **Analytics**: Plant/Soil/Water Analysis, Soil Texture, Weather, Analysis Criteria
- **Diseases & Fertilizers**: Disease, Fertilizer

## Configuration

### hooks.py

Key configuration in `agriculture/hooks.py`:

```python
# Required ERPNext dependency
required_apps = ["erpnext"]

# Installation hooks
after_install = "agriculture.agriculture.setup.setup_agriculture"
after_uninstall = "agriculture.agriculture.setup.cleanup_role_and_permissions"

# Global search configuration
global_search_doctypes = {
    "Agriculture": [
        {'doctype': 'Crop', 'index': 8},
        {'doctype': 'Crop Cycle', 'index': 10},
        # ... other searchable doctypes
    ]
}

# Domain restriction
domains = {
    'Agriculture': 'agriculture.agriculture.agriculture',
}
```

### Custom Analysis Criteria

Add custom analysis parameters:

1. Go to **Agriculture > Agriculture Analysis Criteria**
2. Create new criteria with:
   - Title (parameter name)
   - Linked DocType (which analysis type uses it)
   - Standard flag (appears in default templates)

## Development

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed development guidelines.

### Running Tests

```bash
# Run all agriculture tests
bench --site your-site.local run-tests --app agriculture

# Run specific doctype tests
bench --site your-site.local run-tests --module agriculture.agriculture.doctype.crop.test_crop
```

### Code Structure

Each DocType follows the standard Frappe pattern:

```
doctype/
└── crop/
    ├── crop.json          # Schema definition
    ├── crop.py            # Server-side logic (Document class)
    ├── crop.js            # Client-side logic
    ├── test_crop.py       # Unit tests
    └── crop_dashboard.py  # Dashboard configuration (optional)
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Areas for Contribution

- Additional analysis criteria for regional requirements
- Weather API integrations
- IoT sensor data import
- Mobile-friendly interfaces
- Reporting and analytics dashboards
- Documentation and translations

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md) - System design and patterns
- [DocType Reference](docs/DOCTYPES.md) - Detailed DocType documentation
- [Development Guide](docs/DEVELOPMENT.md) - Setup and development workflow

## License

This project is licensed under the GNU General Public License v3.0 - see the [license.txt](license.txt) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/frappe/agriculture/issues)
- **Forum**: [Frappe Forum](https://discuss.frappe.io)
- **Documentation**: [ERPNext Documentation](https://docs.erpnext.com)

## Credits

- Developed by [Frappe Technologies](https://frappe.io)
- Built on the [Frappe Framework](https://frappeframework.com)
- Part of the [ERPNext](https://erpnext.com) ecosystem
