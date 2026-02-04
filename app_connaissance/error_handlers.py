from django.http import JsonResponse
from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError
from django.conf import settings
from django.utils import timezone
import logging
from .logging_utils import IntegrationLogger

logger = logging.getLogger('integration')

class IntegrationErrorHandler:
    """Gestionnaire d'erreurs centralisé pour le plan d'intégration"""
    
    @staticmethod
    def handle_database_error(request, error, context=""):
        """Gère les erreurs de base de données"""
        error_id = f"DB_{timezone.now().timestamp()}"
        
        if request.user.is_authenticated:
            IntegrationLogger.log_error(
                request.user, 
                "DatabaseError", 
                str(error), 
                f"{context} - Error ID: {error_id}"
            )
        
        if settings.DEBUG:
            # En mode debug, afficher l'erreur détaillée
            return render(request, 'errors/database_debug.html', {
                'error': error,
                'context': context,
                'error_id': error_id
            }, status=500)
        else:
            # En production, afficher une page générique
            return render(request, 'errors/database.html', {
                'error_id': error_id
            }, status=500)
    
    @staticmethod
    def handle_permission_error(request, error, context=""):
        """Gère les erreurs de permission"""
        if request.user.is_authenticated:
            IntegrationLogger.log_error(
                request.user, 
                "PermissionDenied", 
                str(error), 
                context
            )
        
        return render(request, 'errors/permission.html', {
            'error_message': "Vous n'avez pas les permissions nécessaires pour accéder à cette ressource."
        }, status=403)
    
    @staticmethod
    def handle_not_found(request, context=""):
        """Gère les erreurs 404"""
        if request.user.is_authenticated:
            IntegrationLogger.log_error(
                request.user, 
                "NotFound", 
                "Resource not found", 
                context
            )
        
        return render(request, 'errors/404.html', status=404)
    
    @staticmethod
    def handle_validation_error(request, error, context=""):
        """Gère les erreurs de validation"""
        error_id = f"VAL_{timezone.now().timestamp()}"
        
        if request.user.is_authenticated:
            IntegrationLogger.log_error(
                request.user, 
                "ValidationError", 
                str(error), 
                f"{context} - Error ID: {error_id}"
            )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Requête AJAX
            return JsonResponse({
                'success': False,
                'error': str(error),
                'error_id': error_id,
                'error_type': 'validation'
            }, status=400)
        else:
            # Requête normale
            return render(request, 'errors/validation.html', {
                'error': str(error),
                'error_id': error_id
            }, status=400)
    
    @staticmethod
    def handle_general_error(request, error, context=""):
        """Gère les erreurs générales"""
        error_id = f"GEN_{timezone.now().timestamp()}"
        
        if request.user.is_authenticated:
            IntegrationLogger.log_error(
                request.user, 
                "GeneralError", 
                str(error), 
                f"{context} - Error ID: {error_id}"
            )
        
        if settings.DEBUG:
            return render(request, 'errors/general_debug.html', {
                'error': error,
                'context': context,
                'error_id': error_id
            }, status=500)
        else:
            return render(request, 'errors/general.html', {
                'error_id': error_id
            }, status=500)

# Décorateurs pour la gestion des erreurs
def handle_integration_errors(view_func):
    """Décorateur pour gérer les erreurs dans les vues d'intégration"""
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except DatabaseError as e:
            return IntegrationErrorHandler.handle_database_error(
                request, e, f"View: {view_func.__name__}"
            )
        except PermissionDenied as e:
            return IntegrationErrorHandler.handle_permission_error(
                request, e, f"View: {view_func.__name__}"
            )
        except Exception as e:
            return IntegrationErrorHandler.handle_general_error(
                request, e, f"View: {view_func.__name__}"
            )
    return wrapper

def handle_ajax_errors(view_func):
    """Décorateur pour gérer les erreurs dans les vues AJAX"""
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except DatabaseError as e:
            return JsonResponse({
                'success': False,
                'error': 'Database error occurred',
                'error_type': 'database'
            }, status=500)
        except PermissionDenied as e:
            return JsonResponse({
                'success': False,
                'error': 'Permission denied',
                'error_type': 'permission'
            }, status=403)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': 'An error occurred',
                'error_type': 'general'
            }, status=500)
    return wrapper
