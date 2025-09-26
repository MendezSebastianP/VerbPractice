#!/usr/bin/env python3
"""
Script to separate Spanish reflexive verbs into distinct rows
This maintains consistency with French reflexive verb handling
"""

import csv
import shutil
from datetime import datetime

def separate_spanish_reflexives():
    """
    Convert Spanish verbs like 'acostar, acostarse' into separate rows:
    - Original: coucher → acostar (non-reflexive)  
    - New: se coucher → acostarse (reflexive)
    """
    csv_path = '/home/smendez-/Documents/VerbPractice/myproject/verbs/data/1000verbs.csv'
    backup_path = f'/home/smendez-/Documents/VerbPractice/myproject/verbs/data/1000verbs_backup_spanish_separation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    print("=== SEPARATING SPANISH REFLEXIVE VERBS INTO DISTINCT ROWS ===")
    
    # Create backup
    shutil.copy2(csv_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    
    # French translations for new Spanish reflexive entries
    french_reflexive_translations = {
        'irse': 's\'en aller',
        'acordarse': 'se souvenir', 
        'convertirse': 'se convertir',
        'quedarse': 'rester',
        'acostarse': 'se coucher',
        'sentarse': 's\'asseoir',
        'moverse': 'se bouger',
        'hundirse': 'se couler',
        'dormirse': 's\'endormir', 
        'vestirse': 's\'habiller',
        'arrepentirse': 'se repentir',
        'unirse': 's\'unir',
        'apresurarse': 'se dépêcher',
        'derretirse': 'se fondre',
        'romperse': 'se craquer',
        'darse cuenta': 'se rendre compte',
        'acercarse à': 's\'approcher',
        'deshacerse de': 'se débarrasser',
        'tumbarse': 's\'allonger',
        'inclinarse': 'se pencher',
        'hospedarse': 'se loger',
        'ponerse (ropa)': 's\'enfiler',
        'desarrollarse': 'se dérouler',
        'demorarse': 's\'attarder',
        'obstinarse': 's\'obstiner'
    }
    
    # Priority separations (high and medium priority)
    target_separations = {
        14: ('partir', 'irse'),
        29: ('recordar', 'acordarse'), 
        36: ('llegar a ser', 'convertirse'),
        38: ('permanecer', 'quedarse'),
        96: ('realizar', 'darse cuenta'),
        103: ('acostar', 'acostarse'),
        105: ('sentar', 'sentarse'),
        151: ('notar', 'darse cuenta'),
        168: ('mover', 'moverse'),
        215: ('fluir', 'hundirse'),
        304: ('abordar', 'acercarse à'),
        308: ('quitar', 'deshacerse de'),
        349: ('adormecer', 'dormirse'),
        358: ('permanecer', 'quedarse'),
        390: ('hilar', 'irse'),
        401: ('fundir', 'derretirse'),
        507: ('crujir', 'romperse'),
        513: ('vestir', 'vestirse'),
        520: ('lamentar', 'arrepentirse'),
        550: ('alargar', 'tumbarse'),
        565: ('inclinar', 'inclinarse'),
        634: ('alojar', 'hospedarse'),
        665: ('ensartar', 'ponerse (ropa)'),
        721: ('desenrollar', 'desarrollarse'),
        748: ('retrasar(se)', 'demorarse'),
        815: ('reunir', 'unirse'),
        823: ('tropezar', 'obstinarse'),
        901: ('ir rápido', 'apresurarse'),
        948: ('adherir', 'unirse')
    }
    
    # Read current data
    rows = []
    new_reflexive_rows = []
    updates_made = 0
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        max_id = 0
        
        for row in reader:
            current_id = int(row['ID'])
            max_id = max(max_id, current_id)
            
            # Check if this ID needs separation
            if current_id in target_separations:
                non_reflexive_es, reflexive_es = target_separations[current_id]
                french_verb = row['FR'].strip()
                
                print(f"Separating ID {current_id}: '{row['ES']}' → '{non_reflexive_es}' + '{reflexive_es}'")
                
                # Update original row to non-reflexive form
                row['ES'] = non_reflexive_es
                rows.append(row)
                
                # Create new row for reflexive form
                new_row = row.copy()
                new_row['ID'] = str(max_id + len(new_reflexive_rows) + 1)
                new_row['ES'] = reflexive_es
                
                # Generate appropriate French translation for reflexive form
                if reflexive_es in french_reflexive_translations:
                    new_row['FR'] = french_reflexive_translations[reflexive_es]
                else:
                    # Fallback: add 'se' prefix if not already present
                    if not (french_verb.startswith('se ') or french_verb.startswith("s'")):
                        new_row['FR'] = f"se {french_verb}"
                    else:
                        new_row['FR'] = french_verb
                
                new_reflexive_rows.append(new_row)
                updates_made += 1
            else:
                rows.append(row)
    
    # Combine all rows
    all_rows = rows + new_reflexive_rows
    
    # Sort by ID to maintain order
    all_rows.sort(key=lambda x: int(x['ID']))
    
    # Renumber sequentially
    for i, row in enumerate(all_rows):
        row['ID'] = str(i + 1)
    
    # Write updated data
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['ID', 'FR', 'FR_group', 'ES']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    
    print(f"\n=== SEPARATION COMPLETE ===")
    print(f"✅ {updates_made} Spanish verbs separated into distinct reflexive/non-reflexive forms")
    print(f"✅ {len(new_reflexive_rows)} new Spanish reflexive verb rows created")
    print(f"✅ Total verbs now: {len(all_rows)}")
    print(f"✅ All IDs renumbered sequentially (1-{len(all_rows)})")
    print(f"✅ Original file backed up to: {backup_path}")
    print(f"✅ Updated file: {csv_path}")
    
    # Show some examples
    print(f"\n=== EXAMPLES OF SEPARATED VERBS ===")
    reflexive_examples = [row for row in all_rows if any(reflex in row['ES'] for reflex in ['se ', 'arse', 'erse', 'irse'])][:10]
    for example in reflexive_examples:
        print(f"ID {example['ID']}: {example['FR']} → {example['ES']}")
    
    return updates_made, len(new_reflexive_rows), len(all_rows)

if __name__ == "__main__":
    updates, new_rows, total = separate_spanish_reflexives()
    if updates > 0:
        print(f"\n🎉 SUCCESS: {updates} Spanish verbs separated, {new_rows} new reflexive entries created!")
        print("📚 Now Spanish has consistent reflexive handling like French:")
        print("   - Non-reflexive: 'acostar' → practice 'acuesto'")  
        print("   - Reflexive: 'acostarse' → practice 'me acuesto'")
        print(f"🔢 Total verbs: {total} (sequential IDs 1-{total})")
        print("🔄 Ready to regenerate conjugations with complete reflexive consistency!")
    else:
        print("\n✅ No separation needed - target verbs already separated.")
