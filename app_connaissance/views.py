from __future__ import annotations

from typing import Any

import secrets
import string

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordResetConfirmView as DjangoPasswordResetConfirmView
from django.core.mail import EmailMultiAlternatives
from django.db.models import Avg, Count, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone

from .forms import DepartmentForm, OnboardingStepForm, ProfileEditForm, UserCreateForm
from .frontend_auth import frontend_login_required, frontend_roles_required
from .models import (
    Department,
    KnowledgeItem,
    KnowledgeKind,
    KnowledgeVersion,
    Module,
    ModuleStep,
    OnboardingStep,
    PlanIntegration,
    Poste,
    Progression,
    Quiz,
    QuizChoice,
    QuizQuestion,
    Tag,
    UserModuleStepCompletion,
    UserQuizAttempt,
    UserProfile,
)


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


def _filter_knowledge_for_user(request: HttpRequest, qs):
    """Retourne le queryset restreint selon le rôle et le département de l'utilisateur.
    - Les 'admin' et 'manager' voient tout.
    - Les autres utilisateurs ne voient que les contenus attachés à leur département.
    """
    profile = getattr(request.user, "profile", None)
    # Pas de profil -> pas de contenu
    if not profile:
        return qs.none()
    # Admins et managers voient tout
    if profile.role in ("admin", "manager"):
        return qs
    # Les employés voient uniquement les contenus de leur département
    if getattr(profile, "department_id", None):
        return qs.filter(department_id=profile.department_id)
    return qs.none()


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
                next_url = request.POST.get("next") or request.GET.get("next")
                if next_url:
                    return redirect(next_url)
                # Proposer le plan d'intégration si l'utilisateur a un poste avec plan
                if profile and getattr(profile, "poste_id", None):
                    plan = getattr(profile.poste, "plan_integration_id", None)
                    if plan:
                        return redirect("plan_integration_personnel")
                return redirect("dashboard")
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


# Vue de confirmation de réinitialisation du mot de passe : après succès, désactive must_change_password
class PasswordResetConfirmView(DjangoPasswordResetConfirmView):
    template_name = "auth/password_reset_confirm.html"
    success_url = "/password-reset/complete/"

    def form_valid(self, form):
        user = form.save()
        profile = getattr(user, "profile", None)
        if profile and getattr(profile, "must_change_password", False):
            profile.must_change_password = False
            profile.save(update_fields=["must_change_password"])
        return super().form_valid(form)


