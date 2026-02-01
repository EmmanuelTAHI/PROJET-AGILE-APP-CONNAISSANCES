from __future__ import annotations

from functools import wraps
from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse


def frontend_login_required(view_func: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """Redirige vers login si non connecté et pas de session démo."""
    @wraps(view_func)
    def _wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        if request.session.get("frontend_demo_role"):
            return view_func(request, *args, **kwargs)
        return redirect(reverse("login") + "?next=" + request.get_full_path())
    return _wrapped


def frontend_roles_required(*allowed_roles: str) -> Callable[[Callable[..., HttpResponse]], Callable[..., HttpResponse]]:
    """Vérifie le rôle (profil ou session démo) ; sinon 403 ou accès refusé."""

    def _decorator(view_func: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
        @wraps(view_func)
        def _wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            role = None
            if request.user.is_authenticated:
                profile = getattr(request.user, "profile", None)
                role = profile.role if profile else None
            if role is None:
                role = request.session.get("frontend_demo_role")
            if role in allowed_roles:
                return view_func(request, *args, **kwargs)
            return redirect("forbidden")
        return _wrapped
    return _decorator
