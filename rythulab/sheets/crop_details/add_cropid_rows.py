#!/usr/bin/env python3
"""
Script to add CropID rows to all crop detail CSV files.
Matches crop names in headers with crop IDs from the crop list.
"""

import csv
import os
import re
from pathlib import Path
from typing import Dict, Optional

DEFAULT_CROP_LIST = "0.List of All crops - Sheet1.csv"


def normalize_crop_name(name: str) -> str:
    """Normalize crop name for matching: lowercase, remove punctuation, handle variants."""
    name = name.lower().strip()
    # Remove common suffixes and variations
    name = re.sub(r'\s*\(.*?\)', '', name)  # Remove parenthetical info
    name = re.sub(r'\s*\/.*$', '', name)  # Remove "/" variants
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def build_crop_id_map(crop_list_file: str) -> Dict[str, str]:
    """
    Build a mapping from normalized crop names to crop IDs.
    Returns: {normalized_crop_name: crop_id}
    """
    crop_map = {}
    
    with open(crop_list_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            crop_id = row.get('CropID', '').strip()
            crop_name = row.get('Crop Name', '').strip()
            if crop_id and crop_name:
                normalized = normalize_crop_name(crop_name)
                crop_map[normalized] = crop_id
    
    return crop_map


def find_crop_id(column_header: str, crop_map: Dict[str, str]) -> Optional[str]:
    """
    Find the crop ID for a column header.
    Returns crop ID if found, None otherwise.
    """
    normalized = normalize_crop_name(column_header)
    
    # Direct match
    if normalized in crop_map:
        return crop_map[normalized]
    
    # Try partial matching (for headers like "Finger Millet" matching "Finger Millet (Ragi)")
    for key, crop_id in crop_map.items():
        if normalized in key or key in normalized:
            return crop_id
    
    return None


def add_cropid_row_to_file(file_path: str, crop_map: Dict[str, str]) -> tuple:
    """
    Add CropID row to a crop detail CSV file.
    Returns: (success: bool, message: str)
    """
    try:
        # Read the entire file
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        if not rows:
            return False, "Empty file"
        
        # Extract header (first row after "Parameter" column)
        header_row = rows[0]
        
        # Check if CropID row already exists
        if rows[1][0].lower() == 'cropid':
            return False, "CropID row already exists"
        
        # Create CropID row
        crop_id_row = ['CropID']
        unmatched = []
        
        for i, crop_name in enumerate(header_row[1:], start=1):
            crop_id = find_crop_id(crop_name, crop_map)
            if crop_id:
                crop_id_row.append(crop_id)
            else:
                crop_id_row.append('')
                unmatched.append(crop_name)
        
        # Insert CropID row after header
        rows.insert(1, crop_id_row)
        
        # Write back to file
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        
        message = f"✓ Added CropID row"
        if unmatched:
            message += f" (warning: {len(unmatched)} unmatched crops: {', '.join(unmatched[:3])})"
        
        return True, message
    
    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
    """Main function to process all crop detail files."""
    script_dir = Path(__file__).parent
    
    # Build crop ID mapping
    crop_list_path = script_dir / DEFAULT_CROP_LIST
    if not crop_list_path.exists():
        print(f"Error: Crop list file not found: {crop_list_path}")
        return
    
    crop_map = build_crop_id_map(str(crop_list_path))
    print(f"Loaded {len(crop_map)} crops from crop list\n")
    
    # Find and process all crop detail files
    detail_files = sorted([
        f for f in script_dir.glob("*.csv")
        if f.name[0].isdigit() and any(pattern in f.name for pattern in ["Matrix", "Crop"])
        and f.name != DEFAULT_CROP_LIST
    ])
    
    if not detail_files:
        print("No crop detail files found")
        return
    
    print(f"Found {len(detail_files)} crop detail files to process:\n")
    
    success_count = 0
    for file_path in detail_files:
        success, message = add_cropid_row_to_file(str(file_path), crop_map)
        status = "✓" if success else "✗"
        print(f"{status} {file_path.name}: {message}")
        if success:
            success_count += 1
    
    print(f"\n{'='*70}")
    print(f"Summary: {success_count}/{len(detail_files)} files processed successfully")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
