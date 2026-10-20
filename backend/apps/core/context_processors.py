"""Template context for the admin."""


def age_check_banner(request):
    """The admin's "Age verification for the member feed is off" banner, on every staff page
    while the club has it switched off. Admins can open it to change the setting."""
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated and user.is_staff):
        return {}
    from apps.memberships.access import age_check_required

    if age_check_required():
        return {}
    from apps.memberships.age import can_change_setting

    return {"age_check_off": True, "age_check_can_change": can_change_setting(user)}
