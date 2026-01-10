def init_paddle_model():
    """Initialize PaddleOCR model once (for reuse)"""
    from paddleocr import PaddleOCR
    
    ocr = PaddleOCR(
        lang="hi",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False
    )
    return ocr

def run_paddleocr(image_path, model=None):
    """Run PaddleOCR and return standardized results"""
    if model is None:
        model = init_paddle_model()
    
    result = model.predict(input=image_path)
    
    output = []
    if result:
        for res in result:
            texts = res.get("rec_texts", [])
            scores = res.get("rec_scores", [])
            
            for text, score in zip(texts, scores):
                output.append({
                    "text": text,
                    "confidence": float(score)
                })
    
    return output
