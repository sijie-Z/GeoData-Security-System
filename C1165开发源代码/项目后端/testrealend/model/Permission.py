from extension.extension import db


class Permission(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'Permissions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

    # account_permissions = db.relationship('AdmAccountPermission', back_populates='permission')


