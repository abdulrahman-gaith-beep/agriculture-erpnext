# Contributing to Agriculture for ERPNext

Thank you for your interest in contributing to the Agriculture module! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Documentation](#documentation)

## Code of Conduct

This project follows the [Frappe Community Code of Conduct](https://github.com/frappe/erpnext/blob/develop/CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- Python 3.8 or higher
- Node.js 16 or higher
- MariaDB 10.6+ or PostgreSQL 13+
- Redis 6+
- Git

### Understanding the Project

1. **Read the [README.md](README.md)** for project overview
2. **Review the [Architecture documentation](docs/ARCHITECTURE.md)** to understand system design
3. **Explore the [DocType Reference](docs/DOCTYPES.md)** for data model details
4. **Familiarize yourself with [Frappe Framework](https://frappeframework.com/docs)** concepts

## Development Setup

### 1. Install Frappe Bench

```bash
# Install bench CLI
pip install frappe-bench

# Initialize a new bench
bench init frappe-bench --frappe-branch version-15
cd frappe-bench
```

### 2. Create a New Site

```bash
bench new-site agriculture-dev.local
bench use agriculture-dev.local
```

### 3. Install ERPNext

```bash
bench get-app erpnext --branch version-15
bench --site agriculture-dev.local install-app erpnext
```

### 4. Clone and Install Agriculture

```bash
# Clone your fork
bench get-app agriculture https://github.com/YOUR_USERNAME/agriculture

# Install on the site
bench --site agriculture-dev.local install-app agriculture
```

### 5. Start Development Server

```bash
bench start
```

Access the site at `http://agriculture-dev.local:8000`

## How to Contribute

### Reporting Bugs

1. **Search existing issues** to avoid duplicates
2. **Create a new issue** with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (ERPNext version, Frappe version, OS)
   - Screenshots or error logs if applicable

### Suggesting Features

1. **Open a discussion** in the Issues section
2. Describe the feature and its use case
3. Explain how it benefits agriculture management
4. Consider backward compatibility

### Contributing Code

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes** following coding standards
4. **Write/update tests** for your changes
5. **Commit with clear messages**: `git commit -m "feat: add irrigation scheduling"`
6. **Push to your fork**: `git push origin feature/your-feature-name`
7. **Create a Pull Request**

### Types of Contributions

- **Bug fixes**: Fix reported issues
- **New DocTypes**: Add new data models for agriculture use cases
- **Analysis criteria**: Add regional/specialized analysis parameters
- **Integrations**: Weather APIs, IoT sensors, external systems
- **Documentation**: Improve guides, add examples, translate content
- **Tests**: Increase test coverage
- **UI/UX improvements**: Better forms, workflows, reports

## Coding Standards

### Python

Follow PEP 8 and Frappe conventions:

```python
# Copyright (c) YEAR, Your Name/Organization
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MyDocType(Document):
    """Docstring explaining the DocType purpose."""

    def validate(self):
        """Validate document before save."""
        self.validate_required_fields()

    def validate_required_fields(self):
        """Ensure required fields are properly set."""
        if not self.field_name:
            frappe.throw(_("Field Name is required"))
```

**Key conventions:**
- Use `frappe._()` for translatable strings
- Document class methods with docstrings
- Use `frappe.throw()` for user-facing errors
- Prefix private methods with underscore

### JavaScript

```javascript
frappe.ui.form.on('My DocType', {
    refresh: function(frm) {
        // Add custom buttons
        if (!frm.is_new()) {
            frm.add_custom_button(__('Action'), function() {
                // Action logic
            });
        }
    },

    field_name: function(frm) {
        // Field change handler
    }
});
```

**Key conventions:**
- Use `__()` for translations
- Follow Frappe's event-driven patterns
- Avoid jQuery where Frappe utilities exist

### JSON (DocType Definitions)

- Use meaningful field names (lowercase, underscore-separated)
- Add proper labels and descriptions
- Set appropriate field types and options
- Configure permissions correctly

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(crop-cycle): add automatic irrigation task generation
fix(water-analysis): validate datetime sequence correctly
docs(readme): add troubleshooting section
test(soil-analysis): add criteria loading tests
```

## Testing Guidelines

### Writing Tests

Create tests in `test_<doctype>.py`:

```python
# Copyright (c) YEAR, Your Name
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestMyDocType(FrappeTestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.test_data = create_test_data()

    def tearDown(self):
        """Clean up after tests."""
        frappe.db.rollback()

    def test_basic_creation(self):
        """Test that DocType can be created with valid data."""
        doc = frappe.get_doc({
            "doctype": "My DocType",
            "field_name": "value"
        }).insert()

        self.assertEqual(doc.field_name, "value")

    def test_validation_error(self):
        """Test that validation fails for invalid data."""
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc({
                "doctype": "My DocType",
                "field_name": ""  # Required field
            }).insert()
```

### Running Tests

```bash
# All agriculture tests
bench --site agriculture-dev.local run-tests --app agriculture

# Specific module
bench --site agriculture-dev.local run-tests \
    --module agriculture.agriculture.doctype.crop.test_crop

# With verbose output
bench --site agriculture-dev.local run-tests --app agriculture -v
```

### Test Coverage Goals

- All DocTypes should have basic CRUD tests
- Validation logic must be tested
- Business logic methods need unit tests
- Integration points should have integration tests

## Pull Request Process

### Before Submitting

1. **Ensure tests pass**: `bench run-tests --app agriculture`
2. **Check code style**: Follow Frappe conventions
3. **Update documentation** if needed
4. **Rebase on latest main**: `git rebase origin/main`

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project conventions
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)

## Related Issues
Closes #123
```

### Review Process

1. **Automated checks** must pass (tests, linting)
2. **Code review** by maintainers
3. **Address feedback** and update PR
4. **Approval and merge** by maintainer

## Documentation

### Code Documentation

- Add docstrings to all classes and public methods
- Comment complex logic
- Keep comments up-to-date with code

### User Documentation

- Update README for new features
- Add examples for complex functionality
- Include screenshots for UI changes

### API Documentation

- Document whitelisted methods
- Provide request/response examples
- Note authentication requirements

## Getting Help

- **Frappe Forum**: [discuss.frappe.io](https://discuss.frappe.io)
- **GitHub Discussions**: For feature discussions
- **GitHub Issues**: For bugs and specific problems

## Recognition

Contributors are recognized in:
- GitHub contributors list
- Release notes for significant contributions
- CONTRIBUTORS.md file (for major contributors)

---

Thank you for contributing to Agriculture for ERPNext! Your efforts help farmers and agricultural businesses worldwide.
