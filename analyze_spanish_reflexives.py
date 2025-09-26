#!/usr/bin/env python3
"""
Script to analyze Spanish reflexive verbs and identify missing separations
"""

import csv
import re

def analyze_spanish_reflexives():
    """
    Analyze Spanish translations to identify:
    1. Verbs with dual reflexive/non-reflexive forms that should be separated
    2. Missing reflexive Spanish entries
    3. Inconsistent translations
    """
    csv_path = '/home/smendez-/Documents/VerbPractice/myproject/verbs/data/1000verbs.csv'
    
    print("=== ANALYZING SPANISH REFLEXIVE VERBS ===\n")
    
    # Categories for analysis
    dual_spanish_forms = []
    mixed_reflexive_translations = []
    spanish_reflexive_only = []
    potential_missing = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            french_verb = row['FR'].strip()
            spanish_translation = row['ES'].strip()
            verb_id = row['ID']
            
            # Skip header or empty rows
            if not spanish_translation or spanish_translation == 'ES':
                continue
            
            # 1. Look for Spanish entries with comma-separated forms (dual forms)
            if ',' in spanish_translation:
                parts = [part.strip() for part in spanish_translation.split(',')]
                
                # Check if one is reflexive and one is not
                reflexive_parts = [part for part in parts if 'se ' in part or part.endswith('arse') or part.endswith('erse') or part.endswith('irse')]
                non_reflexive_parts = [part for part in parts if part not in reflexive_parts]
                
                if reflexive_parts and non_reflexive_parts:
                    dual_spanish_forms.append({
                        'id': verb_id,
                        'french': french_verb,
                        'spanish_full': spanish_translation,
                        'reflexive_forms': reflexive_parts,
                        'non_reflexive_forms': non_reflexive_parts
                    })
            
            # 2. Look for mixed translations (some reflexive, some not)
            elif ('se ' in spanish_translation or 
                  spanish_translation.endswith('arse') or 
                  spanish_translation.endswith('erse') or 
                  spanish_translation.endswith('irse')):
                
                mixed_reflexive_translations.append({
                    'id': verb_id,
                    'french': french_verb,
                    'spanish': spanish_translation
                })
            
            # 3. Check for potential missing Spanish reflexives
            # If French is not reflexive but Spanish could have reflexive form
            if not ('se ' in french_verb.lower() or "s'" in french_verb.lower()):
                # Common verbs that often have reflexive Spanish equivalents
                reflexive_candidates = [
                    'levantar', 'acostar', 'vestir', 'lavar', 'peinar', 'sentar',
                    'llamar', 'quedar', 'ir', 'caer', 'dormir', 'despertar',
                    'mover', 'parecer', 'encontrar', 'acordar', 'olvidar'
                ]
                
                for candidate in reflexive_candidates:
                    if candidate in spanish_translation.lower():
                        potential_missing.append({
                            'id': verb_id,
                            'french': french_verb,
                            'spanish': spanish_translation,
                            'potential_reflexive': f'{candidate}se'
                        })
                        break
    
    # Print results
    print("🔍 **ANALYSIS RESULTS**\n")
    
    # 1. Dual Spanish forms (should be separated)
    print(f"📝 **1. SPANISH VERBS WITH DUAL FORMS** ({len(dual_spanish_forms)} found)")
    print("These should be separated like we did with French:")
    print("-" * 60)
    for item in dual_spanish_forms[:15]:  # Show first 15
        print(f"ID {item['id']:>3}: {item['french']:<20} → {item['spanish_full']}")
        print(f"     Reflexive: {', '.join(item['reflexive_forms'])}")
        print(f"     Non-reflex: {', '.join(item['non_reflexive_forms'])}")
        print()
    
    if len(dual_spanish_forms) > 15:
        print(f"... and {len(dual_spanish_forms) - 15} more\n")
    
    # 2. Mixed reflexive translations
    print(f"🔄 **2. MIXED REFLEXIVE TRANSLATIONS** ({len(mixed_reflexive_translations)} found)")
    print("These have reflexive Spanish but may need review:")
    print("-" * 60)
    for item in mixed_reflexive_translations[:10]:
        print(f"ID {item['id']:>3}: {item['french']:<20} → {item['spanish']}")
    
    if len(mixed_reflexive_translations) > 10:
        print(f"... and {len(mixed_reflexive_translations) - 10} more\n")
    
    # 3. Potential missing reflexives
    print(f"❓ **3. POTENTIAL MISSING SPANISH REFLEXIVES** ({len(potential_missing)} found)")
    print("These might benefit from reflexive Spanish variants:")
    print("-" * 60)
    for item in potential_missing[:10]:
        print(f"ID {item['id']:>3}: {item['french']:<20} → {item['spanish']}")
        print(f"     Could add: {item['potential_reflexive']}")
        print()
    
    if len(potential_missing) > 10:
        print(f"... and {len(potential_missing) - 10} more\n")
    
    # Summary
    print("=" * 60)
    print("📊 **SUMMARY**")
    print("=" * 60)
    print(f"✅ Dual Spanish forms needing separation: {len(dual_spanish_forms)}")
    print(f"🔄 Mixed reflexive translations: {len(mixed_reflexive_translations)}")
    print(f"❓ Potential missing Spanish reflexives: {len(potential_missing)}")
    
    return dual_spanish_forms, mixed_reflexive_translations, potential_missing

if __name__ == "__main__":
    dual_forms, mixed, potential = analyze_spanish_reflexives()
    
    print(f"\n🎯 **RECOMMENDATION**:")
    if dual_forms:
        print(f"Consider separating {len(dual_forms)} Spanish dual forms similar to French reflexives")
    if potential:
        print(f"Review {len(potential)} verbs that might benefit from Spanish reflexive variants")
    
    print("\n🔄 This analysis helps maintain consistency between French and Spanish reflexive handling!")
