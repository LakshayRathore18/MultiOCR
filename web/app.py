from flask import Flask, render_template, request, jsonify, redirect, send_from_directory, send_file, session
import os
import sys
import json
from werkzeug.utils import secure_filename
from datetime import timedelta

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
import concurrent.futures

# Import database and CER modules
from database.db import get_db
from utils.cer import compute_cer
from utils.image_hash import compute_image_hash
from similarity.embeddings import embed_text
from similarity.search import find_similar_documents

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.secret_key = 'multiocr-secret-key-2025'  # Change this in production!
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

# Initialize models once at startup
print("Initializing OCR models...")
paddle_model = None
easy_model = None
deepseek_model = None

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

# Initialize PostOCR correction module with trie building
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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/session-data')
def get_session_data():
    """Get persisted session data for current document"""
    return jsonify({
        'has_session': bool(session.get('current_filepath')),
        'filename': session.get('current_filename'),
        'filepath': session.get('current_filepath'),
        'doc_id': session.get('current_doc_id'),
        'status': session.get('current_status'),
        'ocr_results': session.get('current_ocr_results')
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, BMP, TIFF'}), 400
    
    # Read file bytes and compute hash BEFORE saving
    file_bytes = file.read()
    image_hash = compute_image_hash(file_bytes)
    
    # Reset file pointer to save the file
    file.seek(0)
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # Check if this image already exists in database
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """SELECT id, image_path, corrected_text, status, version, cer 
           FROM documents 
           WHERE image_hash = %s 
           ORDER BY version DESC LIMIT 1""",
        (image_hash,)
    )
    existing_doc = cur.fetchone()
    conn.close()
    
    if existing_doc:
        doc_id, old_path, corrected_text, status, version, cer = existing_doc
        
        # Store in session for persistence across navigation
        session['current_doc_id'] = doc_id
        session['current_filename'] = filename
        session['current_filepath'] = filepath
        session['current_image_hash'] = image_hash
        session['current_status'] = status
        session.permanent = True
        
        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': filepath,
            'image_hash': image_hash,
            'existing_document': True,
            'doc_id': doc_id,
            'status': status,
            'version': version,
            'has_correction': corrected_text is not None,
            'cer': round(cer, 4) if cer else None,
            'message': 'This image already exists. Showing latest version.'
        })
    
    # Store in session for new documents
    session['current_filename'] = filename
    session['current_filepath'] = filepath
    session['current_image_hash'] = image_hash
    session.permanent = True
    
    return jsonify({
        'success': True,
        'filename': filename,
        'filepath': filepath,
        'image_hash': image_hash,
        'existing_document': False
    })

@app.route('/process', methods=['POST'])
def process_ocr():
    data = request.get_json()
    filepath = data.get('filepath')
    mode = data.get('mode', 'paddleocr')  # 'paddleocr', 'easyocr', 'deepseek', or 'multiocr'
    image_hash = data.get('image_hash')
    force_reprocess = data.get('force_reprocess', False)
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    # Check if document exists and has corrections
    if image_hash and not force_reprocess:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, ocr_text, corrected_text, cer, status, version 
               FROM documents 
               WHERE image_hash = %s 
               ORDER BY version DESC LIMIT 1""",
            (image_hash,)
        )
        existing = cur.fetchone()
        
        if existing:
            doc_id, ocr_text, corrected_text, cer, status, version = existing
            
            # If corrected version exists, return it
            if corrected_text:
                conn.close()
                return jsonify({
                    'success': True,
                    'reused_existing': True,
                    'doc_id': doc_id,
                    'full_text': corrected_text,
                    'status': status,
                    'version': version,
                    'cer': round(cer, 4) if cer else None,
                    'message': 'Showing verified corrected version. Click "Re-run OCR" to reprocess.',
                    'text': [{'text': line, 'confidence': 1.0} for line in corrected_text.split('\\n') if line.strip()]
                })
            
            # If only OCR exists, return that
            elif ocr_text:
                ocr_results = {
                    'success': True,
                    'reused_existing': True,
                    'doc_id': doc_id,
                    'full_text': ocr_text,
                    'status': status,
                    'version': version,
                    'message': 'OCR already processed. Ready for review.',
                    'text': [{'text': line, 'confidence': 0.0} for line in ocr_text.split('\n') if line.strip()]
                }
                # Store in session after successful processing
                session['current_doc_id'] = doc_id
                session['current_filepath'] = filepath
                session['current_image_hash'] = image_hash
                session['current_status'] = status
                session['current_ocr_results'] = ocr_results
                session.permanent = True
                conn.close()
                return jsonify(ocr_results)
        
        conn.close()
    
    try:
        if mode == 'paddleocr':
            # PaddleOCR mode: Use only PaddleOCR (faster, single engine)
            if paddle_model is None:
                return jsonify({'error': 'PaddleOCR model not available. Please check installation.'}), 500
            
            paddle_data = benchmark_ocr(lambda path: run_paddleocr(path, paddle_model), filepath)
            final_output = paddle_data["results"]
            
            # Calculate Devanagari quality metrics
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
            # DeepSeek only mode
            if deepseek_model is None:
                return jsonify({'error': 'DeepSeek model not available.'}), 500
            
            deepseek_data = benchmark_ocr(lambda path: run_deepseek(path, deepseek_model), filepath)
            final_output = deepseek_data["results"]
            
            # Calculate Devanagari quality metrics
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
            # EasyOCR mode: Use only EasyOCR
            if easy_model is None:
                return jsonify({'error': 'EasyOCR model not available. Please check installation.'}), 500
            
            easy_data = benchmark_ocr(lambda path: run_easyocr(path, easy_model), filepath)
            final_output = easy_data["results"]
            
            # Calculate Devanagari quality metrics
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
            # MultiOCR mode: Run Paddle + EasyOCR + DeepSeek (show metrics, no voting)
            if paddle_model is None:
                return jsonify({'error': 'PaddleOCR required. Please check installation.'}), 500
            
            # Determine number of workers based on available models
            max_workers = 0
            if easy_model:
                max_workers += 1
            if deepseek_model:
                max_workers += 1
            max_workers += 1  # Always have Paddle
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                paddle_future = executor.submit(benchmark_ocr, lambda path: run_paddleocr(path, paddle_model), filepath)
                easy_future = executor.submit(benchmark_ocr, lambda path: run_easyocr(path, easy_model), filepath) if easy_model else None
                deepseek_future = executor.submit(benchmark_ocr, lambda path: run_deepseek(path, deepseek_model), filepath) if deepseek_model else None
                
                paddle_data = paddle_future.result()
                easy_data = easy_future.result() if easy_future else None
                deepseek_data = deepseek_future.result() if deepseek_future else None
            
            # Run ensemble voting: merges Paddle + DeepSeek using the voting engine.
            # Handles 0-line edge cases automatically - if one engine failed or
            # timed out it falls back to the other engine's results entirely.
            deepseek_results_for_voting = deepseek_data["results"] if deepseek_data else None
            final_output = ocr_voting(
                paddle_data["results"],
                deepseek_results=deepseek_results_for_voting
            )

            # Fallback: if voting produced nothing, use raw Paddle output
            if not final_output:
                final_output = paddle_data["results"]

            # Calculate Devanagari quality metrics
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
        
        # Save OCR result to database with upsert logic
        conn = get_db()
        cur = conn.cursor()
        
        # Check if this is a reprocess of existing document
        parent_id = None
        current_version = 1
        
        if image_hash:
            cur.execute(
                """SELECT id, version FROM documents 
                   WHERE image_hash = %s 
                   ORDER BY version DESC LIMIT 1""",
                (image_hash,)
            )
            existing = cur.fetchone()
            if existing:
                parent_id = existing[0]
                current_version = existing[1] + 1
        
        # Generate text embedding for semantic similarity
        text_for_embedding = results['full_text']
        embedding = None
        try:
            embedding = embed_text(text_for_embedding)
        except Exception as e:
            print(f"⚠️  Failed to generate embedding: {e}")
        
        # Insert as new version if reprocessing, otherwise new document
        cur.execute(
            """
            INSERT INTO documents (image_path, image_hash, ocr_text, status, version, parent_id, text_embedding)
            VALUES (%s, %s, %s, 'ocr', %s, %s, %s)
            RETURNING id
            """,
            (filepath, image_hash, results['full_text'], current_version, parent_id, 
             json.dumps(embedding) if embedding else None)
        )
        doc_id = cur.fetchone()[0]
        conn.commit()
        conn.close()
        
        # Store in session for persistence across navigation
        session['current_doc_id'] = doc_id
        session['current_filepath'] = filepath
        session['current_image_hash'] = image_hash
        session['current_status'] = 'processed'
        session.permanent = True
        
        results['doc_id'] = doc_id
        results['version'] = current_version
        results['is_reprocess'] = parent_id is not None
        
        # Store OCR results in session for persistence
        session['current_ocr_results'] = results
        session.permanent = True
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/reprocess/<int:doc_id>', methods=['POST'])
def reprocess_ocr(doc_id):
    """
    Explicitly reprocess OCR for an existing document.
    Creates a new version and compares with corrected text.
    """
    conn = get_db()
    cur = conn.cursor()
    
    # Fetch existing document
    cur.execute(
        """SELECT image_path, image_hash, corrected_text 
           FROM documents WHERE id=%s""",
        (doc_id,)
    )
    result = cur.fetchone()
    conn.close()
    
    if not result:
        return jsonify({'error': 'Document not found'}), 404
    
    image_path, image_hash, corrected_text = result
    
    if not os.path.exists(image_path):
        return jsonify({'error': 'Image file not found'}), 404
    
    # Trigger OCR reprocessing with force flag
    return jsonify({
        'success': True,
        'message': 'Reprocessing initiated. Please call /process with force_reprocess=true',
        'filepath': image_path,
        'image_hash': image_hash,
        'has_correction': corrected_text is not None
    })


@app.route('/review/<int:doc_id>', methods=['GET', 'POST'])
def review(doc_id):
    """
    Human-in-the-loop review page for manual correction.
    GET: Display OCR result for review
    POST: Save corrected text and compute CER
    """
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        print(f"\n=== SAVE OPERATION START for doc_id={doc_id} ===")
        
        # Accept both JSON and form data
        if request.is_json:
            data = request.get_json()
            corrected = data.get('corrected_text', '').strip()
            print(f"📥 Received JSON data")
        else:
            corrected = request.form.get('corrected_text', '').strip()
            print(f"📥 Received FORM data")
        
        print(f"📝 Corrected text length: {len(corrected)} chars")
        print(f"📝 First 100 chars: {corrected[:100]}")
        
        if not corrected:
            print("❌ ERROR: No corrected text provided")
            return jsonify({'error': 'No corrected text provided'}), 400

        # Fetch original OCR text
        print(f"🔍 Fetching original OCR text for doc_id={doc_id}")
        cur.execute(
            "SELECT ocr_text FROM documents WHERE id=%s",
            (doc_id,)
        )
        result = cur.fetchone()
        
        if not result:
            print(f"❌ ERROR: Document not found for doc_id={doc_id}")
            conn.close()
            return jsonify({'error': 'Document not found'}), 404
        
        print(f"✅ Found document")
        ocr_text = result[0] or ''
        print(f"📄 OCR text length: {len(ocr_text)} chars")
        print(f"📄 OCR text length: {len(ocr_text)} chars")

        # Compute CER (handle None ocr_text)
        cer = compute_cer(ocr_text, corrected) if ocr_text else None
        print(f"📊 Computed CER: {cer}")
        
        # Generate embedding for corrected text (more accurate than OCR)
        embedding = None
        try:
            embedding = embed_text(corrected)
            print(f"🧠 Generated embedding")
        except Exception as e:
            print(f"⚠️  Failed to generate embedding: {e}")

        # Update document with corrected text and embedding
        print(f"💾 Executing UPDATE query for doc_id={doc_id}")
        print(f"   - corrected_text length: {len(corrected)}")
        print(f"   - cer: {cer}")
        print(f"   - embedding: {'present' if embedding else 'None'}")
        
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
        
        rows_affected = cur.rowcount
        print(f"✅ UPDATE executed, rows affected: {rows_affected}")
        
        conn.commit()
        print(f"✅ Transaction committed")
        
        # Verify the save
        cur.execute("SELECT corrected_text, cer, status FROM documents WHERE id=%s", (doc_id,))
        verify_result = cur.fetchone()
        if verify_result:
            saved_text, saved_cer, saved_status = verify_result
            print(f"🔍 Verification: corrected_text length={len(saved_text or '')} chars, cer={saved_cer}, status={saved_status}")
        else:
            print(f"⚠️  Verification failed: document not found")
        
        conn.close()
        print(f"=== SAVE OPERATION END ===\n")
        
        # Clear session on successful save
        session.pop('current_doc_id', None)
        session.pop('current_filename', None)
        session.pop('current_filepath', None)
        session.pop('current_image_hash', None)
        session.pop('current_status', None)

        # Format message based on whether CER is available
        if cer is not None:
            message = f'Saved successfully! Character Error Rate: {cer:.4f}'
            cer_value = round(cer, 4)
        else:
            message = 'Saved successfully!'
            cer_value = None

        return jsonify({
            'success': True,
            'message': message,
            'cer': cer_value
        })

    # GET request - show review form
    cur.execute(
        """SELECT image_path, ocr_text, corrected_text, cer, status, version, image_hash, parent_id 
           FROM documents WHERE id=%s""",
        (doc_id,)
    )
    result = cur.fetchone()
    
    if not result:
        conn.close()
        return "Document not found", 404
        
    image_path, ocr_text, corrected_text, cer, status, version, image_hash, parent_id = result
    
    # Fetch version history for this document
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
    
    # Find similar documents for reference (word-based similarity)
    similar_docs = []
    try:
        # Use corrected text if available, else OCR text
        text_for_similarity = corrected_text if corrected_text else ocr_text
        if text_for_similarity:
            similar_docs = find_similar_documents(
                current_text=text_for_similarity,
                current_doc_id=doc_id,
                threshold=0.3,  # Lower threshold for word-based similarity
                limit=5
            )
    except Exception as e:
        print(f"⚠️  Failed to find similar documents: {e}")
    
    conn.close()

    return render_template(
        "review_new.html",
        doc_id=doc_id,
        image_path=image_path,
        ocr_text=ocr_text,
        corrected_text=corrected_text,
        cer=cer,
        status=status,
        version=version,
        version_history=version_history,
        similar_docs=similar_docs
    )

@app.route('/correct', methods=['POST'])
def correct_ocr():
    """Correct OCR text using learned confusion pairs and dictionary from postOCR module"""
    print("✨ /correct endpoint called")
    data = request.get_json()
    ocr_text = data.get('text', '')
    doc_id = data.get('doc_id')
    confidence_threshold = data.get('confidence_threshold', 'MEDIUM')
    print(f"   📝 Text length: {len(ocr_text)} chars, doc_id: {doc_id}, threshold: {confidence_threshold}")
    
    if not ocr_text:
        print("   ❌ No text provided")
        return jsonify({'error': 'No text provided'}), 400
    
    try:
        from postocr_integration import correct_text
        
        print("   📡 Calling correct_text from postocr_integration...")
        result = correct_text(ocr_text, confidence_threshold)
        print(f"   ✅ Correction result success: {result.get('success')}")
        
        if result['success']:
            corrected_text = result['corrected_text']
            
            # Format corrections for frontend (list of original->corrected pairs)
            corrections = []
            if result.get('errors'):
                for error in result['errors']:
                    # Find the correction in the corrected text
                    if isinstance(error, dict) and 'word' in error and 'suggestion' in error:
                        corrections.append({
                            'original': error['word'],
                            'corrected': error['suggestion'],
                            'confidence': 0.85  # Default confidence
                        })
            
            # Update database if doc_id provided
            if doc_id:
                conn = get_db()
                cur = conn.cursor()
                
                # Calculate CER between OCR and corrected
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
                
                return jsonify({
                    'success': True,
                    'corrected_text': corrected_text,
                    'corrections': corrections,
                    'errors_found': result.get('errors_found', len(corrections)),
                    'cer': round(cer, 4),
                    'doc_id': doc_id
                })
            else:
                return jsonify({
                    'success': True,
                    'corrected_text': corrected_text,
                    'corrections': corrections,
                    'errors_found': result.get('errors_found', len(corrections))
                })
        else:
            return jsonify({'error': result.get('error', 'Correction failed')}), 500
    
    except Exception as e:
        print(f"❌ Correction error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/detect-errors', methods=['POST'])
def detect_errors_route():
    """Detect OCR errors in text without correcting them"""
    print("🔍 /detect-errors endpoint called")
    data = request.get_json()
    ocr_text = data.get('text', '')
    print(f"   📝 Text length: {len(ocr_text)} chars")
    
    if not ocr_text:
        print("   ❌ No text provided")
        return jsonify({'error': 'No text provided'}), 400
    
    try:
        from postocr_integration import detect_errors
        
        print("   📡 Calling detect_errors from postocr_integration...")
        result = detect_errors(ocr_text)
        print(f"   ✅ Result: {result}")
        
        return jsonify(result)
    
    except Exception as e:
        print(f"❌ Error detection error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/add-to-dictionary', methods=['POST'])
def add_to_dictionary():
    """Add a new word to the custom dictionary for future corrections"""
    print("📚 /add-to-dictionary endpoint called")
    data = request.get_json()
    
    # Support both naming conventions
    original_word = (data.get('original_word') or data.get('incorrect') or '').strip()
    corrected_word = (data.get('corrected_word') or data.get('correct') or '').strip()
    
    if not original_word or not corrected_word:
        return jsonify({'error': 'Both original and corrected words required'}), 400
    
    try:
        # Save to confusion pairs in postOCR module
        from postocr_integration import add_confusion_pair
        
        print(f"   📝 Adding: '{original_word}' -> '{corrected_word}'")
        result = add_confusion_pair(original_word, corrected_word)
        
        return jsonify({
            'success': True,
            'message': f'Word "{corrected_word}" added to dictionary',
            'original': original_word,
            'corrected': corrected_word
        })
    
    except Exception as e:
        print(f"❌ Error adding to dictionary: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/<path:filepath>')
def serve_uploads(filepath):
    """Serve files from uploads directory"""
    import os
    from flask import send_file
    
    # Get the parent directory of web/ (which is the project root)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    uploads_dir = os.path.join(root_dir, 'uploads')
    full_path = os.path.join(uploads_dir, filepath.replace('/', os.sep))
    
    print(f"📁 Serving upload: {filepath}")
    print(f"📁 Full path: {full_path}")
    print(f"📁 File exists: {os.path.exists(full_path)}")
    
    if not os.path.exists(full_path):
        print(f"❌ File not found: {full_path}")
        return jsonify({'error': 'File not found'}), 404
    
    try:
        print(f"✓ Serving file: {full_path}")
        return send_file(full_path, mimetype='image/png')
    except Exception as e:
        print(f"❌ Error serving file: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    print("✓ Directories created/verified")
    
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)