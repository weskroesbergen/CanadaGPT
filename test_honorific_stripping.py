#!/usr/bin/env python3
"""Test honorific stripping logic."""

# Test the honorific stripping logic
test_names = [
    ("Anand, Hon. Anita", "Anita Anand"),
    ("Anandasangaree, Hon. Gary", "Gary Anandasangaree"),
    ("Alty, Hon. Rebecca", "Rebecca Alty"),
    ("Acan,  Sima", "Sima Acan"),  # Extra space
    ("Al Soud,  Fares", "Fares Al Soud"),
    ("Poilievre, Hon. Pierre", "Pierre Poilievre"),
]

honorifics = ["Hon.", "Rt. Hon.", "Dr.", "Rev.", "Prof.", "Mr.", "Mrs.", "Ms.", "Miss"]

print("=" * 80)
print("TESTING HONORIFIC STRIPPING")
print("=" * 80)

for csv_name, expected in test_names:
    # Parse name from "LastName, FirstName" format to "FirstName LastName"
    if "," in csv_name:
        parts = csv_name.split(",")
        if len(parts) == 2:
            last_name = parts[0].strip()
            first_name = parts[1].strip()
            normalized_name = f"{first_name} {last_name}"
        else:
            normalized_name = csv_name.strip()
    else:
        normalized_name = csv_name.strip()

    # Strip honorifics/titles from the name
    for honorific in honorifics:
        normalized_name = normalized_name.replace(honorific, "").strip()
    # Clean up extra spaces
    normalized_name = " ".join(normalized_name.split())

    status = "✅ MATCH" if normalized_name == expected else "❌ FAIL"
    print(f"\n  CSV: '{csv_name}'")
    print(f"  Normalized: '{normalized_name}'")
    print(f"  Expected: '{expected}'")
    print(f"  {status}")

print("\n" + "=" * 80)
