from __future__ import annotations

from typing import Any

import secrets
import string

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Avg, Count, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import DepartmentForm, OnboardingStepForm, UserCreateForm
from .frontend_auth import frontend_login_required, frontend_roles_required
from .models import Department, KnowledgeItem, KnowledgeKind, OnboardingStep, Poste, Tag, UserProfile


ROLES: dict[str, dict[str, str]] = {
    "admin": {"label": "Administrateur", "desc": "Gestion technique & organisationnelle"},
    "employee": {"label": "Employé", "desc": "Contribution & consultation"},
    "manager": {"label": "Manager", "desc": "Validation & suivi"},
    "new_employee": {"label": "Nouveau", "desc": "Parcours d’intégration guidé"},
}


def _parse_tags(raw: str) -> list[str]:
    parts = [p.strip() for p in (raw or "").split(",")]
    clean: list[str] = []
    for p in parts:
        if not p:
            continue
        if p.startswith("#"):
            p = p[1:].strip()
        if p and p.lower() not in {x.lower() for x in clean}:
            clean.append(p)
    return clean


def _estimate_read_time_min(content: str) -> int:
    words = len((content or "").split())
    # ~200 mots/minute, min 1
    return max(1, round(words / 200) or 1)


def index_redirect(request: HttpRequest) -> HttpResponse:
    """Première page : redirige vers login si non connecté, sinon dashboard ou changement mot de passe."""
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile and getattr(profile, "must_change_password", False):
            return redirect("password_change_required")
        return redirect("dashboard")
    return redirect("login")


