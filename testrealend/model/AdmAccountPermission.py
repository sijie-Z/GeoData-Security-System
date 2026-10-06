from extension.extension import db

# class AdmAccountPermission(db.Model):
#     __bind_key__ = 'mysql_db'
#     __tablename__ = 'adm_account_permissions'
#     id = db.Column(db.Integer, primary_key=True)
#     adm_account_id = db.Column(db.Integer, db.ForeignKey('Adm_Account.id'), nullable=False)
#     permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), nullable=False)
#
#     # id = db.Column(db.Integer, primary_key=True)
#     # adm_account_id = db.Column(db.Integer, db.ForeignKey('adm_account.id'))
#     # permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'))
#     # adm_account = db.relationship('AdmAccount', back_populates='permissions')
#     # permission = db.relationship('Permission', back_populates='account_permissions')


class AdmAccountPermissions(db.Model):
    __bind_key__ = "mysql_db"
    __tablename__ = "adm_account_permissions"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    adm_account_id = db.Column(db.Integer, db.ForeignKey("adm_account.id"), nullable=False)
    # Target table is declared as "Permissions" (model/Permission.py). The old lowercase
    # "permissions.id" string failed to resolve inside the same MetaData (case-sensitive),
    # poisoning metadata.sorted_tables; MySQL itself is case-insensitive on Windows and
    # points both spellings at the same physical table, so no migration is needed.
    permission_id = db.Column(db.Integer, db.ForeignKey("Permissions.id"), nullable=False)
