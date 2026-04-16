# 这是一个用于添加新员工用户的脚本。
# 它会使用项目中的 CommonServer.register_employee 方法来确保密码被正确哈希。

from flask import Flask
from server.common_server import CommonServer
from extension.extension import db

# 创建一个 Flask 应用实例
# 这个脚本需要一个应用上下文来与数据库交互，
# 所以我们需要像主应用 (app.py) 那样配置它。
app = Flask(__name__)

# 配置数据库连接 - 请确保这里的配置与您的 app.py 中的一致
# 您可能需要根据您的实际数据库配置进行调整
app.config['SQLALCHEMY_BINDS'] = {
    'mysql_db': 'mysql+mysqldb://root:root@127.0.0.1/esri_test', # 根据您的实际情况修改
    # 如果您使用其他数据库，也请相应配置
    # 'postgres_db': 'postgresql://postgres:root@127.0.0.1/esri_test'
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化 SQLAlchemy 实例
db.init_app(app)

def add_new_employee():
    """
    添加一个新员工的函数。
    它会提示用户输入必要的信息，并使用 CommonServer.register_employee 方法。
    """
    print("请输入新员工的详细信息：")
    name = input("姓名: ")
    employee_number = input("工号 (employee_number): ")
    id_number = input("身份证号: ")
    phone_number = input("电话号码: ")
    password = input("密码: ")
    confirm_password = input("确认密码: ")

    if password != confirm_password:
        print("两次输入的密码不一致，请重新运行脚本。")
        return

    print(f"\n尝试添加用户: {employee_number}")

    # 调用注册员工的方法
    # 这个方法应该处理密码哈希和数据库存储
    result = CommonServer.register_employee(
        name=name,
        employee_number=employee_number,
        id_number=id_number,
        phone_number=phone_number,
        password=password
    )

    if result.get('status'):
        print(f"用户 {employee_number} 添加成功！")
    else:
        print(f"添加用户 {employee_number} 失败: {result.get('message')}")

if __name__ == '__main__':
    # 使用 Flask 应用上下文来执行数据库操作
    with app.app_context():
        print("开始执行添加用户脚本...")
        add_new_employee()
        print("脚本执行完毕。")