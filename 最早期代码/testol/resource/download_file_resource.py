from datetime import datetime
from extension.extension import db

from flask_restful import Resource
from model.Download_Record import DownloadFileRecord

from flask import request, jsonify


class RecordDownload(Resource):
    def post(self):
        data = request.get_json()

        if data:
            record_download = DownloadFileRecord(
                application_id=data.get("application_id"),
                data_id=data.get("data_id"),
                Send_file_person=data.get("send_file_person_user_number"),
                Download_File_Name=data.get("fileName"),
                Download_File_Person=data.get("applicant"),
                Download_Time=datetime.now().strftime('%Y%m%d%H%M%S'),
            )

            print(data.get("applicant"))

            db.session.add(record_download)
            db.session.commit()

            return jsonify({"status": "下载记录录入成功"})

        else:
            return jsonify({"status": "下载记录录入失败"})
