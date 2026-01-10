from ocr.paddle_ocr import run_paddleocr
from ocr.easy_ocr import run_easyocr
from ocr.deepseek_ocr import run_deepseek
from ocr.voting import ocr_voting
from ocr.benchmark import benchmark_ocr
from ocr.tesseract_ocr import run_tesseract

IMAGE_PATH = "ocr_env/images/manu2.jpg"

print("\n" + "=" * 50)
print("Running PaddleOCR...")
print("=" * 50)
paddle_data = benchmark_ocr(run_paddleocr, IMAGE_PATH)

print("\n" + "=" * 50)
# Commented out: EasyOCR disabled
# print("Running EasyOCR...")
# print("=" * 50)
# easy_data = benchmark_ocr(run_easyocr, IMAGE_PATH)

print("\n" + "=" * 50)
print("Running DeepSeek OCR...")
print("=" * 50)
deepseek_data = benchmark_ocr(run_deepseek, IMAGE_PATH)

print("\n" + "=" * 50)
print("Applying OCR Voting...")
print("=" * 50)
# Apply voting (Paddle vs DeepSeek only - EasyOCR disabled)
final_output = ocr_voting(
    paddle_data["results"],
    deepseek_results=deepseek_data["results"]
)

# Fallback to Tesseract if final OCR is empty
if not final_output:
    print("\n⚠️ Primary OCR failed. Falling back to Tesseract...")
    final_output = run_tesseract(IMAGE_PATH)

print("\nOCR BENCHMARK SUMMARY")
print("=" * 50)
print(f"PaddleOCR → Time: {paddle_data['time_sec']}s | "
      f"Lines: {paddle_data['lines']} | "
      f"Avg Conf: {paddle_data['avg_confidence']}")

print(f"EasyOCR   → Time: {easy_data['time_sec']}s | "
      f"Lines: {easy_data['lines']} | "
      f"Avg Conf: {easy_data['avg_confidence']}")

print(f"DeepSeek  → Time: {deepseek_data['time_sec']}s | "
      f"Lines: {deepseek_data['lines']} | "
      f"Avg Conf: {deepseek_data['avg_confidence']}")
print("=" * 50)

print("\n" + "=" * 50)
print("FINAL OCR RESULT")
print("=" * 50)

if not final_output:
    print("No text detected")
else:
    for item in final_output:
        print(f"{item['text']}  |  confidence: {item['confidence']:.4f}")

print("=" * 50)
