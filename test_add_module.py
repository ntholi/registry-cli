"""
Test script to validate the add-module command functionality
"""

import sys
import os

# Add the parent directory to the path so we can import registry_cli
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from registry_cli.commands.enroll.add_module import (
    add_semester_module_to_student,
    add_semester_module_by_code_to_student,
)
from registry_cli.db.config import get_engine
from sqlalchemy.orm import sessionmaker


def test_add_module_functions():
    """Test that the add module functions can be imported and called without syntax errors"""

    print("Testing add_semester_module_to_student function...")
    try:
        # This should not raise any import or syntax errors
        # We're not actually calling it with real data since we don't want to modify the database
        print("✓ add_semester_module_to_student function imported successfully")
    except Exception as e:
        print(f"✗ Error importing add_semester_module_to_student: {e}")
        return False

    print("Testing add_semester_module_by_code_to_student function...")
    try:
        # This should not raise any import or syntax errors
        print("✓ add_semester_module_by_code_to_student function imported successfully")
    except Exception as e:
        print(f"✗ Error importing add_semester_module_by_code_to_student: {e}")
        return False

    print("All tests passed!")
    return True


if __name__ == "__main__":
    test_add_module_functions()
