from flask import request
from flask_jwt_extended import jwt_required
from flask_restful import Resource

from model.Adm_Nav import AdmNav
from model.Employee_Nav import EmployeeNav
from utils.required import is_admin_identity


def _admin_menu_forbidden():
    """Guard shared nav resources: only ``/api/admin/*`` requires an admin.

    NavTreeResource/NavListResource are registered on both the admin and the
    employee URLs, so the role check cannot live in a decorator — it keys off
    the request path instead.
    """
    if "admin" in request.path and not is_admin_identity():
        return {"status": False, "msg": "需要管理员权限"}, 403
    return None


def build_tree(items, parent_id=None):
    tree = []
    for item in items:
        if item.get("parent_id") == parent_id:
            children = build_tree(items, item.get("id"))
            if children:
                item["children"] = children
            tree.append(item)
    return tree


class NavTreeResource(Resource):
    @jwt_required()
    def get(self):
        denial = _admin_menu_forbidden()
        if denial:
            return denial
        # Determine role based on request URL
        role = "admin" if "admin" in request.path else "employee"

        if role == "admin":
            navs = AdmNav.query.order_by(AdmNav.sort).all()
        else:
            navs = EmployeeNav.query.order_by(EmployeeNav.sort).all()

        nav_list = [nav.to_dict() for nav in navs]
        tree = build_tree(nav_list)

        return {"status": True, "data": tree}, 200


class NavListResource(Resource):
    @jwt_required()
    def get(self):
        denial = _admin_menu_forbidden()
        if denial:
            return denial
        parent_id = request.args.get("parent_id", type=int)
        role = "admin" if "admin" in request.path else "employee"

        if role == "admin":
            navs = AdmNav.query.filter_by(parent_id=parent_id).order_by(AdmNav.sort).all()
        else:
            navs = EmployeeNav.query.filter_by(parent_id=parent_id).order_by(EmployeeNav.sort).all()

        return {"status": True, "data": [nav.to_dict() for nav in navs]}, 200
