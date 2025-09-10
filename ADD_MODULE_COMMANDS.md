# Add Module Commands

This document describes the new commands for adding semester modules to students.

## Commands

### `enroll add-module`

Adds a semester module to a student's term using the semester module ID.

**Usage:**

```bash
registry enroll add-module <std_no> <term> <semester_module_id> [--status <status>]
```

**Parameters:**

- `std_no`: Student number (integer)
- `term`: Term name (e.g., "2024-07")
- `semester_module_id`: ID of the semester module to add (integer)
- `--status`: Module status (optional, default: "Add")

**Example:**

```bash
registry enroll add-module 901012345 "2025-02" 15432 --status "Add"
```

### `enroll add-module-by-code`

Adds a semester module to a student's term using the module code. If multiple semester modules exist for the given code, the user will be prompted to select one.

**Usage:**

```bash
registry enroll add-module-by-code <std_no> <term> <module_code> [--status <status>]
```

**Parameters:**

- `std_no`: Student number (integer)
- `term`: Term name (e.g., "2024-07")
- `module_code`: Module code (e.g., "CS 101")
- `--status`: Module status (optional, default: "Add")

**Example:**

```bash
registry enroll add-module-by-code 901012345 "2025-02" "CS 101" --status "Add"
```

## Module Status Options

The available module status values are:

- "Add"
- "Compulsory"
- "Delete"
- "Drop"
- "Exempted"
- "Ineligible"
- "Repeat1" through "Repeat7"
- "Resit1" through "Resit4"
- "Supplementary"

## How It Works

Both commands work by:

1. **Validation**: Checking that the student, term, and module exist in the database
2. **Program Check**: Ensuring the student has an active program
3. **Semester Check**: Verifying the student has a semester for the specified term
4. **Duplicate Check**: Checking if the module is already registered for the student
5. **Web Interface**: Using the existing `r_stdmoduleadd1.php` endpoint (same as `add_modules` in crawler.py)
6. **Verification**: Confirming the module was successfully added

## Implementation Details

The commands use the same web interface mechanism as the existing enrollment system:

- Navigate to the student's module list page
- Access the add module form (`r_stdmoduleadd1.php`)
- Submit the module with the format: `{module_id}-{status}-{credits}-1200`
- Verify successful addition by checking the updated module list

## Error Handling

The commands provide clear error messages for common issues:

- Student not found
- Term not found
- No active program for student
- No semester found for the term
- Module already registered
- Web interface errors

## Dependencies

The new functionality depends on:

- Existing `Crawler` class from `registry_cli.commands.enroll.crawler`
- Database models: `Student`, `StudentProgram`, `StudentSemester`, `SemesterModule`, `Module`, `Term`
- Browser interface from `registry_cli.browser`
