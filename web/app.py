import os
import sys
import json
from datetime import timedelta
from contextlib import asynccontextmanager
import concurrent.futures

# CRITICAL: Set PaddleOCR environment variables BEFORE any imports
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'
os.environ['PADDLEOCR_MODEL_HUB'] = 'false'
os.environ['PADDLE_DISABLE_CPP_EXTENSION'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ocr.paddle_ocr import run_paddleocr, init_paddle_model
from ocr.easy_ocr import run_easyocr, init_easy_model
from ocr.deepseek_ocr import run_deepseek, init_deepseek_model
from ocr.voting import ocr_voting
from ocr.benchmark import benchmark_ocr
from ocr.normalize import validate_ocr_text

# Import database and CER modules
from database.db import get_db
from utils.cer import compute_cer
from similarity.embeddings import embed_text
from similarity.search import find_similar_documents

# FastAPI imports
from fastapi import FastAPI, Request, File, UploadFile, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from typing import Optional

# Setup directories relative to app
web_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(web_dir)
uploads_dir = os.path.join(root_dir, 'uploads')

# Global variables for OCR models
paddle_model = None
easy_model = None
deepseek_model = None
postocr_corrector = None

# Context manager for app startup model loading (lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    global paddle_model, easy_model, deepseek_model, postocr_corrector
    
    # Create uploads directory if not exists
    os.makedirs(uploads_dir, exist_ok=True)
    print("✓ Directories verified")
    
    print("Initializing OCR models...")
    try:
        paddle_model = init_paddle_model()
        print("✓ PaddleOCR loaded successfully!")
    except Exception as e:
        print(f"⚠️  Warning: PaddleOCR failed to load: {e}")
        print("   The app will run with limited functionality.")

    try:
        easy_model = init_easy_model()
        print("✓ EasyOCR loaded successfully!")
    except Exception as e:
        print(f"⚠️  Warning: EasyOCR failed to load: {e}")

    try:
        deepseek_model = init_deepseek_model()
        if deepseek_model:
            print("✓ DeepSeek OCR loaded successfully!")
    except Exception as e:
        print(f"⚠️  Warning: DeepSeek failed to load: {e}")
        print("   DeepSeek OCR will not be available.")

    # Initialize PostOCR correction module
    print("\n📚 Initializing PostOCR correction module...")
    try:
        from postocr_integration import get_corrector
        postocr_corrector = get_corrector()
        print("✓ PostOCR trie built with all words!")
    except Exception as e:
        print(f"⚠️  Warning: PostOCR failed to initialize: {e}")
        print("   Text correction will not be available.")

    if paddle_model or easy_model or deepseek_model:
        print("\n✅ OCR models loaded successfully!")
    else:
        print("\n⚠️  Warning: No OCR models loaded. App may have limited functionality.")
        
    yield
    # Clean up on shutdown if needed
    print("Shutting down MultiOCR application...")

# Initialize FastAPI App
app = FastAPI(
    title="Multi-Model OCR API",
    description="Advanced Document Text Extraction with PaddleOCR, EasyOCR, and DeepSeekOCR",
    lifespan=lifespan
)

# Session Middleware Configuration (equivalent to Flask signed cookies)
app.add_middleware(
    SessionMiddleware, 
    secret_key="multiocr-secret-key-2025",
    max_age=24 * 3600 # 24 hours
)

# Templates & Static Files
templates = Jinja2Templates(directory=os.path.join(web_dir, 'templates'))
app.mount("/static", StaticFiles(directory=os.path.join(web_dir, 'static')), name="static")


# Pydantic schemas for request validation
class ProcessRequest(BaseModel):
    filepath: str
    mode: str = 'paddleocr'
    image_hash: Optional[str] = None
    force_reprocess: bool = False


class CorrectRequest(BaseModel):
    text: str
    doc_id: Optional[int] = None
    confidence_threshold: str = 'MEDIUM'

class DetectRequest(BaseModel):
    text: str

class AddToDictionaryRequest(BaseModel):
    original_word: Optional[str] = None
    corrected_word: Optional[str] = None
    incorrect: Optional[str] = None
    correct: Optional[str] = None

class SaveCorrectionRequest(BaseModel):
    corrected_text: str
    status: str = 'corrected'


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def compact_results_for_session(results):
    """Create a compact copy of OCR results to fit inside browser cookie session limits (<4KB)"""
    if not results:
        return None
    compact = {
        'success': results.get('success'),
        'mode': results.get('mode'),
        'devanagari_quality': results.get('devanagari_quality'),
        'text': results.get('text'),
        'full_text': results.get('full_text'),
        'doc_id': results.get('doc_id'),
        'version': results.get('version'),
        'is_reprocess': results.get('is_reprocess'),
        'reused_existing': results.get('reused_existing'),
        'message': results.get('message'),
        'cer': results.get('cer')
    }
    if 'benchmark' in results and results['benchmark']:
        compact_bench = {}
        for engine, data in results['benchmark'].items():
            if data:
                compact_bench[engine] = {
                    'time': data.get('time'),
                    'lines': data.get('lines'),
                    'avg_confidence': data.get('avg_confidence')
                }
        compact['benchmark'] = compact_bench
    return compact


# Server-side in-memory session store to bypass 4KB cookie size limits
TEMP_SESSION_STORE = {
    'current_doc_id': None,
    'current_filename': None,
    'current_filepath': None,
    'current_image_hash': None,
    'current_status': None,
    'current_ocr_results': None
}


# ----------------------------------------------------
# Route Handlers
# ----------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Serve the main upload/process dashboard"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get('/api/session-data')
def get_session_data(request: Request):
    """Get persisted session data for current document"""
    return {
        'has_session': bool(TEMP_SESSION_STORE.get('current_filepath')),
        'filename': TEMP_SESSION_STORE.get('current_filename'),
        'filepath': TEMP_SESSION_STORE.get('current_filepath'),
        'doc_id': TEMP_SESSION_STORE.get('current_doc_id'),
        'status': TEMP_SESSION_STORE.get('current_status'),
        'ocr_results': TEMP_SESSION_STORE.get('current_ocr_results')
    }


@app.post('/api/clear-session')
def clear_session(request: Request):
    """Clear active document session data from server"""
    TEMP_SESSION_STORE['current_doc_id'] = None
    TEMP_SESSION_STORE['current_filename'] = None
    TEMP_SESSION_STORE['current_filepath'] = None
    TEMP_SESSION_STORE['current_image_hash'] = None
    TEMP_SESSION_STORE['current_status'] = None
    TEMP_SESSION_STORE['current_ocr_results'] = None
    return {'success': True, 'message': 'Session cleared successfully'}


@app.get('/favicon.ico', include_in_schema=False)
def favicon():
    """Silence browser favicon 404 logs"""
    return Response(status_code=204)


@app.post('/upload')
def upload_file(request: Request, file: UploadFile = File(...)):
    """Handle image uploads and save locally"""
    if not file or not file.filename:
        return JSONResponse(status_code=400, content={'error': 'No file provided'})
    
    if not allowed_file(file.filename):
        return JSONResponse(status_code=400, content={'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, BMP, TIFF'})
    
    # Read file bytes
    file_bytes = file.file.read()
    
    from werkzeug.utils import secure_filename
    filename = secure_filename(file.filename)
    filepath = os.path.join(uploads_dir, filename)
    
    # Save the file
    with open(filepath, "wb") as f:
        f.write(file_bytes)
    
    # Store standard relative path for web access and database entry
    db_filepath = f"uploads/{filename}"
    
    # New document session setup
    TEMP_SESSION_STORE['current_doc_id'] = None
    TEMP_SESSION_STORE['current_filename'] = filename
    TEMP_SESSION_STORE['current_filepath'] = db_filepath
    TEMP_SESSION_STORE['current_status'] = 'uploaded'
    TEMP_SESSION_STORE['current_ocr_results'] = None
    
    return {
        'success': True,
        'filename': filename,
        'filepath': db_filepath
    }


@app.post('/process')
def process_ocr(request: Request, data: ProcessRequest):
    """Run OCR pipeline concurrently using ThreadPoolExecutor"""
    filepath = data.filepath
    mode = data.mode
    image_hash = data.image_hash
    force_reprocess = data.force_reprocess
    
    # Resolve absolute path for processing
    abs_filepath = filepath
    if not os.path.isabs(filepath):
        abs_filepath = os.path.join(root_dir, filepath)
        
    if not filepath or not os.path.exists(abs_filepath):
        return JSONResponse(status_code=404, content={'error': 'File not found'})
    
    session = request.session
    

    
    try:
        if mode == 'paddleocr':
            if paddle_model is None:
                return JSONResponse(status_code=500, content={'error': 'PaddleOCR model not available.'})
            
            paddle_data = benchmark_ocr(lambda path: run_paddleocr(path, paddle_model), abs_filepath)
            final_output = paddle_data["results"]
            
            full_text = '\n'.join([item['text'] for item in final_output])
            quality_metrics = validate_ocr_text(full_text)
            
            results = {
                'success': True,
                'mode': 'paddleocr',
                'benchmark': {
                    'paddleocr': {
                        'time': paddle_data['time_sec'],
                        'lines': paddle_data['lines'],
                        'avg_confidence': paddle_data['avg_confidence']
                    }
                },
                'devanagari_quality': {
                    'score': round(quality_metrics['quality_score'], 4),
                    'issues_found': len(quality_metrics['issues']),
                    'devanagari_chars': quality_metrics['devanagari_chars']
                },
                'text': [
                    {
                        'text': item['text'],
                        'confidence': round(item['confidence'], 4)
                    }
                    for item in final_output
                ],
                'full_text': full_text
            }
        elif mode == 'deepseek':
            if deepseek_model is None:
                return JSONResponse(status_code=500, content={'error': 'DeepSeek model not available.'})
            
            deepseek_data = benchmark_ocr(lambda path: run_deepseek(path, deepseek_model), abs_filepath)
            final_output = deepseek_data["results"]
            
            full_text = '\n'.join([item['text'] for item in final_output])
            quality_metrics = validate_ocr_text(full_text)
            
            results = {
                'success': True,
                'mode': 'deepseek',
                'benchmark': {
                    'deepseek': {
                        'time': deepseek_data['time_sec'],
                        'lines': deepseek_data['lines'],
                        'avg_confidence': deepseek_data['avg_confidence']
                    }
                },
                'devanagari_quality': {
                    'score': round(quality_metrics['quality_score'], 4),
                    'issues_found': len(quality_metrics['issues']),
                    'devanagari_chars': quality_metrics['devanagari_chars']
                },
                'text': [
                    {
                        'text': item['text'],
                        'confidence': round(item['confidence'], 4)
                    }
                    for item in final_output
                ],
                'full_text': full_text
            }
        elif mode == 'easyocr':
            if easy_model is None:
                return JSONResponse(status_code=500, content={'error': 'EasyOCR model not available.'})
            
            easy_data = benchmark_ocr(lambda path: run_easyocr(path, easy_model), abs_filepath)
            final_output = easy_data["results"]
            
            full_text = '\n'.join([item['text'] for item in final_output])
            quality_metrics = validate_ocr_text(full_text)
            
            results = {
                'success': True,
                'mode': 'easyocr',
                'benchmark': {
                    'easyocr': {
                        'time': easy_data['time_sec'],
                        'lines': easy_data['lines'],
                        'avg_confidence': easy_data['avg_confidence']
                    }
                },
                'devanagari_quality': {
                    'score': round(quality_metrics['quality_score'], 4),
                    'issues_found': len(quality_metrics['issues']),
                    'devanagari_chars': quality_metrics['devanagari_chars']
                },
                'text': [
                    {
                        'text': item['text'],
                        'confidence': round(item['confidence'], 4)
                    }
                    for item in final_output
                ],
                'full_text': full_text
            }
        else:
            # MultiOCR mode: Run Paddle + EasyOCR + DeepSeek (show metrics, run voting)
            if paddle_model is None:
                return JSONResponse(status_code=500, content={'error': 'PaddleOCR required.'})
            
            max_workers = 1 + (1 if easy_model else 0) + (1 if deepseek_model else 0)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                paddle_future = executor.submit(benchmark_ocr, lambda path: run_paddleocr(path, paddle_model), abs_filepath)
                easy_future = executor.submit(benchmark_ocr, lambda path: run_easyocr(path, easy_model), abs_filepath) if easy_model else None
                deepseek_future = executor.submit(benchmark_ocr, lambda path: run_deepseek(path, deepseek_model), abs_filepath) if deepseek_model else None
                
                paddle_data = paddle_future.result()
                easy_data = easy_future.result() if easy_future else None
                deepseek_data = deepseek_future.result() if deepseek_future else None
            
            # Run ensemble voting
            deepseek_results_for_voting = deepseek_data["results"] if deepseek_data else None
            final_output = ocr_voting(
                paddle_data["results"],
                deepseek_results=deepseek_results_for_voting
            )
            
            # Fallback
            if not final_output:
                final_output = paddle_data["results"]

            full_text = '\n'.join([item['text'] for item in final_output])
            quality_metrics = validate_ocr_text(full_text)
            
            # Build benchmark dictionary with all available metrics
            benchmark_dict = {
                'paddleocr': {
                    'time': paddle_data['time_sec'],
                    'lines': paddle_data['lines'],
                    'avg_confidence': paddle_data['avg_confidence']
                }
            }
            if easy_data:
                benchmark_dict['easyocr'] = {
                    'time': easy_data['time_sec'],
                    'lines': easy_data['lines'],
                    'avg_confidence': easy_data['avg_confidence']
                }
            if deepseek_data:
                benchmark_dict['deepseek'] = {
                    'time': deepseek_data['time_sec'],
                    'lines': deepseek_data['lines'],
                    'avg_confidence': deepseek_data['avg_confidence']
                }
            
            results = {
                'success': True,
                'mode': 'multiocr',
                'benchmark': benchmark_dict,
                'devanagari_quality': {
                    'score': round(quality_metrics['quality_score'], 4),
                    'issues_found': len(quality_metrics['issues']),
                    'devanagari_chars': quality_metrics['devanagari_chars']
                },
                'text': [
                    {
                        'text': item['text'],
                        'confidence': round(item['confidence'], 4),
                        'source': item.get('source', 'unknown')
                    }
                    for item in final_output
                ],
                'full_text': full_text
            }
        
        # Check text-similarity fallback (85% Levenshtein ratio matching threshold)
        text_for_match = results['full_text'].strip()
        matched_doc = None
        
        if text_for_match and not force_reprocess:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                """SELECT id, ocr_text, corrected_text, status, version, image_path, cer 
                   FROM documents 
                   WHERE ocr_text IS NOT NULL OR corrected_text IS NOT NULL
                   ORDER BY id DESC"""
            )
            rows = cur.fetchall()
            conn.close()
            
            import Levenshtein
            for db_doc_id, db_ocr, db_corrected, db_status, db_version, db_image_path, db_cer in rows:
                db_text = (db_corrected or db_ocr or '').strip()
                if not db_text:
                    continue
                # Calculate Levenshtein similarity ratio
                sim = Levenshtein.ratio(text_for_match, db_text)
                if sim >= 0.85:
                    print(f"🎯 Text-similarity match! doc_id: {db_doc_id} similarity: {sim:.4f}")
                    matched_doc = (db_doc_id, db_ocr, db_corrected, db_status, db_version, db_image_path, db_cer)
                    break
                    
        if matched_doc:
            db_doc_id, db_ocr, db_corrected, db_status, db_version, db_image_path, db_cer = matched_doc
            
            if db_corrected:
                ocr_results = {
                    'success': True,
                    'reused_existing': True,
                    'doc_id': db_doc_id,
                    'full_text': db_corrected,
                    'status': db_status,
                    'version': db_version,
                    'cer': round(db_cer, 4) if db_cer else None,
                    'message': '🎯 Image matched via text similarity! Reusing previous verified corrections.',
                    'text': [{'text': line, 'confidence': 1.0} for line in db_corrected.split('\n') if line.strip()]
                }
            else:
                ocr_results = {
                    'success': True,
                    'reused_existing': True,
                    'doc_id': db_doc_id,
                    'full_text': db_ocr,
                    'status': db_status,
                    'version': db_version,
                    'message': '🎯 Image matched via text similarity! Reusing previous OCR results.',
                    'text': [{'text': line, 'confidence': 0.0} for line in db_ocr.split('\n') if line.strip()]
                }
            
            # Store in session
            TEMP_SESSION_STORE['current_doc_id'] = db_doc_id
            TEMP_SESSION_STORE['current_filepath'] = filepath
            TEMP_SESSION_STORE['current_image_hash'] = image_hash
            TEMP_SESSION_STORE['current_status'] = db_status
            TEMP_SESSION_STORE['current_ocr_results'] = ocr_results
            return ocr_results
            
        # DO NOT save document to database yet. It will be saved when user clicks 'Review'.
        TEMP_SESSION_STORE['current_doc_id'] = None
        TEMP_SESSION_STORE['current_filepath'] = filepath
        TEMP_SESSION_STORE['current_image_hash'] = image_hash
        TEMP_SESSION_STORE['current_status'] = 'processed'
        
        results['doc_id'] = None
        results['version'] = 1
        results['is_reprocess'] = False
        
        TEMP_SESSION_STORE['current_ocr_results'] = results
        
        return results
    
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


