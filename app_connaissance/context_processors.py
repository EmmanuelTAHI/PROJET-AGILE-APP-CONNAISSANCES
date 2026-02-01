from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from .models import UserProfile


def frontend_user(request: HttpRequest) -> dict[str, Any]:
    user = request.user
    is_authenticated = user.is_authenticated

    role: str | None = None
    display_name = "Invité"

    if is_authenticated:
        profile: UserProfile | None = getattr(user, "profile", None)
        role = profile.role if profile else None
        display_name = profile.display_name if profile else (user.get_full_name() or user.username)
    else:
        # Mode démo : rôle en session
        role = request.session.get("frontend_demo_role")
        display_name = request.session.get("frontend_demo_name") or (role or "Invité")

    return {
        "frontend": {
            "is_authenticated": is_authenticated,
            "role": role,
            "display_name": display_name,
        }
    }

