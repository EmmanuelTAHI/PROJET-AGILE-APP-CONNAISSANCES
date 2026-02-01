"""Formulaires in-app (création utilisateur, département, étapes d'intégration)."""
from __future__ import annotations

from django import forms
from django.contrib.auth.models import User

from .models import Department, Entreprise, OnboardingStep, Poste, UserProfile


class UserCreateForm(forms.Form):
    """Création d'un utilisateur par l'admin (avec profil et photo)."""
    username = forms.CharField(max_length=150, label="Identifiant (username)")
    first_name = forms.CharField(max_length=150, label="Prénom")
    last_name = forms.CharField(max_length=150, label="Nom")
    email = forms.EmailField(label="Email")
    department = forms.ModelChoiceField(
        queryset=Department.objects.all().order_by("name"),
        label="Département",
        required=True,
    )
    poste = forms.ModelChoiceField(
        queryset=Poste.objects.select_related("department").order_by("department__name", "intitule"),
        label="Poste",
        required=True,
    )
    role = forms.ChoiceField(
        choices=[("", "———")] + list(UserProfile.Role.choices),
        label="Rôle",
        required=True,
    )
    type_contrat = forms.ChoiceField(
        choices=[("", "———")] + list(UserProfile.TypeContrat.choices),
        label="Type de contrat",
        required=True,
    )
    date_embauche = forms.DateField(
        label="Date d'embauche",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    display_name = forms.CharField(
        max_length=120,
        label="Nom affiché",
        required=False,
        help_text="Laisser vide pour utiliser Prénom + Nom.",
    )
    photo = forms.ImageField(label="Photo (avatar)", required=False)

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Cet identifiant est déjà utilisé.")
        return username

    def clean_display_name(self):
        name = (self.cleaned_data.get("display_name") or "").strip()
        return name or None


class DepartmentForm(forms.ModelForm):
    """Création / édition d'un département."""
    class Meta:
        model = Department
        fields = ("name", "description", "manager", "entreprise")
        labels = {"name": "Nom", "description": "Description", "manager": "Responsable (manager)", "entreprise": "Entreprise"}
        widgets = {
            "name": forms.TextInput(attrs={"class": "input-field", "placeholder": "Ex: IT, RH"}),
            "description": forms.Textarea(attrs={"class": "input-field", "rows": 2}),
        }


class OnboardingStepForm(forms.ModelForm):
    """Création / édition d'une étape d'intégration."""
    class Meta:
        model = OnboardingStep
        fields = ("title", "description", "order", "is_required")
        labels = {"title": "Titre", "description": "Description", "order": "Ordre", "is_required": "Obligatoire"}
        widgets = {
            "title": forms.TextInput(attrs={"class": "input-field"}),
            "description": forms.Textarea(attrs={"class": "input-field", "rows": 2}),
            "order": forms.NumberInput(attrs={"class": "input-field", "min": 1}),
        }
