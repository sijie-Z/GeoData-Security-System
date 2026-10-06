"""v2 QR rendering for deliveries.

``box_size`` is the E1-measured minimum that survives the real vector chain
(render -> embed -> extract -> decode -> COSE verify). E1 results on a 60-line
shp: box_size=2 with >=4 votes per embedding chunk (lambda>=4) passed; box 4/6/10
need quadratically more vertices for the same payload and are therefore not the
minimum. The delivery service enforces the lambda>=4 floor separately.
"""

import qrcode

V2_QR_BOX_SIZE = 2


def render_v2_qr_png(text, out_path, box_size=V2_QR_BOX_SIZE, error_correction=qrcode.constants.ERROR_CORRECT_M):
    """Render ``text`` as a 2D (mode "1") PNG QR code.

    Returns ``(png_path, side_length_px)`` where ``side_length_px`` is the real
    pixel edge length of the saved image (what ``algorithm.embed.embed`` will
    report back as ``side_length``).

    ``error_correction`` defaults to the delivery convention (ECC M); the
    raster robustness matrix passes ECC L at box_size=1 so the same payload
    fits the blind scheme's block budget on a 512x512 host.
    """
    qr = qrcode.QRCode(
        error_correction=error_correction,
        border=4,
        box_size=box_size,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").get_image()
    img.save(out_path, format="PNG")
    return out_path, int(img.size[0])