@app.post('/reprocess/{doc_id}')
def reprocess_ocr(doc_id: int):
    """Retrieve document details for UI trigger-reload"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """SELECT image_path, image_hash, corrected_text 
           FROM documents WHERE id=%s""",
        (doc_id,)
    )
    result = cur.fetchone()
    conn.close()
    
    if not result:
        return JSONResponse(status_code=404, content={'error': 'Document not found'})
    
    image_path, image_hash, corrected_text = result
    
    abs_filepath = image_path
    if not os.path.isabs(image_path):
        abs_filepath = os.path.join(root_dir, image_path)
        
    if not os.path.exists(abs_filepath):
        return JSONResponse(status_code=404, content={'error': 'Image file not found'})
    
    return {
        'success': True,
        'message': 'Reprocessing initiated. Please call /process with force_reprocess=true',
        'filepath': image_path,
        'image_hash': image_hash,
        'has_correction': corrected_text is not None
    }


@app.get('/review/new', response_class=HTMLResponse)
def review_new_get(request: Request):
    """Show the human-in-the-loop validation page for unsaved document draft"""
    image_path = TEMP_SESSION_STORE.get('current_filepath')
    ocr_results = TEMP_SESSION_STORE.get('current_ocr_results')
    
    if not image_path or not ocr_results:
        from fastapi.responses import RedirectResponse
        return RedirectResponse('/')
        
    ocr_text = ocr_results.get('full_text', '')
    corrected_text = None
    cer = None
    status = 'ocr'
    version = 1
    version_history = []
    similar_docs = []
    
    # Find similar documents for correction suggestion references
    try:
        if ocr_text:
            similar_docs = find_similar_documents(
                current_text=ocr_text,
                current_doc_id=None,
                threshold=0.3,
                limit=5
            )
    except Exception as e:
        print(f"⚠️  Failed to find similar documents: {e}")
        
    return templates.TemplateResponse(
        "review_new.html",
        {
            "request": request,
            "doc_id": "new",
            "image_path": image_path,
            "ocr_text": ocr_text,
            "corrected_text": corrected_text,
            "cer": cer,
            "status": status,
            "version": version,
            "version_history": version_history,
            "similar_docs": similar_docs
        }
    )


@app.post('/review/new')
def review_new_post(request: Request, data: SaveCorrectionRequest):
    """Create the document in database and save the corrected text for the first time"""
    corrected = data.corrected_text.strip()
    
    if not corrected:
        return JSONResponse(status_code=400, content={'error': 'No corrected text provided'})
        
    filepath = TEMP_SESSION_STORE.get('current_filepath')
    ocr_results = TEMP_SESSION_STORE.get('current_ocr_results')
    
    if not filepath or not ocr_results:
        return JSONResponse(status_code=400, content={'error': 'No active session found'})
        
    ocr_text = ocr_results.get('full_text', '')
    cer = compute_cer(ocr_text, corrected) if ocr_text else None
    
    # Generate text embedding
    embedding = None
    try:
        embedding = embed_text(corrected)
    except Exception as e:
        print(f"⚠️  Failed to generate embedding: {e}")
        
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO documents (image_path, ocr_text, corrected_text, status, version, parent_id, text_embedding, cer)
        VALUES (%s, %s, %s, 'corrected', 1, NULL, %s, %s)
        RETURNING id
        """,
        (filepath, ocr_text, corrected, json.dumps(embedding) if embedding else None, cer)
    )
    doc_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    
    # Update session variables
    TEMP_SESSION_STORE['current_doc_id'] = doc_id
    TEMP_SESSION_STORE['current_status'] = 'corrected'
    if isinstance(TEMP_SESSION_STORE.get('current_ocr_results'), dict):
        TEMP_SESSION_STORE['current_ocr_results']['doc_id'] = doc_id
        
    return {
        'success': True,
        'doc_id': doc_id,
        'cer': cer,
        'version': 1,
        'message': '✓ Document draft saved and corrections applied successfully!'
    }


