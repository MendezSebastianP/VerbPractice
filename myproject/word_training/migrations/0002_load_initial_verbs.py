from django.db import migrations
import csv
import os


def load_words(apps, schema_editor):
    Word = apps.get_model('word_training', 'Word')
    if Word.objects.exists():
        return

    # Compute path to the CSV: <repo_root>/verbs/data/es_fr_top1000.csv
    migrations_dir = os.path.dirname(__file__)              # .../myproject/word_training/migrations
    word_training_dir = os.path.dirname(migrations_dir)     # .../myproject/word_training
    myproject_dir = os.path.dirname(word_training_dir)      # .../myproject
    repo_root = os.path.dirname(myproject_dir)              # .../<repo_root>
    csv_path = os.path.join(repo_root,'myproject', 'word_training', 'data', 'es_fr_top1000.csv')

    if not os.path.exists(csv_path):
        print(f"CSV file not found at: {csv_path}")
        return

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            batch = []
            total = 0
            BATCH_SIZE = 500
            for row in reader:
                if not row:
                    continue
                es = (row.get('spanish') or '').strip()
                fr = (row.get('french') or '').strip()
                es_syn = (row.get('spanish synonyms') or '').strip()
                fr_syn = (row.get('french synonyms') or '').strip()
                if es and fr:
                    batch.append(Word(word=es, translation=fr, word_sy=es_syn, translation_sy=fr_syn))
                    if len(batch) >= BATCH_SIZE:
                        Word.objects.bulk_create(batch, ignore_conflicts=True)
                        total += len(batch)
                        batch.clear()
            if batch:
                Word.objects.bulk_create(batch, ignore_conflicts=True)
                total += len(batch)
            print(f"Loaded {total} words successfully!")
    except Exception as e:
        print(f"Error loading words: {e}")


class Migration(migrations.Migration):
    dependencies = [
        ('word_training', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(load_words, migrations.RunPython.noop),
    ]