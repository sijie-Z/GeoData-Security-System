from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt_identity
from model.Adm_Account import AdmAccount


def is_admin_role(role):
    """Check if a role string represents any admin sub-role (admin1/admin2/admin3)."""
    return bool(role and str(role).startswith('admin'))


def _get_admin_role(identity):
    """Extract admin sub-role from JWT identity or database."""
    if isinstance(identity, dict):
        number = identity.get('number')
        # JWT carries 'role' = 'admin1'/'admin2'/'admin3' for admins
        sub_role = identity.get('admin_sub_role') or identity.get('role')
        if sub_role and sub_role.startswith('admin'):
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


def admin_required(func):
    @wraps(func)
    @jwt_required()
    def wrapper(*args, **kwargs):
        identity = get_jwt_identity()
        if isinstance(identity, dict):
            number = identity.get('number')
            role = identity.get('role')
        else:
            number = identity
            role = None

        # Accept 'admin' (legacy) or 'admin1'/'admin2'/'admin3' (sub-roles)
        if not (role and str(role).startswith('admin')):
            try:
                user = AdmAccount.query.filter_by(adm_number=number).first()
                if not user:
                    return {'status': False, 'msg': '需要管理员权限'}, 403
            except Exception:
                return {'status': False, 'msg': '需要管理员权限'}, 403
        return func(*args, **kwargs)

    return wrapper


def admin_role_required(*required_roles):
    """Decorator that requires specific admin sub-roles.

    Usage:
        @admin_role_required('admin1')           # must be admin1
        @admin_role_required('admin1', 'admin2')  # must be admin1 or admin2
    """
    def decorator(func):
        @wraps(func)
        @jwt_required()
        def wrapper(*args, **kwargs):
            identity = get_jwt_identity()
            sub_role = _get_admin_role(identity)

            if sub_role not in required_roles:
                allowed = ', '.join(required_roles)
                return {
                    'status': False,
                    'msg': f'需要以下角色之一: {allowed}，当前角色: {sub_role or "未知"}'
                }, 403
            return func(*args, **kwargs)
        return wrapper
    return decorator
