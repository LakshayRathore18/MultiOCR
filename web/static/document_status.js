// The OCR text stays original; save information describes its paired correction.
(() => {
    window.renderDocumentStatus = (container, data) => {
        container.replaceChildren();
        const add = (text, className = '') => {
            const item = document.createElement('span');
            item.className = className;
            item.textContent = text;
            container.append(item);
        };
        add('Original OCR');
        if (data.has_correction) add('Correction saved', 'document-correction-saved');
        else if (!data.doc_id) add('Not saved yet');
        if (data.updated_at) {
            const date = new Date(data.updated_at);
            if (!Number.isNaN(date.getTime())) add(`Last edited: ${date.toLocaleString()}`);
        }
        if (data.cer !== undefined && data.cer !== null) {
            add(`CER: ${(data.cer * 100).toFixed(2)}%`);
        }
    };
})();
