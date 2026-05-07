from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required
from model.Adm_Nav import AdmNav
from model.Employee_Nav import EmployeeNav
from extension.extension import db

def build_tree(items, parent_id=None):
    tree = []
    for item in items:
        if item.get('parent_id') == parent_id:
            children = build_tree(items, item.get('id'))
            if children:
                item['children'] = children
            tree.append(item)
    return tree

class NavTreeResource(Resource):
    @jwt_required()
    def get(self):
        # Determine role based on request URL
        role = 'admin' if 'admin' in request.path else 'employee'
        
        if role == 'admin':
            navs = AdmNav.query.order_by(AdmNav.sort).all()
        else:
            navs = EmployeeNav.query.order_by(EmployeeNav.sort).all()
            
        nav_list = [nav.to_dict() for nav in navs]
        tree = build_tree(nav_list)
        
        return {
            'status': True,
            'data': tree
        }, 200

class NavListResource(Resource):
    @jwt_required()
    def get(self):
        parent_id = request.args.get('parent_id', type=int)
        role = 'admin' if 'admin' in request.path else 'employee'
        
        if role == 'admin':
            navs = AdmNav.query.filter_by(parent_id=parent_id).order_by(AdmNav.sort).all()
        else:
            navs = EmployeeNav.query.filter_by(parent_id=parent_id).order_by(EmployeeNav.sort).all()
            
        return {
            'status': True,
            'data': [nav.to_dict() for nav in navs]
        }, 200
