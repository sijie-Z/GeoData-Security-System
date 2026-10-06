from extension.extension import db


class EvidenceEvent(db.Model):
    """Append-only hash-chained evidence event (one row = one chain node).

    ``payload_cbor`` stores the canonical-CBOR event body that ``event_hash``
    commits to; ``signature`` is Ed25519 over the 32 raw bytes of ``event_hash``.
    """

    __bind_key__ = "mysql_db"
    __tablename__ = "evidence_event"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    stream_id = db.Column(db.String(64), index=True)
    seq = db.Column(db.Integer)
    event_type = db.Column(db.String(64))
    payload_cbor = db.Column(db.LargeBinary)
    prev_hash = db.Column(db.String(64))
    event_hash = db.Column(db.String(64), unique=True)
    signature = db.Column(db.LargeBinary)
    kid = db.Column(db.Integer)
    ts = db.Column(db.DateTime)

    __table_args__ = (db.UniqueConstraint("stream_id", "seq", name="uq_evidence_stream_seq"),)
