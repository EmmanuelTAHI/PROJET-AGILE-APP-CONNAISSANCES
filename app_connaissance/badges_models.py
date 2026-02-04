from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError

class Badge(models.Model):
    """Badges et récompenses pour les accomplissements"""
    
    class BadgeType(models.TextChoices):
        PROGRESSION = 'progression', 'Progression'
        QUIZ = 'quiz', 'Quiz'
        STEPS = 'steps', 'Étapes'
        TIME = 'time', 'Temps'
        SPECIAL = 'special', 'Spécial'
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, help_text="Nom de l'icône (ex: trophy, star, medal)")
    badge_type = models.CharField(max_length=20, choices=BadgeType.choices)
    condition = models.JSONField(help_text="Conditions pour obtenir le badge")
    points = models.PositiveIntegerField(default=0, help_text="Points attribués")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['badge_type', 'name']
        verbose_name = "Badge"
        verbose_name_plural = "Badges"
    
    def __str__(self):
        return f"{self.name} ({self.get_badge_type_display()})"

class UserBadge(models.Model):
    """Badges obtenus par les utilisateurs"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='awarded_to')
    earned_at = models.DateTimeField(auto_now_add=True)
    progress_data = models.JSONField(default=dict, help_text="Données de progression au moment de l'obtention")
    
    class Meta:
        unique_together = ['user', 'badge']
        ordering = ['-earned_at']
        verbose_name = "Badge utilisateur"
        verbose_name_plural = "Badges utilisateurs"
    
    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"

class Achievement(models.Model):
    """Accomplissements spéciaux avec récompenses"""
    
    title = models.CharField(max_length=150)
    description = models.TextField()
    badge = models.ForeignKey(Badge, on_delete=models.SET_NULL, null=True, blank=True)
    points_reward = models.PositiveIntegerField(default=0)
    is_secret = models.BooleanField(default=False, help_text="L'accomplissement est caché jusqu'à obtention")
    is_repeatable = models.BooleanField(default=False, help_text="Peut être obtenu plusieurs fois")
    
    class Meta:
        ordering = ['title']
        verbose_name = "Accomplissement"
        verbose_name_plural = "Accomplissements"
    
    def __str__(self):
        return self.title

class UserAchievement(models.Model):
    """Accomplissements obtenus par les utilisateurs"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name='awarded_to')
    earned_at = models.DateTimeField(auto_now_add=True)
    count = models.PositiveIntegerField(default=1, help_text="Nombre de fois obtenu")
    metadata = models.JSONField(default=dict, help_text="Métadonnées de l'obtention")
    
    class Meta:
        unique_together = ['user', 'achievement']
        ordering = ['-earned_at']
        verbose_name = "Accomplissement utilisateur"
        verbose_name_plural = "Accomplissements utilisateurs"
    
    def __str__(self):
        return f"{self.user.username} - {self.achievement.title}"

