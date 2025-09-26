#!/usr/bin/env python3
"""
Script to fix ID sequence and Spanish translations for reflexive French verbs
"""

import csv
import shutil
from datetime import datetime

# Proper Spanish translations for French reflexive verbs
REFLEXIVE_TRANSLATIONS = {
    'se retrouver': 'encontrarse',
    's\'assurer': 'asegurarse',
    's\'arrêter': 'detenerse',
    'se sentir': 'sentirse',
    'se changer': 'cambiarse',
    's\'imaginer': 'imaginarse',
    'se lever': 'levantarse',
    'se tourner': 'girarse',
    'se réaliser': 'realizarse',
    'se présenter': 'presentarse',
    'se coucher': 'acostarse',
    's\'occuper': 'ocuparse',
    's\'asseoir': 'sentarse',
    's\'échapper': 'escaparse',
    'se battre': 'pelearse',
    's\'exprimer': 'expresarse',
    'se retourner': 'darse la vuelta',
    'se défendre': 'defenderse',
    'se rappeler': 'recordarse',
    'se cacher': 'esconderse',
    'se développer': 'desarrollarse',
    'se sauver': 'salvarse',
    'se bouger': 'moverse',
    's\'apercevoir': 'darse cuenta',
    'se placer': 'colocarse',
    'se traiter': 'tratarse',
    's\'étendre': 'extenderse',
    'se fier': 'fiarse',
    'se décider': 'decidirse',
    'entrainer': 'entrenar',
    'se protéger': 'protegerse',
    'se fermer': 'cerrarse',
    'se ramener': 'traerse',
    's\'embrasser': 'besarse',
    's\'élever': 'elevarse',
    'se séparer': 'separarse',
    'se transformer': 'transformarse',
    's\'installer': 'instalarse',
    'se promener': 'pasearse',
    'se laver': 'lavarse',
    'se disposer': 'disponerse',
    's\'intéresser': 'interesarse',
    'se marquer': 'marcarse',
    's\'effectuer': 'efectuarse',
    's\'éloigner': 'alejarse',
    'se réveiller': 'despertarse',
    's\'écarter': 'apartarse',
    'se diriger': 'dirigirse',
    'se retirer': 'retirarse',
    'se tromper': 'equivocarse',
    'se dresser': 'levantarse',
    'se traîner': 'arrastrarse',
    'se débarrasser': 'deshacerse',
    's\'amuser': 'divertirse',
    'se reposer': 'descansar',
    's\'attirer': 'atraerse',
    's\'accompagner': 'acompañarse',
    's\'adresser': 'dirigirse',
    's\'adapter': 'adaptarse',
    'se rapprocher': 'acercarse',
    'se confier': 'confiarse',
    'se serrer': 'apretarse',
    's\'appuyer': 'apoyarse',
    'se surveiller': 'vigilarse',
    's\'endormir': 'dormirse',
    's\'épouser': 'casarse',
    'se libérer': 'liberarse',
    'se consacrer': 'consagrarse',
    'se ranger': 'ordenarse',
    'se communiquer': 'comunicarse',
    'se réunir': 'reunirse',
    'se contrôler': 'controlarse',
    's\'identifier': 'identificarse',
    'se manifester': 'manifestarse',
    'se rétablir': 'restablecerse',
    'se contenter': 'contentarse',
    'se mêler': 'mezclarse',
    'se marier': 'casarse',
    'se soulever': 'levantarse',
    'se dissimuler': 'disimularse',
    's\'allumer': 'encenderse',
    's\'étonner': 'asombrarse',
    'se contempler': 'contemplarse',
    'se déplacer': 'desplazarse',
    's\'habiter': 'habitarse',
    's\'attacher': 'atarse',
    'se soigner': 'cuidarse',
    's\'arranger': 'arreglarse',
    'se reculer': 'retrocederse',
    'se rassurer': 'tranquilizarse',
    's\'orienter': 'orientarse',
    's\'habiller': 'vestirse',
    'se remercier': 'agradecerse',
    's\'inquiéter': 'inquietarse',
    'se secouer': 'sacudirse',
    'se pencher': 'inclinarse',
    's\'informer': 'informarse',
    's\'excuser': 'disculparse',
    'se concentrer': 'concentrarse',
    'se précipiter': 'precipitarse',
    's\'enrichir': 'enriquecerse',
    'se soupçonner': 'sospecharse',
    'repartir': 'repartir',
    'maitriser': 'dominar',
    's\'habituer': 'acostumbrarse',
    'se moquer': 'burlarse',
    'se repentir': 'arrepentirse',
    'se renseigner': 'informarse',
    'se résigner': 'resignarse',
    'se hâter': 'apresurarse',
    'se vanter': 'presumir',
    's\'attarder': 'retrasarse',
    'se déshabiller': 'desvestirse',
    'se préoccuper': 'preocuparse',
    's\'épanouir': 'florecer',
    'tacher': 'manchar',
    'se débrouiller': 'arreglárselas',
    'se réjouir': 'alegrarse'
}

def fix_ids_and_translations():
    """Fix ID sequence and Spanish translations for reflexive verbs"""
    csv_path = '/home/smendez-/Documents/VerbPractice/myproject/verbs/data/1000verbs.csv'
    backup_path = f'/home/smendez-/Documents/VerbPractice/myproject/verbs/data/1000verbs_backup_final_fix_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    print("=== FIXING ID SEQUENCE AND SPANISH TRANSLATIONS ===")
    
    # Create backup
    shutil.copy2(csv_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    
    # Read all rows
    rows = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    
    print(f"📊 Total rows: {len(rows)}")
    
    # Sort by current ID to maintain order
    rows.sort(key=lambda x: int(x['ID']))
    
    # Renumber sequentially and fix translations
    translation_fixes = 0
    for i, row in enumerate(rows):
        # Sequential numbering starting from 1
        new_id = str(i + 1)
        old_id = row['ID']
        
        if old_id != new_id:
            row['ID'] = new_id
        
        # Fix Spanish translations for reflexive verbs
        french_verb = row['FR'].strip()
        if french_verb in REFLEXIVE_TRANSLATIONS:
            old_translation = row['ES']
            new_translation = REFLEXIVE_TRANSLATIONS[french_verb]
            if old_translation.strip() != new_translation:
                print(f"🔧 Translation fix ID {new_id}: {french_verb} → '{new_translation}'")
                row['ES'] = new_translation
                translation_fixes += 1
    
    # Write corrected data
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['ID', 'FR', 'FR_group', 'ES']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\n=== FIX COMPLETE ===")
    print(f"✅ All IDs renumbered sequentially (1-{len(rows)})")
    print(f"✅ {translation_fixes} Spanish translations fixed for reflexive verbs")
    print(f"✅ Total verbs: {len(rows)}")
    print(f"✅ Original file backed up to: {backup_path}")
    print(f"✅ Updated file: {csv_path}")
    
    return len(rows), translation_fixes

if __name__ == "__main__":
    total_verbs, fixes = fix_ids_and_translations()
    print(f"\n🎉 SUCCESS!")
    print(f"📊 Sequential IDs: 1-{total_verbs}")
    print(f"🌍 Translation fixes: {fixes} reflexive verbs now have proper Spanish translations")
    print("🔄 Ready to regenerate conjugations with corrected data!")
