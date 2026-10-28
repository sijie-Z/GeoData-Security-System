import hashlib
import json
import logging
import os
import time
from datetime import UTC, datetime

from flask import request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt_identity,
    jwt_required,
    verify_jwt_in_request,
)
from flask_restful import Resource
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from config import BASE_DIR
from extension.extension import db, limiter
from model.Adm_Account import AdmAccount
from model.Adm_Info import AdmInfo
from model.benchmark_result import BenchmarkResult
from model.Employee_Account import EmployeeAccount
from model.Employee_Info import EmployeeInfo
from utils.log_helper import log_action
from utils.required import admin_required


def _password_matches(stored_password, input_password):
    """Check password. Returns (ok, new_hash_or_none) where new_hash is set
    when a legacy plaintext password needs upgrading.

    Fail closed: a structured hash (anything carrying the ``$`` separator)
    that cannot be verified — malformed, unknown algorithm, verifier exception
    — is never compared against the submitted password as if it were legacy
    plaintext. Only a value with no hash separator (the old plaintext form)
    may authenticate verbatim and be upgraded.
    """
    if not stored_password or not input_password:
        return False, None
    if "$" not in stored_password:
        if stored_password == input_password:
            return True, generate_password_hash(input_password)
        return False, None
    try:
        if check_password_hash(stored_password, input_password):
            return True, None
    except Exception:
        logging.warning("password hash verification failed; refusing login", exc_info=True)
    return False, None


class LoginResource(Resource):
    """
    用户登录
    ---
    tags: [Auth]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [username, password, role]
          properties:
            username: {type: string, description: 用户名}
            password: {type: string, description: 密码}
            role: {type: string, enum: [employee, admin], description: 角色}
    responses:
      200: {description: 登录成功}
      401: {description: 用户名或密码错误}
    """

    @limiter.limit("10 per minute")
    def post(self):
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        role_type = data.get("role")  # 'employee' or 'admin'

        if role_type == "admin":
            user = AdmAccount.query.filter_by(adm_user_name=username).first()
            if user:
                ok, new_hash = _password_matches(user.adm_user_password, password)
                if ok:
                    if new_hash:
                        user.adm_user_password = new_hash

                    # Look up display name BEFORE using it in token creation
                    try:
                        adm_info = AdmInfo.query.filter_by(adm_number=user.adm_number).first()
                    except Exception:
                        adm_info = None
                    display_name = adm_info.name if adm_info and adm_info.name else username

                    access_token = create_access_token(
                        identity={
                            "username": username,
                            "name": display_name,
                            "role": user.role,
                            "number": user.adm_number,
                        }
                    )
                    refresh_token = create_refresh_token(
                        identity={
                            "username": username,
                            "name": display_name,
                            "role": user.role,
                            "number": user.adm_number,
                        },
                        additional_claims={"iat_ts": time.time()},
                    )

                    # Update last login (non-fatal — login succeeds even if this write fails)
                    try:
                        adm_info = AdmInfo.query.filter_by(adm_number=user.adm_number).first()
                        if adm_info:
                            adm_info.last_login_time = datetime.now(UTC)
                        if new_hash:
                            db.session.commit()
                        else:
                            db.session.commit()
                    except Exception:
                        db.session.rollback()
                        logging.warning(f"Failed to update last_login_time for admin {username}", exc_info=True)
                    log_action(user.adm_number, display_name, "登录", "成功", "admin")

                    return {
                        "status": True,
                        "user_number": user.adm_number,
                        "role": user.role,
                        "admin_sub_role": user.role,
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "user_name": display_name,
                        "permissions": ["*"],
                    }, 200
        else:
            user = EmployeeAccount.query.filter_by(employee_user_name=username).first()
            if user:
                ok, new_hash = _password_matches(user.employee_user_password, password)
                if ok:
                    if new_hash:
                        user.employee_user_password = new_hash
                    # 查出真实姓名放入 JWT
                    emp_info_name = None
                    try:
                        emp = EmployeeInfo.query.filter_by(employee_number=user.employee_number).first()
                        emp_info_name = emp.name if emp and emp.name else None
                    except Exception:
                        pass
                    display_name = emp_info_name or username
                    access_token = create_access_token(
                        identity={
                            "username": username,
                            "name": display_name,
                            "role": "employee",
                            "number": user.employee_number,
                        }
                    )
                    refresh_token = create_refresh_token(
                        identity={
                            "username": username,
                            "name": display_name,
                            "role": "employee",
                            "number": user.employee_number,
                        },
                        additional_claims={"iat_ts": time.time()},
                    )

                    # Update last login (non-fatal — login succeeds even if this write fails)
                    try:
                        emp_info = EmployeeInfo.query.filter_by(employee_number=user.employee_number).first()
                        if emp_info:
                            emp_info.last_login_time = datetime.now(UTC)
                        db.session.commit()
                    except Exception:
                        db.session.rollback()
                        logging.warning(f"Failed to update last_login_time for employee {username}", exc_info=True)

                    emp_info = EmployeeInfo.query.filter_by(employee_number=user.employee_number).first()
                    display_name = emp_info.name if emp_info and emp_info.name else username
                    log_action(user.employee_number, display_name, "登录", "成功", "employee")

                    return {
                        "status": True,
                        "user_number": user.employee_number,
                        "role": "employee",
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "user_name": display_name,
                        "permissions": ["view", "apply", "download"],
                    }, 200

        log_action("unknown", username or "unknown", "登录", "失败", f"role={role_type}")
        return {"status": False, "msg": "用户名或密码错误", "message": "用户名或密码错误"}, 401


