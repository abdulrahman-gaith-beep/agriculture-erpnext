# Development Guide

This guide covers setting up a development environment, understanding the codebase, and contributing to the Agriculture module.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Creating DocTypes](#creating-doctypes)
- [Writing Tests](#writing-tests)
- [Debugging](#debugging)
- [Database Operations](#database-operations)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **OS**: Ubuntu 20.04+ / macOS 10.15+ / Windows with WSL2
- **Python**: 3.10 or 3.11
- **Node.js**: 18.x LTS
- **Database**: MariaDB 10.6+ or PostgreSQL 13+
- **Cache**: Redis 6+
- **Git**: 2.x

### Required Knowledge

- Python fundamentals
- Basic SQL and database concepts
- Understanding of web frameworks (helpful)
- Frappe framework basics (see [Frappe Tutorial](https://frappeframework.com/docs/user/en/tutorial))

## Development Setup

### 1. Install Frappe Bench

```bash
# Install system dependencies (Ubuntu)
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip python3-venv \
    redis-server mariadb-server mariadb-client \
    libmysqlclient-dev git curl

# Install Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install yarn
sudo npm install -g yarn

# Install bench CLI
pip3 install frappe-bench
```

### 2. Initialize Bench

```bash
# Create bench directory
bench init frappe-bench --frappe-branch version-15
cd frappe-bench

# Start required services
sudo systemctl start mariadb
sudo systemctl start redis-server
```

### 3. Create Development Site

```bash
# Create new site
bench new-site agriculture-dev.local --admin-password admin

# Set as default site
bench use agriculture-dev.local
```

### 4. Install ERPNext

```bash
# Get ERPNext app
bench get-app erpnext --branch version-15

# Install ERPNext on site
bench --site agriculture-dev.local install-app erpnext
```

### 5. Clone Agriculture App

```bash
# Clone from your fork
bench get-app agriculture https://github.com/YOUR_USERNAME/agriculture

# Or clone the main repository
bench get-app agriculture https://github.com/frappe/agriculture

# Install on site
bench --site agriculture-dev.local install-app agriculture
```

### 6. Start Development Server

```bash
# Start bench in development mode
bench start
```

Access your site at: `http://agriculture-dev.local:8000`

Default credentials:
- Username: `Administrator`
- Password: `admin` (or what you set)

### 7. Enable Developer Mode

```bash
# Enable developer mode for live reload
bench --site agriculture-dev.local set-config developer_mode 1

# Restart bench
bench start
```

## Project Structure

```
agriculture/
├── __init__.py              # Package version
├── hooks.py                 # App configuration hooks
├── modules.txt              # Module registration
├── patches.txt              # Database migration patches
│
├── agriculture/             # Main module
│   ├── __init__.py
│   ├── setup.py             # Installation/setup logic
│   │
│   ├── doctype/             # DocType definitions
│   │   └── crop/
│   │       ├── crop.json    # Schema (auto-generated)
│   │       ├── crop.py      # Server-side logic
│   │       ├── crop.js      # Client-side logic
│   │       └── test_crop.py # Tests
│   │
│   └── workspace/           # Workspace UI
│       └── agriculture/
│           └── agriculture.json
│
├── config/
│   ├── desktop.py           # Desktop configuration
│   └── docs.py              # Documentation context
│
├── templates/               # Jinja templates
│   ├── generators/          # Web page generators
│   └── includes/            # Reusable template parts
│
└── public/                  # Static assets
    ├── css/
    ├── js/
    └── images/
```

### Key Files

| File | Purpose |
|------|---------|
| `hooks.py` | App configuration, hooks, permissions |
| `modules.txt` | Declares modules in the app |
| `patches.txt` | Database migration patches |
| `setup.py` | Installation/uninstallation logic |
| `doctype/*.json` | DocType schema definitions |
| `doctype/*.py` | Server-side Document classes |
| `doctype/*.js` | Client-side form scripts |

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Edit files in the `apps/agriculture` directory.

### 3. Migrate Database (if needed)

```bash
# After modifying DocType JSON files
bench --site agriculture-dev.local migrate
```

### 4. Clear Cache

```bash
# Clear cache after changes
bench --site agriculture-dev.local clear-cache

# Or use keyboard shortcut in browser
# Ctrl+Shift+R (hard refresh)
```

### 5. Run Tests

```bash
bench --site agriculture-dev.local run-tests --app agriculture
```

### 6. Commit Changes

```bash
git add .
git commit -m "feat: add irrigation scheduling to crop cycle"
```

## Creating DocTypes

### Using CLI

```bash
# Create new DocType
bench --site agriculture-dev.local new-doctype "Irrigation Schedule"
```

### DocType Structure

```
doctype/
└── irrigation_schedule/
    ├── irrigation_schedule.json     # Schema (edit via UI or directly)
    ├── irrigation_schedule.py       # Server logic
    ├── irrigation_schedule.js       # Client logic
    └── test_irrigation_schedule.py  # Tests
```

### Document Class Pattern

```python
# irrigation_schedule.py
import frappe
from frappe import _
from frappe.model.document import Document


class IrrigationSchedule(Document):
    """
    Manages irrigation schedules for crop cycles.

    Attributes:
        crop_cycle: Reference to parent Crop Cycle
        frequency: Irrigation frequency (daily, weekly, etc.)
        volume: Water volume per irrigation
    """

    def validate(self):
        """Called before save. Use for validation logic."""
        self.validate_schedule()
        self.calculate_total_volume()

    def before_save(self):
        """Called before document is saved to database."""
        pass

    def after_insert(self):
        """Called after new document is created."""
        self.create_irrigation_tasks()

    def on_update(self):
        """Called after document is updated."""
        pass

    def on_trash(self):
        """Called before document is deleted."""
        self.cleanup_tasks()

    def validate_schedule(self):
        """Ensure schedule configuration is valid."""
        if self.start_date > self.end_date:
            frappe.throw(_("Start date must be before end date"))

    def calculate_total_volume(self):
        """Calculate total water requirement."""
        # Business logic here
        pass

    @frappe.whitelist()
    def generate_schedule(self):
        """Generate irrigation events. Callable from client."""
        # Implementation
        return {"status": "success"}
```

### Client Script Pattern

```javascript
// irrigation_schedule.js
frappe.ui.form.on('Irrigation Schedule', {
    refresh: function(frm) {
        // Add custom buttons
        if (!frm.is_new()) {
            frm.add_custom_button(__('Generate Schedule'), function() {
                frm.call('generate_schedule').then(r => {
                    frappe.msgprint(__('Schedule generated'));
                    frm.reload_doc();
                });
            });
        }
    },

    crop_cycle: function(frm) {
        // Field change handler
        if (frm.doc.crop_cycle) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Crop Cycle',
                    name: frm.doc.crop_cycle
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('start_date', r.message.start_date);
                    }
                }
            });
        }
    },

    validate: function(frm) {
        // Client-side validation before save
        if (frm.doc.volume <= 0) {
            frappe.throw(__('Volume must be greater than zero'));
        }
    }
});
```

### Adding to Workspace

Edit `agriculture/workspace/agriculture/agriculture.json`:

```json
{
    "links": [
        {
            "type": "Link",
            "label": "Irrigation Schedule",
            "link_to": "Irrigation Schedule",
            "link_type": "DocType",
            "onboard": 0
        }
    ]
}
```

## Writing Tests

### Test File Structure

```python
# test_irrigation_schedule.py
import frappe
from frappe.tests.utils import FrappeTestCase


class TestIrrigationSchedule(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests."""
        super().setUpClass()
        cls.crop = create_test_crop()
        cls.crop_cycle = create_test_crop_cycle(cls.crop.name)

    def setUp(self):
        """Set up before each test."""
        frappe.db.begin()

    def tearDown(self):
        """Clean up after each test."""
        frappe.db.rollback()

    def test_create_schedule(self):
        """Test basic schedule creation."""
        schedule = frappe.get_doc({
            "doctype": "Irrigation Schedule",
            "crop_cycle": self.crop_cycle.name,
            "frequency": "Daily",
            "volume": 100
        }).insert()

        self.assertEqual(schedule.frequency, "Daily")
        self.assertEqual(schedule.volume, 100)

    def test_validation_error(self):
        """Test that validation catches invalid data."""
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc({
                "doctype": "Irrigation Schedule",
                "crop_cycle": self.crop_cycle.name,
                "start_date": "2024-12-31",
                "end_date": "2024-01-01"  # Invalid: end before start
            }).insert()

    def test_total_volume_calculation(self):
        """Test volume calculation logic."""
        schedule = frappe.get_doc({
            "doctype": "Irrigation Schedule",
            "crop_cycle": self.crop_cycle.name,
            "frequency": "Weekly",
            "volume": 500,
            "duration_weeks": 4
        }).insert()

        self.assertEqual(schedule.total_volume, 2000)


def create_test_crop():
    """Helper to create test crop."""
    if frappe.db.exists("Crop", "Test Crop"):
        return frappe.get_doc("Crop", "Test Crop")

    return frappe.get_doc({
        "doctype": "Crop",
        "title": "Test Crop",
        "crop_name": "Test Crop",
        "period": 30,
        "agriculture_task": [
            {"task_name": "Task 1", "start_day": 1, "end_day": 10}
        ]
    }).insert()


def create_test_crop_cycle(crop_name):
    """Helper to create test crop cycle."""
    return frappe.get_doc({
        "doctype": "Crop Cycle",
        "title": "Test Cycle",
        "crop": crop_name,
        "start_date": frappe.utils.today()
    }).insert()
```

### Running Tests

```bash
# All agriculture tests
bench --site agriculture-dev.local run-tests --app agriculture

# Specific module
bench --site agriculture-dev.local run-tests \
    --module agriculture.agriculture.doctype.crop.test_crop

# Specific test class
bench --site agriculture-dev.local run-tests \
    --module agriculture.agriculture.doctype.crop.test_crop \
    --test TestCrop

# With verbose output
bench --site agriculture-dev.local run-tests --app agriculture -v

# With coverage report
bench --site agriculture-dev.local run-tests --app agriculture --coverage
```

## Debugging

### Using Frappe Console

```bash
bench --site agriculture-dev.local console
```

```python
>>> import frappe
>>> crop = frappe.get_doc('Crop', 'Tomato')
>>> print(crop.as_dict())
>>> crop.period = 100
>>> crop.save()
```

### Adding Debug Statements

```python
# In Python code
import frappe

def my_function():
    frappe.log("Debug: Starting function")

    # Log variable values
    frappe.log(f"Variable value: {my_var}")

    # Log to Error Log (visible in UI)
    frappe.log_error("Debug message", "Debug Title")

    # Print to console (development mode)
    print(f"Debug: {my_var}")
```

### Browser DevTools

1. Open Developer Tools (F12)
2. Go to Console tab
3. Use `frappe.` to access Frappe client API

```javascript
// In browser console
frappe.call({
    method: 'frappe.client.get',
    args: {doctype: 'Crop', name: 'Tomato'},
    callback: r => console.log(r.message)
});
```

### VS Code Debug Configuration

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Frappe Web",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/env/bin/gunicorn",
            "args": [
                "-b", "0.0.0.0:8000",
                "-w", "1",
                "-t", "120",
                "frappe.app:application"
            ],
            "cwd": "${workspaceFolder}/sites",
            "env": {
                "DEV_SERVER": "1"
            }
        }
    ]
}
```

## Database Operations

### Using Frappe ORM

```python
import frappe

# Get single document
doc = frappe.get_doc('Crop', 'Tomato')

# Get all documents
crops = frappe.get_all('Crop', filters={'type': 'Annual'}, fields=['name', 'period'])

# Get with child tables
cycles = frappe.get_all(
    'Crop Cycle',
    filters={'crop': 'Tomato'},
    fields=['name', 'start_date', 'linked_location.location']
)

# Create document
new_crop = frappe.get_doc({
    'doctype': 'Crop',
    'title': 'New Crop',
    'crop_name': 'New Crop',
    'agriculture_task': [
        {'task_name': 'Prepare', 'start_day': 1, 'end_day': 3}
    ]
}).insert()

# Update document
doc.period = 100
doc.save()

# Delete document
frappe.delete_doc('Crop', 'New Crop')

# Run SQL (when ORM is insufficient)
result = frappe.db.sql("""
    SELECT name, crop_name, period
    FROM `tabCrop`
    WHERE type = %s
    ORDER BY period DESC
""", ('Annual',), as_dict=True)
```

### Database Migrations (Patches)

Create patch file: `agriculture/patches/v1_1/add_irrigation_fields.py`

```python
import frappe


def execute():
    """Add irrigation fields to Crop Cycle."""
    # Check if field exists
    if not frappe.db.has_column('Crop Cycle', 'irrigation_enabled'):
        frappe.db.add_column('Crop Cycle', 'irrigation_enabled', 'Check')

    # Update existing records
    frappe.db.sql("""
        UPDATE `tabCrop Cycle`
        SET irrigation_enabled = 0
        WHERE irrigation_enabled IS NULL
    """)

    frappe.db.commit()
```

Register in `patches.txt`:

```
agriculture.patches.v1_1.add_irrigation_fields
```

Run migration:

```bash
bench --site agriculture-dev.local migrate
```

## Common Tasks

### Adding a New Analysis Criteria

```python
# In setup.py or via console
frappe.get_doc({
    'doctype': 'Agriculture Analysis Criteria',
    'title': 'New Parameter',
    'standard': 1,
    'linked_doctype': 'Soil Analysis'
}).insert()
```

### Extending Existing DocType

Use Custom Fields (non-destructive):

```python
# Create custom field programmatically
frappe.get_doc({
    'doctype': 'Custom Field',
    'dt': 'Crop Cycle',
    'fieldname': 'custom_notes',
    'fieldtype': 'Small Text',
    'label': 'Custom Notes',
    'insert_after': 'project'
}).insert()
```

### Adding Scheduled Task

In `hooks.py`:

```python
scheduler_events = {
    "daily": [
        "agriculture.tasks.send_weather_alerts"
    ],
    "cron": {
        "0 6 * * *": [  # Every day at 6 AM
            "agriculture.tasks.check_irrigation_schedules"
        ]
    }
}
```

Create task file `agriculture/tasks.py`:

```python
import frappe


def send_weather_alerts():
    """Send weather alerts to users."""
    # Implementation
    pass


def check_irrigation_schedules():
    """Check and process irrigation schedules."""
    # Implementation
    pass
```

## Troubleshooting

### Common Issues

#### Module Import Errors

```bash
# Rebuild assets
bench build

# Clear Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete
```

#### Permission Denied

```bash
# Fix file permissions
sudo chown -R $USER:$USER .
```

#### Database Connection Issues

```bash
# Check MariaDB status
sudo systemctl status mariadb

# Reset database password
mysql -u root -p
ALTER USER 'root'@'localhost' IDENTIFIED BY 'new_password';
```

#### Redis Connection Issues

```bash
# Check Redis status
sudo systemctl status redis-server

# Restart Redis
sudo systemctl restart redis-server
```

#### Migration Failures

```bash
# Check migration status
bench --site agriculture-dev.local show-pending-patches

# Skip failed patch (use carefully)
bench --site agriculture-dev.local migrate --skip-failing
```

### Getting Help

- **Frappe Forum**: [discuss.frappe.io](https://discuss.frappe.io)
- **GitHub Issues**: [github.com/frappe/agriculture/issues](https://github.com/frappe/agriculture/issues)
- **Frappe Documentation**: [frappeframework.com/docs](https://frappeframework.com/docs)
- **ERPNext Documentation**: [docs.erpnext.com](https://docs.erpnext.com)

---

For architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md).
For DocType reference, see [DOCTYPES.md](DOCTYPES.md).
