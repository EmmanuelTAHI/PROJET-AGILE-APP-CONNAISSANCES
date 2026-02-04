from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg, Q
from django.utils.safestring import mark_safe
import json

from .models import (
    Department, Poste, PlanIntegration, Module, ModuleStep,
    Quiz, QuizQuestion, QuizChoice, UserProfile, Progression,
    UserModuleStepCompletion, UserQuizAttempt, KnowledgeItem,
    KnowledgeKind, ModuleKnowledgeItem
)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee_count', 'plan_count', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    def employee_count(self, obj):
        count = UserProfile.objects.filter(department=obj).count()
        return f"{count} employé{'s' if count != 1 else ''}"
    employee_count.short_description = "Employés"
    
    def plan_count(self, obj):
        count = PlanIntegration.objects.filter(postes__department=obj).distinct().count()
        return f"{count} plan{'s' if count != 1 else ''}"
    plan_count.short_description = "Plans"

@admin.register(Poste)
class PosteAdmin(admin.ModelAdmin):
    list_display = ('intitule', 'department', 'has_plan', 'employee_count', 'created_at')
    list_filter = ('department', 'created_at')
    search_fields = ('intitule', 'description')
    ordering = ('department', 'intitule')
    
    def has_plan(self, obj):
        if obj.plan_integration:
            return format_html(
                '<a href="{}" class="button">✓</a>',
                reverse('admin:app_connaissance_planintegration_change', args=[obj.plan_integration.id])
            )
        return "✗"
    has_plan.short_description = "Plan"
    has_plan.allow_tags = True
    
    def employee_count(self, obj):
        count = UserProfile.objects.filter(poste=obj).count()
        return f"{count} employé{'s' if count != 1 else ''}"
    employee_count.short_description = "Employés"

