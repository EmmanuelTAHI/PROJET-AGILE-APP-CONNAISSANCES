"""API générique pour création à la volée de modèles de référence (admin uniquement)."""
from __future__ import annotations

import json
from typing import Any

from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.template.defaultfilters import slugify
from django.views.decorators.http import require_http_methods

from .models import (
    Department,
    Entreprise,
    KnowledgeKind,
    PlanIntegration,
    Poste,
    Tag,
)


def _user_has_admin_rights(request: HttpRequest) -> bool:
    """Vérifie si l'utilisateur a les droits admin (staff ou profil role=admin)."""
    if not request.user.is_authenticated:
        return False
    if request.user.is_staff:
        return True
    profile = getattr(request.user, "profile", None)
    return profile is not None and getattr(profile, "role", None) == "admin"


# Registry des modèles autorisés pour création à la volée
# Chaque entrée: (Model, champ_principal, champs_extra_optionnels, check_doublon)
REFERENCE_MODELS: dict[str, dict[str, Any]] = {
    "department": {
        "model": Department,
        "name_field": "name",
        "extra_fields": {"description": ""},
        "unique_check": lambda m, name, **kw: m.objects.filter(name__iexact=name.strip()).exists(),
    },
    "entreprise": {
        "model": Entreprise,
        "name_field": "name",
        "extra_fields": {},
        "unique_check": lambda m, name, **kw: m.objects.filter(name__iexact=name.strip()).exists(),
    },
    "knowledgekind": {
        "model": KnowledgeKind,
        "name_field": "name",
        "extra_fields": {},
        "unique_check": lambda m, name, **kw: m.objects.filter(name__iexact=name.strip()).exists(),
    },
    "tag": {
        "model": Tag,
        "name_field": "name",
        "extra_fields": {},
        "unique_check": lambda m, name, **kw: m.objects.filter(name__iexact=name.strip()).exists(),
    },
    "planintegration": {
        "model": PlanIntegration,
        "name_field": "titre",
        "extra_fields": {"description": "", "duree_estimee_jours": 0},
        "unique_check": lambda m, name, **kw: m.objects.filter(titre__iexact=name.strip()).exists(),
    },
    "poste": {
        "model": Poste,
        "name_field": "intitule",
        "extra_fields": {"description": ""},
        "requires_parent": "department",
        "parent_fk": "department",
        "unique_check": lambda m, name, **kw: m.objects.filter(
            department_id=kw.get("department_id"),
            intitule__iexact=name.strip(),
        ).exists(),
    },
}


@require_http_methods(["POST"])
def reference_create_api(request: HttpRequest) -> JsonResponse:
    """
    Crée une entrée de modèle de référence via AJAX.
    Réservé aux utilisateurs admin. Validation, gestion des doublons, transaction atomique.
    """
    if not _user_has_admin_rights(request):
        return JsonResponse({"success": False, "error": "Accès refusé. Droits administrateur requis."}, status=403)

    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Requête JSON invalide."}, status=400)

    model_key = (data.get("model") or "").strip().lower()
    if not model_key or model_key not in REFERENCE_MODELS:
        return JsonResponse(
            {"success": False, "error": f"Modèle inconnu ou non autorisé: {model_key}"},
            status=400,
        )

    reg = REFERENCE_MODELS[model_key]
    model_cls = reg["model"]
    name_field = reg["name_field"]
    name_value = (data.get("name") or data.get(name_field) or "").strip()

    if not name_value:
        return JsonResponse({"success": False, "error": "Le nom est requis."}, status=400)

    parent_id = data.get("parent_id") or data.get("department_id")
    if reg.get("requires_parent") and not parent_id:
        return JsonResponse(
            {"success": False, "error": "Une sélection parente est requise (ex: département)."},
            status=400,
        )

    # Vérification des doublons
    check_fn = reg["unique_check"]
    kwargs = {}
    if parent_id:
        try:
            kwargs["department_id"] = int(parent_id)
        except (TypeError, ValueError):
            return JsonResponse({"success": False, "error": "Parent invalide."}, status=400)

    if check_fn(model_cls, name_value, **kwargs):
        return JsonResponse(
            {"success": False, "error": "Une entrée avec ce nom existe déjà."},
            status=400,
        )

    try:
        with transaction.atomic():
            extra = dict(reg.get("extra_fields", {}))
            if reg.get("parent_fk") and parent_id:
                extra[f"{reg['parent_fk']}_id"] = int(parent_id)

            instance = model_cls(**{name_field: name_value}, **extra)
            # Slug pour les modèles qui en ont
            if hasattr(instance, "slug") and not getattr(instance, "slug", ""):
                instance.slug = slugify(name_value)
            instance.save()

            # Réponse adaptée au modèle
            display = getattr(instance, name_field, str(instance))
            if model_key == "poste" and hasattr(instance, "department") and instance.department:
                display = f"{display} ({instance.department.name})"

            return JsonResponse({
                "success": True,
                "id": instance.pk,
                "name": display,
                "label": display,
            })
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )
