from datetime import UTC, datetime

from extension.extension import db


class RobustnessResult(db.Model):
    """One (scheme x attack x trial) cell of a robustness-matrix experiment run.

    A "run" is one experiment activity (one ``run_id`` = uuid4): the vector
    watermark matrix embeds the same payload with every requested scheme and
    measures every requested attack, writing one row per (scheme, attack,
    trial). Rows are pre-created with NULL metrics when the run is queued and
    updated in place when the background worker finishes (metrics NULL = still
    pending).

    ``error`` is the only column beyond the taskbook schema: it keeps a run
    that dies mid-flight (or one cell that raised) honestly visible instead of
    leaving NULL metrics that look like "still running" forever.

    ``strength_index`` (feat_strength_sweep) is the 0..4 tier of a sweep row
    and NULL on every matrix row — that NULL is what marks a run as "matrix"
    when the API derives the run's ``mode``.

    Migration: the table itself is created by ``_bootstrap_runtime_schema()``
    (app.py) via ``create_all`` on fresh installs. ``trial`` (feat_experiment_trials)
    was added after the table had already shipped, so live installs get it via
    the idempotent ``ALTER TABLE robustness_result ADD COLUMN trial INT NULL``
    in ``migrate_add_columns.py``; legacy rows keep NULL (= single-trial run).
    ``strength_index`` follows the same pattern (NULL = matrix row).
    """

    __bind_key__ = "mysql_db"
    __tablename__ = "robustness_result"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    run_id = db.Column(db.String(36), index=True, nullable=False)
    scheme = db.Column(db.String(16), nullable=False)
    attack = db.Column(db.String(32), nullable=False)
    trial = db.Column(db.Integer, nullable=True)  # 1-based; NULL = legacy single-trial row
    strength_index = db.Column(db.Integer, nullable=True)  # 0..4 tier; NULL = matrix row
    attack_params = db.Column(db.JSON, nullable=True)
    nc = db.Column(db.Float, nullable=True)
    ber = db.Column(db.Float, nullable=True)
    decode_success = db.Column(db.Boolean, nullable=True)  # TINYINT on MySQL; NULL = pending
    duration_ms = db.Column(db.Integer, nullable=True)
    data_ref = db.Column(db.String(255), nullable=True)
    error = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    def to_dict(self):
        """Row as the API returns it; booleans keep None (pending) distinct."""
        return {
            "scheme": self.scheme,
            "attack": self.attack,
            "trial": self.trial,
            "strength_index": self.strength_index,
            "attack_params": self.attack_params,
            "nc": self.nc,
            "ber": self.ber,
            "decode_success": bool(self.decode_success) if self.decode_success is not None else None,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }
