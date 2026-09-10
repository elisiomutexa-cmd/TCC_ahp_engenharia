from apps.accounts.models import User


def user_context(request):
    user = getattr(request, "user", None)
    return {
        "user_is_admin": bool(user and user.is_authenticated and user.is_administrator),
    }