@frontend_login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    user = request.user
    profile = getattr(user, "profile", None)
    role = profile.role if profile else None

    knowledge_qs = KnowledgeItem.objects.select_related("department").prefetch_related("tags")
    # Restreindre la portée selon le rôle / département de l'utilisateur
    knowledge_qs = _filter_knowledge_for_user(request, knowledge_qs)
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

    plan_has_link = bool(profile and getattr(profile, "poste_id", None) and getattr(profile.poste, "plan_integration_id", None))
    plan_href = reverse("plan_integration_personnel") if plan_has_link else reverse("onboarding_home")
    plan_title = "Mon plan d'intégration" if plan_has_link else "Plan d'intégration"
    plan_desc = "Quiz et suivi de progression" if plan_has_link else "Parcours guidé pour les nouveaux"
    quick_actions: list[dict[str, Any]] = [
        {"title": "Explorer les connaissances", "desc": "Recherche, filtres & tags", "href": reverse("knowledge_list")},
        {"title": "Publier un contenu", "desc": "Procédure, document ou vidéo", "href": reverse("knowledge_create")},
        {"title": "Plan d’intégration", "desc": "Parcours guidé pour les nouveaux", "href": plan_href},
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
    items_qs = (
        KnowledgeItem.objects.select_related("department")
        .prefetch_related("tags", "versions")
        .annotate(version_count=Count("versions"))
        .filter(status=KnowledgeItem.Status.PUBLISHED)
    )
    if query:
        items_qs = items_qs.filter(Q(title__icontains=query) | Q(content__icontains=query) | Q(tags__name__icontains=query)).distinct()
    if kind:
        items_qs = items_qs.filter(kind__id=kind)
    if department:
        items_qs = items_qs.filter(department__id=department)

    # Appliquer la restriction par département selon l'utilisateur connecté
    items_qs = _filter_knowledge_for_user(request, items_qs)

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


def _can_view_knowledge(request: HttpRequest, item: KnowledgeItem) -> bool:
    """Vérifie si l'utilisateur peut consulter cette connaissance.

    - Pour les contenus publiés, seuls les admins/managers ET les employés du même département y ont accès.
    - Pour les contenus non publiés, l'auteur, les managers et admins peuvent y accéder.
    """
    # Cas : publié -> restreindre par département sauf pour admin/manager
    if item.status == KnowledgeItem.Status.PUBLISHED:
        profile = getattr(request.user, "profile", None)
        if not profile:
            return False
        if profile.role in ("admin", "manager"):
            return True
        if profile.department_id and item.department_id == profile.department_id:
            return True
        return False

    # Cas : non publié -> autorisation habituelle
    profile = getattr(request.user, "profile", None)
    if not profile:
        return False
    if profile.role in ("admin", "manager"):
        return True
    if item.author_user_id and item.author_user_id == request.user.id:
        return True
    return False


@frontend_login_required
def knowledge_detail(request: HttpRequest, knowledge_id: int) -> HttpResponse:
    item = get_object_or_404(
        KnowledgeItem.objects.select_related("department", "author_user").prefetch_related(
            "tags", "competences", "versions"
        ),
        pk=knowledge_id,
    )
    if not _can_view_knowledge(request, item):
        messages.error(request, "Vous n'avez pas accès à ce contenu.")
        return redirect("knowledge_list")

    version_id = request.GET.get("version")
    versions = list(item.versions.order_by("-date_creation"))
    selected_version = None
    if version_id:
        try:
            selected_version = next(v for v in versions if str(v.id) == str(version_id))
        except StopIteration:
            pass
    if not selected_version:
        selected_version = item.get_current_version()
    if not selected_version:
        # Aucune version en base : afficher le contenu de l'item (rétrocompat)
        display_content = item.content
        display_date = item.updated_at
        display_numero = item.numero_version
        display_author = item.get_display_author()
    else:
        display_content = selected_version.content
        display_date = selected_version.date_creation
        display_numero = selected_version.numero_version
        display_author = selected_version.author_name or item.get_display_author()

    return render(
        request,
        "knowledge/detail.html",
        {
            "item": item,
            "versions": versions,
            "selected_version": selected_version,
            "display_content": display_content,
            "display_date": display_date,
            "display_numero": display_numero,
            "display_author": display_author,
        },
    )


@frontend_login_required
def knowledge_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        description = (request.POST.get("description") or "").strip()[:500]
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

        author_user = request.user if request.user.is_authenticated else None
        item = KnowledgeItem.objects.create(
            title=title,
            description=description,
            kind=kind_obj,
            department=dept,
            author=author_name,
            author_user=author_user,
            content=content,
            video_url=video_url,
            status=status_raw,
            read_time_min=read_time,
            numero_version=numero_version,
        )

        KnowledgeVersion.objects.create(
            knowledge_item=item,
            numero_version=numero_version,
            content=content,
            author_name=author_name,
            est_actuelle=True,
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


def _can_edit_knowledge(request: HttpRequest, item: KnowledgeItem) -> bool:
    """Vérifie si l'utilisateur peut modifier cette connaissance."""
    profile = getattr(request.user, "profile", None)
    if not profile:
        return False
    if profile.role in ("admin", "manager"):
        return True
    if item.author_user_id and item.author_user_id == request.user.id:
        return True
    return False


@frontend_login_required
def knowledge_edit(request: HttpRequest, knowledge_id: int) -> HttpResponse:
    item = get_object_or_404(
        KnowledgeItem.objects.select_related("department", "kind").prefetch_related(
            "tags", "competences", "versions"
        ),
        pk=knowledge_id,
    )
    if not _can_edit_knowledge(request, item):
        messages.error(request, "Vous n'avez pas le droit de modifier ce contenu.")
        return redirect("knowledge_detail", knowledge_id=item.id)

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        description = (request.POST.get("description") or "").strip()[:500]
        content = (request.POST.get("content") or "").strip()
        numero_version = (request.POST.get("numero_version") or "").strip()
        note_modification = (request.POST.get("note_modification") or "").strip()[:500]
        if not title:
            messages.error(request, "Le titre est requis.")
            return redirect("knowledge_edit", knowledge_id=item.id)
        if not numero_version:
            current = item.get_current_version()
            numero_version = current.numero_version if current else item.numero_version

        item.versions.update(est_actuelle=False)
        KnowledgeVersion.objects.create(
            knowledge_item=item,
            numero_version=numero_version,
            content=content,
            author_name=item.get_display_author(),
            est_actuelle=True,
            note_modification=note_modification,
        )
        item.title = title
        item.description = description
        item.content = content
        item.numero_version = numero_version
        item.read_time_min = _estimate_read_time_min(content)
        item.save(update_fields=["title", "description", "content", "numero_version", "read_time_min", "updated_at"])
        messages.success(request, "Nouvelle version enregistrée.")
        return redirect("knowledge_detail", knowledge_id=item.id)

    current = item.get_current_version()
    return render(
        request,
        "knowledge/edit.html",
        {
            "item": item,
            "current_version": current,
        },
    )


@frontend_login_required
def knowledge_duplicate(request: HttpRequest, knowledge_id: int) -> HttpResponse:
    source = get_object_or_404(
        KnowledgeItem.objects.select_related("department", "kind").prefetch_related("tags", "competences"),
        pk=knowledge_id,
    )
    if source.status != KnowledgeItem.Status.PUBLISHED and not _can_edit_knowledge(request, source):
        messages.error(request, "Vous n'avez pas le droit de dupliquer ce contenu.")
        return redirect("knowledge_list")

    profile = getattr(request.user, "profile", None)
    author_name = (
        profile.display_name
        if profile
        else (request.user.get_full_name() or request.user.get_username())
    )
    new_item = KnowledgeItem.objects.create(
        title=f"{source.title} (copie)",
        description=source.description,
        kind=source.kind,
        department=source.department,
        author=author_name,
        author_user=request.user if request.user.is_authenticated else None,
        content=source.content,
        video_url=source.video_url or "",
        status=KnowledgeItem.Status.DRAFT,
        numero_version=source.numero_version,
        read_time_min=source.read_time_min,
    )
    KnowledgeVersion.objects.create(
        knowledge_item=new_item,
        numero_version=source.numero_version,
        content=source.content,
        author_name=author_name,
        est_actuelle=True,
    )
    for tag in source.tags.all():
        new_item.tags.add(tag)
    for comp in source.competences.all():
        new_item.competences.add(comp)
    messages.success(request, "Connaissance dupliquée. Vous pouvez la modifier.")
    return redirect("knowledge_edit", knowledge_id=new_item.id)


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

    # S'assurer qu'au moins une version existe (rétrocompat)
    if not item.versions.exists():
        KnowledgeVersion.objects.create(
            knowledge_item=item,
            numero_version=item.numero_version,
            content=item.content,
            author_name=item.author,
            est_actuelle=True,
        )
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


def _send_set_password_email(request: HttpRequest, user: User) -> bool:
    """
    Envoie un email à l'utilisateur avec un lien pour définir son mot de passe
    (réutilise le flux de réinitialisation Django : password_reset_confirm).
    """
    to = [user.email] if user.email else []
    if not to:
        return False
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    protocol = "https" if request.is_secure() else "http"
    domain = request.get_host()
    context = {
        "user": user,
        "protocol": protocol,
        "domain": domain,
        "uid": uid,
        "token": token,
    }
    subject = render_to_string("auth/welcome_set_password_subject.txt", context).strip()
    body = render_to_string("auth/welcome_set_password_email.html", context)
    try:
        msg = EmailMultiAlternatives(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            to,
        )
        msg.send(fail_silently=False)
        return True
    except Exception:
        return False


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
            if _send_set_password_email(request, user):
                messages.success(request, f"Utilisateur « {display_name} » créé. Un email avec le lien pour définir le mot de passe a été envoyé à {user.email}.")
            else:
                messages.warning(request, f"Utilisateur « {display_name} » créé, mais l'envoi de l'email a échoué (vérifiez l'adresse email et la configuration SMTP). L'utilisateur peut utiliser « Mot de passe oublié » depuis la page de connexion.")
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


def _get_user_plan(request: HttpRequest) -> PlanIntegration | None:
    """Retourne le plan d'intégration lié au poste de l'utilisateur (département + poste), ou None."""
    if not getattr(request.user, "is_authenticated", False):
        return None
    profile = (
        UserProfile.objects.filter(user=request.user)
        .select_related("department", "poste", "poste__plan_integration")
        .first()
    )
    if not profile or not profile.poste_id:
        return None
    return getattr(profile.poste, "plan_integration", None)


def _progress_for_plan(user, plan: PlanIntegration) -> dict:
    """Calcule la progression (pourcentage, modules complétés, quiz passés, sous-étapes)."""
    # Optimisation: Utiliser select_related et prefetch_related pour minimiser les requêtes
    modules = list(
        plan.modules.prefetch_related(
            "quiz", 
            "quiz__questions", 
            "quiz__questions__choices", 
            "steps",
            "knowledge_links",
            "knowledge_links__knowledge_item",
            "knowledge_links__knowledge_item__versions"
        )
        .select_related("plan")
        .order_by("ordre")
    )
    total = len(modules)
    if total == 0:
        return {"pourcentage": 0, "modules": [], "progression_obj": None}

    # Optimisation: Récupérer toutes les données en une seule requête
    quiz_attempts = UserQuizAttempt.objects.filter(
        user=user, 
        quiz__module__plan=plan
    ).select_related("quiz", "quiz__module")
    
    step_completions = UserModuleStepCompletion.objects.filter(
        user=user,
        module_step__module__plan=plan
    ).select_related("module_step", "module_step__module")
    
    # Créer des sets pour un accès rapide
    quiz_passed_ids = set(
        attempt.quiz_id for attempt in quiz_attempts if attempt.passed
    )
    completed_step_ids = set(
        completion.module_step_id for completion in step_completions
    )
    
    completed = 0
    module_status = []
    previous_module_passed = True  # Le premier module est toujours accessible
    
    for mod in modules:
        has_quiz = hasattr(mod, "quiz") and mod.quiz
        steps = list(getattr(mod, "steps", []).all())
        steps_completed = [s for s in steps if s.id in completed_step_ids]
        steps_passed = len(steps) == 0 or len(steps_completed) == len(steps)
        
        # Récupérer les connaissances liées à ce module
        knowledge_items = []
        if hasattr(mod, 'knowledge_links'):
            for link in mod.knowledge_links.all().order_by('ordre'):
                knowledge_items.append({
                    'item': link.knowledge_item,
                    'ordre': link.ordre
                })
        
        # Vérifier si le module est accessible (module précédent complété)
        module_accessible = previous_module_passed
        
        if has_quiz:
            quiz_passed = mod.quiz.id and mod.quiz.id in quiz_passed_ids
            # Un module est validé seulement si : accessible + étapes complétées + quiz réussi
            mod_passed = module_accessible and quiz_passed and steps_passed
            if mod_passed:
                completed += 1
            module_status.append({
                "module": mod,
                "has_quiz": True,
                "passed": mod_passed,
                "accessible": module_accessible,
                "quiz_passed": quiz_passed,  # Ajout de l'état spécifique du quiz
                "steps_passed": steps_passed,  # Ajout de l'état spécifique des étapes
                "quiz": getattr(mod, "quiz", None),
                "steps": steps,
                "steps_completed": steps_completed,
                "completed_step_ids": completed_step_ids,
                "knowledge_items": knowledge_items,
            })
        else:
            # Un module sans quiz est validé seulement si : accessible + étapes complétées
            mod_passed = module_accessible and steps_passed
            if mod_passed:
                completed += 1
            module_status.append({
                "module": mod,
                "has_quiz": False,
                "passed": mod_passed,
                "accessible": module_accessible,
                "steps_passed": steps_passed,  # Ajout de l'état spécifique des étapes
                "quiz": None,
                "steps": steps,
                "steps_completed": steps_completed,
                "completed_step_ids": completed_step_ids,
                "knowledge_items": knowledge_items,
            })
        
        # Pour le prochain module, vérifier si celui-ci est complété
        if mod_passed:
            previous_module_passed = True
        else:
            # Si le module actuel n'est pas passé, les suivants ne sont pas accessibles
            previous_module_passed = False

    pourcentage = round((completed / total) * 100) if total else 0
    progression_obj = Progression.objects.filter(user=user, plan=plan).first()
    if progression_obj and progression_obj.pourcentage != pourcentage:
        progression_obj.pourcentage = pourcentage
        progression_obj.save(update_fields=["pourcentage"])
    elif not progression_obj:
        progression_obj = Progression.objects.create(user=user, plan=plan, pourcentage=pourcentage)

    return {"pourcentage": pourcentage, "modules": module_status, "progression_obj": progression_obj}


@frontend_login_required
def onboarding_home(request: HttpRequest) -> HttpResponse:
    """Page d'accueil intégration : plan personnel si poste avec plan, sinon étapes génériques."""
    plan = _get_user_plan(request)
    if plan:
        return redirect("plan_integration_personnel")
    steps = OnboardingStep.objects.all()
    return render(request, "onboarding/home.html", {"steps": list(steps)})


@frontend_login_required
def module_step_toggle(request: HttpRequest, step_id: int) -> HttpResponse:
    """Bascule l'état coché/décoché d'une sous-étape (AJAX POST)."""
    from django.http import JsonResponse
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Méthode non autorisée"}, status=405)
    plan = _get_user_plan(request)
    if not plan:
        return JsonResponse({"ok": False, "error": "Plan non trouvé"}, status=403)
    step = get_object_or_404(ModuleStep.objects.select_related("module"), pk=step_id)
    if step.module.plan_id != plan.id:
        return JsonResponse({"ok": False, "error": "Sous-étape hors plan"}, status=403)
    compl, created = UserModuleStepCompletion.objects.get_or_create(
        user=request.user, module_step=step
    )
    if created:
        return JsonResponse({"ok": True, "checked": True})
    compl.delete()
    return JsonResponse({"ok": True, "checked": False})


@frontend_login_required
def plan_integration_personnel(request: HttpRequest) -> HttpResponse:
    """Mon plan d'intégration : modules et quiz selon le poste/département, avec suivi de progression."""
    plan = _get_user_plan(request)
    if not plan:
        messages.info(request, "Aucun plan d'intégration n'est associé à votre poste. Consultez les étapes générales ci-dessous.")
        return redirect("onboarding_home")
    
    # Récupérer le profil utilisateur pour afficher le contexte
    profile = (
        UserProfile.objects.filter(user=request.user)
        .select_related("department", "poste")
        .first()
    )
    
    progress = _progress_for_plan(request.user, plan)
    return render(
        request,
        "onboarding/plan_personnel.html",
        {
            "plan": plan,
            "progress": progress,
            "profile": profile,  # Ajout du profil pour le contexte
        },
    )


@frontend_login_required
def quiz_take(request: HttpRequest, quiz_id: int) -> HttpResponse:
    """Affiche un quiz et enregistre les réponses (score, passage)."""
    quiz = get_object_or_404(
        Quiz.objects.select_related("module").prefetch_related("questions", "questions__choices"),
        pk=quiz_id,
    )
    # Vérifier que le quiz appartient au plan du poste/département de l'utilisateur
    plan = _get_user_plan(request)
    if not plan or not quiz.module or getattr(quiz.module, "plan_id", None) != plan.id:
        messages.error(request, "Ce quiz ne fait pas partie de votre plan d'intégration.")
        return redirect("onboarding_home")

    # Vérifier les prérequis : toutes les sous-étapes du module doivent être complétées
    progress = _progress_for_plan(request.user, plan)
    current_module_status = None
    for module_status in progress["modules"]:
        if module_status["module"].id == quiz.module.id:
            current_module_status = module_status
            break
    
    if not current_module_status:
        messages.error(request, "Module introuvable dans votre progression.")
        return redirect("plan_integration_personnel")
    
    # Vérifier que le module est accessible
    if not current_module_status.get("accessible", False):
        messages.error(request, "Vous devez d'abord compléter le module précédent avant d'accéder à ce quiz.")
        return redirect("plan_integration_personnel")
    
    # Vérifier que toutes les sous-étapes sont complétées
    steps = current_module_status.get("steps", [])
    steps_completed = current_module_status.get("steps_completed", [])
    
    if len(steps) > 0 and len(steps_completed) < len(steps):
        remaining_steps = len(steps) - len(steps_completed)
        messages.error(request, f"Vous devez d'abord compléter toutes les sous-étapes ({remaining_steps} restante{'s' if remaining_steps > 1 else ''}) avant de passer le quiz.")
        return redirect("plan_integration_personnel")

    if request.method == "POST":
        # Corriger les réponses : question_id -> choice_id (choix sélectionné)
        selected = {}
        for key, value in request.POST.items():
            if key.startswith("q_") and value.isdigit():
                selected[int(key[2:])] = int(value)

        total_questions = quiz.questions.count()
        if total_questions == 0:
            messages.warning(request, "Ce quiz n'a pas de questions.")
            return redirect("plan_integration_personnel")

        correct = 0
        for q in quiz.questions.all():
            choice_id = selected.get(q.id)
            if choice_id:
                if QuizChoice.objects.filter(question=q, id=choice_id, is_correct=True).exists():
                    correct += 1
        score_pct = round((correct / total_questions) * 100)
        passed = score_pct >= quiz.seuil_reussite_pct

        attempt, _ = UserQuizAttempt.objects.update_or_create(
            user=request.user,
            quiz=quiz,
            defaults={"score_pct": score_pct, "passed": passed},
        )

        _progress_for_plan(request.user, plan)

        if passed:
            messages.success(request, f"Quiz réussi avec {score_pct} %.")
        else:
            messages.warning(request, f"Score : {score_pct} %. Il faut {quiz.seuil_reussite_pct} % pour valider. Vous pouvez réessayer.")
        return redirect("plan_integration_personnel")

    return render(
        request,
        "onboarding/quiz_take.html",
        {"quiz": quiz},
    )


@frontend_login_required
def trainings(request: HttpRequest) -> HttpResponse:

    # La vue training/list.html et la logique TrainingModule ont été supprimées
    return render(request, "training/list.html", {"trainings": []})



# La vue tests_home et toute la logique quiz ont été supprimées


@frontend_login_required
def profile(request: HttpRequest) -> HttpResponse:
    user = request.user
    profile_obj = None
    role = None

    if getattr(user, "is_authenticated", False):
        profile_obj = (
            UserProfile.objects.filter(user=user)
            .select_related("department", "poste")
            .first()
        )
        role = profile_obj.role if profile_obj else None
    else:
        role = request.session.get("frontend_role")
        if role:
            profile_obj = UserProfile.objects.filter(
                display_name=f"frontend:{role}"
            ).select_related("department").first()

    # Formulaire d'édition (uniquement pour utilisateur authentifié avec profil)
    form = None
    if profile_obj and getattr(user, "is_authenticated", False) and getattr(user, "pk", None):
        if request.method == "POST":
            form = ProfileEditForm(
                request.POST,
                request.FILES,
                user_instance=user,
                profile_instance=profile_obj,
            )
            if form.is_valid():
                user.first_name = form.cleaned_data["first_name"].strip()
                user.last_name = form.cleaned_data["last_name"].strip()
                user.email = form.cleaned_data["email"].strip().lower()
                user.save(update_fields=["first_name", "last_name", "email"])
                display_name = form.cleaned_data.get("display_name")
                if not display_name:
                    display_name = (user.get_full_name() or user.username or "").strip() or user.username
                if UserProfile.objects.filter(display_name=display_name).exclude(pk=profile_obj.pk).exists():
                    display_name = f"{display_name} ({user.username})"
                profile_obj.display_name = display_name
                if form.cleaned_data.get("photo"):
                    profile_obj.photo = form.cleaned_data["photo"]
                profile_obj.save(update_fields=["display_name", "photo"])
                messages.success(request, "Profil mis à jour.")
                return redirect("profile")
        else:
            form = ProfileEditForm(
                initial={
                    "first_name": user.first_name or "",
                    "last_name": user.last_name or "",
                    "email": user.email or "",
                    "display_name": (profile_obj.display_name or "").strip() or None,
                },
                user_instance=user,
                profile_instance=profile_obj,
            )

    return render(
        request,
        "profile/index.html",
        {
            "form": form,
            "profile": profile_obj,
            "role": role,
            "roles": ROLES,
        },
    )
