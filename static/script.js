let currentFilePath = null;

// DOM Elements
const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const previewSection = document.getElementById('previewSection');
const previewImage = document.getElementById('previewImage');
const parseBtn = document.getElementById('parseBtn');
const clearBtn = document.getElementById('clearBtn');
const reprocessBtn = document.getElementById('reprocessBtn');
const loading = document.getElementById('loading');
const resultsPlaceholder = document.getElementById('resultsPlaceholder');
const resultsSection = document.getElementById('resultsSection');
const errorMessage = document.getElementById('errorMessage');
const benchmarkStats = document.getElementById('benchmarkStats');
const textLines = document.getElementById('textLines');
const fullText = document.getElementById('fullText');
const copyBtn = document.getElementById('copyBtn');

// Upload box click
uploadBox.addEventListener('click', () => {
    fileInput.click();
});

// File input change
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        handleFileUpload(file);
    }
});

// Drag and drop
uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.classList.add('drag-over');
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.classList.remove('drag-over');
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) {
        handleFileUpload(file);
    }
});

// Handle file upload
async function handleFileUpload(file) {
    hideError();
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentFilePath = data.filepath;
            window.currentImageHash = data.image_hash;
            
            // Show preview
            const reader = new FileReader();
            reader.onload = (e) => {
                previewImage.src = e.target.result;
                uploadBox.style.display = 'none';
                previewSection.style.display = 'flex';
                resultsSection.style.display = 'none';
                resultsPlaceholder.style.display = 'block';
                
                // If existing document, show info
                if (data.existing_document) {
                    const msg = data.has_correction 
                        ? `📋 This document already exists (v${data.version}). Showing verified version (CER: ${data.cer || 'N/A'}).`
                        : `📋 This document already exists (v${data.version}). Click Parse to see results.`;
                    showInfo(msg);
                    window.existingDocId = data.doc_id;
                    // Show reprocess button
                    if (reprocessBtn) {
                        reprocessBtn.style.display = 'block';
                    }
                } else {
                    window.existingDocId = null;
                    if (reprocessBtn) {
                        reprocessBtn.style.display = 'none';
                    }
                }
            };
            reader.readAsDataURL(file);
        } else {
            showError(data.error);
        }
    } catch (error) {
        showError('Failed to upload file: ' + error.message);
    }
}

// Parse document
parseBtn.addEventListener('click', async () => {
    if (!currentFilePath) {
        showError('No file selected');
        return;
    }
    
    // Get selected mode
    const selectedMode = document.querySelector('input[name="mode"]:checked').value;
    
    hideError();
    hideInfo();
    loading.style.display = 'block';
    resultsSection.style.display = 'none';
    resultsPlaceholder.style.display = 'none';
    
    try {
        // Start both OCR and visualization in parallel
        console.log('🚀 Starting OCR and visualization for:', currentFilePath);
        
        // Check if currentFilePath exists
        if (!currentFilePath) {
            console.error('❌ ERROR: currentFilePath is undefined!');
            throw new Error('No file path available');
        }
        
        console.log('📡 Creating OCR request...');
        const ocrPromise = fetch('/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                filepath: currentFilePath,
                mode: selectedMode,
                image_hash: window.currentImageHash || null,
                force_reprocess: false
            })
        });

        console.log('📡 Creating Visualization request...');
        const vizPromise = fetch('/visualize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                filepath: currentFilePath
            })
        });
        
        console.log('⏳ Waiting for both requests to complete...');
        const [ocrResponse, vizResponse] = await Promise.all([ocrPromise, vizPromise]);
        
        console.log('✓ OCR Response status:', ocrResponse.status);
        console.log('✓ Visualization Response status:', vizResponse.status);
        
        const ocrData = await ocrResponse.json();
        
        // Handle visualization response more carefully
        let vizData = null;
        try {
            if (vizResponse.ok) {
                vizData = await vizResponse.json();
                console.log('🎨 Visualization Data:', vizData);
            } else {
                console.error('❌ Visualization request failed with status:', vizResponse.status);
                const errorText = await vizResponse.text();
                console.error('❌ Error response:', errorText);
            }
        } catch (vizError) {
            console.error('❌ Failed to parse visualization response:', vizError);
        }
        
        console.log('📊 OCR Data:', ocrData);
        console.log('🎨 Viz data:', vizData);
        
        loading.style.display = 'none';
        
        if (ocrData.success) {
            resultsPlaceholder.style.display = 'none';
            
            // Show info if reused existing
            if (ocrData.reused_existing) {
                showInfo(ocrData.message);
            }
            
            displayResults(ocrData, vizData);
        } else {
            resultsPlaceholder.style.display = 'block';
            showError(ocrData.error);
        }
    } catch (error) {
        console.error('❌ Error processing document:', error);
        loading.style.display = 'none';
        resultsPlaceholder.style.display = 'block';
        showError('Failed to process document: ' + error.message);
    }
});