def login_view(request: HttpRequest) -> HttpResponse:
    """Page de connexion : formulaire username/mot de passe, ou sélection rôle (démo)."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        from django.contrib.auth import authenticate, login

        # Connexion réelle si username + password fournis
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                profile = getattr(user, "profile", None)
                if profile and getattr(profile, "must_change_password", False):
                    return redirect("password_change_required")
                next_url = request.POST.get("next") or request.GET.get("next") or reverse("dashboard")
                return redirect(next_url)
            messages.error(request, "Identifiants incorrects.")
        else:
            # Mode démo : rôle en session
            role = (request.POST.get("role") or "employee").strip()
            display = {"employee": "Employé", "manager": "Manager", "admin": "Administrateur", "new_employee": "Nouveau"}.get(role, "Employé")
            request.session["frontend_demo_role"] = role
            request.session["frontend_demo_name"] = display
            return redirect("dashboard")
    return render(request, "auth/login.html", {})


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    request.session.flush()
    messages.info(request, "Tu es déconnecté.")
    return redirect("login")


def password_change_required(request: HttpRequest) -> HttpResponse:
    """Changement de mot de passe obligatoire (première connexion)."""
    if not request.user.is_authenticated:
        return redirect(settings.LOGIN_URL + "?next=" + request.path)
    profile = getattr(request.user, "profile", None)
    if not profile or not getattr(profile, "must_change_password", False):
        return redirect("dashboard")
    if request.method == "POST":
        from django.contrib.auth.forms import SetPasswordForm
        form = SetPasswordForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            profile.must_change_password = False
            profile.save(update_fields=["must_change_password"])
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, form.user)
            messages.success(request, "Votre mot de passe a été modifié. Vous pouvez accéder à la plateforme.")
            return redirect("dashboard")
    else:
        from django.contrib.auth.forms import SetPasswordForm
        form = SetPasswordForm(request.user)
    return render(request, "auth/password_change_required.html", {"form": form})


def forbidden(request: HttpRequest) -> HttpResponse:
    return render(request, "errors/403.html", status=403)


@frontend_login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    user = request.user
    profile = getattr(user, "profile", None)
    role = profile.role if profile else None

    knowledge_qs = KnowledgeItem.objects.select_related("department").prefetch_related("tags")
    pending_validation = list(knowledge_qs.filter(status=KnowledgeItem.Status.IN_REVIEW)[:8])

    agg = knowledge_qs.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(status=KnowledgeItem.Status.PUBLISHED)),
        pending=Count("id", filter=Q(status=KnowledgeItem.Status.IN_REVIEW)),
        avg_read=Avg("read_time_min"),
    )

    stats = {
        "total": int(agg["total"] or 0),
        "published": int(agg["published"] or 0),
        "pending": int(agg["pending"] or 0),
        "avg_read": round(float(agg["avg_read"] or 0)) or 0,
    }

    quick_actions: list[dict[str, Any]] = [
        {"title": "Explorer les connaissances", "desc": "Recherche, filtres & tags", "href": reverse("knowledge_list")},
        {"title": "Publier un contenu", "desc": "Procédure, document ou vidéo", "href": reverse("knowledge_create")},
        {"title": "Plan d’intégration", "desc": "Parcours guidé pour les nouveaux", "href": reverse("onboarding_home")},
    ]
    if role == "manager":
        quick_actions.insert(
            1,
            {"title": "Valider des contenus", "desc": "File de validation", "href": reverse("validation_queue")},
        )
    if role == "admin":
        quick_actions.append(
            {"title": "Administration", "desc": "Utilisateurs & départements", "href": reverse("departments")}
        )

    return render(
        request,
        "dashboard/index.html",
        {
            "stats": stats,
            "knowledge": list(knowledge_qs[:3]),
            "pending_validation": pending_validation,
            "quick_actions": quick_actions,
        },
    )


@frontend_login_required
def knowledge_list(request: HttpRequest) -> HttpResponse:
    query = (request.GET.get("q") or "").strip()
    kind = (request.GET.get("kind") or "").strip()
    department = (request.GET.get("department") or "").strip()

    # La liste publique ne montre que les contenus publiés
    items_qs = KnowledgeItem.objects.select_related("department").prefetch_related("tags").filter(
        status=KnowledgeItem.Status.PUBLISHED
    )
    if query:
        items_qs = items_qs.filter(Q(title__icontains=query) | Q(content__icontains=query) | Q(tags__name__icontains=query)).distinct()
    if kind:
        items_qs = items_qs.filter(kind__id=kind)
    if department:
        items_qs = items_qs.filter(department__id=department)

    kinds = KnowledgeKind.objects.all()
    departments = Department.objects.all()

    return render(
        request,
        "knowledge/list.html",
        {
            "items": list(items_qs),
            "q": query,
            "kind": kind,
            "department": department,
            "kinds": kinds,
            "departments": departments,
        },
    )


@frontend_login_required
def knowledge_detail(request: HttpRequest, knowledge_id: int) -> HttpResponse:
    try:
        item = KnowledgeItem.objects.select_related("department").prefetch_related("tags").get(pk=knowledge_id)
    except KnowledgeItem.DoesNotExist:
        messages.error(request, "Contenu introuvable.")
        return redirect("knowledge_list")

    return render(request, "knowledge/detail.html", {"item": item})


@frontend_login_required
def knowledge_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        kind_id = (request.POST.get("kind") or "").strip()
        department_id = (request.POST.get("department") or "").strip()
        content = (request.POST.get("content") or "").strip()
        video_url = (request.POST.get("video_url") or "").strip()
        author_name = (request.POST.get("author") or "").strip()
        status_raw = (request.POST.get("status") or "").strip() or KnowledgeItem.Status.DRAFT
        tags_csv = request.POST.get("tags") or ""
        numero_version = (request.POST.get("numero_version") or "1.0").strip() or "1.0"

        if not title:
            messages.error(request, "Le titre est requis.")
            return redirect("knowledge_create")

        try:
            dept = Department.objects.get(pk=department_id)
        except Department.DoesNotExist:
            messages.error(request, "Département invalide.")
            return redirect("knowledge_create")

        try:
            kind_obj = KnowledgeKind.objects.get(pk=kind_id)
        except (KnowledgeKind.DoesNotExist, ValueError):
            messages.error(request, "Type invalide.")
            return redirect("knowledge_create")

        if not author_name:
            # Par défaut on utilise le nom du profil ou de l'utilisateur connecté
            user = request.user
            profile = getattr(user, "profile", None)
            author_name = (
                profile.display_name
                if profile
                else (user.get_full_name() or user.get_username())
            )

        read_time = _estimate_read_time_min(content)

        # Seulement deux statuts possibles à la création : brouillon ou en validation
        if status_raw not in {KnowledgeItem.Status.DRAFT, KnowledgeItem.Status.IN_REVIEW}:
            status_raw = KnowledgeItem.Status.DRAFT

        item = KnowledgeItem.objects.create(
            title=title,
            kind=kind_obj,
            department=dept,
            author=author_name,
            content=content,
            video_url=video_url,
            status=status_raw,
            read_time_min=read_time,
            numero_version=numero_version,
        )

        tag_names = _parse_tags(tags_csv)
        if tag_names:
            tags = [Tag.objects.get_or_create(name=n)[0] for n in tag_names]
            item.tags.add(*tags)

        if request.FILES.get("file"):
            item.attachment = request.FILES["file"]
            item.save(update_fields=["attachment"])

        if item.status == KnowledgeItem.Status.IN_REVIEW:
            messages.success(request, "Contenu créé et envoyé en validation.")
        else:
            messages.success(request, "Brouillon créé. Tu pourras l’envoyer en validation plus tard.")
        return redirect("knowledge_detail", knowledge_id=item.id)

    return render(
        request,
        "knowledge/create.html",
        {
            "kinds": KnowledgeKind.objects.all(),
            "departments": Department.objects.all(),
        },
    )


@frontend_roles_required("manager")
def validation_queue(request: HttpRequest) -> HttpResponse:
    items = (
        KnowledgeItem.objects.select_related("department")
        .prefetch_related("tags")
        .filter(status=KnowledgeItem.Status.IN_REVIEW)
        .order_by("-updated_at")[:50]
    )
    return render(request, "validation/queue.html", {"items": list(items)})


@frontend_roles_required("manager")
def validation_approve(request: HttpRequest, knowledge_id: int) -> HttpResponse:
    if request.method != "POST":
        return redirect("validation_queue")

    try:
        item = KnowledgeItem.objects.get(pk=knowledge_id)
    except KnowledgeItem.DoesNotExist:
        messages.error(request, "Contenu introuvable.")
        return redirect("validation_queue")

    item.status = KnowledgeItem.Status.PUBLISHED
    item.published_at = timezone.now()
    item.save(update_fields=["status", "published_at", "updated_at"])
    messages.success(request, "Contenu publié.")
    return redirect("validation_queue")


@frontend_roles_required("manager")
def validation_reject(request: HttpRequest, knowledge_id: int) -> HttpResponse:
    if request.method != "POST":
        return redirect("validation_queue")

    try:
        item = KnowledgeItem.objects.get(pk=knowledge_id)
    except KnowledgeItem.DoesNotExist:
        messages.error(request, "Contenu introuvable.")
        return redirect("validation_queue")

    comment = (request.POST.get("rejection_comment") or "").strip()
    item.status = KnowledgeItem.Status.REJECTED
    item.rejection_comment = comment
    item.save(update_fields=["status", "rejection_comment", "updated_at"])
    messages.info(request, "Contenu rejeté." + (" Commentaire enregistré." if comment else ""))
    return redirect("validation_queue")


def _send_credentials_email(user: User, raw_password: str) -> None:
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
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, to, fail_silently=False)
    except Exception:
        pass


@frontend_roles_required("admin")
def user_create(request: HttpRequest) -> HttpResponse:
    """Création d'un utilisateur par l'admin (formulaire in-app)."""
    postes = list(Poste.objects.select_related("department").order_by("department__name", "intitule"))
    if request.method == "POST":
        form = UserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            # Mot de passe aléatoire sécurisé (16 car. alphanum.) — valide pour les validateurs Django
            chars = string.ascii_letters + string.digits
            raw_password = "".join(secrets.choice(chars) for _ in range(16))
            user = User.objects.create_user(
                username=form.cleaned_data["username"].strip(),
                email=form.cleaned_data["email"].strip(),
                password=raw_password,
                first_name=form.cleaned_data["first_name"].strip(),
                last_name=form.cleaned_data["last_name"].strip(),
            )
            display_name = form.cleaned_data.get("display_name") or None
            if not display_name:
                display_name = (user.get_full_name() or user.username or "").strip() or user.username
            if UserProfile.objects.filter(display_name=display_name).exists():
                display_name = f"{display_name} ({user.username})"
            profile = UserProfile.objects.create(
                user=user,
                display_name=display_name,
                role=form.cleaned_data["role"],
                department=form.cleaned_data["department"],
                poste=form.cleaned_data["poste"],
                type_contrat=form.cleaned_data["type_contrat"] or "",
                date_embauche=form.cleaned_data.get("date_embauche"),
                must_change_password=True,
                is_active=True,
            )
            if form.cleaned_data.get("photo"):
                profile.photo = form.cleaned_data["photo"]
                profile.save(update_fields=["photo"])
            _send_credentials_email(user, raw_password)
            messages.success(request, f"Utilisateur « {display_name} » créé. Identifiants envoyés par email.")
            return redirect("users_admin")
    else:
        form = UserCreateForm()
    return render(
        request,
        "admin/user_create.html",
        {"form": form, "roles": ROLES, "postes": postes},
    )


@frontend_roles_required("admin")
def departments(request: HttpRequest) -> HttpResponse:
    deps = (
        Department.objects.annotate(members=Count("profiles"), knowledge=Count("knowledge_items"))
        .order_by("name")
        .all()
    )
    return render(request, "admin/departments.html", {"departments": list(deps)})


@frontend_roles_required("admin")
def department_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Département créé.")
            return redirect("departments")
    else:
        form = DepartmentForm()
    return render(request, "admin/department_form.html", {"form": form, "title": "Créer un département"})


@frontend_roles_required("admin")
def department_edit(request: HttpRequest, pk: int) -> HttpResponse:
    dept = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=dept)
        if form.is_valid():
            form.save()
            messages.success(request, "Département mis à jour.")
            return redirect("departments")
    else:
        form = DepartmentForm(instance=dept)
    return render(request, "admin/department_form.html", {"form": form, "title": "Modifier le département", "department": dept})


@frontend_roles_required("admin")
def users_admin(request: HttpRequest) -> HttpResponse:
    users = UserProfile.objects.select_related("department", "poste").all()
    return render(request, "admin/users.html", {"users": list(users), "roles": ROLES})


@frontend_roles_required("admin")
def onboarding_steps_admin(request: HttpRequest) -> HttpResponse:
    """Liste des étapes d'intégration (admin)."""
    steps = OnboardingStep.objects.all().order_by("order", "id")
    return render(request, "admin/onboarding_steps.html", {"steps": list(steps)})


