from pathlib import Path
from PIL import Image

SRC = Path(r"C:\Users\Mauro\.gemini\antigravity-ide\brain\77e6be95-cbca-4f94-8f0f-54b363cf5354\.user_uploaded\media_1790123145706.png")
PWA_PUB = Path(r"c:\Users\Mauro\Proyectos\Fildlab\pwa\public")
FRONT_PUB = Path(r"c:\Users\Mauro\Proyectos\Fildlab\frontend\public")

def process_icons():
    img = Image.open(SRC).convert("RGBA")
    
    # 1. PWA Icons
    PWA_PUB.mkdir(parents=True, exist_ok=True)
    img.resize((192, 192), Image.Resampling.LANCZOS).save(PWA_PUB / "icon-192.png", "PNG")
    img.resize((512, 512), Image.Resampling.LANCZOS).save(PWA_PUB / "icon-512.png", "PNG")
    img.resize((180, 180), Image.Resampling.LANCZOS).save(PWA_PUB / "apple-touch-icon.png", "PNG")
    img.resize((64, 64), Image.Resampling.LANCZOS).save(PWA_PUB / "favicon.png", "PNG")
    img.resize((512, 512), Image.Resampling.LANCZOS).save(PWA_PUB / "logo.png", "PNG")
    
    # 2. Frontend Icons
    FRONT_PUB.mkdir(parents=True, exist_ok=True)
    img.resize((512, 512), Image.Resampling.LANCZOS).save(FRONT_PUB / "logo.png", "PNG")
    img.resize((64, 64), Image.Resampling.LANCZOS).save(FRONT_PUB / "favicon.png", "PNG")
    
    print("[+] Iconos y logos generados exitosamente para PWA y Frontend.")

if __name__ == "__main__":
    process_icons()
