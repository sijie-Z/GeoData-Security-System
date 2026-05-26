"""
Comprehensive robustness benchmark: LSB vs DWT vs Histogram Shifting.

Tests all three reversible watermarking algorithms under identical attack
conditions (JPEG compression, Gaussian noise, cropping) and measures
PSNR, NC, BER, SSIM, and reversibility.

Outputs results as JSON for the WatermarkQualityDashboard.
"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime

import numpy as np
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── Test image generators ──────────────────────────────────────────────


def create_realistic_host(size=256):
    """Simulated terrain image with natural variation (gradients + patterns)."""
    Y, X = np.ogrid[:size, :size]
    cx, cy = size // 2, size // 2
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    base = np.clip((1 - dist / (size * 0.7)) * 200 + 30, 0, 255)

    x = np.linspace(0, 4 * np.pi, size)
    y = np.linspace(0, 4 * np.pi, size)
    Xm, Ym = np.meshgrid(x, y)
    waves = np.sin(Xm) * np.cos(Ym) * 30 + np.sin(Xm * 2.5) * np.cos(Ym * 1.8) * 20 + np.sin(Xm * 0.7 + Ym * 1.3) * 25

    spots = (
        np.exp(-((X - size * 0.3) ** 2 + (Y - size * 0.4) ** 2) / 2000) * 80
        + np.exp(-((X - size * 0.7) ** 2 + (Y - size * 0.6) ** 2) / 3000) * 60
        + np.exp(-((X - size * 0.5) ** 2 + (Y - size * 0.25) ** 2) / 1500) * 90
    )

    r = np.clip(base + waves + spots, 0, 255).astype(np.uint8)
    g = np.clip(base + waves * 0.9 + spots * 1.1 + 5, 0, 255).astype(np.uint8)
    b = np.clip(base + waves * 1.1 + spots * 0.9 - 3, 0, 255).astype(np.uint8)
    return Image.fromarray(np.stack([r, g, b], axis=-1), mode="RGB")


def create_concentrated_host(size=128):
    """Near-uniform image (simulates medical scan / document) for Histogram.
    Background value 80 covering ~98% of pixels, with a bright circular ROI."""
    arr = np.full((size, size), 80, dtype=np.uint8)
    cy, cx = size // 2, size // 2
    Y, X = np.ogrid[:size, :size]
    roi = ((X - cx) ** 2 + (Y - cy) ** 2) < (size * 0.3) ** 2
    arr[roi] = np.clip(80 + np.random.randint(20, 180, size=arr[roi].shape), 0, 255)
    # Add sparse noise pixels
    noise_mask = np.random.random((size, size)) < 0.005
    arr[noise_mask] = np.random.randint(0, 256, size=noise_mask.sum())
    rgb = np.stack([arr, arr, arr], axis=-1)
    return Image.fromarray(rgb, mode="RGB")


def create_watermark(size=64):
    """QR-code-like binary watermark pattern."""
    wm = np.zeros((size, size), dtype=np.uint8)
    # Finder patterns (3 corners)
    for ox, oy in [(0, 0), (0, size - 8), (size - 8, 0)]:
        wm[ox : ox + 8, oy : oy + 8] = 255
        wm[ox + 1 : ox + 7, oy + 1 : oy + 7] = 0
        wm[ox + 2 : ox + 6, oy + 2 : oy + 6] = 255
    # Data modules
    for i in range(8, size, 3):
        for j in range(8, size, 3):
            if (i + j) % 5 == 0:
                wm[i : min(i + 2, size), j : min(j + 2, size)] = 255
    # Timing patterns
    for j in range(8, size, 2):
        wm[6, j] = 255
        wm[j, 6] = 255
    return Image.fromarray(wm, mode="L")


# ── Metrics ────────────────────────────────────────────────────────────


def _to_bits_resized(img, target_size):
    """Resize img to target_size then convert to flat bit array."""
    resized = img.convert("L").resize(target_size, Image.Resampling.NEAREST)
    return (np.array(resized, dtype=np.uint8) > 127).astype(int).flatten()


def compute_nc(a, b):
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    if np.sum(a) == 0 and np.sum(b) == 0:
        return 1.0
    d = np.sqrt(np.dot(a, a)) * np.sqrt(np.dot(b, b))
    return float(np.dot(a, b) / d) if d > 1e-10 else 1.0


def compute_ber(a, b):
    a, b = np.array(a, dtype=int), np.array(b, dtype=int)
    n = min(len(a), len(b))
    return float(np.sum(a[:n] != b[:n]) / n)


def compute_psnr(orig, other):
    orig = np.array(orig, dtype=np.float64)
    other = np.array(other, dtype=np.float64)
    mse = np.mean((orig - other) ** 2)
    return float(10 * np.log10(255.0**2 / mse)) if mse > 1e-10 else 999.0


def compute_ssim(orig, other):
    if orig.ndim == 3:
        orig = orig.mean(axis=2)
    if other.ndim == 3:
        other = other.mean(axis=2)
    orig, other = orig.astype(np.float64), other.astype(np.float64)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    mu1, mu2 = orig.mean(), other.mean()
    s1, s2 = orig.var(), other.var()
    s12 = np.mean((orig - mu1) * (other - mu2))
    num = (2 * mu1 * mu2 + C1) * (2 * s12 + C2)
    den = (mu1**2 + mu2**2 + C1) * (s1 + s2 + C2)
    return float(num / den) if den > 1e-10 else 1.0


# ── Attack simulators ──────────────────────────────────────────────────


def attack_jpeg(img_path, quality):
    img = Image.open(img_path)
    if img.mode == "RGBA":
        img = img.convert("RGB")
    out = img_path + f"_jpeg{quality}.jpg"
    img.save(out, "JPEG", quality=quality)
    return out


def attack_noise(img_path, sigma):
    arr = np.array(Image.open(img_path).convert("RGB"), dtype=np.float64)
    noise = np.random.normal(0, sigma, arr.shape)
    noisy = np.clip(arr + noise, 0, 255).astype(np.uint8)
    out = img_path + f"_noise{sigma}.png"
    Image.fromarray(noisy).save(out, "PNG")
    return out


def attack_crop(img_path, pct):
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    cw, ch = int(w * (1 - pct)), int(h * (1 - pct))
    left, top = (w - cw) // 2, (h - ch) // 2
    cropped = img.crop((left, top, left + cw, top + ch))
    resized = cropped.resize((w, h), Image.Resampling.BILINEAR)
    out = img_path + f"_crop{int(pct * 100)}.png"
    resized.save(out, "PNG")
    return out


# ── Main benchmark routine ─────────────────────────────────────────────

ATTACKS = [
    ("JPEG q=90", "jpeg", {"quality": 90}),
    ("JPEG q=70", "jpeg", {"quality": 70}),
    ("JPEG q=50", "jpeg", {"quality": 50}),
    ("JPEG q=30", "jpeg", {"quality": 30}),
    ("Noise σ=1", "noise", {"sigma": 1}),
    ("Noise σ=3", "noise", {"sigma": 3}),
    ("Noise σ=5", "noise", {"sigma": 5}),
    ("Noise σ=10", "noise", {"sigma": 10}),
    ("Crop 5%", "crop", {"pct": 0.05}),
    ("Crop 10%", "crop", {"pct": 0.10}),
    ("Crop 25%", "crop", {"pct": 0.25}),
]


def benchmark_algorithm(alg_name, host_path, wm_img, tmp_dir, wm_size):
    """Run embed → baseline check → attacks → extract → recover."""
    results = []
    out_dir = os.path.join(tmp_dir, alg_name)
    os.makedirs(out_dir, exist_ok=True)

    # ── Import ──
    if alg_name == "LSB":
        from algorithm.raster_reversible_watermark import decode_reversible, embed_reversible, recover_reversible

        embed_fn = embed_reversible
        decode_fn = decode_reversible
        recover_fn = recover_reversible
    elif alg_name == "DWT":
        from algorithm.raster_dwt_watermark import embed_dwt, extract_dwt, recover_dwt

        embed_fn = embed_dwt
        decode_fn = extract_dwt
        recover_fn = recover_dwt
    elif alg_name == "Histogram":
        from algorithm.raster_histogram_watermark import embed_histogram, extract_histogram, recover_histogram

        embed_fn = embed_histogram
        decode_fn = extract_histogram
        recover_fn = recover_histogram

    # ── Embed ──
    t0 = time.time()
    try:
        emb = embed_fn(host_path, wm_img, out_dir, "bench")
        embed_time = time.time() - t0
    except Exception as e:
        return [{"algorithm": alg_name, "embed_error": str(e), "embed_success": False}]

    stego_path = emb["stego_path"]
    wm_meta_path = emb["wm_meta_path"]
    wm_map_path = emb.get("wm_map_path")

    # ── Stego quality ──
    host_arr = np.array(Image.open(host_path).convert("RGB"))
    stego_arr = np.array(Image.open(stego_path).convert("RGB"))
    stego_psnr = compute_psnr(host_arr, stego_arr)
    stego_ssim = compute_ssim(host_arr, stego_arr)

    # Original watermark bits (reference)
    ref_bits = _to_bits_resized(wm_img, wm_size)

    # ── Baseline extraction ──
    try:
        decoded_base = os.path.join(out_dir, "decoded_baseline.png")
        decode_fn(stego_path, wm_meta_path, decoded_base)
        ext_bits = _to_bits_resized(Image.open(decoded_base), wm_size)
        base_nc = compute_nc(ref_bits, ext_bits)
        base_ber = compute_ber(ref_bits, ext_bits)
    except Exception:
        base_nc, base_ber = None, None

    # ── Reversibility ──
    try:
        recovered_path = os.path.join(out_dir, "recovered_baseline.png")
        if alg_name == "LSB":
            recover_fn(stego_path, wm_map_path, wm_meta_path, recovered_path)
        elif alg_name == "DWT":
            recover_fn(stego_path, wm_meta_path, recovered_path)
        else:
            recover_fn(stego_path, wm_meta_path, recovered_path)
        rec_arr = np.array(Image.open(recovered_path).convert("RGB"))
        recovery_psnr = compute_psnr(host_arr, rec_arr)
        recovery_perfect = bool(np.array_equal(host_arr, rec_arr))
    except Exception:
        recovery_psnr, recovery_perfect = None, False

    # Summary
    summary = {
        "algorithm": alg_name,
        "embed_time": round(embed_time, 4),
        "embed_success": True,
        "stego_psnr": round(stego_psnr, 2),
        "stego_ssim": round(stego_ssim, 6),
        "baseline_nc": round(base_nc, 6) if base_nc is not None else None,
        "baseline_ber": round(base_ber, 6) if base_ber is not None else None,
        "recovery_psnr": round(recovery_psnr, 2) if recovery_psnr else None,
        "recovery_perfect": recovery_perfect,
        "wm_bit_count": emb.get("bit_count", emb.get("capacity", None)),
    }
    results.append(summary)

    # ── Attacks ──
    for atk_name, atk_type, atk_params in ATTACKS:
        entry = {
            "algorithm": alg_name,
            "attack": atk_name,
            "attack_type": atk_type,
            "attack_params": atk_params,
            "nc": None,
            "ber": None,
            "decode_success": False,
            "decode_error": None,
            "recovery_psnr": None,
            "recovery_perfect": False,
        }
        try:
            # Apply attack
            if atk_type == "jpeg":
                atk_path = attack_jpeg(stego_path, atk_params["quality"])
            elif atk_type == "noise":
                atk_path = attack_noise(stego_path, atk_params["sigma"])
            else:
                atk_path = attack_crop(stego_path, atk_params["pct"])

            # Extract
            slug = atk_name.replace(" ", "_").replace("=", "").replace("σ", "s")
            dec_path = os.path.join(out_dir, f"decoded_{slug}.png")
            decode_fn(atk_path, wm_meta_path, dec_path)
            ext_bits = _to_bits_resized(Image.open(dec_path), wm_size)
            entry["nc"] = round(compute_nc(ref_bits, ext_bits), 6)
            entry["ber"] = round(compute_ber(ref_bits, ext_bits), 6)
            entry["decode_success"] = True

            # Recovery
            try:
                rec_path = os.path.join(out_dir, f"recovered_{slug}.png")
                if alg_name == "LSB":
                    recover_fn(atk_path, wm_map_path, wm_meta_path, rec_path)
                elif alg_name == "DWT":
                    recover_fn(atk_path, wm_meta_path, rec_path)
                else:
                    recover_fn(atk_path, wm_meta_path, rec_path)
                rec_arr2 = np.array(Image.open(rec_path).convert("RGB"))
                entry["recovery_psnr"] = round(compute_psnr(host_arr, rec_arr2), 2)
                entry["recovery_perfect"] = bool(np.array_equal(host_arr, rec_arr2))
            except Exception:
                entry["recovery_psnr"] = None
                entry["recovery_perfect"] = False
        except Exception as e:
            entry["decode_error"] = str(e)[:200]

        results.append(entry)

    return results


# ── CLI ────────────────────────────────────────────────────────────────


def main():
    print("=" * 70)
    print("  WATERMARK ROBUSTNESS BENCHMARK — LSB vs DWT vs Histogram Shifting")
    print("=" * 70)

    all_results = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        # ── Scenario A: Natural image (LSB + DWT) ──
        print("\n── Scenario A: Natural terrain image (256×256) ──")
        host_a = create_realistic_host(256)
        host_a_path = os.path.join(tmp_dir, "host_natural.png")
        host_a.save(host_a_path, "PNG")
        wm_img = create_watermark(64)

        for alg in ["LSB", "DWT"]:
            print(f"\n  [{alg}]")
            res = benchmark_algorithm(alg, host_a_path, wm_img, tmp_dir, (64, 64))
            if res[0].get("embed_error"):
                print(f"    EMBED FAILED: {res[0]['embed_error']}")
            else:
                s = res[0]
                print(
                    f"    Embed: {s['embed_time']}s  PSNR={s['stego_psnr']}dB  "
                    f"SSIM={s['stego_ssim']}  NC={s['baseline_nc']}  "
                    f"BER={s['baseline_ber']}  Recovery={s['recovery_perfect']}"
                )
                for r in res[1:]:
                    nc_s = f"NC={r['nc']:.4f}" if r["nc"] is not None else "FAIL"
                    ber_s = f"BER={r['ber']:.4f}" if r["ber"] is not None else ""
                    print(f"      {r['attack']:16s}  {nc_s:10s}  {ber_s}")
            all_results.extend(res)

        # ── Scenario B: Concentrated histogram test ──
        print("\n── Scenario B: Concentrated image (128×128, 98% uniform) ──")
        host_b = create_concentrated_host(128)
        host_b_path = os.path.join(tmp_dir, "host_concentrated.png")
        host_b.save(host_b_path, "PNG")

        # Check histogram peak
        ch0 = np.array(host_b)[:, :, 0].ravel()
        peak_val = int(np.argmax(np.bincount(ch0, minlength=256)))
        peak_cnt = int(np.bincount(ch0, minlength=256)[peak_val])
        print(
            f"    R-channel peak: value={peak_val}, count={peak_cnt}/{128 * 128} ({100 * peak_cnt / (128 * 128):.1f}%)"
        )

        print("\n  [Histogram]")
        res_h = benchmark_algorithm("Histogram", host_b_path, wm_img, tmp_dir, (64, 64))
        if res_h[0].get("embed_error"):
            print(f"    EMBED FAILED: {res_h[0]['embed_error']}")
        else:
            s = res_h[0]
            print(
                f"    Embed: {s['embed_time']}s  PSNR={s['stego_psnr']}dB  "
                f"SSIM={s['stego_ssim']}  NC={s['baseline_nc']}  "
                f"BER={s['baseline_ber']}  Recovery={s['recovery_perfect']}"
            )
            for r in res_h[1:]:
                nc_s = f"NC={r['nc']:.4f}" if r["nc"] is not None else "FAIL"
                print(f"      {r['attack']:16s}  {nc_s}")
        all_results.extend(res_h)

        # Also run LSB + DWT on the concentrated image for fair comparison
        for alg in ["LSB", "DWT"]:
            print(f"\n  [{alg}] (on concentrated image)")
            res_c = benchmark_algorithm(alg, host_b_path, wm_img, tmp_dir, (64, 64))
            if res_c[0].get("embed_error"):
                print(f"    EMBED FAILED: {res_c[0]['embed_error']}")
            else:
                s = res_c[0]
                print(
                    f"    Embed: {s['embed_time']}s  PSNR={s['stego_psnr']}dB  "
                    f"NC={s['baseline_nc']}  Recovery={s['recovery_perfect']}"
                )
            # Tag with host type for disambiguation
            for r in res_c:
                if "attack" in r:
                    r["attack"] = r["attack"] + " [conc]"
                r["host_type"] = "concentrated"
            all_results.extend(res_c)
        # Tag histogram results too
        for r in res_h:
            if "attack" in r:
                r["attack"] = r["attack"] + " [conc]"
            r["host_type"] = "concentrated"

        # Tag natural-image results
        for r in all_results:
            if "host_type" not in r:
                r["host_type"] = "natural"

    # ── Save ──
    output_dir = os.path.join(PROJECT_ROOT, "static", "benchmark_results")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "robustness_benchmark.json")

    output = {
        "benchmark_metadata": {
            "timestamp": datetime.now().isoformat(),
            "host_images": {
                "natural": "256×256 simulated terrain (gradients + wave patterns + hotspots)",
                "concentrated": "128×128 near-uniform background (~98% at one value) with small bright ROI",
            },
            "watermark": "64×64 QR-like binary pattern",
            "metrics": ["PSNR", "SSIM", "NC", "BER", "recovery_psnr", "recovery_perfect"],
            "attacks": [
                "JPEG compression (q=90,70,50,30)",
                "Gaussian noise (σ=1,3,5,10)",
                "Crop+resize (5%,10%,25%)",
            ],
        },
        "results": all_results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # ── Print summary ──
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    # Per-algorithm summary
    for alg in ["LSB", "DWT", "Histogram"]:
        summaries = [r for r in all_results if "stego_psnr" in r and r["algorithm"] == alg]
        if not summaries:
            errs = [r for r in all_results if r["algorithm"] == alg and r.get("embed_error")]
            if errs:
                print(f"\n{alg}: EMBED FAILED — {errs[0]['embed_error'][:120]}")
            continue
        s = summaries[0]
        print(
            f"\n{alg}: PSNR={s['stego_psnr']}dB  SSIM={s['stego_ssim']}  "
            f"Baseline NC={s['baseline_nc']}  BER={s['baseline_ber']}  "
            f"Perfect recovery={s['recovery_perfect']}  Time={s['embed_time']}s"
        )

        # Attack results for this algo
        atk_rows = [
            r for r in all_results if r["algorithm"] == alg and "attack" in r and "conc" not in str(r.get("attack", ""))
        ]
        if atk_rows:
            print(f"  {'Attack':<16s} {'NC':>8s} {'BER':>8s} {'Recovery':>10s}")
            for r in atk_rows:
                nc_s = f"{r['nc']:.4f}" if r["nc"] is not None else "FAIL"
                ber_s = f"{r['ber']:.4f}" if r["ber"] is not None else "-"
                rec_s = f"{r['recovery_psnr']}dB" if r["recovery_psnr"] else "FAIL"
                print(f"  {r['attack']:<16s} {nc_s:>8s} {ber_s:>8s} {rec_s:>10s}")

    print(f"\nResults saved to: {output_path}")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
