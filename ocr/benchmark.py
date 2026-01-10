import time

def benchmark_ocr(ocr_func, image_path):
    start = time.time()
    results = ocr_func(image_path)
    elapsed = time.time() - start

    avg_conf = (
        sum(r["confidence"] for r in results) / len(results)
        if results else 0
    )

    return {
        "time_sec": round(elapsed, 3),
        "lines": len(results),
        "avg_confidence": round(avg_conf, 4),
        "results": results
    }
