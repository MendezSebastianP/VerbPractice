#!/usr/bin/env python3
"""
Priority list of Spanish reflexive verbs that should be separated
"""

import csv

def generate_priority_spanish_separations():
    """Generate a focused list of the most important Spanish verb separations"""
    
    csv_path = '/home/smendez-/Documents/VerbPractice/myproject/verbs/data/1000verbs.csv'
    
    # High-priority Spanish dual forms that should definitely be separated
    high_priority_separations = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            french_verb = row['FR'].strip()
            spanish_translation = row['ES'].strip()
            verb_id = row['ID']
            
            # Focus on common, high-frequency verbs with clear dual forms
            if ',' in spanish_translation:
                parts = [part.strip() for part in spanish_translation.split(',')]
                
                # Identify clear reflexive vs non-reflexive pairs
                reflexive_parts = []
                non_reflexive_parts = []
                
                for part in parts:
                    if ('se ' in part or 
                        part.endswith('arse') or 
                        part.endswith('erse') or 
                        part.endswith('irse') or
                        'darse' in part):
                        reflexive_parts.append(part)
                    else:
                        non_reflexive_parts.append(part)
                
                if reflexive_parts and non_reflexive_parts:
                    # Priority based on verb frequency and importance
                    priority_verbs = [
                        'partir', 'quedar', 'ir', 'acostar', 'sentar', 'levantar',
                        'mover', 'dormir', 'despertar', 'lavar', 'vestir', 'llamar',
                        'acordar', 'encontrar', 'dar cuenta', 'caer', 'convertir'
                    ]
                    
                    is_high_priority = any(priority in spanish_translation.lower() 
                                         for priority in priority_verbs)
                    
                    separation_item = {
                        'id': verb_id,
                        'french': french_verb,
                        'spanish_full': spanish_translation,
                        'non_reflexive': non_reflexive_parts[0] if non_reflexive_parts else '',
                        'reflexive': reflexive_parts[0] if reflexive_parts else '',
                        'priority': 'HIGH' if is_high_priority else 'MEDIUM'
                    }
                    
                    high_priority_separations.append(separation_item)
    
    # Sort by priority and ID
    high_priority_separations.sort(key=lambda x: (x['priority'] == 'MEDIUM', int(x['id'])))
    
    print("=" * 70)
    print("🎯 **PRIORITY SPANISH REFLEXIVE VERB SEPARATIONS**")
    print("=" * 70)
    
    print("\n📚 **RECOMMENDED SEPARATIONS** (Similar to French reflexive handling)\n")
    
    high_count = 0
    medium_count = 0
    
    for item in high_priority_separations:
        priority_icon = "🔥" if item['priority'] == 'HIGH' else "⭐"
        
        print(f"{priority_icon} **ID {item['id']}**: {item['french']}")
        print(f"   Current: {item['spanish_full']}")
        print(f"   Should split into:")
        print(f"   → Non-reflexive: {item['non_reflexive']}")
        print(f"   → Reflexive: {item['reflexive']}")
        print()
        
        if item['priority'] == 'HIGH':
            high_count += 1
        else:
            medium_count += 1
    
    print("=" * 70)
    print("📊 **SUMMARY OF RECOMMENDED SEPARATIONS**")
    print("=" * 70)
    print(f"🔥 High Priority: {high_count} verbs")
    print(f"⭐ Medium Priority: {medium_count} verbs")
    print(f"📝 Total Spanish separations recommended: {len(high_priority_separations)}")
    
    print("\n🎯 **TOP 10 MOST IMPORTANT TO SEPARATE**:")
    print("-" * 50)
    for i, item in enumerate(high_priority_separations[:10], 1):
        print(f"{i:2}. {item['french']} → {item['non_reflexive']} | {item['reflexive']}")
    
    print(f"\n✅ **BENEFITS OF SEPARATION**:")
    print(f"• Consistent with French reflexive handling")
    print(f"• Clear learning objectives (reflexive vs non-reflexive)")
    print(f"• Eliminates ambiguity in Spanish conjugation practice")
    print(f"• Pedagogically sound for language learners")
    
    return high_priority_separations

if __name__ == "__main__":
    separations = generate_priority_spanish_separations()
    
    print(f"\n🔄 **NEXT STEPS**:")
    print(f"1. Review the {len(separations)} recommended separations")
    print(f"2. Create separation script similar to French reflexive handling")
    print(f"3. Generate appropriate French translations for new Spanish reflexive entries")
    print(f"4. Maintain pedagogical consistency across both languages")
