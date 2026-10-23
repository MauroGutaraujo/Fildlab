import base64
from io import BytesIO

from PIL import Image, ImageDraw


def firma_png(*, color="black", size=(100, 40), fondo="white", vacia=False, formato="PNG"):
    image = Image.new("RGBA", size, fondo)
    if not vacia:
        ImageDraw.Draw(image).line([(5, 25), (30, 10), (60, 30), (90, 10)], fill=color, width=3)
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format=formato) if formato == "JPEG" else image.save(buffer, format=formato)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
