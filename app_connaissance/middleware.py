"""Middleware pour forcer le changement de mot de passe à la première connexion."""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import resolve


def require_password_change_middleware(get_response):
    """Redirige vers la page de changement de mot de passe si must_change_password."""
    def middleware(request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated:
            profile = getattr(request.user, "profile", None)
            if profile and getattr(profile, "must_change_password", False):
                try:
                    match = resolve(request.path_info)
                    if match.url_name not in ("password_change_required", "logout_view", "password_reset", "password_reset_done", "password_reset_confirm", "password_reset_complete"):
                        return redirect("password_change_required")
                except Exception:
                    return redirect("password_change_required")
        return get_response(request)
    return middleware
