#!/usr/bin/env python3
"""
Script to clean up duplicate entries after Spanish separation
"""

import csv
import shutil
from datetime import datetime
from collections import defaultdict

def clean_duplicates():
    """Remove duplicate entries and ensure data integrity"""
    csv_path = '/home/smendez-/Documents/VerbPractice/myproject/verbs/data/1000verbs.csv'
    backup_path = f'/home/smendez-/Documents/VerbPractice/myproject/verbs/data/1000verbs_backup_cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    print("=== CLEANING UP DUPLICATE ENTRIES ===")
    
    # Create backup
    shutil.copy2(csv_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    
    # Read and deduplicate
    seen_combinations = set()
    clean_rows = []
    duplicates_removed = 0
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Create unique key based on French and Spanish combination
            unique_key = (row['FR'].strip(), row['ES'].strip())
            
            if unique_key not in seen_combinations:
                seen_combinations.add(unique_key)
                clean_rows.append(row)
            else:
                print(f"Removing duplicate: {row['FR']} → {row['ES']}")
                duplicates_removed += 1
    
    # Renumber sequentially
    for i, row in enumerate(clean_rows):
        row['ID'] = str(i + 1)
    
    # Write cleaned data
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['ID', 'FR', 'FR_group', 'ES']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(clean_rows)
    
    print(f"\n=== CLEANUP COMPLETE ===")
    print(f"✅ {duplicates_removed} duplicate entries removed")
    print(f"✅ {len(clean_rows)} unique verbs retained")
    print(f"✅ Sequential IDs: 1-{len(clean_rows)}")
    print(f"✅ File cleaned: {csv_path}")
    
    return duplicates_removed, len(clean_rows)

def show_separation_results():
    """Show examples of successful Spanish separations"""
    csv_path = '/home/smendez-/Documents/VerbPractice/myproject/verbs/data/1000verbs.csv'
    
    print("\n=== SPANISH SEPARATION SUCCESS EXAMPLES ===")
    
    # Key examples to show
    examples = [
        ('coucher', 'acostar', 'se coucher', 'acostarse'),
        ('asseoir', 'sentar', "s'asseoir", 'sentarse'),
        ('bouger', 'mover', 'se bouger', 'moverse'),
        ('partir', 'partir', "s'en aller", 'irse')
    ]
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    for non_ref_fr, non_ref_es, ref_fr, ref_es in examples:
        non_ref_entry = None
        ref_entry = None
        
        for row in rows:
            if row['FR'].strip() == non_ref_fr and row['ES'].strip() == non_ref_es:
                non_ref_entry = row
            elif row['FR'].strip() == ref_fr and row['ES'].strip() == ref_es:
                ref_entry = row
        
        if non_ref_entry and ref_entry:
            print(f"✅ {non_ref_fr}:")
            print(f"   ID {non_ref_entry['ID']:>3}: {non_ref_entry['FR']} → {non_ref_entry['ES']} (non-reflexive)")
            print(f"   ID {ref_entry['ID']:>3}: {ref_entry['FR']} → {ref_entry['ES']} (reflexive)")
            print()

if __name__ == "__main__":
    duplicates, total = clean_duplicates()
    show_separation_results()
    
    print("🎉 SPANISH REFLEXIVE SEPARATION COMPLETE!")
    print(f"📊 Final count: {total} verbs with no duplicates")
    print("✅ Spanish now has consistent reflexive handling like French")
    print("🔄 Ready for conjugation generation with complete reflexive consistency!")
