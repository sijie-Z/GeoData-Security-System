import os
import sys
import numpy as np
from PIL import Image


def image_to_array(path):
    image = Image.open(path)
    image_array = np.array(image).astype(int)
    return image_array


def NC(original_watermark, extract_watermark):
    """Compute Normalized Correlation (NC) between two binary watermark arrays.
    If sizes differ, the smaller array is zero-padded to match the larger one.
    """
    orig = np.array(original_watermark, dtype=int)
    extr = np.array(extract_watermark, dtype=int)

    # Pad the smaller array with zeros to match sizes
    if orig.shape != extr.shape:
        max_size = max(orig.size, extr.size)
        if orig.size < max_size:
            orig = np.pad(orig.flatten(), (0, max_size - orig.size), mode='constant').reshape(extr.shape) if extr.size == max_size else np.pad(orig.flatten(), (0, max_size - orig.size), mode='constant')
        if extr.size < max_size:
            extr = np.pad(extr.flatten(), (0, max_size - extr.size), mode='constant').reshape(orig.shape) if orig.size == max_size else np.pad(extr.flatten(), (0, max_size - extr.size), mode='constant')
        # Flatten both for comparison
        orig = orig.flatten()
        extr = extr.flatten()

    if not (np.all(np.isin(orig, [0, 1])) and np.all(np.isin(extr, [0, 1]))):
        raise ValueError('Input images must be binary (0 or 1)')

    same_pixels = (orig.astype(bool) == extr.astype(bool))
    return np.sum(same_pixels) / orig.size


def BER(original_watermark, extract_watermark):
    """Compute Bit Error Rate (BER) between two binary watermark arrays.
    If sizes differ, the smaller array is zero-padded to match the larger one.
    """
    orig = np.array(original_watermark, dtype=int).flatten()
    extr = np.array(extract_watermark, dtype=int).flatten()

    # Pad the smaller array with zeros to match sizes
    if orig.size != extr.size:
        max_size = max(orig.size, extr.size)
        if orig.size < max_size:
            orig = np.pad(orig, (0, max_size - orig.size), mode='constant')
        if extr.size < max_size:
            extr = np.pad(extr, (0, max_size - extr.size), mode='constant')

    if not (np.all(np.isin(orig, [0, 1])) and np.all(np.isin(extr, [0, 1]))):
        raise ValueError('Input images must be binary (0 or 1)')

    return float(np.sum(orig != extr) / len(orig))


if __name__ == "__main__":
    original_watermark_path = "path/to/original_watermark.png"
    extract_watermark_path = "path/to/extracted_watermark.png"

    try:
        original_watermark = image_to_array(original_watermark_path)
        extract_watermark = image_to_array(extract_watermark_path)
        print(f"NC value: {NC(original_watermark, extract_watermark)}")
        print(f"BER value: {BER(original_watermark, extract_watermark)}")
    except FileNotFoundError:
        print("Error: Test files not found. Please replace with actual file paths.")
    except ValueError as e:
        print(f"Error: {e}")