// Reprocess OCR button
if (reprocessBtn) {
    reprocessBtn.addEventListener('click', async () => {
        if (!currentFilePath) {
            showError('No file selected');
            return;
        }
        
        if (!confirm('⚠️ Re-run OCR on this document? This will create a new version.')) {
            return;
        }
        
        const selectedMode = document.querySelector('input[name="mode"]:checked').value;
        
        hideError();
        hideInfo();
        loading.style.display = 'block';
        resultsSection.style.display = 'none';
        resultsPlaceholder.style.display = 'none';
        
        try {
            console.log('🔄 Reprocessing OCR for:', currentFilePath);
            
            // Call both OCR and visualization in parallel
            const ocrPromise = fetch('/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    filepath: currentFilePath,
                    mode: selectedMode,
                    image_hash: window.currentImageHash || null,
                    force_reprocess: true  // Force reprocessing
                })
            });
            
            const vizPromise = fetch('/visualize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    filepath: currentFilePath
                })
            });
            
            const [ocrResponse, vizResponse] = await Promise.all([ocrPromise, vizPromise]);
            
            const ocrData = await ocrResponse.json();
            
            // Handle visualization response
            let vizData = null;
            try {
                if (vizResponse.ok) {
                    vizData = await vizResponse.json();
                }
            } catch (e) {
                console.error('Visualization failed:', e);
            }
            
            loading.style.display = 'none';
            
            if (ocrData.success) {
                resultsPlaceholder.style.display = 'none';
                showInfo(`✅ OCR reprocessed! New version ${ocrData.version || ''} created.`);
                displayResults(ocrData, vizData);
            } else {
                resultsPlaceholder.style.display = 'block';
                showError(data.error);
            }
        } catch (error) {
            loading.style.display = 'none';
            resultsPlaceholder.style.display = 'block';
            showError('Failed to reprocess: ' + error.message);
        }
    });
}

