import json
import os
from datetime import datetime

import numpy as np
from PIL import Image


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _to_binary_watermark(watermark_img: Image.Image, width: int, height: int) -> np.ndarray:
    wm = watermark_img.convert("L").resize((width, height), Image.Resampling.NEAREST)
    return (np.array(wm, dtype=np.uint8) > 127).astype(np.uint8)


def embed_reversible(host_path: str, watermark_img: Image.Image, output_dir: str, prefix: str) -> dict:
    _ensure_dir(output_dir)
    host_img = Image.open(host_path).convert("RGB")
    host_arr = np.array(host_img, dtype=np.uint8)
    h, w, _ = host_arr.shape
    wm_w = min(w, max(64, min(512, w)))
    wm_h = min(h, max(64, min(512, h)))
    wm_bits_2d = _to_binary_watermark(watermark_img, wm_w, wm_h)
    wm_bits = wm_bits_2d.reshape(-1)
    channel = host_arr[:, :, 0].reshape(-1).copy()
    bit_count = int(wm_bits.size)
    if bit_count > channel.size:
        raise ValueError("载体图像容量不足，无法嵌入当前水印。")
    original_values = channel[:bit_count].copy()
    embedded_values = (original_values & 0xFE) | wm_bits
    changed_mask = original_values != embedded_values
    changed_idx = np.nonzero(changed_mask)[0].astype(np.int64)
    changed_vals = original_values[changed_mask].astype(np.uint8)
    channel[:bit_count] = embedded_values
    stego_arr = host_arr.copy()
    stego_arr[:, :, 0] = channel.reshape(h, w)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    stego_path = os.path.join(output_dir, f"{prefix}_{timestamp}_stego.png")
    wm_map_path = os.path.join(output_dir, f"{prefix}_{timestamp}_wm_map.npz")
    wm_meta_path = os.path.join(output_dir, f"{prefix}_{timestamp}_wm_meta.json")
    Image.fromarray(stego_arr, mode="RGB").save(stego_path, format="PNG")
    np.savez_compressed(wm_map_path, changed_idx=changed_idx, changed_vals=changed_vals)
    meta = {
        "shape": {"height": int(h), "width": int(w), "channels": 3},
        "watermark": {
            "height": int(wm_h),
            "width": int(wm_w),
            "bit_count": bit_count
        }
    }
    with open(wm_meta_path, "w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False)
    return {
        "stego_path": stego_path,
        "wm_map_path": wm_map_path,
        "wm_meta_path": wm_meta_path,
        "bit_count": bit_count,
        "changed_count": int(changed_idx.size)
    }


def recover_reversible(stego_path: str, wm_map_path: str, wm_meta_path: str, output_path: str) -> str:
    with open(wm_meta_path, "r", encoding="utf-8") as fp:
        meta = json.load(fp)
    stego_arr = np.array(Image.open(stego_path).convert("RGB"), dtype=np.uint8)
    h = int(meta["shape"]["height"])
    w = int(meta["shape"]["width"])
    if stego_arr.shape[0] != h or stego_arr.shape[1] != w:
        raise ValueError("输入图像尺寸与元数据不一致。")
    ch0 = stego_arr[:, :, 0].reshape(-1).copy()
    wm_map = np.load(wm_map_path)
    changed_idx = wm_map["changed_idx"].astype(np.int64)
    changed_vals = wm_map["changed_vals"].astype(np.uint8)
    ch0[changed_idx] = changed_vals
    recovered = stego_arr.copy()
    recovered[:, :, 0] = ch0.reshape(h, w)
    Image.fromarray(recovered, mode="RGB").save(output_path, format="PNG")
    return output_path


def decode_reversible(stego_path: str, wm_meta_path: str, output_path: str) -> str:
    with open(wm_meta_path, "r", encoding="utf-8") as fp:
        meta = json.load(fp)
    stego_arr = np.array(Image.open(stego_path).convert("RGB"), dtype=np.uint8)
    h = int(meta["shape"]["height"])
    w = int(meta["shape"]["width"])
    wm_h = int(meta["watermark"]["height"])
    wm_w = int(meta["watermark"]["width"])
    bit_count = int(meta["watermark"]["bit_count"])
    if stego_arr.shape[0] != h or stego_arr.shape[1] != w:
        raise ValueError("输入图像尺寸与元数据不一致。")
    bits = (stego_arr[:, :, 0].reshape(-1)[:bit_count] & 0x01).astype(np.uint8)
    wm = (bits.reshape(wm_h, wm_w) * 255).astype(np.uint8)
    Image.fromarray(wm, mode="L").save(output_path, format="PNG")
    return output_path
