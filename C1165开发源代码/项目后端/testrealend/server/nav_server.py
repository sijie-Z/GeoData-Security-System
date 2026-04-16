from model.Adm_Nav import AdmNav
from model.Employee_Nav import EmployeeNav
from extension.extension import db



class AdmNavServer:
    def get_nav_list(self):
        nav_list_data = db.session.query(AdmNav).all()
        return nav_list_data

    def get_list_id(self, nav_id):
        if nav_id:
            nav_items = db.session.query(AdmNav).filter(AdmNav.id == nav_id).all()
        else:
            nav_items = None
        return nav_items

    def get_all_children(self, parent_id):
        if parent_id:
            nav_items = db.session.query(AdmNav).filter(AdmNav.parent_id == parent_id).all()
        else:
            nav_items = None
        return nav_items

    def get_nav_item(self, nav_item_id):
        nav_item = db.session.query(AdmNav).filter(AdmNav.id == nav_item_id).first()
        return nav_item

    def build_adm_nav_tree(self, nav_datas):
        adm_nav_tree = []
        nav_dict = {nav_data.id: {
            "id": str(nav_data.id),
            "parent_id": str(nav_data.parent_id),
            "name": nav_data.name,
            "path": nav_data.path,
            "level": str(nav_data.level),
            "sort": str(nav_data.sort),
            "status": str(nav_data.status),
            "children": []  # 设置初始值为空列表
        } for nav_data in nav_datas}

        for nav_data in nav_datas:
            if nav_data.parent_id == 0:
                adm_nav_tree.append(nav_dict[nav_data.id])
            else:
                parent_nav = nav_dict.get(nav_data.parent_id)
                if parent_nav:
                    parent_nav["children"].append(nav_dict[nav_data.id])

        # 将所有没有子节点的导航项的 children 设置为 None
        for nav in nav_dict.values():
            if len(nav["children"]) == 0:
                nav["children"] = None

        return adm_nav_tree


class EmpNavServer:
    def get_nav_list(self):
        nav_list_data = db.session.query(EmployeeNav).all()
        return nav_list_data

    def build_emp_nav_tree(self, nav_datas):
        emp_nav_tree = []
        nav_dict = {nav_data.id: {
            "id": str(nav_data.id),
            "parent_id": str(nav_data.parent_id),
            "name": nav_data.name,
            "path": nav_data.path,
            "level": str(nav_data.level),
            "sort": str(nav_data.sort),
            "status": str(nav_data.status),
            "children": []  # 设置初始值为空列表
        } for nav_data in nav_datas}

        for nav_data in nav_datas:
            if nav_data.parent_id == 0:
                emp_nav_tree.append(nav_dict[nav_data.id])
            else:
                parent_nav = nav_dict.get(nav_data.parent_id)
                if parent_nav:
                    parent_nav["children"].append(nav_dict[nav_data.id])

        # 将所有没有子节点的导航项的 children 设置为 None
        for nav in nav_dict.values():
            if len(nav["children"]) == 0:
                nav["children"] = None

        return emp_nav_tree