@app.get('/review/{doc_id}', response_class=HTMLResponse)
def review_get(request: Request, doc_id: int):
    """Show the human-in-the-loop validation page"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """SELECT image_path, ocr_text, corrected_text, cer, status, version, image_hash, parent_id 
           FROM documents WHERE id=%s""",
        (doc_id,)
    )
    result = cur.fetchone()
    
    if not result:
        conn.close()
        return HTMLResponse("Document not found", status_code=404)
        
    image_path, ocr_text, corrected_text, cer, status, version, image_hash, parent_id = result
    
    version_history = []
    if image_hash:
        cur.execute(
            """SELECT id, version, status, cer, created_at, updated_at
               FROM documents 
               WHERE image_hash = %s 
               ORDER BY version ASC""",
            (image_hash,)
        )
        version_history = cur.fetchall()
    
    similar_docs = []
    try:
        text_for_similarity = corrected_text if corrected_text else ocr_text
        if text_for_similarity:
            similar_docs = find_similar_documents(
                current_text=text_for_similarity,
                current_doc_id=doc_id,
                threshold=0.3,
                limit=5
            )
    except Exception as e:
        print(f"⚠️  Failed to find similar documents: {e}")
    
    conn.close()

    return templates.TemplateResponse(
        "review_new.html",
        {
            "request": request,
            "doc_id": doc_id,
            "image_path": image_path,
            "ocr_text": ocr_text,
            "corrected_text": corrected_text,
            "cer": cer,
            "status": status,
            "version": version,
            "version_history": version_history,
            "similar_docs": similar_docs
        }
    )


@app.post('/review/{doc_id}')
def review_post(request: Request, doc_id: int, data: SaveCorrectionRequest):
    """Save manual correction corrections and update status, embedding & CER"""
    corrected = data.corrected_text.strip()
    
    if not corrected:
        return JSONResponse(status_code=400, content={'error': 'No corrected text provided'})

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT ocr_text FROM documents WHERE id=%s", (doc_id,))
    result = cur.fetchone()
    
    if not result:
        conn.close()
        return JSONResponse(status_code=404, content={'error': 'Document not found'})
    
    ocr_text = result[0] or ''
    cer = compute_cer(ocr_text, corrected) if ocr_text else None
    
    embedding = None
    try:
        embedding = embed_text(corrected)
    except Exception as e:
        print(f"⚠️  Failed to generate embedding: {e}")

    cur.execute(
        """
        UPDATE documents
        SET corrected_text=%s,
            cer=%s,
            status='corrected',
            version=2,
            text_embedding=%s,
            updated_at=NOW()
        WHERE id=%s
        """,
        (corrected, cer, json.dumps(embedding) if embedding else None, doc_id)
    )
    conn.commit()
    conn.close()
    
    # Clear session values
    session = request.session
    session.pop('current_doc_id', None)
    session.pop('current_filename', None)
    session.pop('current_filepath', None)
    session.pop('current_image_hash', None)
    session.pop('current_status', None)

    return {
        'success': True,
        'message': f'Saved successfully! Character Error Rate: {cer:.4f}' if cer is not None else 'Saved successfully!',
        'cer': round(cer, 4) if cer is not None else None,
        'version': 2
    }


@app.post('/correct')
def correct_ocr(data: CorrectRequest):
    """Correct OCR text using learned confusion pairs & corrector engine"""
    ocr_text = data.text
    doc_id = data.doc_id
    confidence_threshold = data.confidence_threshold
    
    if not ocr_text:
        return JSONResponse(status_code=400, content={'error': 'No text provided'})
    
    try:
        from postocr_integration import correct_text
        result = correct_text(ocr_text, confidence_threshold)
        
        if result['success']:
            corrected_text = result['corrected_text']
            
            corrections = []
            if result.get('errors'):
                for error in result['errors']:
                    if isinstance(error, dict) and 'word' in error and 'suggestion' in error:
                        corrections.append({
                            'original': error['word'],
                            'corrected': error['suggestion'],
                            'confidence': 0.85
                        })
            
            if doc_id:
                conn = get_db()
                cur = conn.cursor()
                try:
                    cer = compute_cer(ocr_text, corrected_text)
                except:
                    cer = 0
                
                cur.execute(
                    """UPDATE documents 
                       SET corrected_text = %s, status = 'corrected', cer = %s 
                       WHERE id = %s""",
                    (corrected_text, cer, doc_id)
                )
                conn.commit()
                conn.close()
                
                return {
                    'success': True,
                    'corrected_text': corrected_text,
                    'corrections': corrections,
                    'errors_found': result.get('errors_found', len(corrections)),
                    'cer': round(cer, 4),
                    'doc_id': doc_id
                }
            else:
                return {
                    'success': True,
                    'corrected_text': corrected_text,
                    'corrections': corrections,
                    'errors_found': result.get('errors_found', len(corrections))
                }
        else:
            return JSONResponse(status_code=500, content={'error': result.get('error', 'Correction failed')})
    
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


@app.post('/detect-errors')
def detect_errors_route(data: DetectRequest):
    """Detect potential OCR spellcheck errors in text"""
    ocr_text = data.text
    if not ocr_text:
        return JSONResponse(status_code=400, content={'error': 'No text provided'})
    
    try:
        from postocr_integration import detect_errors
        result = detect_errors(ocr_text)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={'error': str(e)})


@app.post('/add-to-dictionary')
def add_to_dictionary(data: AddToDictionaryRequest):
    """Add a new verified word translation suggestion to confusion dictionary"""
    original_word = (data.original_word or data.incorrect or '').strip()
    corrected_word = (data.corrected_word or data.correct or '').strip()
    
    if not original_word or not corrected_word:
        return JSONResponse(status_code=400, content={'error': 'Both original and corrected words required'})
    
    try:
        from postocr_integration import add_confusion_pair
        add_confusion_pair(original_word, corrected_word)
        
        return {
            'success': True,
            'message': f'Word "{corrected_word}" added to dictionary',
            'original': original_word,
            'corrected': corrected_word
        }
    
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


@app.get('/uploads/{filepath:path}')
def serve_uploads(filepath: str):
    """Serve uploaded manuscript images dynamically with correct content type"""
    full_path = os.path.join(uploads_dir, filepath.replace('/', os.sep))
    
    if not os.path.exists(full_path):
        return JSONResponse(status_code=404, content={'error': 'File not found'})
    
    try:
        return FileResponse(full_path, media_type='image/png')
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


if __name__ == '__main__':
    import uvicorn
    # Start server locally
    uvicorn.run("app:app", host='0.0.0.0', port=5000, reload=True)