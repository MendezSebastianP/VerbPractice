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
    help = 'Generates a CSV file with conjugations for French and Spanish verbs.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--add-compound-tenses',
            action='store_true',
            help='Add missing compound tenses (Passé composé, etc.) to existing data',
        )

    def generate_passe_compose_french(self, verb_infinitive):
        """
        Generate Passé composé conjugations for French verbs.
        
        This manually creates compound tenses since mlconjug3 doesn't handle them well.
        """
        
        # Define verbs that use être as auxiliary (motion/state change verbs and reflexive verbs)
        # NOTE: être as a verb uses avoir as auxiliary (j'ai été), it's NOT in this list
        etre_verbs = {
            'aller', 'venir', 'arriver', 'partir', 'sortir', 'entrer', 'rentrer', 
            'monter', 'descendre', 'naître', 'mourir', 'tomber', 'rester', 
            'retourner', 'devenir', 'revenir', 'passer'
        }
        
        # Common past participles for frequent verbs
        past_participles = {
            'être': 'été', 'avoir': 'eu', 'aller': 'allé', 'venir': 'venu',
            'faire': 'fait', 'dire': 'dit', 'voir': 'vu', 'savoir': 'su',
            'pouvoir': 'pu', 'vouloir': 'voulu', 'devoir': 'dû', 'falloir': 'fallu',
            'prendre': 'pris', 'mettre': 'mis', 'donner': 'donné', 'parler': 'parlé',
            'finir': 'fini', 'choisir': 'choisi', 'attendre': 'attendu', 'vendre': 'vendu',
            'manger': 'mangé', 'acheter': 'acheté', 'appeler': 'appelé', 'jeter': 'jeté',
            'commencer': 'commencé', 'préférer': 'préféré', 'espérer': 'espéré',
            'créer': 'créé', 'employer': 'employé', 'essayer': 'essayé',
            # Weather/impersonal verbs
            'pleuvoir': 'plu', 'neiger': 'neigé'
        }
        
        # Determine auxiliary verb and past participle
        uses_etre = verb_infinitive in etre_verbs or verb_infinitive.startswith('se ')
        auxiliary = 'être' if uses_etre else 'avoir'
        
        # Get past participle
        if verb_infinitive in past_participles:
            past_participle = past_participles[verb_infinitive]
        else:
            # Generate regular past participle based on verb ending
            if verb_infinitive.endswith('er'):
                past_participle = verb_infinitive[:-2] + 'é'
            elif verb_infinitive.endswith('ir'):
                past_participle = verb_infinitive[:-2] + 'i'
            elif verb_infinitive.endswith('re'):
                past_participle = verb_infinitive[:-2] + 'u'
            else:
                past_participle = verb_infinitive + 'é'  # fallback
        
        # Auxiliary conjugations in present
        if auxiliary == 'avoir':
            aux_conjugations = {
                'je': "j'ai", 'tu': 'as', 'il (elle, on)': 'a',
                'nous': 'avons', 'vous': 'avez', 'ils (elles)': 'ont'
            }
        else:  # être
            aux_conjugations = {
                'je': 'suis', 'tu': 'es', 'il (elle, on)': 'est',
                'nous': 'sommes', 'vous': 'êtes', 'ils (elles)': 'sont'
            }
        
        # Generate Passé composé conjugations
        passe_compose_conjugations = []
        
        for pronoun, aux_form in aux_conjugations.items():
            if uses_etre:
                # With être, add agreement markers
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
                # With avoir, no agreement in most cases
                conjugated_form = f"{aux_form} {past_participle}"
            
            passe_compose_conjugations.append(('Indicatif', 'Passé composé', pronoun, conjugated_form))
        
        return passe_compose_conjugations

    def add_compound_tenses_to_database(self):
        """
        Add missing compound tenses to the database for existing verbs.
        """
        self.stdout.write(self.style.SUCCESS('Adding compound tenses to existing verbs...'))
        
        # Get all French verbs from the database
        french_verbs = Verb.objects.all()
        
        added_count = 0
        
        for verb in french_verbs:
            verb_infinitive = verb.infinitive
            
            # Check if this verb already has Passé composé
            existing_passe_compose = VerbConjugation.objects.filter(
                verb=verb,
                language='FR',
                tense='Passé composé'
            ).exists()
            
            if not existing_passe_compose:
                # Generate Passé composé conjugations
                passe_compose_conjugations = self.generate_passe_compose_french(verb_infinitive)
                
                # Add to database
                for mood, tense, pronoun, conjugated_form in passe_compose_conjugations:
                    VerbConjugation.objects.create(
                        verb=verb,
                        language='FR',
                        mood=mood,
                        tense=tense,
                        pronoun=pronoun,
                        conjugated_form=conjugated_form
                    )
                    added_count += 1
                
                self.stdout.write(f'Added Passé composé for {verb_infinitive} (ID: {verb.id})')
        
        # Also fix "Conditionnel présent" by copying from "Conditionnel - Présent"
        self.stdout.write('Fixing Conditionnel présent tense names...')
        
        conditionnel_present = VerbConjugation.objects.filter(
            language='FR',
            mood='Conditionnel',
            tense='Présent'
        )
        
        fixed_count = 0
        for conj in conditionnel_present:
            # Check if "Conditionnel présent" version already exists
            existing = VerbConjugation.objects.filter(
                verb=conj.verb,
                language='FR',
                mood='Indicatif',
                tense='Conditionnel présent',
                pronoun=conj.pronoun
            ).exists()
            
            if not existing:
                # Create the "Conditionnel présent" version
                VerbConjugation.objects.create(
                    verb=conj.verb,
                    language='FR',
                    mood='Indicatif',
                    tense='Conditionnel présent',
                    pronoun=conj.pronoun,
                    conjugated_form=conj.conjugated_form
                )
                fixed_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'✅ Added {added_count} Passé composé conjugations'))
        self.stdout.write(self.style.SUCCESS(f'✅ Fixed {fixed_count} Conditionnel présent conjugations'))

    def is_reflexive_verb(self, verb_text):
        """Check if a Spanish verb is reflexive based on its text pattern."""
        return '(se)' in verb_text.lower()

    def is_french_reflexive_verb(self, verb_text):
        """Check if a French verb has reflexive forms based on its text pattern."""
        return '/ se ' in verb_text.lower() or '/ s\'' in verb_text.lower()

    def extract_french_verb_forms(self, verb_text):
        """Extract both non-reflexive and reflexive forms from French verb text."""
        forms = []
        if '/' in verb_text:
            # Split by '/' and clean each form
            parts = [part.strip() for part in verb_text.split('/')]
            forms = parts
        else:
            forms = [verb_text.strip()]
        return forms

    def clean_reflexive_verb(self, verb_text):
        """Extract the base verb from reflexive patterns like 'preocupar(se)'."""
        cleaned = re.sub(r'\([^)]*\)', '', verb_text)
        cleaned = cleaned.split(',')[0].strip()
        return cleaned

    def add_reflexive_pronouns(self, conjugations):
        """Add reflexive pronouns to conjugations for reflexive verbs."""
        
        reflexive_pronouns = {
            'yo': 'me',
            'tú': 'te', 
            'él': 'se',
            'nosotros': 'nos',
            'vosotros': 'os',
            'ellos': 'se',
            # Negative imperative forms
            'tú no': 'te',
            'él no': 'se',
            'nosotros no': 'nos',
            'vosotros no': 'os',
            'ellos no': 'se'
        }
        
        reflexive_conjugations = []
        for conj_tuple in conjugations:
            if len(conj_tuple) == 4:
                mood, tense, pronoun, conjugated = conj_tuple
                if conjugated and pronoun in reflexive_pronouns:
                    reflexive_pronoun = reflexive_pronouns[pronoun]
                    
                    if mood == "Imperativo":
                        if "non" in tense:
                            # Negative imperative: "no te preocupes"
                            reflexive_form = f"no {reflexive_pronoun} {conjugated}"
                        else:
                            # Positive imperative: attach pronoun to end
                            if pronoun == 'tú':
                                # preocupa -> preocúpate
                                if conjugated.endswith('a'):
                                    reflexive_form = f"{conjugated[:-1]}áte"
                                else:
                                    reflexive_form = f"{conjugated}te"
                            elif pronoun == 'vosotros':
                                # preocupad -> preocupaos  
                                if conjugated.endswith('d'):
                                    reflexive_form = f"{conjugated[:-1]}os"
                                else:
                                    reflexive_form = f"{conjugated}os"
                            else:
                                # él, nosotros, ellos: pronoun goes before
                                reflexive_form = f"{reflexive_pronoun} {conjugated}"
                    else:
                        # Regular conjugations: "te preocupas"
                        reflexive_form = f"{reflexive_pronoun} {conjugated}"
                    
                    reflexive_conjugations.append((mood, tense, pronoun, reflexive_form))
                else:
                    reflexive_conjugations.append(conj_tuple)
            else:
                reflexive_conjugations.append(conj_tuple)
        
        return reflexive_conjugations

    def conjugate_spanish_verb_with_reflexive(self, original_spanish_verb, es_conjugator):
        """
        Conjugate a Spanish verb, handling reflexive forms properly.
        
        Args:
            original_spanish_verb: The original verb text (e.g., "preocupar(se)")
            es_conjugator: The mlconjug3 Spanish conjugator
            
        Returns:
            List of conjugation tuples: (mood, tense, pronoun, conjugated_form)
        """
        
        # Check if it's a reflexive verb
        is_reflexive = self.is_reflexive_verb(original_spanish_verb)
        
        # Clean the verb to get the base form
        base_verb = self.clean_reflexive_verb(original_spanish_verb)
        
        # Conjugate the base verb
        verb_result = es_conjugator.conjugate(base_verb)
        if not verb_result:
            return []
        
        # Get all conjugations
        all_conjugations = list(verb_result.iterate())
        
        # If it's reflexive, add reflexive pronouns
        if is_reflexive:
            return self.add_reflexive_pronouns(all_conjugations)
        else:
            return all_conjugations

    def extract_conjugations_from_full_forms(self, verb_obj, language='FR'):
        """
        Extract conjugations directly from the verb object's full_forms when iteration fails.
        This is a workaround for mlconjug3 bugs with impersonal verbs like 'falloir'.
        """
        conjugations = []
        
        if not hasattr(verb_obj, 'full_forms') or not verb_obj.full_forms:
            return conjugations
            
        for mood, mood_data in verb_obj.full_forms.items():
            if not isinstance(mood_data, dict):
                continue
                
            for tense, tense_data in mood_data.items():
                if isinstance(tense_data, dict):
                    # Tense data contains pronouns and conjugated forms
                    for pronoun, conjugated_form in tense_data.items():
                        if conjugated_form:  # Skip None values
                            conjugations.append((mood, tense, pronoun, conjugated_form))
                else:
                    # Direct form (like infinitive)
                    if tense_data:
                        conjugations.append((mood, tense, '', tense_data))
        
        return conjugations

    def handle(self, *args, **options):
        # Check if we should only add compound tenses
        if options['add_compound_tenses']:
            self.add_compound_tenses_to_database()
            return
        
        # Original conjugation generation logic
        self.stdout.write(self.style.SUCCESS('🚀 Starting comprehensive verb conjugation generation...'))
        self.stdout.write(self.style.SUCCESS('📝 This includes all basic tenses from mlconjug3 + compound tenses like Passé composé'))
        # Path to the source CSV file with verbs
        verbs_csv_path = os.path.join(settings.BASE_DIR, 'verbs', 'data', '1000verbs.csv')
        
        # Path for the output CSV file
        output_dir = os.path.join(settings.BASE_DIR, 'verbs_conjugation', 'data')
        os.makedirs(output_dir, exist_ok=True)
        conjugations_csv_path = os.path.join(output_dir, 'conjugations.csv')
        
        # Path for the error log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        error_log_path = os.path.join(output_dir, f'conjugation_errors_{timestamp}.txt')

        try:
            # Initialize conjugators
            fr_conjugator = mlconjug3.Conjugator(language='fr')
            es_conjugator = mlconjug3.Conjugator(language='es')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error initializing mlconjug3: {e}'))
            self.stderr.write(self.style.ERROR('Try running with --add-compound-tenses to only add missing tenses to existing data'))
            return

        verbs_to_conjugate = []
        with open(verbs_csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Extract Spanish verb - handle cases like "hacer falta, necesitar"
                spanish_verbs = row['ES'].strip().split(',')
                spanish_verb = spanish_verbs[0].strip() if spanish_verbs else ''
                
                verbs_to_conjugate.append({
                    'id': row['ID'],
                    'fr': row['FR'].strip(),
                    'es': spanish_verb
                })

        with open(conjugations_csv_path, 'w', newline='', encoding='utf-8') as f, \
             open(error_log_path, 'w', encoding='utf-8') as error_log:
            
            writer = csv.writer(f)
            writer.writerow(['verb_id', 'language', 'mood', 'tense', 'pronoun', 'conjugated_form'])
            
            # Write header to error log
            error_log.write(f"Conjugation Errors Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            error_log.write("=" * 60 + "\n\n")

            for verb_data in verbs_to_conjugate:
                self.stdout.write(f"Processing verb ID: {verb_data['id']}")

                # French conjugations
                if verb_data['fr']:
                    # Extract all French verb forms (non-reflexive and reflexive)
                    french_forms = self.extract_french_verb_forms(verb_data['fr'])
                    
                    for french_verb in french_forms:
                        french_verb = french_verb.strip()
                        if not french_verb:
                            continue
                            
                        try:
                            fr_verb = fr_conjugator.conjugate(french_verb)
                            # Use 'is not None' instead of 'if fr_verb' to avoid mlconjug3 __len__ bug
                            if fr_verb is not None:
                                # First, add all basic conjugations from mlconjug3
                                basic_conjugations_added = 0
                                try:
                                    for conjugation_tuple in fr_verb.iterate():
                                        if len(conjugation_tuple) == 4:  # (mood, tense, pronoun, conjugated_form)
                                            mood, tense, pronoun, conjugated = conjugation_tuple
                                            if conjugated:  # Skip None values
                                                writer.writerow([verb_data['id'], 'FR', mood, tense, pronoun, conjugated])
                                                basic_conjugations_added += 1
                                        elif len(conjugation_tuple) == 3:  # (mood, tense, infinitive_form)
                                            mood, tense, conjugated = conjugation_tuple
                                            if conjugated:  # Skip None values
                                                writer.writerow([verb_data['id'], 'FR', mood, tense, '', conjugated])
                                                basic_conjugations_added += 1
                                except AttributeError as attr_error:
                                    # Handle mlconjug3 bug with impersonal verbs like "falloir"
                                    # Try to extract conjugations directly from full_forms
                                    fallback_conjugations = self.extract_conjugations_from_full_forms(fr_verb, 'FR')
                                    if fallback_conjugations:
                                        self.stdout.write(self.style.SUCCESS(f"Verb ID {verb_data['id']}: Using fallback method for French verb '{french_verb}' - found {len(fallback_conjugations)} conjugations"))
                                        for mood, tense, pronoun, conjugated in fallback_conjugations:
                                            writer.writerow([verb_data['id'], 'FR', mood, tense, pronoun, conjugated])
                                            basic_conjugations_added += 1
                                    else:
                                        error_msg = f"Verb ID {verb_data['id']}: mlconjug3 library bug with French verb '{french_verb}' and fallback failed: {attr_error}\n"
                                        error_log.write(error_msg)
                                        self.stderr.write(self.style.WARNING(error_msg.strip()))
                                
                                # Now add compound tenses (Passé composé, etc.)
                                compound_conjugations_added = 0
                                try:
                                    passe_compose_conjugations = self.generate_passe_compose_french(french_verb)
                                    for mood, tense, pronoun, conjugated_form in passe_compose_conjugations:
                                        writer.writerow([verb_data['id'], 'FR', mood, tense, pronoun, conjugated_form])
                                        compound_conjugations_added += 1
                                    
                                    if basic_conjugations_added > 0 or compound_conjugations_added > 0:
                                        self.stdout.write(f"✅ Verb ID {verb_data['id']} '{french_verb}': {basic_conjugations_added} basic + {compound_conjugations_added} compound = {basic_conjugations_added + compound_conjugations_added} total conjugations")
                                        
                                except Exception as compound_error:
                                    error_msg = f"Verb ID {verb_data['id']}: Could not generate compound tenses for French verb '{french_verb}': {compound_error}\n"
                                    error_log.write(error_msg)
                                    self.stderr.write(self.style.WARNING(error_msg.strip()))
                            else:
                                error_msg = f"Verb ID {verb_data['id']}: French verb '{french_verb}' returned None (not found or unsupported)\n"
                                error_log.write(error_msg)
                                self.stderr.write(self.style.WARNING(error_msg.strip()))
                        except Exception as e:
                            error_msg = f"Verb ID {verb_data['id']}: Could not conjugate French verb '{french_verb}': {e}\n"
                            error_log.write(error_msg)
                            self.stderr.write(self.style.ERROR(error_msg.strip()))

                # Spanish conjugations
                if verb_data['es']:
                    # Handle multi-word Spanish verbs by taking only the first word
                    spanish_verb = verb_data['es'].split()[0] if ' ' in verb_data['es'] else verb_data['es']
                    try:
                        # Use the new reflexive-aware conjugation method
                        spanish_conjugations = self.conjugate_spanish_verb_with_reflexive(spanish_verb, es_conjugator)
                        
                        if spanish_conjugations:
                            for conjugation_tuple in spanish_conjugations:
                                if len(conjugation_tuple) == 4:  # (mood, tense, pronoun, conjugated_form)
                                    mood, tense, pronoun, conjugated = conjugation_tuple
                                    if conjugated:  # Skip None values
                                        writer.writerow([verb_data['id'], 'ES', mood, tense, pronoun, conjugated])
                                elif len(conjugation_tuple) == 3:  # (mood, tense, infinitive_form)
                                    mood, tense, conjugated = conjugation_tuple
                                    if conjugated:  # Skip None values
                                        writer.writerow([verb_data['id'], 'ES', mood, tense, '', conjugated])
                        else:
                            # Fallback to original method if reflexive method returns empty
                            es_verb = es_conjugator.conjugate(spanish_verb)
                            # Use 'is not None' instead of 'if es_verb' to avoid mlconjug3 __len__ bug
                            if es_verb is not None:
                                try:
                                    for conjugation_tuple in es_verb.iterate():
                                        if len(conjugation_tuple) == 4:  # (mood, tense, pronoun, conjugated_form)
                                            mood, tense, pronoun, conjugated = conjugation_tuple
                                            if conjugated:  # Skip None values
                                                writer.writerow([verb_data['id'], 'ES', mood, tense, pronoun, conjugated])
                                        elif len(conjugation_tuple) == 3:  # (mood, tense, infinitive_form)
                                            mood, tense, conjugated = conjugation_tuple
                                            if conjugated:  # Skip None values
                                                writer.writerow([verb_data['id'], 'ES', mood, tense, '', conjugated])
                                except AttributeError as attr_error:
                                    # Handle mlconjug3 bug with impersonal verbs
                                    fallback_conjugations = self.extract_conjugations_from_full_forms(es_verb, 'ES')
                                    if fallback_conjugations:
                                        self.stdout.write(self.style.SUCCESS(f"Verb ID {verb_data['id']}: Using fallback method for Spanish verb '{spanish_verb}' - found {len(fallback_conjugations)} conjugations"))
                                        for mood, tense, pronoun, conjugated in fallback_conjugations:
                                            writer.writerow([verb_data['id'], 'ES', mood, tense, pronoun, conjugated])
                                    else:
                                        error_msg = f"Verb ID {verb_data['id']}: mlconjug3 library bug with Spanish verb '{spanish_verb}' and fallback failed: {attr_error}\n"
                                        error_log.write(error_msg)
                                        self.stderr.write(self.style.WARNING(error_msg.strip()))
                            else:
                                error_msg = f"Verb ID {verb_data['id']}: Spanish verb '{spanish_verb}' returned None (not found or unsupported)\n"
                                error_log.write(error_msg)
                                self.stderr.write(self.style.WARNING(error_msg.strip()))
                            
                    except Exception as e:
                        error_msg = f"Verb ID {verb_data['id']}: Could not conjugate Spanish verb '{spanish_verb}': {e}\n"
                        error_log.write(error_msg)
                        self.stderr.write(self.style.ERROR(error_msg.strip()))

        self.stdout.write(self.style.SUCCESS(f'Successfully generated conjugations file at {conjugations_csv_path}'))
        self.stdout.write(self.style.SUCCESS(f'Error log saved at {error_log_path}'))