// Display results
function displayResults(data, vizData) {
    console.log('🎬 displayResults called');
    console.log('  OCR data success:', data.success);
    console.log('  Viz data:', vizData);
    
    // Store visualization data globally
    window.currentVizData = vizData;
    
    // Remove any previous version info boxes
    const oldVersionInfo = document.querySelector('.version-info-box');
    if (oldVersionInfo) {
        oldVersionInfo.remove();
    }
    
    // Remove any previous review buttons
    const oldReviewBtn = document.querySelector('.review-btn');
    if (oldReviewBtn) {
        oldReviewBtn.remove();
    }

    // Display Visualization Section
    const visualizationSection = document.getElementById('visualizationSection');
    const vizStats = document.getElementById('vizStats');
    const vizImage = document.getElementById('vizImage');
    
    console.log('📌 Visualization section element:', visualizationSection);
    console.log('📌 Viz data success:', vizData && vizData.success);
    
    if (vizData && vizData.success) {
        console.log('✅ Visualization data is valid, displaying...');
        console.log('   Images:', vizData.images);
        
        // Show stats
        vizStats.innerHTML = `
            <div class="viz-stat-item">
                <span class="viz-stat-label">Characters</span>
                <span class="viz-stat-value">${vizData.stats.total_characters}</span>
            </div>
            <div class="viz-stat-item">
                <span class="viz-stat-label">Lines</span>
                <span class="viz-stat-value">${vizData.stats.total_lines}</span>
            </div>
            <div class="viz-stat-item">
                <span class="viz-stat-label">Avg/Line</span>
                <span class="viz-stat-value">${vizData.stats.avg_chars_per_line}</span>
            </div>
        `;
        
        // Set default image (combined view)
        vizImage.src = vizData.images.combined_analysis;
        console.log('🖼️  Set vizImage.src to:', vizData.images.combined_analysis);
        
        // Setup tab switching
        document.querySelectorAll('.viz-tab').forEach(tab => {
            tab.addEventListener('click', function() {
                document.querySelectorAll('.viz-tab').forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                const vizType = this.getAttribute('data-viz');
                switch(vizType) {
                    case 'combined':
                        vizImage.src = vizData.images.combined_analysis;
                        break;
                    case 'bounding':
                        vizImage.src = vizData.images.bounding_boxes;
                        break;
                    case 'heatmap':
                        vizImage.src = vizData.images.heatmap;
                        break;
                    case 'lines':
                        vizImage.src = vizData.images.line_segmentation;
                        break;
                }
            });
        });
        
        console.log('✅ Showing visualization section');
        visualizationSection.style.display = 'block';
    } else {
        // Show error or hide section
        if (vizData && vizData.error) {
            console.warn('⚠️  Visualization failed:', vizData.error);
        } else {
            console.warn('⚠️  Visualization data missing or invalid');
        }
        console.log('❌ Hiding visualization section');
        visualizationSection.style.display = 'none';
    }
    
    // Benchmark stats - adjust based on mode
    let statsHTML = '';
    
    // Check if this is cached/reused data (no benchmark)
    if (data.reused_existing && !data.benchmark) {
        statsHTML = `
            <div class="stat-card">
                <h4>📋 Cached Result</h4>
                <div class="stat-value">v${data.version || 'N/A'}</div>
                <div class="stat-details">
                    ${data.status === 'corrected' ? 'Human-verified text' : 'Previous OCR result'}<br>
                    No reprocessing needed
                </div>
            </div>
            <div class="stat-card">
                <h4>✨ Text Lines</h4>
                <div class="stat-value">${data.text ? data.text.length : 0}</div>
                <div class="stat-details">
                    ${data.status === 'corrected' ? 'Corrected by scholar' : 'OCR extracted'}<br>
                    Click "Re-run OCR" to reprocess
                </div>
            </div>
        `;
    } else if (data.mode === 'fast' && data.benchmark) {
        statsHTML = `
            <div class="stat-card">
                <h4>⚡ Fast Mode</h4>
                <div class="stat-value">${data.benchmark.paddleocr.time}s</div>
                <div class="stat-details">
                    ${data.benchmark.paddleocr.lines} lines detected<br>
                    Avg Confidence: ${(data.benchmark.paddleocr.avg_confidence * 100).toFixed(1)}%
                </div>
            </div>
            <div class="stat-card">
                <h4>✨ Final Output</h4>
                <div class="stat-value">${data.text.length}</div>
                <div class="stat-details">
                    Unique lines extracted<br>
                    PaddleOCR only
                </div>
            </div>
        `;
    } else if (data.benchmark) {
        statsHTML = `
            <div class="stat-card">
                <h4>🚀 PaddleOCR</h4>
                <div class="stat-value">${data.benchmark.paddleocr.time}s</div>
                <div class="stat-details">
                    ${data.benchmark.paddleocr.lines} lines detected<br>
                    Avg Confidence: ${(data.benchmark.paddleocr.avg_confidence * 100).toFixed(1)}%
                </div>
            </div>
            <div class="stat-card">
                <h4>👁️ EasyOCR</h4>
                <div class="stat-value">${data.benchmark.easyocr.time}s</div>
                <div class="stat-details">
                    ${data.benchmark.easyocr.lines} lines detected<br>
                    Avg Confidence: ${(data.benchmark.easyocr.avg_confidence * 100).toFixed(1)}%
                </div>
            </div>
            <div class="stat-card">
                <h4>✨ Final Output</h4>
                <div class="stat-value">${data.text.length}</div>
                <div class="stat-details">
                    Unique lines extracted<br>
                    After voting & filtering
                </div>
            </div>
        `;
    }
    
    // Add Devanagari quality metrics if available
    if (data.devanagari_quality && data.devanagari_quality.devanagari_chars > 0) {
        const qualityPercent = (data.devanagari_quality.score * 100).toFixed(1);
        let qualityIcon = '✓';
        let qualityClass = 'quality-excellent';
        
        if (data.devanagari_quality.score < 0.8) {
            qualityIcon = '⚠';
            qualityClass = 'quality-warning';
        }
        if (data.devanagari_quality.score < 0.6) {
            qualityIcon = '✗';
            qualityClass = 'quality-poor';
        }
        
        statsHTML += `
            <div class="stat-card ${qualityClass}">
                <h4>${qualityIcon} देवनागरी Quality</h4>
                <div class="stat-value">${qualityPercent}%</div>
                <div class="stat-details">
                    ${data.devanagari_quality.devanagari_chars} Devanagari chars<br>
                    ${data.devanagari_quality.issues_found} issues found
                </div>
            </div>
        `;
    }
    
    benchmarkStats.innerHTML = statsHTML;
    
    // Text lines - handle both array of objects and simple array
    if (data.text && Array.isArray(data.text)) {
        textLines.innerHTML = data.text.map(item => {
            // Handle both {text: "...", confidence: 0.9} and simple strings
            const text = typeof item === 'string' ? item : item.text;
            const confidence = typeof item === 'object' && item.confidence !== undefined ? item.confidence : null;
            
            if (confidence !== null) {
                const confidencePercent = (confidence * 100).toFixed(1);
                let confidenceClass = 'confidence-low';
                if (confidence >= 0.8) confidenceClass = 'confidence-high';
                else if (confidence >= 0.6) confidenceClass = 'confidence-medium';
                
                return `
                    <div class="text-line">
                        <div class="text-content">${escapeHtml(text)}</div>
                        <div class="text-confidence">
                            Confidence: <span class="${confidenceClass}">${confidencePercent}%</span>
                        </div>
                    </div>
                `;
            } else {
                // Cached/corrected text - no confidence score
                return `
                    <div class="text-line">
                        <div class="text-content">${escapeHtml(text)}</div>
                        <div class="text-confidence">
                            <span class="confidence-high">✓ Verified</span>
                        </div>
                    </div>
                `;
            }
        }).join('');
    } else {
        textLines.innerHTML = '<p>No text lines available</p>';
    }
    
    // Full text
    fullText.value = data.full_text;
    
    // Show version and CER info if available
    if (data.version || data.cer) {
        const versionInfo = document.createElement('div');
        versionInfo.className = 'version-info-box';
        versionInfo.style.cssText = 'background: #e3f2fd; padding: 12px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #2196F3;';
        
        let infoHTML = '<div style="display: flex; justify-content: space-between; align-items: center;">';
        
        if (data.version) {
            infoHTML += `<span style="font-weight: 600; color: #1976d2;">📌 Version ${data.version}</span>`;
        }
        
        if (data.cer !== undefined && data.cer !== null) {
            const cerPercent = (data.cer * 100).toFixed(2);
            let cerColor = '#4caf50';
            if (data.cer > 0.15) cerColor = '#ff9800';
            if (data.cer > 0.30) cerColor = '#f44336';
            infoHTML += `<span style="color: ${cerColor}; font-weight: 600;">📊 CER: ${cerPercent}%</span>`;
        }
        
        if (data.is_reprocess) {
            infoHTML += '<span style="color: #9c27b0; font-weight: 600;">🔄 Reprocessed</span>';
        }
        
        if (data.reused_existing) {
            infoHTML += '<span style="color: #4caf50; font-weight: 600;">✓ Verified</span>';
        }
        
        infoHTML += '</div>';
        versionInfo.innerHTML = infoHTML;
        
        const fullTextArea = document.querySelector('.full-text-area');
        if (fullTextArea && !document.querySelector('.version-info-box')) {
            fullTextArea.insertAdjacentElement('beforebegin', versionInfo);
        }
    }
    
    // Add "Review & Correct" button if doc_id is present
    if (data.doc_id) {
        const reviewBtn = document.createElement('button');
        reviewBtn.className = 'btn btn-success btn-block review-btn';
        reviewBtn.innerHTML = '<span class="btn-icon">✏️</span> Review & Correct Text';
        reviewBtn.onclick = () => {
            window.location.href = `/review/${data.doc_id}`;
        };
        
        // Insert after full text area
        const fullTextArea = document.querySelector('.full-text-area');
        fullTextArea.insertAdjacentElement('afterend', reviewBtn);
    }
    
    resultsSection.style.display = 'block';
}