class Leaderboard(models.Model):
    """Classements et compétitions"""
    
    class LeaderboardType(models.TextChoices):
        WEEKLY = 'weekly', 'Hebdomadaire'
        MONTHLY = 'monthly', 'Mensuel'
        ALL_TIME = 'all_time', 'Tous les temps'
        DEPARTMENT = 'department', 'Par département'
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    leaderboard_type = models.CharField(max_length=20, choices=LeaderboardType.choices)
    department = models.ForeignKey('Department', on_delete=models.CASCADE, null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = "Classement"
        verbose_name_plural = "Classements"
    
    def __str__(self):
        return f"{self.name} ({self.get_leaderboard_type_display()})"

class LeaderboardEntry(models.Model):
    """Entrées dans les classements"""
    leaderboard = models.ForeignKey(Leaderboard, on_delete=models.CASCADE, related_name='entries')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leaderboard_entries')
    score = models.PositiveIntegerField(default=0)
    rank = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['leaderboard', 'user']
        ordering = ['leaderboard', 'rank']
        verbose_name = "Entrée de classement"
        verbose_name_plural = "Entrées de classement"
    
    def __str__(self):
        return f"#{self.rank} {self.user.username} - {self.score} pts"

class BadgeService:
    """Service pour la gestion des badges et accomplissements"""
    
    @staticmethod
    def check_and_award_badges(user, event_type, event_data):
        """Vérifie et attribue les badges selon les événements"""
        badges = Badge.objects.filter(is_active=True, badge_type=event_type)
        
        for badge in badges:
            if BadgeService._check_condition(badge.condition, event_data):
                UserBadge.objects.get_or_create(
                    user=user,
                    badge=badge,
                    defaults={'progress_data': event_data}
                )
    
    @staticmethod
    def _check_condition(condition, data):
        """Vérifie si une condition est remplie"""
        condition_type = condition.get('type')
        
        if condition_type == 'percentage':
            return data.get('percentage', 0) >= condition.get('value', 0)
        
        elif condition_type == 'count':
            return data.get('count', 0) >= condition.get('value', 0)
        
        elif condition_type == 'exact':
            return data.get('value') == condition.get('value')
        
        elif condition_type == 'range':
            value = data.get('value', 0)
            return condition.get('min', 0) <= value <= condition.get('max', 100)
        
        return False
    
    @staticmethod
    def get_user_stats(user):
        """Statistiques de badges pour un utilisateur"""
        badges = UserBadge.objects.filter(user=user).select_related('badge')
        achievements = UserAchievement.objects.filter(user=user).select_related('achievement')
        
        total_points = sum(badge.badge.points for badge in badges)
        total_points += sum(achievement.achievement.points_reward for achievement in achievements)
        
        return {
            'badges_count': badges.count(),
            'achievements_count': achievements.count(),
            'total_points': total_points,
            'badges_by_type': {
                badge_type: badges.filter(badge__badge_type=badge_type).count()
                for badge_type, _ in Badge.BadgeType.choices
            }
        }
    
    @staticmethod
    def update_leaderboard(leaderboard_type='all_time'):
        """Met à jour les classements"""
        if leaderboard_type == 'all_time':
            # Classement tous les temps
            users = User.objects.annotate(
                total_points=models.Sum(
                    models.Case(
                        models.When(
                            badges__badge__points__gt=0,
                            then=models.F('badges__badge__points')
                        ),
                        default=0,
                        output_field=models.IntegerField()
                    )
                )
            ).order_by('-total_points')
            
            leaderboard, created = Leaderboard.objects.get_or_create(
                name="Classement général",
                leaderboard_type=Leaderboard.LeaderboardType.ALL_TIME,
                defaults={
                    'description': "Classement général de tous les temps",
                    'start_date': timezone.now()
                }
            )
            
            # Mettre à jour les entrées
            for rank, user in enumerate(users, 1):
                LeaderboardEntry.objects.update_or_create(
                    leaderboard=leaderboard,
                    user=user,
                    defaults={
                        'score': user.total_points or 0,
                        'rank': rank
                    }
                )

# Signaux pour automatiquement attribuer les badges
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=UserQuizAttempt)
def quiz_attempt_badge_check(sender, instance, created, **kwargs):
    """Attribue des badges lors des tentatives de quiz"""
    if created and instance.passed:
        BadgeService.check_and_award_badges(
            instance.user,
            Badge.BadgeType.QUIZ,
            {
                'quiz_id': instance.quiz.id,
                'score': instance.score_pct,
                'passed': instance.passed
            }
        )

@receiver(post_save, sender=UserModuleStepCompletion)
def step_completion_badge_check(sender, instance, created, **kwargs):
    """Attribue des badges lors des complétions d'étapes"""
    if created:
        # Compter le nombre total d'étapes complétées
        total_steps = UserModuleStepCompletion.objects.filter(
            user=instance.user
        ).count()
        
        BadgeService.check_and_award_badges(
            instance.user,
            Badge.BadgeType.STEPS,
            {
                'step_id': instance.module_step.id,
                'count': total_steps
            }
        )

@receiver(post_save, sender=Progression)
def progression_badge_check(sender, instance, created, **kwargs):
    """Attribue des badges lors de la progression"""
    BadgeService.check_and_award_badges(
        instance.user,
        Badge.BadgeType.PROGRESSION,
        {
            'percentage': instance.pourcentage,
            'plan_id': instance.plan.id
        }
    )
