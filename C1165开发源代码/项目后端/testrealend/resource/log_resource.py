# resource/log_resource.py
from flask import request
from flask_restful import Resource
# from flask_jwt_extended import jwt_required # 如果这个接口需要登录保护，取消注释

# 【重要】将你在Vue组件中修改和丰富后的 mockLogData 数组完整地复制到这里
# （包含20条记录，时间更新到2025年，IP地址为127.0.0.1或::1）
mock_log_data_from_backend = [
    { 'id': 1, 'timestamp': '2025-06-15 10:30:05', 'username': 'adm1', 'ip_address': '127.0.0.1', 'action': '审批数据申请', 'status': '成功', 'details': { 'request_id': 101, 'applicant': '张三丰', 'decision': '通过', 'shp_name': '苏州市商业区划' } },
    { 'id': 2, 'timestamp': '2025-06-15 09:15:22', 'username': 'employee_gis', 'ip_address': '127.0.0.1', 'action': '提交数据申请', 'status': '成功', 'details': { 'data_id': 205, 'data_name': '长江流域水系', 'reason': '年度报告分析' } },
    { 'id': 3, 'timestamp': '2025-06-14 17:05:00', 'username': 'employee_data', 'ip_address': '127.0.0.1', 'action': '用户登录', 'status': '成功', 'details': None },
    { 'id': 4, 'timestamp': '2025-06-14 16:30:15', 'username': 'adm1', 'ip_address': '127.0.0.1', 'action': '嵌入水印', 'status': '成功', 'details': { 'data_id': 203, 'data_name': '全国高速公路网', 'applicant': '李四' } },
    { 'id': 5, 'timestamp': '2025-06-14 14:20:45', 'username': 'adm1', 'ip_address': '127.0.0.1', 'action': '生成水印', 'status': '成功', 'details': { 'request_id': 98, 'for_data': '城市绿地分布' } },
    { 'id': 6, 'timestamp': '2025-06-13 11:00:30', 'username': 'guest_user', 'ip_address': '127.0.0.1', 'action': '用户登录', 'status': '失败', 'details': { 'reason': '密码连续错误三次，账户已锁定' } },
    { 'id': 7, 'timestamp': '2025-06-13 10:50:10', 'username': 'adm2', 'ip_address': '127.0.0.1', 'action': '审批数据申请', 'status': '驳回', 'details': { 'request_id': 95, 'applicant': '王五', 'reason': '申请信息不完整', 'shp_name': '土地利用类型' } },
    { 'id': 8, 'timestamp': '2025-06-12 15:00:00', 'username': 'employee_gis', 'ip_address': '127.0.0.1', 'action': '数据上传', 'status': '成功', 'details': { 'filename': 'new_district_plan.zip', 'size': '5.2MB' } },
    { 'id': 9, 'timestamp': '2025-06-12 14:30:00', 'username': 'adm1', 'ip_address': '127.0.0.1', 'action': '用户权限修改', 'status': '成功', 'details': { 'target_user': 'employee_data', 'new_role': '高级分析员' } },
    { 'id': 10, 'timestamp': '2025-06-11 18:00:00', 'username': 'system_batch', 'ip_address': '::1', 'action': '数据备份', 'status': '成功', 'details': { 'target': 'PostGIS_DB', 'duration': '35min' } },
    { 'id': 11, 'timestamp': '2025-05-20 10:00:00', 'username': 'employee_data', 'ip_address': '127.0.0.1', 'action': '提交数据申请', 'status': '成功', 'details': { 'data_id': 199, 'data_name': '历史气象站点数据', 'reason': '气候变化研究' } },
    { 'id': 12, 'timestamp': '2025-05-19 11:30:00', 'username': 'adm1', 'ip_address': '127.0.0.1', 'action': '系统参数配置', 'status': '成功', 'details': { 'parameter': 'session_timeout', 'new_value': '60min' } },
    { 'id': 13, 'timestamp': '2025-05-18 16:45:00', 'username': 'test_user_01', 'ip_address': '127.0.0.1', 'action': '用户登录', 'status': '成功', 'details': None },
    { 'id': 14, 'timestamp': '2025-05-18 09:00:00', 'username': 'employee_gis', 'ip_address': '127.0.0.1', 'action': '提取水印', 'status': '成功', 'details': { 'data_id': 180, 'data_name': '受保护区域影像' } },
    { 'id': 15, 'timestamp': '2025-05-17 14:00:00', 'username': 'adm2', 'ip_address': '127.0.0.1', 'action': '审批数据申请', 'status': '通过', 'details': { 'request_id': 88, 'applicant': '赵六', 'decision': '部分通过', 'shp_name': '季度销售数据' } },
    { 'id': 16, 'timestamp': '2025-06-16 11:00:00', 'username': 'adm1', 'ip_address': '127.0.0.1', 'action': '用户登出', 'status': '成功', 'details': None },
    { 'id': 17, 'timestamp': '2025-06-16 10:55:00', 'username': 'employee_sec', 'ip_address': '127.0.0.1', 'action': '安全策略更新', 'status': '成功', 'details': { 'policy_id': 'SEC-003', 'description': '增强密码复杂度要求' } },
    { 'id': 18, 'timestamp': '2025-06-16 09:30:00', 'username': 'employee_gis', 'ip_address': '127.0.0.1', 'action': '下载数据', 'status': '成功', 'details': { 'data_id': 210, 'data_name': '地形DEM数据', 'format': 'GeoTIFF' } },
    { 'id': 19, 'timestamp': '2025-06-15 18:00:00', 'username': 'data_analyst', 'ip_address': '127.0.0.1', 'action': '生成报告', 'status': '成功', 'details': { 'report_name': '月度空间数据使用分析', 'period': '2025-05' } },
    { 'id': 20, 'timestamp': '2025-06-15 17:30:00', 'username': 'adm1', 'ip_address': '127.0.0.1', 'action': '删除用户', 'status': '成功', 'details': { 'deleted_user': 'temp_user002', 'reason': '账户过期' } },
]

class SystemLogResource(Resource):
    # @jwt_required() # 如果需要登录验证，取消此行注释
    def get(self):
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 10)) # 保持与前端 pageSize ref 的初始值一致
            username_filter = request.args.get('username', None)
            action_filter = request.args.get('action', None)

            current_logs = mock_log_data_from_backend
            if username_filter:
                current_logs = [log for log in current_logs if username_filter.lower() in log['username'].lower()]
            if action_filter:
                current_logs = [log for log in current_logs if log['action'] == action_filter]
            
            total_logs = len(current_logs)

            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paginated_logs = current_logs[start_index:end_index]

            total_pages = (total_logs + page_size - 1) // page_size if page_size > 0 else 0
            if total_pages == 0 and total_logs > 0: # 如果有数据但不足一页，也算1页
                total_pages = 1


            return {
                'data': {
                    'list': paginated_logs,
                    'total': total_logs,
                    'page': page,
                    'pageSize': page_size,
                    'pages': total_pages
                },
                'msg': '日志获取成功',
                'status': True
            }, 200

        except Exception as e:
            # 打印详细错误到后端控制台
            import traceback
            traceback.print_exc()
            return {'msg': f'获取日志失败: {str(e)}', 'status': False, 'data': None}, 500