import logging
from django.conf import settings
from django.utils import timezone

# Configuration du logging pour l'application d'intégration
logger = logging.getLogger('integration')

class IntegrationLogger:
    """Logger spécialisé pour les actions du plan d'intégration"""
    
    @staticmethod
    def log_user_action(user, action, details=None, level='info'):
        """Enregistre une action utilisateur"""
        message = f"User {user.username} ({user.id}) - {action}"
        if details:
            message += f" - Details: {details}"
        
        getattr(logger, level)(message, extra={
            'user_id': user.id,
            'username': user.username,
            'action': action,
            'details': details,
            'timestamp': timezone.now().isoformat()
        })
    
    @staticmethod
    def log_module_progress(user, module, step_action, details=None):
        """Enregistre la progression sur un module"""
        action = f"Module {module.id} ({module.titre}) - {step_action}"
        IntegrationLogger.log_user_action(user, action, details)
    
    @staticmethod
    def log_quiz_attempt(user, quiz, score, passed):
        """Enregistre une tentative de quiz"""
        action = f"Quiz {quiz.id} ({quiz.titre}) - Score: {score}% - {'Passed' if passed else 'Failed'}"
        IntegrationLogger.log_user_action(user, action)
    
    @staticmethod
    def log_plan_access(user, plan, progress_pct=None):
        """Enregistre l'accès au plan d'intégration"""
        action = f"Plan {plan.id} ({plan.titre}) - Accessed"
        if progress_pct is not None:
            action += f" - Progress: {progress_pct}%"
        IntegrationLogger.log_user_action(user, action)
    
    @staticmethod
    def log_error(user, error_type, error_message, context=None):
        """Enregistre une erreur"""
        action = f"Error {error_type}: {error_message}"
        if context:
            action += f" - Context: {context}"
        IntegrationLogger.log_user_action(user, action, level='error')
    
    @staticmethod
    def log_admin_action(user, admin_action, target_type, target_id, details=None):
        """Enregistre une action d'administration"""
        action = f"Admin {admin_action} - {target_type} {target_id}"
        if details:
            action += f" - {details}"
        IntegrationLogger.log_user_action(user, action)

# Middleware pour capturer les actions utilisateur
class IntegrationLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Logger l'accès aux pages du plan d'intégration
        if request.user.is_authenticated and '/integration/' in request.path:
            IntegrationLogger.log_user_action(
                request.user, 
                f"Page accessed: {request.path}",
                f"Method: {request.method}, Status: {response.status_code}"
            )
        
        return response
