# Student Numbers File Format

This document explains how to create a file containing student numbers for use with the `graduating-students` command.

## File Format

The file can contain student numbers in any of these formats:

### One student number per line

```
901001234
901005678
901009999
```

### Comma-separated on one line

```
901001234, 901005678, 901009999
```

### Space-separated on one line

```
901001234 901005678 901009999
```

### Mixed formats

```
901001234
901005678, 901009999
901012345 901015678 901018901

# This is a comment - it will be ignored
901022234
901025678, 901029999, 901032345

# Another comment
901035678 901038901
```

## Features

- **Comments**: Lines starting with `#` are ignored
- **Empty lines**: Blank lines are ignored
- **Duplicates**: Duplicate student numbers are automatically removed
- **Mixed formats**: You can mix different formats in the same file
- **Whitespace**: Extra spaces around numbers are ignored

## Usage Examples

### Using file only

```bash
registry-cli export graduating-students --file student_numbers.txt
```

### Using file with short alias

```bash
registry-cli export graduating-students -f student_numbers.txt
```

### Combining file and command line arguments

```bash
registry-cli export graduating-students --file student_numbers.txt 901888888 901999999
```

## Creating the File

You can create the file using any text editor:

### Windows Notepad

1. Open Notepad
2. Type or paste the student numbers (one per line or comma-separated)
3. Save as `student_numbers.txt`

### Excel Export

1. Put student numbers in column A of Excel
2. Save As → Text (Tab delimited) or CSV
3. The exported file will work with this command

### From Database Query

If you have student numbers from a database query, you can export them directly to a text file.

## Error Handling

The command will show helpful error messages if:

- The file doesn't exist
- The file contains invalid student numbers
- The file cannot be read

Example error:

```
Error reading file student_numbers.txt: Invalid student number 'abc123' on line 5
```
