import datetime

from extension.extension import db
from model.Application import Application
import logging

from model.Embed_File_Record import EmbedFileRecord

from model.SendFileRecord import SendFileRecord


class EmpServer:
    def emp_get_approved_applications(self, page, page_size, user_number):
        try:
            # query = db.session.query(Application)
            # query = Application.query.filter_by(applicant_user_number=user_number, adm1_statu=True, adm2_statu=True)
            # total = query.count()

            subquery = db.session.query(EmbedFileRecord.application_id).filter(
                EmbedFileRecord.application_id == Application.id)

            query = Application.query.filter(

                Application.applicant_user_number == user_number,
                Application.adm1_statu == True,
                Application.adm2_statu == True,
                Application.id.in_(subquery),

            )

            total = query.count()

            emp_get_applications = query.offset((page - 1) * page_size).limit(page_size).all()
            pagination = {
                'has_next': page * page_size < total,
                'has_previous': page > 1,
                'next': page + 1 if page * page_size < total else None,
                'page': page,
                'page_size': page_size,
                'pages': (total + page_size - 1) // page_size,
                'previous': page - 1 if page > 1 else None,
                'total': total
            }
            return emp_get_applications, pagination
        except Exception as e:
            db.session.rollback()
            logging.error(e)
            return [], None

    def select_download_zip(self, application_id):
        query = EmbedFileRecord.query.filter_by(application_id=application_id)
        record = query.first()

        if record:
            zip_path = record.generate_file_path
            zip_name = record.generate_file_path
            return zip_path, zip_name
        else:
            return None

    def record_send_file(self, application_id, data_id, ApplicantUserNumber, send_file_person_UserNumber):
        query = SendFileRecord.query.filter_by()
