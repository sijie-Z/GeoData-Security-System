"""Watermark quality metrics: PSNR, SSIM, BER, NC, capacity report."""
import numpy as np
from PIL import Image


def compute_nc(original_bits, extracted_bits):
    """Normalized Correlation between two binary arrays."""
    orig = np.array(original_bits, dtype=float)
    extr = np.array(extracted_bits, dtype=float)
    if orig.shape != extr.shape:
        min_len = min(len(orig), len(extr))
        orig = orig[:min_len]
        extr = extr[:min_len]
    if np.sum(orig) == 0 and np.sum(extr) == 0:
        return 1.0
    return float(np.dot(orig, extr) / (np.sqrt(np.dot(orig, orig)) * np.sqrt(np.dot(extr, extr)) + 1e-10))


def compute_ber(original_bits, extracted_bits):
    """Bit Error Rate."""
    orig = np.array(original_bits, dtype=int)
    extr = np.array(extracted_bits, dtype=int)
    min_len = min(len(orig), len(extr))
    orig = orig[:min_len]
    extr = extr[:min_len]
    return float(np.sum(orig != extr) / len(orig))


def compute_psnr(original_img, watermarked_img):
    """PSNR between two images (numpy arrays or PIL Images)."""
    if isinstance(original_img, Image.Image):
        original_img = np.array(original_img, dtype=np.float64)
    if isinstance(watermarked_img, Image.Image):
        watermarked_img = np.array(watermarked_img, dtype=np.float64)
    mse = np.mean((original_img - watermarked_img) ** 2)
    if mse == 0:
        return float('inf')
    return float(10 * np.log10(255.0**2 / mse))


def compute_ssim_simple(original_img, watermarked_img):
    """Simplified SSIM for grayscale or single-channel comparison."""
    if isinstance(original_img, Image.Image):
        original_img = np.array(original_img, dtype=np.float64)
    if isinstance(watermarked_img, Image.Image):
        watermarked_img = np.array(watermarked_img, dtype=np.float64)
    if original_img.ndim == 3:
        original_img = original_img.mean(axis=2)
    if watermarked_img.ndim == 3:
        watermarked_img = watermarked_img.mean(axis=2)
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2
    mu1 = original_img.mean()
    mu2 = watermarked_img.mean()
    sigma1_sq = original_img.var()
    sigma2_sq = watermarked_img.var()
    sigma12 = np.mean((original_img - mu1) * (watermarked_img - mu2))
    ssim_val = ((2*mu1*mu2 + C1) * (2*sigma12 + C2)) / ((mu1**2 + mu2**2 + C1) * (sigma1_sq + sigma2_sq + C2))
    return float(ssim_val)


def capacity_report(n_vertices, n_bits_needed, n=4):
    """Report embedding capacity utilization."""
    available_chunks = n_vertices
    needed_chunks = int(np.ceil(n_bits_needed / n))
    utilization = needed_chunks / max(available_chunks, 1) * 100
    return {
        'total_vertices': n_vertices,
        'available_chunks': available_chunks,
        'needed_chunks': needed_chunks,
        'utilization_percent': round(utilization, 2),
        'sufficient': available_chunks >= needed_chunks
    }