class RegisterResource(Resource):
    """
    员工注册
    ---
    tags: [Auth]
    consumes: [multipart/form-data]
    parameters:
      - in: formData
        name: name
        type: string
        required: true
        description: 员工姓名
      - in: formData
        name: employeeId
        type: string
        required: true
        description: 员工编号
      - in: formData
        name: idNumber
        type: string
        required: true
        description: 身份证号（唯一，不可为空）
      - in: formData
        name: phone
        type: string
        required: true
        description: 手机号（唯一，不可为空）
      - in: formData
        name: password
        type: string
        required: true
        description: 密码
      - in: formData
        name: avatar
        type: file
        description: 头像
    responses:
      201: {description: 注册成功}
      400: {description: 员工编号/工号/账号名已存在、编号被管理员占用、身份证号或手机号已被注册、缺少必填字段}
    """

    @limiter.limit("5 per minute")
    def post(self):
        # Multipart form data
        name = (request.form.get("name") or "").strip()
        employee_id = (request.form.get("employeeId") or "").strip()
        id_number = (request.form.get("idNumber") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        password = request.form.get("password")
        avatar = request.files.get("avatar")

        # Validate password complexity
        if not password or len(password) < 8:
            return {"status": False, "msg": "密码长度至少8位"}, 400
        if not any(c.isdigit() for c in password) or not any(c.isalpha() for c in password):
            return {"status": False, "msg": "密码必须包含字母和数字"}, 400

        # Required fields — the matching Employee_Info columns are NOT NULL
        # (model/Employee_Info.py), so a missing value must surface as a
        # readable 400 instead of a DB IntegrityError mapped to a generic 500.
        missing = [
            label
            for value, label in (
                (name, "姓名"),
                (employee_id, "员工编号"),
                (id_number, "身份证号"),
                (phone, "手机号"),
            )
            if not value
        ]
        if missing:
            msg = f"缺少必填字段: {', '.join(missing)}"
            return {"status": False, "msg": msg, "message": msg}, 400

        # Unique-column pre-checks, naming the conflicting field
        if EmployeeInfo.query.filter_by(employee_number=employee_id).first():
            return {"status": False, "msg": "员工编号已存在"}, 400
        if EmployeeInfo.query.filter_by(job_number=employee_id).first():
            return {"status": False, "msg": "工号已被占用"}, 400
        # The identity namespace is shared with admins at the application layer:
        # an employee number that equals an admin number makes identity lookups
        # ambiguous (and used to die as an IntegrityError -> 500 downstream).
        if (
            AdmInfo.query.filter_by(adm_number=employee_id).first()
            or AdmAccount.query.filter_by(adm_number=employee_id).first()
        ):
            return {"status": False, "msg": "该编号已被管理员账号占用"}, 400
        # Registration creates the account with employeeId as its login name.
        if EmployeeAccount.query.filter_by(employee_user_name=employee_id).first():
            return {"status": False, "msg": "账号名已被占用"}, 400
        if EmployeeInfo.query.filter_by(id_number=id_number).first():
            msg = "身份证号已被注册"
            return {"status": False, "msg": msg, "message": msg}, 400
        if EmployeeInfo.query.filter_by(phone_number=phone).first():
            msg = "手机号已被注册"
            return {"status": False, "msg": msg, "message": msg}, 400

        # Create Info
        new_info = EmployeeInfo(
            employee_number=employee_id,
            name=name,
            job_number=employee_id,
            id_number=id_number,
            phone_number=phone,
            address="未填写",
            create_time=datetime.now(UTC),
            face_photo=avatar.read() if avatar else None,
        )

        # Create Account
        new_account = EmployeeAccount(
            employee_user_name=employee_id,
            employee_user_password=generate_password_hash(password),
            employee_number=employee_id,
            role="employee",
        )

        try:
            db.session.add(new_info)
            db.session.flush()
            db.session.add(new_account)
            db.session.commit()
            return {"status": True, "msg": "注册成功", "message": "注册成功"}, 201
        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {"status": False, "msg": "操作失败，请稍后重试", "message": "操作失败，请稍后重试"}, 500


def _logout_marker_jti(number):
    """Synthetic blacklist key holding the last logout time of one identity.

    Length is exactly 36 chars (the ``token_blacklist.jti`` column width):
    ``LOGOUT:`` + 29 hex chars of the number's SHA-256.
    """
    digest = hashlib.sha256(str(number).encode("utf-8")).hexdigest()[:29]
    return f"LOGOUT:{digest}"


def _refresh_token_revoked(payload):
    """True when a refresh token is blacklisted or predates a logout.

    ``jti`` covers explicit revocation (logout with the refresh token in the
    body).  The per-identity marker covers the current frontend, which posts
    ``/api/logout`` without its refresh token — any refresh token issued
    before that logout instant is rejected.  ``iat_ts`` (float, set on every
    token minted here) keeps the comparison sub-second precise; legacy tokens
    fall back to the whole-second ``iat`` claim.
    """
    from model.TokenBlacklist import TokenBlacklist

    jti = payload.get("jti")
    if jti and TokenBlacklist.query.filter_by(jti=jti).first() is not None:
        return True
    identity = payload.get("sub")
    number = identity.get("number") if isinstance(identity, dict) else identity
    issued = payload.get("iat_ts", payload.get("iat"))
    if not number or issued is None:
        return False
    marker = TokenBlacklist.query.filter_by(jti=_logout_marker_jti(number)).first()
    if marker is None or marker.created_at is None:
        return False
    created = marker.created_at
    if created.tzinfo is None:
        # DATETIME columns store UTC wall time without tzinfo (project convention).
        created = created.replace(tzinfo=UTC)
    return float(issued) < created.timestamp()


class LogoutResource(Resource):
    @jwt_required()
    def post(self):
        from flask_jwt_extended import get_jwt

        from model.TokenBlacklist import TokenBlacklist

        payload = get_jwt()
        identity = get_jwt_identity()
        jti = payload.get("jti")

        # 1) Explicit refresh token (optional, backwards compatible): the
        #    frontend may start sending it without any server change.
        body = request.get_json(silent=True) or {}
        refresh_token = body.get("refresh_token")
        refresh_jti = None
        if refresh_token:
            try:
                decoded = decode_token(refresh_token)
                if decoded.get("type") == "refresh" and decoded.get("sub") == identity:
                    refresh_jti = decoded.get("jti")
            except Exception:
                logging.warning("logout: invalid refresh_token ignored")

        for value in (jti, refresh_jti):
            if value and TokenBlacklist.query.filter_by(jti=value).first() is None:
                db.session.add(TokenBlacklist(jti=value))

        # 2) Per-identity logout marker so refresh tokens are revoked even when
        #    the client does not send one (the current frontend posts no body).
        number = identity.get("number") if isinstance(identity, dict) else identity
        if number:
            marker_jti = _logout_marker_jti(number)
            marker = TokenBlacklist.query.filter_by(jti=marker_jti).first()
            now = datetime.now(UTC)
            if marker is None:
                db.session.add(TokenBlacklist(jti=marker_jti, created_at=now))
            else:
                marker.created_at = now
        try:
            db.session.commit()
        except IntegrityError:
            # Two concurrent logouts can both miss the marker and race the
            # INSERT. The loser rolls back and treats the row as already
            # present — logout stays idempotent instead of returning 500.
            db.session.rollback()
            logging.info("logout blacklist insert raced with a concurrent logout; treated as already present")
        return {"status": True, "msg": "登出成功"}, 200


def _refresh_identity_account_valid(identity):
    """Re-check a role-bearing refresh identity against the account tables.

    Rotation must not outlive the account it was minted for: a deleted account
    or a role/number change since issuance fails closed (401, re-login). Legacy
    tokens without a role claim (and plain-string identities) keep the old
    behaviour — the check is skipped.
    """
    if not isinstance(identity, dict):
        return True
    role = identity.get("role")
    if not role:
        return True
    username = identity.get("username")
    number = identity.get("number")
    if not username or not number:
        return False
    role = str(role)
    if role.startswith("admin"):
        account = AdmAccount.query.filter_by(adm_user_name=username, adm_number=number, role=role).first()
    else:
        account = EmployeeAccount.query.filter_by(
            employee_user_name=username, employee_number=number, role=role
        ).first()
    return account is not None


class RefreshTokenResource(Resource):
    """
    刷新访问令牌
    ---
    tags: [Auth]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            refresh_token: {type: string, description: 刷新令牌}
    responses:
      200: {description: 刷新成功}
      401: {description: 令牌无效或过期}
    """

    def post(self):
        from flask_jwt_extended import get_jwt

        identity = None
        revoked = {
            "status": False,
            "msg": "refresh_token 已被撤销",
            "message": "refresh_token 已被撤销",
        }

        # 兼容两种刷新方式：
        # 1) Authorization: Bearer <refresh_token>
        # 2) JSON body: {"refresh_token": "..."}
        try:
            verify_jwt_in_request(refresh=True)
            identity = get_jwt_identity()
            payload = get_jwt()
            if _refresh_token_revoked(payload):
                return revoked, 401
        except Exception:
            data = request.get_json(silent=True) or {}
            refresh_token = data.get("refresh_token")
            if not refresh_token:
                return {"status": False, "msg": "缺少 refresh_token", "message": "缺少 refresh_token"}, 401
            try:
                decoded = decode_token(refresh_token)
                if decoded.get("type") != "refresh":
                    return {"status": False, "msg": "refresh_token 无效", "message": "refresh_token 无效"}, 401
                if _refresh_token_revoked(decoded):
                    return revoked, 401
                identity = decoded.get("sub")
            except Exception:
                return {
                    "status": False,
                    "msg": "refresh_token 无效或已过期",
                    "message": "refresh_token 无效或已过期",
                }, 401

        if not identity:
            return {"status": False, "msg": "无法解析用户身份", "message": "无法解析用户身份"}, 401
        if not _refresh_identity_account_valid(identity):
            msg = "账号不存在或角色已变更，请重新登录"
            return {"status": False, "msg": msg, "message": msg}, 401

        access_token = create_access_token(identity=identity)
        refresh_token = create_refresh_token(identity=identity, additional_claims={"iat_ts": time.time()})
        return {
            "status": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "msg": "刷新成功",
            "message": "刷新成功",
        }, 200


BENCHMARK_JSON_PATH = os.path.join(BASE_DIR, "data", "benchmark_results", "robustness_benchmark.json")


class BenchmarkResultsResource(Resource):
    """Serve robustness benchmark results for the WatermarkQualityDashboard.

    Kept for frontend compatibility — the JSON moved out of the web-exposed
    ``static/`` folder (it was readable without authentication) to
    ``data/benchmark_results/``. Same response shape as before.
    """

    @jwt_required()
    def get(self):
        if not os.path.exists(BENCHMARK_JSON_PATH):
            return {
                "status": False,
                "msg": "Benchmark results not found. Run tests/benchmark_all_algorithms.py first.",
            }, 404
        try:
            with open(BENCHMARK_JSON_PATH, encoding="utf-8") as f:
                data = json.load(f)
            return {"status": True, "data": data}, 200
        except Exception as e:
            return {"status": False, "msg": str(e)}, 500


class BenchmarkStatsResource(Resource):
    """GET /api/benchmark/stats — admin. DB-backed benchmark results.

    Returns the latest imported run plus a run counter. Each ``results`` entry
    is row-compatible with the old JSON structure (summary rows carry
    ``stego_psnr``; attack rows carry attack/attack_type/nc/ber/...), so the
    quality dashboard can switch to this endpoint without changing row parsing.
    """

    @admin_required
    def get(self):
        runs_count = db.session.query(func.count(func.distinct(BenchmarkResult.run_id))).scalar() or 0
        latest = (
            BenchmarkResult.query.order_by(BenchmarkResult.created_at.desc(), BenchmarkResult.run_id.desc())
            .limit(1)
            .first()
        )
        if latest is None:
            return {"status": True, "latest_run": None, "runs_count": 0, "results": []}, 200

        rows = BenchmarkResult.query.filter_by(run_id=latest.run_id).order_by(BenchmarkResult.id.asc()).all()
        return {
            "status": True,
            "latest_run": {
                "run_id": latest.run_id,
                "created_at": latest.created_at.isoformat() if latest.created_at else None,
            },
            "runs_count": int(runs_count),
            "results": [row.to_dict() for row in rows],
        }, 200
