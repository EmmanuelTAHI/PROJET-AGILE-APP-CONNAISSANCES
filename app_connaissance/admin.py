from __future__ import annotations

import secrets
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils.text import capfirst

from .models import (
    Department,
    Entreprise,
    KnowledgeKind,
    KnowledgeItem,
    Module,
    ModuleStep,
    OnboardingStep,
    PlanIntegration,
    Poste,
    Quiz,
    QuizChoice,
    QuizQuestion,
    Tag,
    UserProfile,
    UserQuizAttempt,
)


# ---------------------------------------------------------------------------
# Formulaire de création d'utilisateur : mot de passe optionnel (généré + envoyé par email)
# ---------------------------------------------------------------------------
class UserCreationFormWithOptionalPassword(BaseUserCreationForm):
    """Mot de passe optionnel : si vide, un mot de passe est généré et envoyé par email."""

    class Meta(BaseUserCreationForm.Meta):
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].required = False
        self.fields["password2"].required = False
        self.fields["password1"].help_text = "Laisser vide pour générer un mot de passe et l'envoyer par email à l'utilisateur (première connexion = changement obligatoire)."
        self.fields["password2"].help_text = ""

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 or password2:
            if password1 != password2:
                from django.core.exceptions import ValidationError
                raise ValidationError("Les deux mots de passe ne correspondent pas.")
            return password2
        return ""

    def save(self, commit=True):
        # Appel direct à ModelForm pour ne pas appeler UserCreationForm.save (qui utilise password1)
        from django.forms import ModelForm
        user = ModelForm.save(self, commit=False)
        password = self.cleaned_data.get("password1")
        if not password:
            password = secrets.token_urlsafe(12)
            user._temporary_password = password
        user.set_password(password)
        if commit:
            user.save()
        return user


# ---------------------------------------------------------------------------
# Inline : profil (département, poste, rôle, type contrat, date embauche)
# ---------------------------------------------------------------------------
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = capfirst(UserProfile._meta.verbose_name)
    verbose_name_plural = capfirst(UserProfile._meta.verbose_name_plural)
    fields = (
        "display_name",
        "role",
        "department",
        "poste",
        "type_contrat",
        "date_embauche",
        "must_change_password",
        "is_active",
    )
    filter_horizontal = ()
    autocomplete_fields = ("department", "poste")



# ---------------------------------------------------------------------------
# Admin User personnalisé : création avec envoi email identifiants
# ---------------------------------------------------------------------------
try:
    admin.site.unregister(User)
except Exception:
    pass


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    add_form = UserCreationFormWithOptionalPassword
    add_fieldsets = (
        (None, {"fields": ("username",)}),
        ("Identité", {"fields": ("first_name", "last_name", "email")}),
        (
            "Mot de passe",
            {
                "fields": ("password1", "password2"),
                "description": "Laisser vide pour générer un mot de passe et l'envoyer par email.",
            },
        ),
    )
    inlines = (UserProfileInline,)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Rien à faire ici : le mot de passe est déjà géré par le formulaire
        # L'envoi d'email et must_change_password seront faits dans save_related

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        user = form.instance
        raw_password = getattr(user, "_temporary_password", None)
        if not change and raw_password:
            profile = getattr(user, "profile", None)
            if not profile:
                display_name = (user.get_full_name() or user.username or "").strip() or user.username
                if UserProfile.objects.filter(display_name=display_name).exists():
                    display_name = f"{display_name} ({user.username})"
                profile = UserProfile.objects.create(
                    user=user,
                    display_name=display_name,
                    role=UserProfile.Role.EMPLOYEE,
                    must_change_password=True,
                )
            else:
                profile.must_change_password = True
                if not (profile.display_name or "").strip():
                    profile.display_name = (user.get_full_name() or user.username or "").strip() or user.username
                    if UserProfile.objects.filter(display_name=profile.display_name).exclude(pk=profile.pk).exists():
                        profile.display_name = f"{profile.display_name} ({user.username})"
                profile.save()
            self._send_credentials_email(user, raw_password)
            if hasattr(user, "_temporary_password"):
                del user._temporary_password

    def _send_credentials_email(self, user, raw_password: str):
        to = [user.email] if user.email else []
        if not to:
            to = [f"{user.username}@example.com"]
        subject = "[Savoirs] Vos identifiants de connexion"
        body = (
            f"Bonjour {user.get_full_name() or user.username},\n\n"
            "Votre compte sur la plateforme de gestion des connaissances a été créé.\n\n"
            f"Identifiant : {user.username}\n"
            f"Mot de passe temporaire : {raw_password}\n\n"
            "Lors de votre première connexion, vous devrez modifier ce mot de passe.\n\n"
            "Cordialement,\nL'équipe"
        )
        try:
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                to,
                fail_silently=False,
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Autres modèles
# ---------------------------------------------------------------------------
@admin.register(Entreprise)
class EntrepriseAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "manager", "entreprise")
    list_filter = ("entreprise",)
    search_fields = ("name", "slug")
    autocomplete_fields = ("manager", "entreprise")


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 0
    ordering = ("ordre",)


@admin.register(PlanIntegration)
class PlanIntegrationAdmin(admin.ModelAdmin):
    list_display = ("titre", "duree_estimee_jours")
    search_fields = ("titre", "description")
    inlines = (ModuleInline,)


class ModuleStepInline(admin.TabularInline):
    model = ModuleStep
    extra = 1
    ordering = ("ordre",)


class QuizInline(admin.StackedInline):
    model = Quiz
    extra = 0
    max_num = 1
    fk_name = "module"


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("titre", "plan", "ordre", "duree_jours")
    list_filter = ("plan",)
    search_fields = ("titre",)
    inlines = (ModuleStepInline, QuizInline,)


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 0
    ordering = ("ordre",)


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("titre", "module", "seuil_reussite_pct")
    list_filter = ("module__plan",)
    search_fields = ("titre",)
    inlines = (QuizQuestionInline,)


class QuizChoiceInline(admin.TabularInline):
    model = QuizChoice
    extra = 1
    ordering = ("question", "id")


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("enonce", "quiz", "ordre")
    list_filter = ("quiz",)
    search_fields = ("enonce",)
    inlines = (QuizChoiceInline,)


@admin.register(UserQuizAttempt)
class UserQuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "quiz", "score_pct", "passed", "completed_at")
    list_filter = ("passed", "quiz")
    search_fields = ("user__username",)
    readonly_fields = ("completed_at",)


@admin.register(Poste)
class PosteAdmin(admin.ModelAdmin):
    list_display = ("intitule", "department", "plan_integration")
    list_filter = ("department",)
    search_fields = ("intitule", "description")
    autocomplete_fields = ("department", "plan_integration")
    filter_horizontal = ("competences",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


@admin.register(KnowledgeKind)
class KnowledgeKindAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


@admin.register(KnowledgeItem)
class KnowledgeItemAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "department", "status", "author", "numero_version", "updated_at")
    list_filter = ("kind", "status", "department")
    search_fields = ("title", "author", "content")
    autocomplete_fields = ("department", "tags")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "role", "department", "poste", "type_contrat", "must_change_password", "is_active")
    list_filter = ("role", "is_active", "department", "type_contrat")
    search_fields = ("display_name", "user__username", "user__email")
    autocomplete_fields = ("department", "poste", "user")


@admin.register(OnboardingStep)
class OnboardingStepAdmin(admin.ModelAdmin):
    list_display = ("order", "title", "is_required")
    list_filter = ("is_required",)
    search_fields = ("title", "description")
