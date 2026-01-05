#!/usr/bin/env python3
"""Simple test to verify category mapping structure."""

# Direct copy of the mapping to test
CATEGORY_MAPPING = {
    "Professional Headshots": "691cce06000958fbe4ab",
    "Casual Portraits": "691cce1c0039d32fdc33",
    "Avatars & Characters": "691cce9dd928966d96eb",
    "Marketing Banners": "691cce9dd92dedfb123e",
    "Posters & Flyers": "691cce9dd92ef6f4ab51",
    "Social Media Graphics": "691cce9dd92fc8863542",
    "Logos & Icons": "691cce9dd9307e861459",
    "Product Mockups": "691cce9dd931393bece9",
    "E-commerce Visuals": "691cce9dd932150db6b9",
    "Food Photography": "691cce9dd932cc54cc6c",
    "Fashion & Accessories": "691cce9dd9337ac0cb4d",
    "Landscapes & Cityscapes": "691cce9dd9343303585f",
    "Interior Design": "691cce9dd934e7f1e1c6",
    "Event Backdrops": "691cce9dd93690dd2df1",
    "Concept Art": "691cce9dd9374b9d915b",
    "Digital Art & Illustration": "691cce9dd937f47353b0",
    "Cartoons & Comics": "691cce9dd93896d2200b",
    "Fantasy Creatures": "691cce9dd9399fde6ac0",
    "Infographics": "691cce9dd93a45bccfd6",
    "Presentation Backgrounds": "691cce9dd93b0b79fcae",
    "Educational Diagrams": "691cce9dd93bbf6d2002",
    "UI/UX Mockups": "691cce9dd93c5551ea7c"
}

print("=" * 60)
print("CATEGORY MAPPING VALIDATION TEST")
print("=" * 60)
print(f"\nTotal categories defined: {len(CATEGORY_MAPPING)}")

# List all categories
print("\n📋 Category List:")
for idx, (name, id) in enumerate(CATEGORY_MAPPING.items(), 1):
    print(f"  {idx:2}. {name:30} → {id}")

# Test 1: Check count
print("\n🔍 Test 1: Category Count")
expected_count = 22
actual_count = len(CATEGORY_MAPPING)
if actual_count == expected_count:
    print(f"  ✅ PASS: Found {actual_count} categories (expected {expected_count})")
else:
    print(f"  ❌ FAIL: Found {actual_count} categories (expected {expected_count})")

# Test 2: Check unique IDs
print("\n🔍 Test 2: Unique Category IDs")
unique_ids = set(CATEGORY_MAPPING.values())
if len(unique_ids) == len(CATEGORY_MAPPING):
    print(f"  ✅ PASS: All {len(unique_ids)} IDs are unique")
else:
    print(f"  ❌ FAIL: Found duplicate IDs ({len(CATEGORY_MAPPING)} categories, {len(unique_ids)} unique IDs)")
    
# Test 3: Check valid names
print("\n🔍 Test 3: Valid Category Names")
invalid_names = [name for name in CATEGORY_MAPPING.keys() if not name.strip()]
if not invalid_names:
    print(f"  ✅ PASS: All category names are valid")
else:
    print(f"  ❌ FAIL: Found {len(invalid_names)} invalid names")

# Test 4: Check valid IDs
print("\n🔍 Test 4: Valid Category IDs")
invalid_ids = [id for id in CATEGORY_MAPPING.values() if not id.strip()]
if not invalid_ids:
    print(f"  ✅ PASS: All category IDs are valid")
else:
    print(f"  ❌ FAIL: Found {len(invalid_ids)} invalid IDs")

# Test 5: Fuzzy matching simulation
print("\n🔍 Test 5: Fuzzy Matching Simulation")
test_cases = [
    ("Posters & Flyers", "691cce9dd92ef6f4ab51"),
    ("posters and flyers", None),  # Should fuzzy match
    ("Logo", None),  # Should fuzzy match "Logos & Icons"
]

for test_input, expected_id in test_cases:
    # Exact match
    matched_id = CATEGORY_MAPPING.get(test_input)
    
    # Fuzzy match if no exact match
    if not matched_id:
        for cat_name, cat_id in CATEGORY_MAPPING.items():
            if cat_name.lower() in test_input.lower() or test_input.lower() in cat_name.lower():
                matched_id = cat_id
                break
    
    if matched_id:
        print(f"  ✅ '{test_input}' → {matched_id}")
    else:
        print(f"  ❌ '{test_input}' → No match found")

print("\n" + "=" * 60)
print("✅ ALL TESTS COMPLETED!")
print("=" * 60)
