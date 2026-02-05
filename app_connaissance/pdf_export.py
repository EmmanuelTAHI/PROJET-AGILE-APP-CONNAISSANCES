from django.http import HttpResponse, Http404
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from weasyprint import HTML, CSS
from weasyprint.text.font_config import FontConfiguration

from app_connaissance.models import PlanIntegration, Module, ModuleStep, Progression, UserModuleStepCompletion
from app_connaissance.views import _get_user_plan, _progress_for_plan
from app_connaissance.logging_utils import IntegrationLogger

@login_required
def export_plan_pdf(request):
    """Exporte le plan d'intégration en PDF"""
    try:
        # Récupérer le plan de l'utilisateur
        plan = _get_user_plan(request)
        if not plan:
            raise Http404("Aucun plan d'intégration trouvé")
        
        # Récupérer la progression
        progress = _progress_for_plan(request.user, plan)
        
        # Préparer les données pour le template
        context = {
            'user': request.user,
            'plan': plan,
            'progress': progress,
            'modules': progress['modules'],
            'export_date': timezone.now(),
            'base_url': request.build_absolute_uri('/'),
        }
        
        # Rendre le template HTML
        html_string = render_to_string('integration/plan_export.html', context)
        
        # Remplacer les data-percentage par style width pour WeasyPrint
        import re
        html_string = re.sub(
            r'<div class="progress-fill" data-percentage="(\d+)">',
            lambda m: f'<div class="progress-fill" style="width: {m.group(1)}%">',
            html_string
        )
        
        # Configuration des polices
        font_config = FontConfiguration()
        
        # Créer le PDF
        html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
        css = CSS(string='''
            @page {
                size: A4;
                margin: 2cm;
                @top-center {
                    content: "Plan d'Intégration";
                    font-size: 10pt;
                    color: #666;
                }
                @bottom-center {
                    content: "Page " counter(page) " / " counter(pages);
                    font-size: 10pt;
                    color: #666;
                }
            }
            body {
                font-family: Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.4;
                color: #333;
            }
            h1 {
                color: #2563eb;
                font-size: 24pt;
                margin-bottom: 20px;
                border-bottom: 2px solid #2563eb;
                padding-bottom: 10px;
            }
            h2 {
                color: #1e40af;
                font-size: 16pt;
                margin-top: 20px;
                margin-bottom: 10px;
            }
            h3 {
                color: #3730a3;
                font-size: 14pt;
                margin-top: 15px;
                margin-bottom: 8px;
            }
            .header-info {
                background: #f8fafc;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
            .progress-bar {
                width: 100%;
                height: 20px;
                background: #e5e7eb;
                border-radius: 10px;
                overflow: hidden;
                margin: 10px 0;
            }
            .progress-fill {
                height: 100%;
                background: #10b981;
                transition: width 0.3s ease;
            }
            .module-card {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
                page-break-inside: avoid;
            }
            .step-item {
                margin-left: 20px;
                padding: 5px 0;
                border-left: 2px solid #e5e7eb;
                padding-left: 15px;
                position: relative;
            }
            .step-item::before {
                content: "✓";
                position: absolute;
                left: -8px;
                background: white;
                border: 2px solid #10b981;
                border-radius: 50%;
                width: 16px;
                height: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 10px;
                color: #10b981;
            }
            .step-item.completed::before {
                background: #10b981;
                color: white;
            }
            .step-item.pending::before {
                content: "○";
                border-color: #6b7280;
                color: #6b7280;
            }
            .quiz-info {
                background: #fef3c7;
                border: 1px solid #f59e0b;
                border-radius: 5px;
                padding: 10px;
                margin-top: 10px;
            }
            .footer-info {
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e5e7eb;
                font-size: 10pt;
                color: #6b7280;
            }
            .page-break {
                page-break-before: always;
            }
        ''')
        
        # Générer le PDF
        pdf = html.write_pdf(stylesheets=[css], font_config=font_config)
        
        # Logger l'export
        IntegrationLogger.log_user_action(
            request.user,
            "Plan PDF exported",
            f"Plan: {plan.titre}"
        )
        
        # Créer la réponse HTTP
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"plan_integration_{request.user.username}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        IntegrationLogger.log_error(
            request.user,
            "PDFExportError",
            str(e),
            "Plan PDF export"
        )
        raise Http404("Erreur lors de la génération du PDF")

