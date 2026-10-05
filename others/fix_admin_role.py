#!/usr/bin/env python3
"""
修复管理员角色：将 admin 角色更新为 admin1
用法: python others/fix_admin_role.py
"""

import pymysql
from pymysql.cursors import DictCursor
from werkzeug.security import generate_password_hash
from datetime import datetime


def fix_admin_role():
    """将用户名 22200214135 的角色从 admin 更新为 admin1"""

    ADMIN_USERNAME = "22200214135"
    ADMIN_PASSWORD = "liyi"
    ADM_NUMBER = "22200214135"  # 用用户名作为管理员编号
    TARGET_ROLE = "admin1"

    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='root',
            database='esri_test',
            port=3306,
            charset='utf8mb4',
            cursorclass=DictCursor
        )
        cursor = conn.cursor()

        # ========== 第一步：检查 adm_info 是否存在 ==========
        cursor.execute(
            "SELECT * FROM adm_info WHERE adm_number = %s",
            (ADM_NUMBER,)
        )
        adm_info = cursor.fetchone()

        if not adm_info:
            print(f"adm_info 表中不存在 adm_number={ADM_NUMBER}，正在创建...")
            cursor.execute(
                """INSERT INTO adm_info (adm_number, name, job_number, phone_number, address, id_number, create_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    ADM_NUMBER,
                    "管理员",
                    ADM_NUMBER,
                    "00000000000",
                    "未填写",
                    "000000000000000000",
                    datetime.now()
                )
            )
            print(f"✅ adm_info 记录已创建: adm_number={ADM_NUMBER}")
        else:
            print(f"adm_info 记录已存在: {adm_info}")

        # ========== 第二步：检查 adm_account 是否存在 ==========
        cursor.execute(
            "SELECT * FROM adm_account WHERE adm_user_name = %s",
            (ADMIN_USERNAME,)
        )
        adm_account = cursor.fetchone()

        if adm_account:
            current_role = adm_account.get('role', '未知')
            print(f"adm_account 记录已存在: adm_user_name={ADMIN_USERNAME}, 当前 role={current_role}")

            if current_role != TARGET_ROLE:
                print(f"正在将 role 从 '{current_role}' 更新为 '{TARGET_ROLE}'...")
                cursor.execute(
                    "UPDATE adm_account SET role = %s WHERE adm_user_name = %s",
                    (TARGET_ROLE, ADMIN_USERNAME)
                )
                print(f"✅ role 已更新为 '{TARGET_ROLE}'")
            else:
                print(f"role 已经是 '{TARGET_ROLE}'，无需修改")

            # 检查是否需要更新密码
            if adm_account.get('adm_user_password', '') != ADMIN_PASSWORD:
                # 检查是否是哈希密码
                stored_pw = adm_account.get('adm_user_password', '')
                if stored_pw.startswith(('pbkdf2:', 'sha$', '$2b$', '$2a$')):
                    print("密码已是哈希格式，跳过密码更新（如需重置密码请使用其他方式）")
                else:
                    new_hash = generate_password_hash(ADMIN_PASSWORD)
                    cursor.execute(
                        "UPDATE adm_account SET adm_user_password = %s WHERE adm_user_name = %s",
                        (new_hash, ADMIN_USERNAME)
                    )
                    print("✅ 密码已更新")
        else:
            print(f"adm_account 中不存在 adm_user_name={ADMIN_USERNAME}，正在创建...")
            password_hash = generate_password_hash(ADMIN_PASSWORD)
            cursor.execute(
                """INSERT INTO adm_account (adm_user_name, adm_user_password, role, create_time, adm_number)
                VALUES (%s, %s, %s, %s, %s)""",
                (
                    ADMIN_USERNAME,
                    password_hash,
                    TARGET_ROLE,
                    datetime.now(),
                    ADM_NUMBER
                )
            )
            print(f"✅ adm_account 记录已创建: adm_user_name={ADMIN_USERNAME}, role={TARGET_ROLE}")

        conn.commit()

        # ========== 验证结果 ==========
        cursor.execute(
            "SELECT a.adm_user_name, a.role, a.adm_number, i.name FROM adm_account a LEFT JOIN adm_info i ON a.adm_number = i.adm_number WHERE a.adm_user_name = %s",
            (ADMIN_USERNAME,)
        )
        result = cursor.fetchone()
        print("\n========== 最终结果 ==========")
        print(f"用户名: {result.get('adm_user_name')}")
        print(f"角色:   {result.get('role')}")
        print(f"编号:   {result.get('adm_number')}")
        print(f"姓名:   {result.get('name', '未设置')}")
        print("=============================")

        cursor.close()
        conn.close()

        print("\n✅ 修复完成！请重新登录以获取新的 JWT token（旧 token 中的 role 仍是旧值）。")
        return True

    except Exception as e:
        print(f"❌ 操作失败：{e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    fix_admin_role()
