from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app_connaissance.models import Department, Poste, UserProfile

class Command(BaseCommand):
    help = 'Crée un utilisateur de test complet avec le profil bk/bk123'

    def handle(self, *args, **options):
        self.stdout.write('Création de l\'utilisateur de test bk...')

        # Vérifier si l'utilisateur existe déjà
        if User.objects.filter(username='bk').exists():
            self.stdout.write(self.style.WARNING('L\'utilisateur bk existe déjà. Suppression de l\'ancien utilisateur...'))
            User.objects.filter(username='bk').delete()

        # Créer l'utilisateur Django
        user = User.objects.create_user(
            username='bk',
            email='bk@test.com',
            password='bk123',
            first_name='Test',
            last_name='User'
        )

        # Récupérer un département et un poste existants
        department = Department.objects.first()
        if not department:
            self.stdout.write(self.style.ERROR('Aucun département trouvé. Veuillez d\'abord exécuter les commandes de peuplement.'))
            user.delete()
            return

        poste = Poste.objects.filter(department=department).first()
        if not poste:
            self.stdout.write(self.style.ERROR('Aucun poste trouvé. Veuillez d\'abord exécuter les commandes de peuplement.'))
            user.delete()
            return

        # Créer le profil utilisateur
        profile = UserProfile.objects.create(
            user=user,
            display_name='Test User BK',
            role='employee',
            department=department,
            poste=poste,
            type_contrat='CDI',
            must_change_password=False,
            is_active=True
        )

        self.stdout.write(self.style.SUCCESS(f'✅ Utilisateur bk créé avec succès!'))
        self.stdout.write(f'   📧 Email: {user.email}')
        self.stdout.write(f'   👤 Nom: {user.get_full_name()}')
        self.stdout.write(f'   🏢 Département: {department.name}')
        self.stdout.write(f'   💼 Poste: {poste.intitule}')
        self.stdout.write(f'   📋 Plan d\'intégration: {poste.plan_integration.titre if poste.plan_integration else "Aucun"}')
        self.stdout.write(f'')
        self.stdout.write(self.style.SUCCESS('🔑 Identifiants de connexion:'))
        self.stdout.write(f'   Utilisateur: bk')
        self.stdout.write(f'   Mot de passe: bk123')
        self.stdout.write(f'')
        self.stdout.write('🌐 Vous pouvez maintenant vous connecter et tester le plan d\'intégration!')
