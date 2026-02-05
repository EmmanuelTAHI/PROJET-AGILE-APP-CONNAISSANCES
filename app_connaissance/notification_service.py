from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q
import logging

from app_connaissance.models import Progression, UserQuizAttempt, UserModuleStepCompletion
from app_connaissance.logging_utils import IntegrationLogger

logger = logging.getLogger('integration')

class NotificationService:
    """Service pour gérer les notifications email du plan d'intégration"""
    
    @staticmethod
    def send_welcome_email(user):
        """Envoie l'email de bienvenue avec le plan d'intégration"""
        try:
            subject = "Bienvenue dans votre plan d'intégration !"
            
            context = {
                'user': user,
                'login_url': f"{settings.BASE_URL}/login",
                'plan_url': f"{settings.BASE_URL}/integration/mon-plan/",
            }
            
            html_message = render_to_string('emails/welcome.html', context)
            text_message = render_to_string('emails/welcome.txt', context)
            
            send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            IntegrationLogger.log_user_action(
                user, 
                "Welcome email sent", 
                f"Email sent to {user.email}"
            )
            
        except Exception as e:
            IntegrationLogger.log_error(
                user, 
                "EmailError", 
                str(e), 
                "Welcome email"
            )
    
    @staticmethod
    def send_progress_reminder(user, days_inactive=7):
        """Envoie un rappel de progression"""
        try:
            # Vérifier si l'utilisateur est inactif
            last_activity = UserModuleStepCompletion.objects.filter(
                user=user
            ).order_by('-created_at').first()
            
            if not last_activity:
                days_since_start = (timezone.now() - user.date_joined).days
                if days_since_start >= days_inactive:
                    NotificationService._send_inactive_reminder(user, days_inactive)
            else:
                days_inactive_calc = (timezone.now() - last_activity.created_at).days
                if days_inactive_calc >= days_inactive:
                    NotificationService._send_inactive_reminder(user, days_inactive_calc)
                    
        except Exception as e:
            IntegrationLogger.log_error(
                user, 
                "EmailError", 
                str(e), 
                "Progress reminder"
            )
    
    @staticmethod
    def _send_inactive_reminder(user, days_inactive):
        """Envoie le rappel d'inactivité"""
        subject = f"Rappel : Votre plan d'intégration vous attend !"
        
        context = {
            'user': user,
            'days_inactive': days_inactive,
            'plan_url': f"{settings.BASE_URL}/integration/mon-plan/",
        }
        
        html_message = render_to_string('emails/inactivity_reminder.html', context)
        text_message = render_to_string('emails/inactivity_reminder.txt', context)
        
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False
        )
        
        IntegrationLogger.log_user_action(
            user, 
            "Inactivity reminder sent", 
            f"Days inactive: {days_inactive}"
        )
    
    @staticmethod
    def send_milestone_achievement(user, progression):
        """Envoie une notification de jalon atteint"""
        try:
            milestone = NotificationService._get_milestone(progression.pourcentage)
            if not milestone:
                return
            
            subject = f"🎉 Félicitations ! Vous avez atteint {milestone['percentage']}% de votre plan !"
            
            context = {
                'user': user,
                'milestone': milestone,
                'progression': progression,
                'plan_url': f"{settings.BASE_URL}/integration/mon-plan/",
            }
            
            html_message = render_to_string('emails/milestone.html', context)
            text_message = render_to_string('emails/milestone.txt', context)
            
            send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            IntegrationLogger.log_user_action(
                user, 
                "Milestone email sent", 
                f"Milestone: {milestone['percentage']}%"
            )
            
        except Exception as e:
            IntegrationLogger.log_error(
                user, 
                "EmailError", 
                str(e), 
                "Milestone notification"
            )
    
    @staticmethod
    def _get_milestone(percentage):
        """Détermine le jalon correspondant au pourcentage"""
        milestones = [
            {'percentage': 25, 'title': 'Débutant', 'message': 'Vous avez bien commencé !'},
            {'percentage': 50, 'title': 'Intermédiaire', 'message': 'Vous êtes à mi-chemin !'},
            {'percentage': 75, 'title': 'Avancé', 'message': 'Bientôt au bout !'},
            {'percentage': 100, 'title': 'Expert', 'message': 'Mission accomplie !'},
        ]
        
        for milestone in milestones:
            if percentage >= milestone['percentage']:
                return milestone
        
        return None
    
    @staticmethod
    def send_quiz_results(user, quiz_attempt):
        """Envoie les résultats d'un quiz"""
        try:
            subject = f"Résultats du quiz : {quiz_attempt.quiz.titre}"
            
            context = {
                'user': user,
                'quiz_attempt': quiz_attempt,
                'quiz': quiz_attempt.quiz,
                'plan_url': f"{settings.BASE_URL}/integration/mon-plan/",
            }
            
            html_message = render_to_string('emails/quiz_results.html', context)
            text_message = render_to_string('emails/quiz_results.txt', context)
            
            send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            IntegrationLogger.log_user_action(
                user, 
                "Quiz results sent", 
                f"Quiz: {quiz_attempt.quiz.titre}, Score: {quiz_attempt.score_pct}%"
            )
            
        except Exception as e:
            IntegrationLogger.log_error(
                user, 
                "EmailError", 
                str(e), 
                "Quiz results"
            )
    
    @staticmethod
    def send_completion_certificate(user, progression):
        """Envoie le certificat de complétion"""
        try:
            if progression.pourcentage < 100:
                return
            
            subject = "🏆 Félicitations ! Vous avez terminé votre plan d'intégration !"
            
            context = {
                'user': user,
                'progression': progression,
                'completion_date': timezone.now(),
                'certificate_url': f"{settings.BASE_URL}/integration/certificate/",
            }
            
            html_message = render_to_string('emails/completion_certificate.html', context)
            text_message = render_to_string('emails/completion_certificate.txt', context)
            
            send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            IntegrationLogger.log_user_action(
                user, 
                "Completion certificate sent", 
                f"Plan: {progression.plan.titre}"
            )
            
        except Exception as e:
            IntegrationLogger.log_error(
                user, 
                "EmailError", 
                str(e), 
                "Completion certificate"
            )
    
    @staticmethod
    def send_weekly_digest():
        """Envoie le résumé hebdomadaire aux managers"""
        try:
            # Récupérer tous les managers
            managers = User.objects.filter(
                profile__role='manager',
                is_active=True
            ).select_related('profile')
            
            for manager in managers:
                # Récupérer les statistiques des employés du manager
                department = manager.profile.department
                
                if not department:
                    continue
                
                # Statistiques des employés du département
                employees = User.objects.filter(
                    profile__department=department,
                    profile__role='employee',
                    is_active=True
                ).select_related('profile')
                
                stats = {
                    'total_employees': employees.count(),
                    'active_users': 0,
                    'completed_plans': 0,
                    'average_progress': 0,
                    'recent_completions': []
                }
                
                total_progress = 0
                for employee in employees:
                    # Vérifier l'activité (7 derniers jours)
                    recent_activity = UserModuleStepCompletion.objects.filter(
                        user=employee,
                        created_at__gte=timezone.now() - timezone.timedelta(days=7)
                    ).exists()
                    
                    if recent_activity:
                        stats['active_users'] += 1
                    
                    # Progression
                    progression = Progression.objects.filter(
                        user=employee
                    ).select_related('plan').first()
                    
                    if progression:
                        total_progress += progression.pourcentage
                        
                        if progression.pourcentage >= 100:
                            stats['completed_plans'] += 1
                            
                            # Vérifier si complété récemment
                            if progression.updated_at >= timezone.now() - timezone.timedelta(days=7):
                                stats['recent_completions'].append({
                                    'employee': employee.get_full_name() or employee.username,
                                    'plan': progression.plan.titre,
                                    'completion_date': progression.updated_at
                                })
                
                if stats['total_employees'] > 0:
                    stats['average_progress'] = total_progress / stats['total_employees']
                
                # Envoyer l'email
                subject = f"Résumé hebdomadaire - Département {department.name}"
                
                context = {
                    'manager': manager,
                    'department': department,
                    'stats': stats,
                    'admin_url': f"{settings.BASE_URL}/admin/",
                }
                
                html_message = render_to_string('emails/weekly_digest.html', context)
                text_message = render_to_string('emails/weekly_digest.txt', context)
                
                send_mail(
                    subject=subject,
                    message=text_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[manager.email],
                    html_message=html_message,
                    fail_silently=False
                )
                
                IntegrationLogger.log_user_action(
                    manager, 
                    "Weekly digest sent", 
                    f"Department: {department.name}"
                )
                
        except Exception as e:
            logger.error(f"Error sending weekly digest: {str(e)}")

# Signaux pour déclencher les notifications
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=UserQuizAttempt)
def quiz_attempt_notification(sender, instance, created, **kwargs):
    """Envoie les résultats de quiz par email"""
    if created:
        NotificationService.send_quiz_results(instance.user, instance)

@receiver(post_save, sender=Progression)
def progression_notification(sender, instance, created, **kwargs):
    """Envoie les notifications de progression"""
    if not created:  # Mise à jour de progression
        NotificationService.send_milestone_achievement(instance.user, instance)
        
        if instance.pourcentage >= 100:
            NotificationService.send_completion_certificate(instance.user, instance)
