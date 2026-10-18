from functools import wraps

from flask_jwt_extended import get_jwt_identity, jwt_required

from model.Adm_Account import AdmAccount


def is_admin_role(role):
    """Check if a role string represents any admin sub-role (admin1/admin2/admin3)."""
    return bool(role and str(role).startswith("admin"))


def _get_admin_role(identity):
    """Extract admin sub-role from JWT identity or database.

    The JWT ``role`` claim is authoritative whenever it is present: an explicit
    non-admin role (e.g. ``employee``) must never fall back to ``AdmAccount``,
    otherwise an employee whose number collides with an admin's ``adm_number``
    would inherit admin rights.  Only legacy tokens that carry no ``role``
    claim at all may use the database fallback.
    """
    if isinstance(identity, dict):
        number = identity.get("number")
        if "role" in identity:
            role = identity.get("role")
            return role if is_admin_role(role) else None
        # Legacy token shape: no role claim, but possibly an admin_sub_role.
        sub_role = identity.get("admin_sub_role")
        if sub_role and str(sub_role).startswith("admin"):
            return sub_role
    else:
        number = identity

    try:
        user = AdmAccount.query.filter_by(adm_number=number).first()
        if user:
            return user.role
    except Exception:
        pass
    return None


def current_identity():
    """Return ``(number, username, role)`` for the current JWT identity.

    Legacy tokens may carry a plain string identity — only ``number`` is
    meaningful in that case (``username``/``role`` are None).
    """
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        return identity.get("number"), identity.get("username"), identity.get("role")
    return identity, None, None


def is_admin_identity():
    """True when the current identity is an admin (admin1/admin2/admin3 or
    legacy ``admin``), honouring the strict role-claim rule in ``_get_admin_role``.
    """
    return is_admin_role(_get_admin_role(get_jwt_identity()))


def current_admin_role():
    """Admin sub-role of the current identity, or None for non-admins."""
    return _get_admin_role(get_jwt_identity())


def has_admin_role(*required_roles):
    """True when the current admin sub-role is one of ``required_roles``.

    Mirrors ``admin_role_required``: the super-admin (``admin`` or ``ADM*``)
    always passes.
    """
    sub_role = current_admin_role()
    if sub_role == "admin" or (sub_role and str(sub_role).startswith("ADM")):
        return True
    return sub_role in required_roles


def ensure_owner_or_admin(application):
    """Return a 403 response tuple unless the caller owns *application* or is admin.

    Ownership is derived from the JWT identity number — never from query/body
    parameters — and compared with ``application.applicant_user_number``.
    Callers must reject a missing row (404) before calling this helper.
    """
    if is_admin_identity():
        return None
    number, _username, _role = current_identity()
    applicant = getattr(application, "applicant_user_number", None)
    if number and applicant is not None and str(applicant) == str(number):
        return None
    return {"status": False, "msg": "无权访问该申请"}, 403


def admin_required(func):
    @wraps(func)
    @jwt_required()
    def wrapper(*args, **kwargs):
        # Role claim present and non-admin -> 403; DB fallback only for
        # legacy tokens without a role claim (see _get_admin_role).
        if not is_admin_identity():
            return {"status": False, "msg": "需要管理员权限"}, 403
        return func(*args, **kwargs)

    return wrapper


def admin_role_required(*required_roles):
    """Decorator that requires specific admin sub-roles.

    Usage:
        @admin_role_required('admin1')           # must be admin1
        @admin_role_required('admin1', 'admin2')  # must be admin1 or admin2

    Super-admin ('admin' or 'ADM*') always passes.
    """

    def decorator(func):
        @wraps(func)
        @jwt_required()
        def wrapper(*args, **kwargs):
            identity = get_jwt_identity()
            sub_role = _get_admin_role(identity)

            # Super-admin bypass (role='admin' or sub_role starts with 'ADM')
            if sub_role == "admin" or (sub_role and sub_role.startswith("ADM")):
                return func(*args, **kwargs)

            if sub_role not in required_roles:
                allowed = ", ".join(required_roles)
                return {"status": False, "msg": f"需要以下角色之一: {allowed}，当前角色: {sub_role or '未知'}"}, 403
            return func(*args, **kwargs)

        return wrapper

    return decorator