@admin.register(PlanIntegration)
class PlanIntegrationAdmin(admin.ModelAdmin):
    list_display = ('titre', 'duration', 'module_count', 'poste_count', 'progress_stats', 'created_at')
    list_filter = ('created_at', 'duree_semaines')
    search_fields = ('titre', 'description')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('titre', 'description', 'duree_semaines')
        }),
        ('Statistiques', {
            'fields': ('module_count', 'poste_count', 'user_progress'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ('module_count', 'poste_count', 'user_progress')
    
    def module_count(self, obj):
        count = obj.modules.count()
        return f"{count} module{'s' if count != 1 else ''}"
    module_count.short_description = "Modules"
    
    def poste_count(self, obj):
        count = Poste.objects.filter(plan_integration=obj).count()
        return f"{count} poste{'s' if count != 1 else ''}"
    poste_count.short_description = "Postes"
    
    def progress_stats(self, obj):
        # Calculer les statistiques de progression
        progressions = Progression.objects.filter(plan=obj)
        if not progressions:
            return "Aucune progression"
        
        avg_progress = progressions.aggregate(Avg('pourcentage'))['pourcentage__avg']
        completed = progressions.filter(pourcentage=100).count()
        total = progressions.count()
        
        return format_html(
            '<div style="width: 100px; background: #e0e0e0; border-radius: 3px;">'
            '<div style="width: {}%; background: #4caf50; border-radius: 3px; height: 20px;"></div>'
            '</div><br>Moyenne: {:.1f}% | Terminés: {}/{}',
            avg_progress or 0, avg_progress or 0, completed, total
        )
    progress_stats.short_description = "Progression"
    
    def user_progress(self, obj):
        progressions = Progression.objects.filter(plan=obj).select_related('user')
        if not progressions:
            return "Aucun utilisateur"
        
        html = "<table style='width: 100%;'><tr><th>Utilisateur</th><th>Progression</th></tr>"
        for prog in progressions:
            html += f"<tr><td>{prog.user.username}</td><td>{prog.pourcentage}%</td></tr>"
        html += "</table>"
        return mark_safe(html)
    user_progress.short_description = "Progression par utilisateur"

class ModuleStepInline(admin.TabularInline):
    model = ModuleStep
    extra = 3
    fields = ('titre', 'ordre', 'completion_rate')
    readonly_fields = ('completion_rate',)
    
    def completion_rate(self, obj):
        if not obj.id:
            return "-"
        
        total = UserProfile.objects.filter(
            poste__plan_integration=obj.module.plan
        ).count()
        
        if total == 0:
            return "0%"
        
        completed = UserModuleStepCompletion.objects.filter(
            module_step=obj
        ).count()
        
        percentage = (completed / total) * 100
        return format_html(
            '<div style="width: 100px; background: #e0e0e0; border-radius: 3px;">'
            '<div style="width: {}%; background: #2196f3; border-radius: 3px; height: 15px;"></div>'
            '</div> {:.1f}%',
            percentage, percentage
        )
    completion_rate.short_description = "Taux de complétion"

class ModuleKnowledgeItemInline(admin.TabularInline):
    model = ModuleKnowledgeItem
    extra = 2
    fields = ('knowledge_item', 'ordre')
    autocomplete_fields = ('knowledge_item',)

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('titre', 'plan', 'ordre', 'duration', 'has_quiz', 'step_count', 'completion_rate')
    list_filter = ('plan', 'duree_jours', 'ordre')
    search_fields = ('titre', 'description')
    ordering = ('plan', 'ordre')
    
    inlines = [ModuleStepInline, ModuleKnowledgeItemInline]
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('titre', 'plan', 'ordre', 'duree_jours')
        }),
        ('Quiz', {
            'fields': ('quiz',)
        })
    )
    readonly_fields = ('step_count', 'completion_rate')
    
    def has_quiz(self, obj):
        if hasattr(obj, 'quiz') and obj.quiz:
            return format_html(
                '<a href="{}" class="button">✓ {} questions</a>',
                reverse('admin:app_connaissance_quiz_change', args=[obj.quiz.id]),
                obj.quiz.questions.count()
            )
        return "✗"
    has_quiz.short_description = "Quiz"
    has_quiz.allow_tags = True
    
    def step_count(self, obj):
        count = obj.steps.count()
        return f"{count} étape{'s' if count != 1 else ''}"
    step_count.short_description = "Étapes"
    
    def duration(self, obj):
        if obj.duree_jours:
            return f"{obj.duree_jours} jour{'s' if obj.duree_jours != 1 else ''}"
        return "-"
    duration.short_description = "Durée"
    
    def completion_rate(self, obj):
        # Calculer le taux de complétion moyen du module
        users = UserProfile.objects.filter(poste__plan_integration=obj.plan).count()
        if users == 0:
            return "0%"
        
        steps = obj.steps.all()
        if not steps:
            return "100%"
        
        total_completions = 0
        for step in steps:
            total_completions += UserModuleStepCompletion.objects.filter(
                module_step=step
            ).count()
        
        total_possible = users * len(steps)
        percentage = (total_completions / total_possible) * 100
        
        return format_html(
            '<div style="width: 100px; background: #e0e0e0; border-radius: 3px;">'
            '<div style="width: {}%; background: #4caf50; border-radius: 3px; height: 20px;"></div>'
            '</div> {:.1f}%',
            percentage, percentage
        )
    completion_rate.short_description = "Taux de complétion"

class QuizChoiceInline(admin.TabularInline):
    model = QuizChoice
    extra = 4
    fields = ('texte', 'is_correct')

