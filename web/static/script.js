let currentFilePath = null;
let currentDocId = null;

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

// Correction Elements
const correctionSection = document.getElementById('correctionSection');
const detectErrorsBtn = document.getElementById('detectErrorsBtn');
const correctTextBtn = document.getElementById('correctTextBtn');
const errorDetection = document.getElementById('errorDetection');
const errorsList = document.getElementById('errorsList');
const correctionResults = document.getElementById('correctionResults');
const correctedText = document.getElementById('correctedText');
const acceptCorrectionBtn = document.getElementById('acceptCorrectionBtn');
const correctionLoading = document.getElementById('correctionLoading');
const errorCount = document.getElementById('errorCount');

// Restore session data on page load
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/api/session-data');
        const sessionData = await response.json();
        
        if (sessionData.has_session && sessionData.filepath) {
            console.log('📝 Restoring session data...', sessionData);
            currentFilePath = sessionData.filepath;
            currentDocId = sessionData.doc_id;
            
            // Restore image preview
            fetch(sessionData.filepath)
                .then(resp => resp.blob())
                .then(blob => {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        previewImage.src = e.target.result;
                        uploadBox.style.display = 'none';
                        previewSection.style.display = 'flex';
                    };
                    reader.readAsDataURL(blob);
                })
                .catch(err => console.log('Could not restore image preview'));
            
            // Restore OCR results if available
            if (sessionData.ocr_results) {
                console.log('📊 Restoring OCR results...');
                displayOCRResults(sessionData.ocr_results);
                
                // Restore visualization if available
                if (sessionData.visualization_path) {
                    console.log('📸 Restoring visualization...');
                    const vizDiv = document.querySelector('[id*="visualization"]');
                    if (vizDiv) {
                        vizDiv.innerHTML = `
                            <div class="visualization-container">
                                <img src="${sessionData.visualization_path}" alt="Bounding Boxes" style="max-width: 100%; border-radius: 8px;">
                            </div>
                        `;
                    }
                }
            }
        }
    } catch (error) {
        console.log('No session data to restore');
    }
});