// Copy text
copyBtn.addEventListener('click', () => {
    fullText.select();
    document.execCommand('copy');
    
    const originalText = copyBtn.innerHTML;
    copyBtn.innerHTML = '<span class="btn-icon">✅</span> Copied!';
    setTimeout(() => {
        copyBtn.innerHTML = originalText;
    }, 2000);
});

// Clear and upload new
clearBtn.addEventListener('click', () => {
    currentFilePath = null;
    fileInput.value = '';
    previewSection.style.display = 'none';
    uploadBox.style.display = 'block';
    resultsSection.style.display = 'none';
    resultsPlaceholder.style.display = 'block';
    hideError();
});

// Show error
function showError(message) {
    errorMessage.textContent = '❌ ' + message;
    errorMessage.style.display = 'block';
}

// Hide error
function hideError() {
    errorMessage.style.display = 'none';
}

// Show info message
function showInfo(message) {
    const infoBox = document.getElementById('infoMessage');
    if (!infoBox) {
        const box = document.createElement('div');
        box.id = 'infoMessage';
        box.className = 'info-message';
        box.style.cssText = 'background: #e3f2fd; color: #1976d2; padding: 12px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #1976d2;';
        previewSection.insertAdjacentElement('afterend', box);
    }
    document.getElementById('infoMessage').textContent = 'ℹ️ ' + message;
    document.getElementById('infoMessage').style.display = 'block';
}

// Hide info message
function hideInfo() {
    const infoBox = document.getElementById('infoMessage');
    if (infoBox) {
        infoBox.style.display = 'none';
    }
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