class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 3
    fields = ('enonce', 'ordre')
    show_change_link = True

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('titre', 'module', 'question_count', 'success_rate', 'seuil_reussite_pct')
    list_filter = ('seuil_reussite_pct', 'module__plan')
    search_fields = ('titre', 'module__titre')
    ordering = ('module__plan', 'module__ordre')
    
    inlines = [QuizQuestionInline]
    
    def question_count(self, obj):
        count = obj.questions.count()
        return f"{count} question{'s' if count != 1 else ''}"
    question_count.short_description = "Questions"
    
    def success_rate(self, obj):
        attempts = UserQuizAttempt.objects.filter(quiz=obj)
        if not attempts:
            return "Aucune tentative"
        
        passed = attempts.filter(passed=True).count()
        total = attempts.count()
        percentage = (passed / total) * 100
        
        return format_html(
            '<div style="width: 100px; background: #e0e0e0; border-radius: 3px;">'
            '<div style="width: {}%; background: {};">'
            '</div><br>{}/{} ({:.1f}%)',
            percentage,
            '#4caf50' if percentage >= 70 else '#ff9800',
            passed, total, percentage
        )
    success_rate.short_description = "Taux de réussite"

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'user', 'department', 'poste', 'role', 'integration_progress', 'last_login')
    list_filter = ('department', 'role', 'is_active', 'created_at')
    search_fields = ('display_name', 'user__username', 'user__email')
    ordering = ('department', 'display_name')
    
    fieldsets = (
        ('Informations utilisateur', {
            'fields': ('user', 'display_name', 'role')
        }),
        ('Poste et département', {
            'fields': ('department', 'poste')
        }),
        ('Contrat et statut', {
            'fields': ('type_contrat', 'must_change_password', 'is_active')
        })
    )
    readonly_fields = ('integration_progress', 'last_login')
    
    def integration_progress(self, obj):
        if not obj.poste or not obj.poste.plan_integration:
            return "Aucun plan"
        
        progression = Progression.objects.filter(
            user=obj.user,
            plan=obj.poste.plan_integration
        ).first()
        
        if not progression:
            return "0%"
        
        return format_html(
            '<div style="width: 150px; background: #e0e0e0; border-radius: 3px;">'
            '<div style="width: {}%; background: #4caf50; border-radius: 3px; height: 20px;"></div>'
            '</div> {}%',
            progression.pourcentage, progression.pourcentage
        )
    integration_progress.short_description = "Progression"
    
    def last_login(self, obj):
        if obj.user.last_login:
            return obj.user.last_login.strftime('%d/%m/%Y %H:%M')
        return "Jamais"
    last_login.short_description = "Dernière connexion"

@admin.register(Progression)
class ProgressionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'pourcentage', 'last_updated', 'status')
    list_filter = ('pourcentage', 'last_updated')
    search_fields = ('user__username', 'plan__titre')
    ordering = ('-last_updated',)
    
    def status(self, obj):
        if obj.pourcentage >= 100:
            return format_html('<span style="color: green;">✓ Terminé</span>')
        elif obj.pourcentage >= 50:
            return format_html('<span style="color: orange;">⚡ En cours</span>')
        else:
            return format_html('<span style="color: red;">▶ Début</span>')
    status.short_description = "Statut"
    status.allow_tags = True

# Configuration de l'admin pour les autres modèles
@admin.register(KnowledgeItem)
class KnowledgeItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'kind', 'department', 'status', 'read_time', 'created_at')
    list_filter = ('kind', 'department', 'status', 'created_at')
    search_fields = ('title', 'content')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('title', 'description', 'kind', 'department')
        }),
        ('Contenu', {
            'fields': ('content', 'video_url', 'attachment')
        }),
        ('Métadonnées', {
            'fields': ('author', 'read_time_min', 'status')
        })
    )

@admin.register(KnowledgeKind)
class KnowledgeKindAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'item_count')
    search_fields = ('name',)
    ordering = ('name',)
    
    def item_count(self, obj):
        count = KnowledgeItem.objects.filter(kind=obj).count()
        return f"{count} article{'s' if count != 1 else ''}"
    item_count.short_description = "Articles"

# Personnalisation du titre de l'admin
admin.site.site_header = "Administration Plan d'Intégration"
admin.site.site_title = "Admin Integration"
admin.site.index_title = "Gestion du plan d'intégration"