@frontend_roles_required("admin")
def onboarding_step_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = OnboardingStepForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Étape créée.")
            return redirect("onboarding_steps_admin")
    else:
        form = OnboardingStepForm(initial={"order": OnboardingStep.objects.count() + 1})
    return render(request, "admin/onboarding_step_form.html", {"form": form, "title": "Ajouter une étape"})


@frontend_roles_required("admin")
def onboarding_step_edit(request: HttpRequest, pk: int) -> HttpResponse:
    step = get_object_or_404(OnboardingStep, pk=pk)
    if request.method == "POST":
        form = OnboardingStepForm(request.POST, instance=step)
        if form.is_valid():
            form.save()
            messages.success(request, "Étape mise à jour.")
            return redirect("onboarding_steps_admin")
    else:
        form = OnboardingStepForm(instance=step)
    return render(request, "admin/onboarding_step_form.html", {"form": form, "title": "Modifier l'étape", "step": step})


@frontend_login_required
def onboarding_home(request: HttpRequest) -> HttpResponse:
    steps = OnboardingStep.objects.all()
    return render(request, "onboarding/home.html", {"steps": list(steps)})


@frontend_login_required
def trainings(request: HttpRequest) -> HttpResponse:

    # La vue training/list.html et la logique TrainingModule ont été supprimées
    return render(request, "training/list.html", {"trainings": []})



# La vue tests_home et toute la logique quiz ont été supprimées


@frontend_login_required
def profile(request: HttpRequest) -> HttpResponse:
    user = request.user

    # If the real user is authenticated, look up their profile by relation.
    if getattr(user, "is_authenticated", False):
        profile_obj = UserProfile.objects.filter(user=user).select_related("department").first()
        role = profile_obj.role if profile_obj else None

    else:
        # Anonymous frontend usage: try to derive a role from the session
        # (set by the simple frontend login flow), and map to a lightweight
        # UserProfile by display_name if available. If not found, leave
        # profile_obj as None so the template shows empty department.
        role = (request.session.get("frontend_role") or None)
        profile_obj = None
        if role:
            # Prefer a UserProfile created for frontend sessions named 'frontend:<role>'
            display_name = f"frontend:{role}"
            profile_obj = (
                UserProfile.objects.filter(display_name=display_name).select_related("department").first()
            )

    return render(request, "profile/index.html", {"roles": ROLES, "role": role, "profile": profile_obj})
