from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from verbs.services import init_user_conjugations

class Command(BaseCommand):
    help = 'Initialize conjugation data for users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Specific username to initialize (if not provided, initializes all users)',
        )
        parser.add_argument(
            '--language',
            type=str,
            default='FR',
            choices=['FR', 'ES'],
            help='Language to initialize (FR for French, ES for Spanish)',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of verbs to initialize per user',
        )

    def handle(self, *args, **options):
        username = options['username']
        language = options['language']
        count = options['count']
        
        if username:
            # Initialize specific user
            try:
                user = User.objects.get(username=username)
                init_user_conjugations(user, language, count)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully initialized {count} {language} verbs for user "{username}"'
                    )
                )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User "{username}" not found')
                )
        else:
            # Initialize all users
            users = User.objects.all()
            if not users.exists():
                self.stdout.write(
                    self.style.WARNING('No users found in the database')
                )
                return
            
            for user in users:
                init_user_conjugations(user, language, count)
                self.stdout.write(f'Initialized user: {user.username}')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully initialized {count} {language} verbs for {users.count()} users'
                )
            )
