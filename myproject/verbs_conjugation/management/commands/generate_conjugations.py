import csv
import mlconjug3
import os
import re
from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import datetime

class Command(BaseCommand):
    help = 'Generates a CSV file with conjugations for French and Spanish verbs.'

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
        # Path to the source CSV file with verbs
        verbs_csv_path = os.path.join(settings.BASE_DIR, 'verbs', 'data', '1000verbs.csv')
        
        # Path for the output CSV file
        output_dir = os.path.join(settings.BASE_DIR, 'verbs_conjugation', 'data')
        os.makedirs(output_dir, exist_ok=True)
        conjugations_csv_path = os.path.join(output_dir, 'conjugations.csv')
        
        # Path for the error log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        error_log_path = os.path.join(output_dir, f'conjugation_errors_{timestamp}.txt')

        # Initialize conjugators
        fr_conjugator = mlconjug3.Conjugator(language='fr')
        es_conjugator = mlconjug3.Conjugator(language='es')

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
                                try:
                                    for conjugation_tuple in fr_verb.iterate():
                                        if len(conjugation_tuple) == 4:  # (mood, tense, pronoun, conjugated_form)
                                            mood, tense, pronoun, conjugated = conjugation_tuple
                                            if conjugated:  # Skip None values
                                                writer.writerow([verb_data['id'], 'FR', mood, tense, pronoun, conjugated])
                                        elif len(conjugation_tuple) == 3:  # (mood, tense, infinitive_form)
                                            mood, tense, conjugated = conjugation_tuple
                                            if conjugated:  # Skip None values
                                                writer.writerow([verb_data['id'], 'FR', mood, tense, '', conjugated])
                                except AttributeError as attr_error:
                                    # Handle mlconjug3 bug with impersonal verbs like "falloir"
                                    # Try to extract conjugations directly from full_forms
                                    fallback_conjugations = self.extract_conjugations_from_full_forms(fr_verb, 'FR')
                                    if fallback_conjugations:
                                        self.stdout.write(self.style.SUCCESS(f"Verb ID {verb_data['id']}: Using fallback method for French verb '{french_verb}' - found {len(fallback_conjugations)} conjugations"))
                                        for mood, tense, pronoun, conjugated in fallback_conjugations:
                                            writer.writerow([verb_data['id'], 'FR', mood, tense, pronoun, conjugated])
                                    else:
                                        error_msg = f"Verb ID {verb_data['id']}: mlconjug3 library bug with French verb '{french_verb}' and fallback failed: {attr_error}\n"
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
