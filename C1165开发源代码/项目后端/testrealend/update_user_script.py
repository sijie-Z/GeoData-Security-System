# 这是一个用于修改现有员工用户信息的脚本。
# 它会提示用户输入员工工号，然后允许用户更新员工的某些信息，
# 如姓名、身份证号、电话号码或重置密码。
# 如果修改密码，脚本会确保新密码被正确哈希。

from flask import Flask
from werkzeug.security import generate_password_hash
from model.Employee_Info import EmployeeInfo
from model.Employee_Account import EmployeeAccount
from extension.extension import db

# 创建一个 Flask 应用实例
# 这个脚本需要一个应用上下文来与数据库交互，
# 所以我们需要像主应用 (app.py) 那样配置它。
app = Flask(__name__)

# 配置数据库连接 - 请确保这里的配置与您的 app.py 中的一致
# 您可能需要根据您的实际数据库配置进行调整
app.config['SQLALCHEMY_BINDS'] = {
    'mysql_db': 'mysql+mysqldb://root:root@127.0.0.1/esri_test', # 根据您的实际情况修改
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化 SQLAlchemy 实例
db.init_app(app)

def update_employee_info():
    """
    修改现有员工信息的函数。
    它会提示用户输入员工工号，然后允许用户选择要更新的字段并输入新值。
    如果更新密码，密码会被哈希处理。
    """
    print("--- 修改员工信息脚本 ---")
    employee_number_to_update = input("请输入要修改信息的员工工号: ")

    # 查询员工信息和账户信息
    employee_info = EmployeeInfo.query.filter_by(employee_number=employee_number_to_update).first()
    employee_account = EmployeeAccount.query.filter_by(employee_number=employee_number_to_update).first()

    if not employee_info or not employee_account:
        print(f"未找到工号为 {employee_number_to_update} 的员工。请检查工号是否正确。")
        return

    print(f"\n找到员工: {employee_info.name} (工号: {employee_info.employee_number})")
    print(f"当前信息:")
    print(f"  姓名: {employee_info.name}")
    print(f"  身份证号: {employee_info.id_number}")
    print(f"  电话号码: {employee_info.phone_number}")
    print(f"  地址: {employee_info.address}")
    # 出于安全考虑，不直接显示密码

    updated_fields = []

    # 询问是否修改姓名
    if input("是否修改姓名? (y/n): ").lower() == 'y':
        new_name = input(f"请输入新的姓名 (当前: {employee_info.name}): ")
        if new_name:
            employee_info.name = new_name
            updated_fields.append("姓名")

    # 询问是否修改身份证号
    if input("是否修改身份证号? (y/n): ").lower() == 'y':
        new_id_number = input(f"请输入新的身份证号 (当前: {employee_info.id_number}): ")
        if new_id_number:
            # 检查新的身份证号是否已存在 (如果需要唯一性检查)
            existing_employee_by_id = EmployeeInfo.query.filter(
                EmployeeInfo.id_number == new_id_number,
                EmployeeInfo.employee_number != employee_number_to_update
            ).first()
            if existing_employee_by_id:
                print(f"错误：身份证号 {new_id_number} 已被其他员工使用。身份证号未修改。")
            else:
                employee_info.id_number = new_id_number
                updated_fields.append("身份证号")

    # 询问是否修改电话号码
    if input("是否修改电话号码? (y/n): ").lower() == 'y':
        new_phone_number = input(f"请输入新的电话号码 (当前: {employee_info.phone_number}): ")
        if new_phone_number:
            # 检查新的电话号码是否已存在 (如果需要唯一性检查)
            existing_employee_by_phone = EmployeeInfo.query.filter(
                EmployeeInfo.phone_number == new_phone_number,
                EmployeeInfo.employee_number != employee_number_to_update
            ).first()
            if existing_employee_by_phone:
                print(f"错误：电话号码 {new_phone_number} 已被其他员工使用。电话号码未修改。")
            else:
                employee_info.phone_number = new_phone_number
                updated_fields.append("电话号码")

    # 询问是否修改地址
    if input("是否修改地址? (y/n): ").lower() == 'y':
        new_address = input(f"请输入新的地址 (当前: {employee_info.address}): ")
        if new_address:
            employee_info.address = new_address
            updated_fields.append("地址")

    # 询问是否重置密码
    if input("是否重置密码? (y/n): ").lower() == 'y':
        new_password = input("请输入新密码: ")
        confirm_password = input("请再次输入新密码以确认: ")
        if new_password and new_password == confirm_password:
            employee_account.employee_user_password = generate_password_hash(new_password)
            updated_fields.append("密码")
            print("密码已设置为新密码。")
        elif new_password != confirm_password:
            print("两次输入的密码不一致。密码未修改。")
        else:
            print("密码未提供。密码未修改。")

    if not updated_fields:
        print("没有进行任何修改。")
        return

    try:
        db.session.commit()
        print(f"\n员工 {employee_number_to_update} 的信息已成功更新。")
        print(f"更新的字段: {', '.join(updated_fields)}")
    except Exception as e:
        db.session.rollback()
        print(f"更新员工信息时发生错误: {str(e)}")

if __name__ == '__main__':
    # 使用 Flask 应用上下文来执行数据库操作
    with app.app_context():
        print("开始执行修改用户脚本...")
        update_employee_info()
        print("脚本执行完毕。")