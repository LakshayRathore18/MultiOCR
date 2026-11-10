// Load references separately so a slow search never holds back fresh OCR.
(() => {
    const panel = document.getElementById('similarDocuments');
    const status = document.getElementById('similarDocumentsStatus');
    const list = document.getElementById('similarDocumentsList');
    const retry = document.getElementById('retrySimilarDocuments');
    const more = document.getElementById('moreSimilarDocuments');
    const pageSize = 3;
    let activeRequest = null;
    let lastQuery = null;
    let matches = [];
    let visibleCount = pageSize;

    function element(tag, className, text) {
        const node = document.createElement(tag);
        node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function textSection(title, text, placeholder, docId, source) {
        const section = element('section', `home-similar-source home-similar-source--${source}`);
        section.append(element('h5', '', title));
        const preview = element('div', 'home-similar-preview', text || placeholder);
        preview.setAttribute('tabindex', '0');
        preview.setAttribute('role', 'region');
        preview.setAttribute('aria-label', `${title} for Document #${docId}`);
        section.append(preview);
        if (text) {
            const button = element('button', 'btn btn-secondary btn-small', `Copy ${title}`);
            button.type = 'button';
            button.addEventListener('click', async () => {
                const label = `Copy ${title}`;
                try {
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        await navigator.clipboard.writeText(text);
                    } else {
                        const textarea = document.createElement('textarea');
                        textarea.value = text;
                        textarea.style.position = 'fixed';
                        textarea.style.opacity = '0';
                        document.body.append(textarea);
                        try {
                            textarea.select();
                            if (!document.execCommand('copy')) throw new Error('Copy failed');
                        } finally {
                            textarea.remove();
                        }
                    }
                    button.textContent = 'Copied!';
                } catch {
                    button.textContent = 'Copy failed';
                }
                setTimeout(() => { button.textContent = label; }, 2000);
            });
            section.append(button);
        }
        return section;
    }

    function render() {
        list.replaceChildren();
        for (const doc of matches.slice(0, visibleCount)) {
            const card = element('article', 'text-output home-similar-card');
            const header = element('div', 'home-similar-header');
            header.append(element('h4', '', `Document #${doc.doc_id}`));
            header.append(element('span', 'home-similar-score', `${(doc.score * 100).toFixed(1)}% similarity`));
            card.append(header);
            const source = doc.matched_on === 'raw' ? 'Original OCR' : 'Saved Correction';
            const method = doc.similarity_method === 'jaccard' ? ' (word overlap)' : '';
            card.append(element('p', 'home-similar-match', `Best match: ${source}${method}`));
            const texts = element('div', 'home-similar-texts');
            texts.append(textSection('Original OCR', doc.ocr_text, 'No original OCR available', doc.doc_id, 'raw'));
            texts.append(textSection('Saved Correction', doc.corrected_text, 'No saved correction', doc.doc_id, 'corrected'));
            card.append(texts);
            const view = element('a', 'btn btn-primary btn-small home-similar-view', 'View document');
            view.href = `/review/${encodeURIComponent(doc.doc_id)}`;
            card.append(view);
            list.append(card);
        }
        const shown = Math.min(visibleCount, matches.length);
        status.textContent = matches.length
            ? `Showing ${shown} of ${matches.length} similar documents.`
            : 'No similar documents found.';
        more.hidden = matches.length <= pageSize;
        more.textContent = shown < matches.length ? 'View more' : 'View less';
        more.setAttribute('aria-expanded', String(visibleCount > pageSize));
    }

    window.clearSimilarDocuments = () => {
        if (activeRequest) activeRequest.abort();
        activeRequest = null;
        lastQuery = null;
        matches = [];
        visibleCount = pageSize;
        panel.hidden = true;
        panel.setAttribute('aria-busy', 'false');
        list.replaceChildren();
        status.textContent = '';
        retry.hidden = true;
        more.hidden = true;
        more.setAttribute('aria-expanded', 'false');
    };

    window.loadSimilarDocuments = async (text, docId = null) => {
        window.clearSimilarDocuments();
        if (!text.trim()) return;
        lastQuery = { text, doc_id: docId ?? null };
        const controller = new AbortController();
        activeRequest = controller;
        panel.hidden = false;
        panel.setAttribute('aria-busy', 'true');
        status.textContent = 'Finding similar documents…';
        try {
            const response = await fetch('/similar-documents', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(lastQuery),
                signal: controller.signal
            });
            const data = await response.json();
            if (activeRequest !== controller) return;
            if (!response.ok || !data.success || !Array.isArray(data.similar_docs)) {
                throw new Error('Search unavailable');
            }
            matches = data.similar_docs;
            render();
        } catch (error) {
            if (activeRequest !== controller || error.name === 'AbortError') return;
            status.textContent = 'Could not load similar documents. You can still review your OCR output.';
            retry.hidden = false;
        } finally {
            if (activeRequest === controller) {
                panel.setAttribute('aria-busy', 'false');
                activeRequest = null;
            }
        }
    };

    retry.addEventListener('click', () => {
        if (lastQuery) window.loadSimilarDocuments(lastQuery.text, lastQuery.doc_id);
    });
    more.addEventListener('click', () => {
        visibleCount = visibleCount < matches.length ? visibleCount + pageSize : pageSize;
        render();
    });
})();
