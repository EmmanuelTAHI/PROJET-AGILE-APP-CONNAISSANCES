from django.core.management.base import BaseCommand
from app_connaissance.badges_models import Badge, Achievement
import json

class Command(BaseCommand):
    help = 'Crée les badges et accomplissements par défaut pour le plan d intégration'
    
    def handle(self, *args, **options):
        self.stdout.write('Création des badges et accomplissements...')
        
        # Badges de progression
        self._create_progression_badges()
        
        # Badges de quiz
        self._create_quiz_badges()
        
        # Badges d'étapes
        self._create_step_badges()
        
        # Badges spéciaux
        self._create_special_badges()
        
        # Accomplissements
        self._create_achievements()
        
        self.stdout.write(self.style.SUCCESS('✅ Badges et accomplissements créés avec succès!'))
    
    def _create_progression_badges(self):
        """Crée les badges de progression"""
        badges_data = [
            {
                'name': 'Premiers pas',
                'description': 'Commencer son plan d\'intégration',
                'icon': 'baby',
                'badge_type': 'progression',
                'condition': {'type': 'percentage', 'value': 1},
                'points': 10
            },
            {
                'name': 'Apprenti',
                'description': 'Atteindre 25% de progression',
                'icon': 'graduation-cap',
                'badge_type': 'progression',
                'condition': {'type': 'percentage', 'value': 25},
                'points': 25
            },
            {
                'name': 'Confirmé',
                'description': 'Atteindre 50% de progression',
                'icon': 'award',
                'badge_type': 'progression',
                'condition': {'type': 'percentage', 'value': 50},
                'points': 50
            },
            {
                'name': 'Expert',
                'description': 'Atteindre 75% de progression',
                'icon': 'star',
                'badge_type': 'progression',
                'condition': {'type': 'percentage', 'value': 75},
                'points': 75
            },
            {
                'name': 'Maître',
                'description': 'Terminer son plan d\'intégration à 100%',
                'icon': 'trophy',
                'badge_type': 'progression',
                'condition': {'type': 'percentage', 'value': 100},
                'points': 100
            }
        ]
        
        for badge_data in badges_data:
            badge, created = Badge.objects.get_or_create(
                name=badge_data['name'],
                defaults=badge_data
            )
            if created:
                self.stdout.write(f'  🏆 Badge créé: {badge.name}')
    
    def _create_quiz_badges(self):
        """Crée les badges de quiz"""
        badges_data = [
            {
                'name': 'Premier quiz',
                'description': 'Passer son premier quiz',
                'icon': 'clipboard-check',
                'badge_type': 'quiz',
                'condition': {'type': 'count', 'value': 1},
                'points': 15
            },
            {
                'name': 'Génie des quiz',
                'description': 'Réussir 5 quiz avec un score parfait',
                'icon': 'brain',
                'badge_type': 'quiz',
                'condition': {'type': 'count', 'value': 5},
                'points': 50
            },
            {
                'name': 'Score parfait',
                'description': 'Obtenir 100% à un quiz',
                'icon': 'target',
                'badge_type': 'quiz',
                'condition': {'type': 'exact', 'value': 100},
                'points': 30
            }
        ]
        
        for badge_data in badges_data:
            badge, created = Badge.objects.get_or_create(
                name=badge_data['name'],
                defaults=badge_data
            )
            if created:
                self.stdout.write(f'  🎯 Badge créé: {badge.name}')
    
    def _create_step_badges(self):
        """Crée les badges d'étapes"""
        badges_data = [
            {
                'name': 'Travailleur acharné',
                'description': 'Compléter 10 étapes',
                'icon': 'check-double',
                'badge_type': 'steps',
                'condition': {'type': 'count', 'value': 10},
                'points': 40
            },
            {
                'name': 'Machine à étapes',
                'description': 'Compléter 25 étapes',
                'icon': 'cogs',
                'badge_type': 'steps',
                'condition': {'type': 'count', 'value': 25},
                'points': 75
            },
            {
                'name': 'Maître des étapes',
                'description': 'Compléter 50 étapes',
                'icon': 'crown',
                'badge_type': 'steps',
                'condition': {'type': 'count', 'value': 50},
                'points': 150
            }
        ]
        
        for badge_data in badges_data:
            badge, created = Badge.objects.get_or_create(
                name=badge_data['name'],
                defaults=badge_data
            )
            if created:
                self.stdout.write(f'  ✅ Badge créé: {badge.name}')
    
    def _create_special_badges(self):
        """Crée les badges spéciaux"""
        badges_data = [
            {
                'name': 'Pionnier',
                'description': 'Être parmi les 10 premiers utilisateurs',
                'icon': 'rocket',
                'badge_type': 'special',
                'condition': {'type': 'range', 'min': 1, 'max': 10},
                'points': 100
            },
            {
                'name': 'Sprinter',
                'description': 'Terminer le plan en moins d\'une semaine',
                'icon': 'zap',
                'badge_type': 'time',
                'condition': {'type': 'exact', 'value': 'fast'},
                'points': 80
            },
            {
                'name': 'Persévérant',
                'description': 'Prendre plus d\'un mois mais terminer le plan',
                'icon': 'hourglass-half',
                'badge_type': 'time',
                'condition': {'type': 'exact', 'value': 'persistent'},
                'points': 60
            }
        ]
        
        for badge_data in badges_data:
            badge, created = Badge.objects.get_or_create(
                name=badge_data['name'],
                defaults=badge_data
            )
            if created:
                self.stdout.write(f'  ⭐ Badge spécial créé: {badge.name}')
    
    def _create_achievements(self):
        """Crée les accomplissements"""
        achievements_data = [
            {
                'title': 'Début de l\'aventure',
                'description': 'Commencer son premier jour d\'intégration',
                'points_reward': 20,
                'is_secret': False,
                'is_repeatable': False
            },
            {
                'title': 'Quiz Master',
                'description': 'Réussir tous les quiz du plan',
                'points_reward': 100,
                'is_secret': False,
                'is_repeatable': False
            },
            {
                'title': 'Compléteur obsessionnel',
                'description': 'Compléter toutes les étapes disponibles',
                'points_reward': 150,
                'is_secret': False,
                'is_repeatable': False
            },
            {
                'title': 'Explorateur',
                'description': 'Consulter toutes les connaissances liées',
                'points_reward': 50,
                'is_secret': True,
                'is_repeatable': False
            },
            {
                'title': 'Vitesse lumière',
                'description': 'Terminer un module en un jour',
                'points_reward': 75,
                'is_secret': True,
                'is_repeatable': True
            },
            {
                'title': 'Marathonien',
                'description': 'Être actif pendant 30 jours consécutifs',
                'points_reward': 200,
                'is_secret': True,
                'is_repeatable': False
            }
        ]
        
        for achievement_data in achievements_data:
            achievement, created = Achievement.objects.get_or_create(
                title=achievement_data['title'],
                defaults=achievement_data
            )
            if created:
                self.stdout.write(f'  🎖️ Accomplissement créé: {achievement.title}')
