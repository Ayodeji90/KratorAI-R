#!/usr/bin/env python3
"""Test script to verify category classification implementation."""

import sys
sys.path.insert(0, '/home/machinemustlearn/Desktop/KratorAI/gemini-integration')

from src.services.reasoning_service import CATEGORY_MAPPING

def test_category_mapping():
    """Test that all 22 categories are defined with IDs."""
    print("Testing Category Mapping...")
    print(f"Total categories: {len(CATEGORY_MAPPING)}")
    print("\nCategory mappings:")
    
    for idx, (category_name, category_id) in enumerate(CATEGORY_MAPPING.items(), 1):
        print(f"{idx}. {category_name}: {category_id}")
    
    # Verify all IDs are unique
    unique_ids = set(CATEGORY_MAPPING.values())
    print(f"\nUnique IDs count: {len(unique_ids)}")
    
    if len(unique_ids) == 22:
        print("✅ All category IDs are unique!")
    else:
        print("❌ Duplicate category IDs found!")
        return False
    
    # Verify all names are non-empty
    if all(name.strip() for name in CATEGORY_MAPPING.keys()):
        print("✅ All category names are valid!")
    else:
        print("❌ Some category names are empty!")
        return False
    
    # Verify all IDs are non-empty
    if all(id.strip() for id in CATEGORY_MAPPING.values()):
        print("✅ All category IDs are valid!")
    else:
        print("❌ Some category IDs are empty!")
        return False
    
    print("\n✅ ALL TESTS PASSED!")
    return True

if __name__ == "__main__":
    success = test_category_mapping()
    sys.exit(0 if success else 1)
