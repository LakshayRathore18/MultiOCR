from ocr.paddle_ocr import run_paddleocr
from ocr.easy_ocr import run_easyocr

IMAGE_PATH = "ocr_env/images/sanskrit1.jpg"

print("\n" + "=" * 60)
print("PaddleOCR Results")
print("=" * 60)
paddle_output = run_paddleocr(IMAGE_PATH)
for i, item in enumerate(paddle_output, 1):
    print(f"{i}. {item['text']}  |  conf: {item['confidence']:.4f}")

print("\n" + "=" * 60)
print("EasyOCR Results")
print("=" * 60)
easy_output = run_easyocr(IMAGE_PATH)
for i, item in enumerate(easy_output, 1):
    print(f"{i}. {item['text']}  |  conf: {item['confidence']:.4f}")

print("\n" + "=" * 60)
print(f"PaddleOCR detected: {len(paddle_output)} lines")
print(f"EasyOCR detected: {len(easy_output)} lines")
print("=" * 60)
