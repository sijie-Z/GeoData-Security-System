from datetime import UTC, datetime

from extension.extension import db


class BenchmarkResult(db.Model):
    """One robustness-benchmark row, imported from ``robustness_benchmark.json``.

    ``kind`` distinguishes the three row shapes the JSON uses:
    ``summary`` (per-algorithm aggregate, carries ``stego_psnr``), ``attack``
    (one attack trial — attack/attack_type/nc/ber/decode_success/...) and
    ``failure`` (embed failed — embed_error). Every metric column is nullable:
    each kind only fills its own subset of columns.
    """

    __bind_key__ = "mysql_db"
    __tablename__ = "benchmark_result"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    run_id = db.Column(db.String(36), index=True, nullable=False)
    algorithm = db.Column(db.String(32), nullable=True)
    host_type = db.Column(db.String(16), nullable=True)
    kind = db.Column(db.String(16), nullable=True)  # 'summary' | 'attack' | 'failure'
    attack = db.Column(db.String(64), nullable=True)
    attack_type = db.Column(db.String(32), nullable=True)
    attack_params = db.Column(db.JSON, nullable=True)
    embed_time = db.Column(db.Float, nullable=True)
    embed_success = db.Column(db.Boolean, nullable=True)  # TINYINT on MySQL
    embed_error = db.Column(db.String(255), nullable=True)
    stego_psnr = db.Column(db.Float, nullable=True)
    stego_ssim = db.Column(db.Float, nullable=True)
    baseline_nc = db.Column(db.Float, nullable=True)
    baseline_ber = db.Column(db.Float, nullable=True)
    nc = db.Column(db.Float, nullable=True)
    ber = db.Column(db.Float, nullable=True)
    decode_success = db.Column(db.Boolean, nullable=True)
    # decode_error exists in the JSON's attack rows; kept so the DB-backed
    # endpoint stays lossless vs the old file endpoint.
    decode_error = db.Column(db.String(255), nullable=True)
    recovery_psnr = db.Column(db.Float, nullable=True)
    recovery_perfect = db.Column(db.Boolean, nullable=True)
    wm_bit_count = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    def to_dict(self):
        """Row in the same shape as the corresponding JSON ``results`` entry."""
        if self.kind == "summary":
            return {
                "algorithm": self.algorithm,
                "host_type": self.host_type,
                "embed_time": self.embed_time,
                "embed_success": bool(self.embed_success) if self.embed_success is not None else True,
                "stego_psnr": self.stego_psnr,
                "stego_ssim": self.stego_ssim,
                "baseline_nc": self.baseline_nc,
                "baseline_ber": self.baseline_ber,
                "recovery_psnr": self.recovery_psnr,
                "recovery_perfect": bool(self.recovery_perfect) if self.recovery_perfect is not None else False,
                "wm_bit_count": self.wm_bit_count,
            }
        if self.kind == "attack":
            return {
                "algorithm": self.algorithm,
                "host_type": self.host_type,
                "attack": self.attack,
                "attack_type": self.attack_type,
                "attack_params": self.attack_params,
                "nc": self.nc,
                "ber": self.ber,
                "decode_success": bool(self.decode_success) if self.decode_success is not None else False,
                "decode_error": self.decode_error,
                "recovery_psnr": self.recovery_psnr,
                "recovery_perfect": bool(self.recovery_perfect) if self.recovery_perfect is not None else False,
            }
        return {
            "algorithm": self.algorithm,
            "embed_error": self.embed_error,
            "embed_success": bool(self.embed_success) if self.embed_success is not None else False,
        }
