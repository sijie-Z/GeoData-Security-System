from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import jsonify
from model.Adm_Account import AdmAccount


def admin_required(func):
    @wraps(func)
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user = get_jwt_identity()
        user = AdmAccount.query.filter_by(adm_number=current_user).first()
        if not user:
            return jsonify(message="Unauthorized"), 401
        return func(*args, **kwargs)

    return wrapper


def permission_required(permission):
    def decorator(func):
        @wraps(func)
        @jwt_required()
        def wrapper(*args, **kwargs):
            current_user = get_jwt_identity()
            user = AdmAccount.query.filter_by(adm_number=current_user).first()
            if not user or permission not in [p.name for p in user.permissions]:
                return jsonify(message="Permission denied"), 403
            return func(*args, **kwargs)

        return wrapper

    return decorator
