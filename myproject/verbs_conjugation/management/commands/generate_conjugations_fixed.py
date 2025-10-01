import csv
import mlconjug3
import os
import re
from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import datetime
from verbs_conjugation.models import VerbConjugation
from verbs.models import Verb

class Command(BaseCommand):
    help = 'Generates a CSV file with conjugations for French and Spanish verbs (FIXED VERSION)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--add-compound-tenses',
            action='store_true',
            help='Add missing compound tenses (Passé composé, etc.) to existing data',
        )

    def standardize_french_tense_name(self, mood, tense):
        """
        Create proper tense names by combining mood and tense.
        This fixes the tense mixing issue.
        """
        # Handle special cases first
        if mood == 'Infinitif':
            return 'Infinitif'
        elif mood == 'Participe':
            if 'Passé' in tense:
                return 'Participe passé'
            else:
                return 'Participe présent'
        elif mood == 'Imperatif':
            return 'Impératif'
        
        # For regular moods, combine mood and tense
        mood_map = {
            'Indicatif': '',  # Indicatif is default, no prefix needed
            'Subjonctif': 'Subjonctif ',
            'Conditionnel': 'Conditionnel '
        }
        
        # Tense standardization
        tense_map = {
            'Présent': 'présent',
            'Imparfait': 'imparfait', 
            'Passé Simple': 'passé simple',
            'Futur': 'futur',
        }
        
        mood_prefix = mood_map.get(mood, mood + ' ')
        standardized_tense = tense_map.get(tense, tense.lower())
        
        return f"{mood_prefix}{standardized_tense}".strip()

    def standardize_spanish_tense_name(self, mood, tense):
        """
        Standardize Spanish tense names for clarity.
        """
        if mood == 'Infinitivo':
            return 'Infinitivo'
        elif mood == 'Participio':
            return 'Participio'
        elif mood == 'Gerundio':
            return 'Gerundio'
        elif mood == 'Imperativo':
            return 'Imperativo'
        
        # Clean up tense names that already include mood
        if tense.startswith(mood):
            tense = tense[len(mood):].strip()
        
        # For other moods, simplify the tense names
        tense_simplification = {
            'presente': 'Presente',
            'pretérito imperfecto': 'Pretérito imperfecto',
            'pretérito perfecto simple': 'Pretérito indefinido',
            'futuro': 'Futuro',
            'condicional simple': 'Condicional',
            'presente': 'Presente',  # for subjuntivo
            'pretérito imperfecto': 'Imperfecto',  # for subjuntivo
        }
        
        standardized_tense = tense_simplification.get(tense.lower(), tense)
        
        # Add mood prefix for subjunctive
        if mood == 'Subjuntivo':
            return f"Subjuntivo {standardized_tense.lower()}"
        else:
            return standardized_tense

    def standardize_spanish_pronouns(self, pronoun):
        """
        Standardize Spanish pronouns to include gender forms.
        """
        pronoun_map = {
            'él': 'él/ella',
            'ellos': 'ellos/ellas',
            'él no': 'él/ella no',
            'ellos no': 'ellos/ellas no'
        }
        return pronoun_map.get(pronoun, pronoun)

    def generate_passe_compose_french(self, verb_infinitive):
        """
        Generate Passé composé conjugations for French verbs.
        """
        # Define verbs that use être as auxiliary
        etre_verbs = {
            'aller', 'venir', 'arriver', 'partir', 'sortir', 'entrer', 'rentrer', 
            'monter', 'descendre', 'naître', 'mourir', 'tomber', 'rester', 
            'retourner', 'devenir', 'revenir', 'passer'
        }
        
        # Common past participles
        past_participles = {
            'être': 'été', 'avoir': 'eu', 'aller': 'allé', 'venir': 'venu',
            'faire': 'fait', 'dire': 'dit', 'voir': 'vu', 'savoir': 'su',
            'pouvoir': 'pu', 'vouloir': 'voulu', 'devoir': 'dû', 'falloir': 'fallu',
            'prendre': 'pris', 'mettre': 'mis', 'donner': 'donné', 'parler': 'parlé',
            'finir': 'fini', 'choisir': 'choisi', 'attendre': 'attendu', 'vendre': 'vendu',
            'manger': 'mangé', 'acheter': 'acheté', 'appeler': 'appelé', 'jeter': 'jeté',
            'commencer': 'commencé', 'préférer': 'préféré', 'espérer': 'espéré',
            'créer': 'créé', 'employer': 'employé', 'essayer': 'essayé',
            'pleuvoir': 'plu', 'neiger': 'neigé'
        }
        
        # Determine auxiliary and past participle
        uses_etre = verb_infinitive in etre_verbs or verb_infinitive.startswith('se ')
        auxiliary = 'être' if uses_etre else 'avoir'
        
        if verb_infinitive in past_participles:
            past_participle = past_participles[verb_infinitive]
        else:
            # Generate regular past participle
            if verb_infinitive.endswith('er'):
                past_participle = verb_infinitive[:-2] + 'é'
            elif verb_infinitive.endswith('ir'):
                past_participle = verb_infinitive[:-2] + 'i'
            elif verb_infinitive.endswith('re'):
                past_participle = verb_infinitive[:-2] + 'u'
            else:
                past_participle = verb_infinitive + 'é'
        
        # Auxiliary conjugations
        if auxiliary == 'avoir':
            aux_conjugations = {
                'je': "j'ai", 'tu': 'as', 'il (elle, on)': 'a',
                'nous': 'avons', 'vous': 'avez', 'ils (elles)': 'ont'
            }
        else:
            aux_conjugations = {
                'je': 'suis', 'tu': 'es', 'il (elle, on)': 'est',
                'nous': 'sommes', 'vous': 'êtes', 'ils (elles)': 'sont'
            }
        
        # Generate Passé composé
        conjugations = []
        for pronoun, aux_form in aux_conjugations.items():
            if uses_etre:
                # Add agreement markers for être
                if pronoun in ['je', 'tu']:
                    conjugated_form = f"{aux_form} {past_participle}(e)"
                elif pronoun == 'il (elle, on)':
                    conjugated_form = f"{aux_form} {past_participle}(e)"
                elif pronoun == 'nous':
                    conjugated_form = f"{aux_form} {past_participle}(e)s"
                elif pronoun == 'vous':
                    conjugated_form = f"{aux_form} {past_participle}(e)(s)"
                elif pronoun == 'ils (elles)':
                    conjugated_form = f"{aux_form} {past_participle}(e)s"
                else:
                    conjugated_form = f"{aux_form} {past_participle}"
            else:
                conjugated_form = f"{aux_form} {past_participle}"
            
            conjugations.append(('Passé composé', pronoun, conjugated_form))
        
        return conjugations

    def add_compound_tenses_to_database(self):
        """Add missing compound tenses to existing verbs."""
        self.stdout.write(self.style.SUCCESS('Adding compound tenses to existing verbs...'))
        
        french_verbs = Verb.objects.all()
        added_count = 0
        
        for verb in french_verbs:
            verb_infinitive = verb.infinitive
            
            # Check if Passé composé already exists
            existing = VerbConjugation.objects.filter(
                verb=verb, language='FR', tense='Passé composé'
            ).exists()
            
            if not existing:
                conjugations = self.generate_passe_compose_french(verb_infinitive)
                
                for tense, pronoun, conjugated_form in conjugations:
                    VerbConjugation.objects.create(
                        verb=verb,
                        language='FR',
                        mood='Indicatif',
                        tense=tense,
                        pronoun=pronoun,
                        conjugated_form=conjugated_form
                    )
                    added_count += 1
                
                self.stdout.write(f'Added Passé composé for {verb_infinitive}')
        
        self.stdout.write(self.style.SUCCESS(f'✅ Added {added_count} Passé composé conjugations'))

    def is_reflexive_verb(self, verb_text):
        """Check if a Spanish verb is reflexive."""
        return '(se)' in verb_text.lower()

    def clean_reflexive_verb(self, verb_text):
        """Extract base verb from reflexive patterns."""
        cleaned = re.sub(r'\([^)]*\)', '', verb_text)
        return cleaned.split(',')[0].strip()

    def add_reflexive_pronouns(self, conjugations):
        """Add reflexive pronouns to Spanish conjugations."""
        reflexive_pronouns = {
            'yo': 'me', 'tú': 'te', 'él/ella': 'se',
            'nosotros': 'nos', 'vosotros': 'os', 'ellos/ellas': 'se',
            'tú no': 'te', 'él/ella no': 'se', 'nosotros no': 'nos',
            'vosotros no': 'os', 'ellos/ellas no': 'se'
        }
        
        reflexive_conjugations = []
        for conj_tuple in conjugations:
            if len(conj_tuple) == 4:
                mood, tense, pronoun, conjugated = conj_tuple
                
                # First standardize the pronoun
                standardized_pronoun = self.standardize_spanish_pronouns(pronoun)
                
                if conjugated and standardized_pronoun in reflexive_pronouns:
                    reflexive_pronoun = reflexive_pronouns[standardized_pronoun]
                    
                    if mood == "Imperativo":
                        if "no" in standardized_pronoun:
                            reflexive_form = f"no {reflexive_pronoun} {conjugated}"
                        else:
                            # Positive imperative: attach pronoun
                            if standardized_pronoun == 'tú':
                                if conjugated.endswith('a'):
                                    reflexive_form = f"{conjugated[:-1]}áte"
                                else:
                                    reflexive_form = f"{conjugated}te"
                            elif standardized_pronoun == 'vosotros':
                                if conjugated.endswith('d'):
                                    reflexive_form = f"{conjugated[:-1]}os"
                                else:
                                    reflexive_form = f"{conjugated}os"
                            else:
                                reflexive_form = f"{reflexive_pronoun} {conjugated}"
                    else:
                        reflexive_form = f"{reflexive_pronoun} {conjugated}"
                    
                    reflexive_conjugations.append((mood, tense, standardized_pronoun, reflexive_form))
                else:
                    reflexive_conjugations.append((mood, tense, standardized_pronoun, conjugated))
            else:
                reflexive_conjugations.append(conj_tuple)
        
        return reflexive_conjugations

    def conjugate_spanish_verb_with_reflexive(self, original_spanish_verb, es_conjugator):
        """Conjugate Spanish verb with reflexive handling."""
        is_reflexive = self.is_reflexive_verb(original_spanish_verb)
        base_verb = self.clean_reflexive_verb(original_spanish_verb)
        
        verb_result = es_conjugator.conjugate(base_verb)
        if not verb_result:
            return []
        
        try:
            all_conjugations = list(verb_result.iterate())
        except AttributeError:
            return []
        
        # Standardize pronouns for ALL Spanish verbs
        standardized_conjugations = []
        for conj in all_conjugations:
            if len(conj) == 4:
                mood, tense, pronoun, conjugated = conj
                standardized_pronoun = self.standardize_spanish_pronouns(pronoun)
                standardized_conjugations.append((mood, tense, standardized_pronoun, conjugated))
            else:
                standardized_conjugations.append(conj)
        
        # Add reflexive pronouns if needed
        if is_reflexive:
            return self.add_reflexive_pronouns(standardized_conjugations)
        else:
            return standardized_conjugations

    def extract_french_verb_forms(self, verb_text):
        """Extract French verb forms."""
        if '/' in verb_text:
            return [part.strip() for part in verb_text.split('/')]
        return [verb_text.strip()]

    def extract_conjugations_from_full_forms(self, verb_obj, language='FR'):
        """Fallback method for problematic verbs."""
        conjugations = []
        
        if not hasattr(verb_obj, 'full_forms') or not verb_obj.full_forms:
            return conjugations
        
        for mood, mood_data in verb_obj.full_forms.items():
            if not isinstance(mood_data, dict):
                continue
            
            for tense, tense_data in mood_data.items():
                if isinstance(tense_data, dict):
                    for pronoun, conjugated_form in tense_data.items():
                        if conjugated_form:
                            conjugations.append((mood, tense, pronoun, conjugated_form))
                else:
                    if tense_data:
                        conjugations.append((mood, tense, '', tense_data))
        
        return conjugations

    def handle(self, *args, **options):
        if options['add_compound_tenses']:
            self.add_compound_tenses_to_database()
            return
        
        self.stdout.write(self.style.SUCCESS('🚀 Starting FIXED verb conjugation generation...'))
        self.stdout.write(self.style.SUCCESS('🔧 Fixed: Tense separation, pronoun standardization, duplicate prevention'))
        
        # Paths
        verbs_csv_path = os.path.join(settings.BASE_DIR, 'verbs', 'data', '1000verbs.csv')
        output_dir = os.path.join(settings.BASE_DIR, 'verbs_conjugation', 'data')
        os.makedirs(output_dir, exist_ok=True)
        conjugations_csv_path = os.path.join(output_dir, 'conjugations_fixed.csv')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        error_log_path = os.path.join(output_dir, f'conjugation_errors_fixed_{timestamp}.txt')

        try:
            fr_conjugator = mlconjug3.Conjugator(language='fr')
            es_conjugator = mlconjug3.Conjugator(language='es')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error initializing mlconjug3: {e}'))
            return

        # Load verbs
        verbs_to_conjugate = []
        with open(verbs_csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                spanish_verbs = row['ES'].strip().split(',')
                spanish_verb = spanish_verbs[0].strip() if spanish_verbs else ''
                
                verbs_to_conjugate.append({
                    'id': row['ID'],
                    'fr': row['FR'].strip(),
                    'es': spanish_verb
                })

        # Process conjugations
        total_conjugations = 0
        seen_conjugations = set()  # For duplicate prevention
        
        with open(conjugations_csv_path, 'w', newline='', encoding='utf-8') as f, \
             open(error_log_path, 'w', encoding='utf-8') as error_log:
            
            writer = csv.writer(f)
            writer.writerow(['verb_id', 'language', 'mood', 'tense', 'pronoun', 'conjugated_form'])
            
            error_log.write(f"Fixed Conjugation Generation - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            error_log.write("=" * 60 + "\n\n")

            for verb_data in verbs_to_conjugate:
                self.stdout.write(f"Processing verb ID: {verb_data['id']}")

                # French conjugations
                if verb_data['fr']:
                    french_forms = self.extract_french_verb_forms(verb_data['fr'])
                    
                    for french_verb in french_forms:
                        french_verb = french_verb.strip()
                        if not french_verb:
                            continue
                        
                        try:
                            fr_verb = fr_conjugator.conjugate(french_verb)
                            if fr_verb is not None:
                                conjugations_added = 0
                                try:
                                    for conjugation_tuple in fr_verb.iterate():
                                        if len(conjugation_tuple) == 4:
                                            mood, tense, pronoun, conjugated = conjugation_tuple
                                            if conjugated:
                                                # FIX: Use standardized tense name
                                                standardized_tense = self.standardize_french_tense_name(mood, tense)
                                                
                                                # FIX: Prevent duplicates
                                                duplicate_key = (verb_data['id'], 'FR', mood, standardized_tense, pronoun, conjugated)
                                                if duplicate_key not in seen_conjugations:
                                                    seen_conjugations.add(duplicate_key)
                                                    writer.writerow([verb_data['id'], 'FR', mood, standardized_tense, pronoun, conjugated])
                                                    conjugations_added += 1
                                                    total_conjugations += 1
                                        
                                        elif len(conjugation_tuple) == 3:
                                            mood, tense, conjugated = conjugation_tuple
                                            if conjugated:
                                                standardized_tense = self.standardize_french_tense_name(mood, tense)
                                                duplicate_key = (verb_data['id'], 'FR', mood, standardized_tense, '', conjugated)
                                                if duplicate_key not in seen_conjugations:
                                                    seen_conjugations.add(duplicate_key)
                                                    writer.writerow([verb_data['id'], 'FR', mood, standardized_tense, '', conjugated])
                                                    conjugations_added += 1
                                                    total_conjugations += 1
                                
                                except AttributeError as attr_error:
                                    # Fallback for problematic verbs
                                    fallback_conjugations = self.extract_conjugations_from_full_forms(fr_verb, 'FR')
                                    for mood, tense, pronoun, conjugated in fallback_conjugations:
                                        standardized_tense = self.standardize_french_tense_name(mood, tense)
                                        duplicate_key = (verb_data['id'], 'FR', mood, standardized_tense, pronoun, conjugated)
                                        if duplicate_key not in seen_conjugations:
                                            seen_conjugations.add(duplicate_key)
                                            writer.writerow([verb_data['id'], 'FR', mood, standardized_tense, pronoun, conjugated])
                                            conjugations_added += 1
                                            total_conjugations += 1
                                
                                # Add compound tenses
                                try:
                                    passe_compose_conjugations = self.generate_passe_compose_french(french_verb)
                                    for tense, pronoun, conjugated_form in passe_compose_conjugations:
                                        duplicate_key = (verb_data['id'], 'FR', 'Indicatif', tense, pronoun, conjugated_form)
                                        if duplicate_key not in seen_conjugations:
                                            seen_conjugations.add(duplicate_key)
                                            writer.writerow([verb_data['id'], 'FR', 'Indicatif', tense, pronoun, conjugated_form])
                                            conjugations_added += 1
                                            total_conjugations += 1
                                except Exception as compound_error:
                                    error_msg = f"Verb ID {verb_data['id']}: Compound tense error for '{french_verb}': {compound_error}\n"
                                    error_log.write(error_msg)
                                
                                if conjugations_added > 0:
                                    self.stdout.write(f"✅ French '{french_verb}': {conjugations_added} conjugations")
                            
                            else:
                                error_msg = f"Verb ID {verb_data['id']}: French verb '{french_verb}' not found\n"
                                error_log.write(error_msg)
                        
                        except Exception as e:
                            error_msg = f"Verb ID {verb_data['id']}: Error with French verb '{french_verb}': {e}\n"
                            error_log.write(error_msg)
                            self.stderr.write(self.style.ERROR(error_msg.strip()))

                # Spanish conjugations
                if verb_data['es']:
                    spanish_verb = verb_data['es'].split()[0] if ' ' in verb_data['es'] else verb_data['es']
                    try:
                        # FIX: Use standardized Spanish conjugation method
                        spanish_conjugations = self.conjugate_spanish_verb_with_reflexive(spanish_verb, es_conjugator)
                        
                        if spanish_conjugations:
                            conjugations_added = 0
                            for conjugation_tuple in spanish_conjugations:
                                if len(conjugation_tuple) == 4:
                                    mood, tense, pronoun, conjugated = conjugation_tuple
                                    if conjugated:
                                        # FIX: Use standardized tense name  
                                        standardized_tense = self.standardize_spanish_tense_name(mood, tense)
                                        
                                        # FIX: Prevent duplicates
                                        duplicate_key = (verb_data['id'], 'ES', mood, standardized_tense, pronoun, conjugated)
                                        if duplicate_key not in seen_conjugations:
                                            seen_conjugations.add(duplicate_key)
                                            writer.writerow([verb_data['id'], 'ES', mood, standardized_tense, pronoun, conjugated])
                                            conjugations_added += 1
                                            total_conjugations += 1
                                
                                elif len(conjugation_tuple) == 3:
                                    mood, tense, conjugated = conjugation_tuple
                                    if conjugated:
                                        standardized_tense = self.standardize_spanish_tense_name(mood, tense)
                                        duplicate_key = (verb_data['id'], 'ES', mood, standardized_tense, '', conjugated)
                                        if duplicate_key not in seen_conjugations:
                                            seen_conjugations.add(duplicate_key)
                                            writer.writerow([verb_data['id'], 'ES', mood, standardized_tense, '', conjugated])
                                            conjugations_added += 1
                                            total_conjugations += 1
                            
                            if conjugations_added > 0:
                                self.stdout.write(f"✅ Spanish '{spanish_verb}': {conjugations_added} conjugations")
                        
                        else:
                            error_msg = f"Verb ID {verb_data['id']}: No Spanish conjugations for '{spanish_verb}'\n"
                            error_log.write(error_msg)
                    
                    except Exception as e:
                        error_msg = f"Verb ID {verb_data['id']}: Error with Spanish verb '{spanish_verb}': {e}\n"
                        error_log.write(error_msg)
                        self.stderr.write(self.style.ERROR(error_msg.strip()))

        self.stdout.write(self.style.SUCCESS(f'✅ FIXED conjugation generation completed!'))
        self.stdout.write(self.style.SUCCESS(f'📄 Generated file: {conjugations_csv_path}'))
        self.stdout.write(self.style.SUCCESS(f'📊 Total conjugations: {total_conjugations}'))
        self.stdout.write(self.style.SUCCESS(f'🔍 Duplicates prevented: {len(seen_conjugations)} unique entries'))
        self.stdout.write(self.style.SUCCESS(f'📝 Error log: {error_log_path}'))
