from datetime import datetime
import base64
import json
from extension.extension import db


class Application(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'application'

    # Basic Info
    id = db.Column(db.Integer, primary_key=True)
    data_id = db.Column(db.Integer, nullable=False)
    data_name = db.Column(db.String(255), nullable=False)
    data_alias = db.Column(db.String(255), nullable=False)
    data_url = db.Column(db.String(500), nullable=True)
    data_type = db.Column(db.String(50), nullable=True)  # 'vector' or 'raster'
    applicant_name = db.Column(db.String(255), nullable=False)
    applicant_user_number = db.Column(db.String(255), nullable=False)
    reason = db.Column(db.String(5000), nullable=False)

    # First Review (adm1)
    adm1_user_number = db.Column(db.String(255), nullable=True)
    adm1_name = db.Column(db.String(255), nullable=True)
    adm1_statu = db.Column(db.Boolean, nullable=True)  # null=pending, true=pass, false=fail
    adm1_approval_time = db.Column(db.DateTime)

    # Second Review (adm2)
    adm2_user_number = db.Column(db.String(255), nullable=True)
    adm2_name = db.Column(db.String(255), nullable=True)
    adm2_statu = db.Column(db.Boolean, nullable=True)  # null=pending, true=pass, false=fail
    adm2_approval_time = db.Column(db.DateTime)

    # Watermark Status
    watermark_generated = db.Column(db.Boolean, default=False)
    watermark_embedded = db.Column(db.Boolean, default=False)

    # Watermark Data
    qrcode = db.Column('QRcode', db.Text, nullable=True)  # 映射到MySQL中的QRcode列
    watermark_path = db.Column(db.String(500), nullable=True)
    watermark_path_meta = db.Column(db.String(500), nullable=True)
    watermark_path_map = db.Column(db.String(500), nullable=True)
    vr_data = db.Column(db.Text, nullable=True)

    # Watermark Metadata (NEW)
    purpose = db.Column(db.String(500), nullable=True)
    usage_scope = db.Column(db.String(255), nullable=True)
    security_level = db.Column(db.String(50), nullable=True, default='normal')  # 'normal', 'internal', 'sensitive'
    custom_tag = db.Column(db.String(255), nullable=True)
    qr_version = db.Column(db.Integer, nullable=True)
    qr_signature = db.Column(db.Text, nullable=True)
    generation_timestamp = db.Column(db.DateTime, nullable=True)

    # Recall Status (NEW)
    is_recalled = db.Column(db.Boolean, default=False)
    recalled_at = db.Column(db.DateTime, nullable=True)
    recall_reason = db.Column(db.Text, nullable=True)
    download_enabled = db.Column(db.Boolean, default=True)

    # Timestamps
    application_submission_time = db.Column(db.DateTime, default=datetime.utcnow)

    # Database indexes for query performance
    __table_args__ = (
        db.Index('idx_applicant_user_number', 'applicant_user_number'),
        db.Index('idx_adm1_statu', 'adm1_statu'),
        db.Index('idx_adm2_statu', 'adm2_statu'),
        db.Index('idx_data_type', 'data_type'),
        db.Index('idx_is_recalled', 'is_recalled'),
        db.Index('idx_submission_time', 'application_submission_time'),
    )

    def to_dict(self):
        qr_data = self.qrcode
        if isinstance(qr_data, bytes):
            qr_data = base64.b64encode(qr_data).decode('utf-8')

        return {
            'id': self.id,
            'data_id': self.data_id,
            'data_name': self.data_name,
            'data_alias': self.data_alias,
            'data_url': self.data_url,
            'data_type': self.data_type,
            'applicant_name': self.applicant_name,
            'applicant_user_number': self.applicant_user_number,
            'reason': self.reason,
            # First Review
            'adm1_user_number': self.adm1_user_number,
            'adm1_name': self.adm1_name,
            'first_statu': self.adm1_statu,
            'adm1_approval_time': self.adm1_approval_time.isoformat() if self.adm1_approval_time else None,
            # Second Review
            'adm2_user_number': self.adm2_user_number,
            'adm2_name': self.adm2_name,
            'second_statu': self.adm2_statu,
            'adm2_approval_time': self.adm2_approval_time.isoformat() if self.adm2_approval_time else None,
            # Watermark
            'watermark_generated': self.watermark_generated,
            'watermark_embedded': self.watermark_embedded,
            'qrcode': qr_data or '',
            'watermark_path': self.watermark_path,
            # Watermark Metadata
            'purpose': self.purpose,
            'usage_scope': self.usage_scope,
            'security_level': self.security_level,
            'custom_tag': self.custom_tag,
            'qr_version': self.qr_version,
            'qr_signature': self.qr_signature,
            'generation_timestamp': self.generation_timestamp.isoformat() if self.generation_timestamp else None,
            # Recall Status
            'is_recalled': self.is_recalled,
            'recalled_at': self.recalled_at.isoformat() if self.recalled_at else None,
            'recall_reason': self.recall_reason,
            'download_enabled': self.download_enabled,
            # Timestamps
            'application_submission_time': self.application_submission_time.isoformat() if self.application_submission_time else None
        }

    def to_simple_dict(self):
        """Simplified dict for list views"""
        return {
            'id': self.id,
            'data_alias': self.data_alias,
            'data_type': self.data_type,
            'applicant_name': self.applicant_name,
            'applicant_user_number': self.applicant_user_number,
            'reason': self.reason,
            'status': self._get_status(),
            'is_recalled': self.is_recalled,
            'download_enabled': self.download_enabled,
            'application_time': self.application_submission_time.strftime('%Y-%m-%d %H:%M:%S') if self.application_submission_time else None
        }

    def _get_status(self):
        if self.is_recalled:
            return 'recalled'
        if self.adm2_statu is True:
            return 'approved'
        if self.adm2_statu is False:
            return 'rejected'
        if self.adm1_statu is True:
            return 'adm1_approved'
        if self.adm1_statu is False:
            return 'adm1_rejected'
        return 'pending'
