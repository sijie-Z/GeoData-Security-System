# from flask_sqlalchemy import SQLAlchemy
#
# db = SQLAlchemy()
#
#
# from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address
#
#
# # 设置 Flask-Limiter
# limiter = Limiter(get_remote_address)


from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# 初始化 SQLAlchemy
db = SQLAlchemy()

# 初始化 Flask-Limiter
limiter = Limiter(get_remote_address)