@login_required
def export_certificate_pdf(request):
    """Exporte le certificat de complétion en PDF"""
    try:
        # Récupérer le plan et la progression
        plan = _get_user_plan(request)
        if not plan:
            raise Http404("Aucun plan d'intégration trouvé")
        
        progress = _progress_for_plan(request.user, plan)
        
        # Vérifier si le plan est complété
        if progress['pourcentage'] < 100:
            raise Http404("Le plan n'est pas encore complété")
        
        # Préparer les données
        context = {
            'user': request.user,
            'plan': plan,
            'completion_date': progress['progression_obj'].updated_at,
            'export_date': timezone.now(),
            'base_url': request.build_absolute_uri('/'),
        }
        
        # Rendre le template
        html_string = render_to_string('integration/certificate_export.html', context)
        
        # Configuration des polices
        font_config = FontConfiguration()
        
        # Créer le PDF
        html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
        css = CSS(string='''
            @page {
                size: A4 landscape;
                margin: 1cm;
            }
            body {
                font-family: Georgia, serif;
                font-size: 14pt;
                text-align: center;
                background: linear-gradient(45deg, #f0f9ff 0%, #e0f2fe 100%);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            }
            .certificate {
                background: white;
                border: 3px solid #2563eb;
                border-radius: 15px;
                padding: 40px;
                max-width: 800px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                position: relative;
            }
            .certificate::before {
                content: "";
                position: absolute;
                top: -15px;
                left: 50%;
                transform: translateX(-50%);
                width: 30px;
                height: 30px;
                background: #2563eb;
                border-radius: 50%;
            }
            .certificate::after {
                content: "";
                position: absolute;
                bottom: -15px;
                left: 50%;
                transform: translateX(-50%);
                width: 30px;
                height: 30px;
                background: #2563eb;
                border-radius: 50%;
            }
            h1 {
                font-size: 36pt;
                color: #1e40af;
                margin-bottom: 10px;
                text-transform: uppercase;
                letter-spacing: 2px;
            }
            .subtitle {
                font-size: 18pt;
                color: #64748b;
                margin-bottom: 30px;
            }
            .recipient {
                font-size: 24pt;
                font-weight: bold;
                color: #1e293b;
                margin: 20px 0;
                border-bottom: 2px solid #cbd5e1;
                padding-bottom: 10px;
                display: inline-block;
            }
            .achievement {
                font-size: 16pt;
                color: #475569;
                margin: 20px 0;
                line-height: 1.6;
            }
            .plan-name {
                font-size: 20pt;
                font-weight: bold;
                color: #2563eb;
                margin: 15px 0;
            }
            .completion-date {
                font-size: 14pt;
                color: #64748b;
                margin: 20px 0;
            }
            .signatures {
                display: flex;
                justify-content: space-around;
                margin-top: 50px;
            }
            .signature {
                text-align: center;
                min-width: 200px;
            }
            .signature-line {
                border-bottom: 1px solid #374151;
                margin: 40px 0 10px 0;
            }
            .signature-title {
                font-size: 12pt;
                color: #6b7280;
            }
            .seal {
                position: absolute;
                bottom: 20px;
                right: 20px;
                width: 80px;
                height: 80px;
                border: 3px solid #dc2626;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12pt;
                font-weight: bold;
                color: #dc2626;
                transform: rotate(-15deg);
            }
        ''')
        
        # Générer le PDF
        pdf = html.write_pdf(stylesheets=[css], font_config=font_config)
        
        # Logger l'export
        IntegrationLogger.log_user_action(
            request.user,
            "Certificate PDF exported",
            f"Plan: {plan.titre}"
        )
        
        # Créer la réponse HTTP
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"certificat_{request.user.username}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        IntegrationLogger.log_error(
            request.user,
            "CertificatePDFError",
            str(e),
            "Certificate PDF export"
        )
        raise Http404("Erreur lors de la génération du certificat")
