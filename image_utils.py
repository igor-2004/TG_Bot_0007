# image_utils.py
import io
from PIL import Image, ImageDraw, ImageFont

def overlay_id_on_image(image_bytes: bytes, text: str) -> bytes:
    # Накладывает text (обычно id) в правый нижний угол, возвращает новые байты JPEG.
    try:
        if not image_bytes:
            return image_bytes
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        W, H = img.size
        # Шрифт: попробуем загрузить системный; если нет — используем встроенный.
        font_size = max(18, W // 25)
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()
        draw = ImageDraw.Draw(img)
        padding = int(font_size * 0.4)
        text_to_draw = text

        # Точная метрика текста: используем textbbox если есть, иначе textsize
        try:
            bbox = draw.textbbox((0,0), text_to_draw, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
        except Exception:
            w, h = draw.textsize(text_to_draw, font=font)

        x = W - w - padding
        y = H - h - padding
        # полупрозрачная подложка
        rect_x0 = x - padding//2
        rect_y0 = y - padding//2
        rect_x1 = x + w + padding//2
        rect_y1 = y + h + padding//2
        overlay = Image.new("RGBA", img.size, (255,255,255,0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle((rect_x0, rect_y0, rect_x1, rect_y1), fill=(0,0,0,120))
        overlay_draw.text((x, y), text_to_draw, font=font, fill=(255,255,255,255))
        combined = Image.alpha_composite(img, overlay).convert("RGB")
        out = io.BytesIO()
        combined.save(out, format="JPEG", quality=85)
        out.seek(0)
        return out.read()
    except Exception as e:
        print("overlay error:", e)
        return image_bytes