// Add correction event listeners
if (detectErrorsBtn) {
    detectErrorsBtn.addEventListener('click', detectOCRErrors);
}
if (correctTextBtn) {
    correctTextBtn.addEventListener('click', performOCRCorrection);
}
if (acceptCorrectionBtn) {
    acceptCorrectionBtn.addEventListener('click', acceptAndSaveCorrection);
}

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
                console.log('🎨 Visualization Data:', vizData);
            } else {
                console.error('❌ Visualization request failed with status:', vizResponse.status);
            }
        } catch (vizError) {
            console.error('❌ Failed to parse visualization response:', vizError);
        }
        
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
            console.log('🔄 Reprocessing OCR and visualizing for:', currentFilePath);
            
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
                showError(ocrData.error);
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
    console.log('OCR Data:', data);
    console.log('Visualization Data:', vizData);
    
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
    console.log('Visualization section element:', visualizationSection);
    
    if (vizData && vizData.success) {
        console.log('✅ Visualization data is valid, displaying...');
        console.log('Images object:', vizData.images);
        
        // Stop any polling that might be running
        if (visualizationPollInterval) {
            console.log('⏹️ Stopping visualization polling');
            clearInterval(visualizationPollInterval);
            visualizationPollInterval = null;
        }
        
        // Update visualization images
        const vizBoundingBoxes = document.getElementById('vizBoundingBoxes');
        const vizHeatmap = document.getElementById('vizHeatmap');
        const vizLineSegmentation = document.getElementById('vizLineSegmentation');
        const vizCombined = document.getElementById('vizCombined');
        
        console.log('Element vizBoundingBoxes:', vizBoundingBoxes);
        console.log('Element vizHeatmap:', vizHeatmap);
        console.log('Element vizLineSegmentation:', vizLineSegmentation);
        console.log('Element vizCombined:', vizCombined);
        
        if (vizBoundingBoxes && vizData.images && vizData.images.bounding_boxes) {
            console.log('Setting vizBoundingBoxes.src to:', vizData.images.bounding_boxes);
            vizBoundingBoxes.src = vizData.images.bounding_boxes;
        }
        if (vizHeatmap && vizData.images && vizData.images.heatmap) {
            console.log('Setting vizHeatmap.src to:', vizData.images.heatmap);
            vizHeatmap.src = vizData.images.heatmap;
        }
        if (vizLineSegmentation && vizData.images && vizData.images.line_segmentation) {
            console.log('Setting vizLineSegmentation.src to:', vizData.images.line_segmentation);
            vizLineSegmentation.src = vizData.images.line_segmentation;
        }
        if (vizCombined && vizData.images && vizData.images.combined_analysis) {
            console.log('Setting vizCombined.src to:', vizData.images.combined_analysis);
            vizCombined.src = vizData.images.combined_analysis;
        }
        
        console.log('Setting visualization section to display: block');
        visualizationSection.style.display = 'block';
    } else {
        if (vizData && vizData.error) {
            console.warn('⚠️  Visualization failed:', vizData.error);
        } else {
            console.warn('⚠️  Visualization data missing or invalid');
        }
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
    } else if (data.mode === 'paddleocr' && data.benchmark) {
        statsHTML = `
            <div class="stat-card">
                <h4>🚀 PaddleOCR</h4>
                <div class="stat-details">
                    ${data.benchmark.paddleocr.lines} lines detected<br>
                    Avg Confidence: ${(data.benchmark.paddleocr.avg_confidence * 100).toFixed(1)}%
                </div>
            </div>
            <div class="stat-card">
                <h4>✨ Final Output</h4>
                <div class="stat-details">
                    ${data.text.length} Unique lines extracted<br>
                    PaddleOCR only
                </div>
            </div>
        `;
    } else if (data.mode === 'easyocr' && data.benchmark) {
        statsHTML = `
            <div class="stat-card">
                <h4>👁️ EasyOCR</h4>
                <div class="stat-details">
                    ${data.benchmark.easyocr.lines} lines detected<br>
                    Avg Confidence: ${(data.benchmark.easyocr.avg_confidence * 100).toFixed(1)}%
                </div>
            </div>
            <div class="stat-card">
                <h4>✨ Final Output</h4>
                <div class="stat-details">
                    ${data.text.length} Unique lines extracted<br>
                    EasyOCR only
                </div>
            </div>
        `;
    } else if (data.mode === 'deepseek' && data.benchmark) {
        statsHTML = `
            <div class="stat-card">
                <h4>🤖 DeepSeek</h4>
                <div class="stat-details">
                    ${data.benchmark.deepseek.lines} lines detected<br>
                    Avg Confidence: ${(data.benchmark.deepseek.avg_confidence * 100).toFixed(1)}%
                </div>
            </div>
            <div class="stat-card">
                <h4>✨ Final Output</h4>
                <div class="stat-details">
                    ${data.text.length} Unique lines extracted<br>
                    AI Vision OCR
                </div>
            </div>
        `;
    } else if (data.benchmark) {
        // MultiOCR mode with multiple engines
        let engines = [];
        
        if (data.benchmark.paddleocr) {
            engines.push(`
                <div class="stat-card clickable" data-engine="paddleocr" title="Click to view PaddleOCR results">
                    <h4>🚀 PaddleOCR</h4>
                    <div class="stat-details">
                        ${data.benchmark.paddleocr.lines} lines detected<br>
                        Avg Confidence: ${(data.benchmark.paddleocr.avg_confidence * 100).toFixed(1)}%
                    </div>
                </div>
            `);
        }
        
        if (data.benchmark.easyocr) {
            engines.push(`
                <div class="stat-card clickable" data-engine="easyocr" title="Click to view EasyOCR results">
                    <h4>👁️ EasyOCR</h4>
                    <div class="stat-details">
                        ${data.benchmark.easyocr.lines} lines detected<br>
                        Avg Confidence: ${(data.benchmark.easyocr.avg_confidence * 100).toFixed(1)}%
                    </div>
                </div>
            `);
        }
        
        if (data.benchmark.deepseek) {
            engines.push(`
                <div class="stat-card clickable" data-engine="deepseek" title="Click to view DeepSeek results">
                    <h4>🤖 DeepSeek</h4>
                    <div class="stat-details">
                        ${data.benchmark.deepseek.lines} lines detected<br>
                        Avg Confidence: ${(data.benchmark.deepseek.avg_confidence * 100).toFixed(1)}%
                    </div>
                </div>
            `);
        }
        
        statsHTML = engines.join('') + `
            <div class="stat-card clickable" data-engine="final" title="Click to view combined final output">
                <h4>✨ Final Output</h4>
                <div class="stat-details">
                    ${data.text.length} Unique lines extracted<br>
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
    
    // Store benchmark data globally for click handlers
    window.currentBenchmarkData = data.benchmark;
    window.currentFinalOutput = data.text;
    
    // Add click handlers to stat cards
    document.querySelectorAll('.stat-card.clickable').forEach(card => {
        card.addEventListener('click', function() {
            const engine = this.getAttribute('data-engine');
            displayEngineResults(engine);
            
            // Visual feedback - highlight selected card
            document.querySelectorAll('.stat-card.clickable').forEach(c => c.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // Text lines - handle both array of objects and simple array
    if (data.text && Array.isArray(data.text)) {
        textLines.innerHTML = data.text.map(item => {
            // Handle both {text: "...", confidence: 0.9} and simple strings
            const text = typeof item === 'string' ? item : item.text;
            const confidence = typeof item === 'object' && item.confidence !== undefined ? item.confidence : null;
            
            // Only show confidence if NOT a reused/cached result
            if (confidence !== null && !data.reused_existing) {
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
                // Cached/corrected text or no confidence score - show simple text only
                return `
                    <div class="text-line">
                        <div class="text-content">${escapeHtml(text)}</div>
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
    
    // Show correction section
    showCorrectionSection(data);
    
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

// Display individual engine results
function displayEngineResults(engine) {
    let resultsToDisplay = [];
    let title = '';
    
    if (engine === 'paddleocr' && window.currentBenchmarkData && window.currentBenchmarkData.paddleocr && window.currentBenchmarkData.paddleocr.results) {
        resultsToDisplay = window.currentBenchmarkData.paddleocr.results;
        title = '🚀 PaddleOCR Results';
    } else if (engine === 'easyocr' && window.currentBenchmarkData && window.currentBenchmarkData.easyocr && window.currentBenchmarkData.easyocr.results) {
        resultsToDisplay = window.currentBenchmarkData.easyocr.results;
        title = '👁️ EasyOCR Results';
    } else if (engine === 'deepseek' && window.currentBenchmarkData && window.currentBenchmarkData.deepseek && window.currentBenchmarkData.deepseek.results) {
        resultsToDisplay = window.currentBenchmarkData.deepseek.results;
        title = '🤖 DeepSeek Results';
    } else if (engine === 'final' && window.currentFinalOutput) {
        resultsToDisplay = window.currentFinalOutput;
        title = '✨ Final Output (After Voting)';
    }
    
    if (resultsToDisplay.length === 0) {
        return;
    }
    
    // Update the text lines display with engine-specific results
    const textLinesContainer = document.getElementById('textLines');
    const outputHeader = document.querySelector('.output-header h3');
    
    outputHeader.textContent = title;
    
    textLinesContainer.innerHTML = resultsToDisplay.map((item, index) => {
        const text = typeof item === 'string' ? item : item.text;
        const confidence = typeof item === 'object' && item.confidence !== undefined ? item.confidence : null;
        
        if (confidence !== null) {
            const confidencePercent = (confidence * 100).toFixed(1);
            let confidenceClass = 'confidence-low';
            if (confidence >= 0.8) confidenceClass = 'confidence-high';
            else if (confidence >= 0.6) confidenceClass = 'confidence-medium';
            
            return `
                <div class="text-line">
                    <div class="line-number">${index + 1}</div>
                    <div class="text-content">${escapeHtml(text)}</div>
                    <div class="text-confidence">
                        <span class="${confidenceClass}">${confidencePercent}%</span>
                    </div>
                </div>
            `;
        } else {
            return `
                <div class="text-line">
                    <div class="line-number">${index + 1}</div>
                    <div class="text-content">${escapeHtml(text)}</div>
                </div>
            `;
        }
    }).join('');
    
    // Update full text area
    const fullTextArea = document.getElementById('fullText');
    fullTextArea.value = resultsToDisplay.map(item => 
        typeof item === 'string' ? item : item.text
    ).join('\n');
}

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
// Visualization Polling System
let visualizationPollInterval = null;

function startVisualizationPolling(imageHash) {
    // Stop any existing polling
    if (visualizationPollInterval) {
        clearInterval(visualizationPollInterval);
    }
    
    // Show loading indicator
    const vizLoading = document.getElementById('visualizationLoading');
    const vizSection = document.getElementById('visualizationSection');
    if (vizLoading) vizLoading.style.display = 'flex';
    if (vizSection) vizSection.style.display = 'none';
    
    // Start polling every 1 second
    visualizationPollInterval = setInterval(() => {
        checkVisualizationStatus(imageHash);
    }, 1000);
}

async function checkVisualizationStatus(imageHash) {
    try {
        const response = await fetch(`/visualization-status/${imageHash}`);
        const data = await response.json();
        
        if (data.success && data.ready) {
            // Visualization is ready - display it
            displayVisualization(data.images);
            
            // Stop polling
            if (visualizationPollInterval) {
                clearInterval(visualizationPollInterval);
                visualizationPollInterval = null;
            }
        }
    } catch (error) {
        console.error('Error checking visualization status:', error);
    }
}

function displayVisualization(images) {
    const vizLoading = document.getElementById('visualizationLoading');
    const vizSection = document.getElementById('visualizationSection');
    
    if (vizLoading) vizLoading.style.display = 'none';
    if (vizSection) vizSection.style.display = 'block';
    
    // Set image sources
    const bbImg = document.getElementById('vizBoundingBoxes');
    const heatmapImg = document.getElementById('vizHeatmap');
    const lineSegImg = document.getElementById('vizLineSegmentation');
    const combinedImg = document.getElementById('vizCombined');
    
    if (bbImg && images.bounding_boxes) {
        bbImg.src = '/' + images.bounding_boxes;
    }
    if (heatmapImg && images.heatmap) {
        heatmapImg.src = '/' + images.heatmap;
    }
    if (lineSegImg && images.line_segmentation) {
        lineSegImg.src = '/' + images.line_segmentation;
    }
    if (combinedImg && images.combined_analysis) {
        combinedImg.src = '/' + images.combined_analysis;
    }
    
    // Add click to enlarge functionality
    document.querySelectorAll('.viz-image').forEach(img => {
        img.addEventListener('click', function() {
            openImageModal(this.src, this.alt);
        });
    });
}

function openImageModal(imageSrc, imageAlt) {
    // Create modal
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
        cursor: pointer;
    `;
    
    const img = document.createElement('img');
    img.src = imageSrc;
    img.alt = imageAlt;
    img.style.cssText = 'max-width: 90vw; max-height: 90vh; border-radius: 8px;';
    
    modal.appendChild(img);
    modal.addEventListener('click', () => modal.remove());
    
    document.body.appendChild(modal);
}

// ============ TEXT CORRECTION FUNCTIONS ============

async function detectOCRErrors() {
    const text = fullText.value;
    
    if (!text.trim()) {
        showError('Please extract text first');
        return;
    }
    
    correctionLoading.style.display = 'block';
    errorDetection.style.display = 'none';
    
    try {
        const response = await fetch('/detect-errors', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: text })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            displayErrorDetection(result);
        } else {
            showError(result.error || 'Failed to detect errors');
        }
    } catch (error) {
        console.error('❌ Error detection error:', error);
        showError('Failed to detect errors: ' + error.message);
    } finally {
        correctionLoading.style.display = 'none';
    }
}

async function performOCRCorrection() {
    const text = fullText.value;
    
    if (!text.trim()) {
        showError('Please extract text first');
        return;
    }
    
    correctionLoading.style.display = 'block';
    correctionResults.style.display = 'none';
    errorDetection.style.display = 'none';
    
    try {
        const response = await fetch('/correct', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                doc_id: currentDocId,
                confidence_threshold: 'MEDIUM'
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            displayCorrectionResults(result);
        } else {
            showError(result.error || 'Failed to correct text');
        }
    } catch (error) {
        console.error('❌ Correction error:', error);
        showError('Failed to correct text: ' + error.message);
    } finally {
        correctionLoading.style.display = 'none';
    }
}

function displayErrorDetection(result) {
    console.log('📋 Error detection result:', result);
    
    if (!result.errors || result.errors.length === 0) {
        errorsList.innerHTML = '<p style="color: #4caf50;">✓ No errors detected!</p>';
    } else {
        errorsList.innerHTML = result.errors.map(error => {
            const suggestions = error.suggestions || [];
            return `
                <div class="error-item">
                    <div class="error-word">❌ "${error.word}"</div>
                    ${suggestions.length > 0 ? `
                        <div class="error-suggestions">
                            Suggestions: ${suggestions.slice(0, 3).map(s => `<span class="suggestion-badge">${s}</span>`).join(' ')}
                        </div>
                    ` : '<div class="error-suggestions">No suggestions available</div>'}
                </div>
            `;
        }).join('');
    }
    
    errorDetection.style.display = 'block';
}

function displayCorrectionResults(result) {
    console.log('✏️ Correction result:', result);
    
    if (result.success && result.corrected_text) {
        correctedText.value = result.corrected_text;
        errorCount.textContent = `Errors fixed: ${result.errors_found || 0}`;
        correctionResults.style.display = 'block';
    } else {
        showError(result.error || 'Correction failed');
    }
}

function acceptAndSaveCorrection() {
    const originalText = fullText.value;
    const correctedTextValue = correctedText.value;
    
    if (originalText === correctedTextValue) {
        showError('No changes to save');
        return;
    }
    
    // Update the full text with corrected version
    fullText.value = correctedTextValue;
    
    // Hide correction section
    correctionResults.style.display = 'none';
    errorDetection.style.display = 'none';
    
    // Show success message
    const successMsg = document.createElement('div');
    successMsg.className = 'success-message';
    successMsg.style.cssText = `
        background: #4caf50;
        color: white;
        padding: 12px 16px;
        border-radius: 4px;
        margin: 10px 0;
        animation: slideIn 0.3s ease;
    `;
    successMsg.textContent = '✓ Text correction applied successfully!';
    
    correctionSection.insertAdjacentElement('afterend', successMsg);
    
    setTimeout(() => {
        successMsg.remove();
    }, 3000);
}

// Show/hide correction section in displayResults
function showCorrectionSection(data) {
    if (data && data.full_text && correctionSection) {
        correctionSection.style.display = 'block';
        
        // Store doc_id for later use
        if (data.doc_id) {
            currentDocId = data.doc_id;
        }
    }
}