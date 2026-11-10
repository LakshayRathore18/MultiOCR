// Run with: node --test tests/test_document_status.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function setup() {
    const container = {
        children: [],
        replaceChildren() { this.children = []; },
        append(item) { this.children.push(item); },
    };
    const window = {};
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../web/static/document_status.js'), 'utf8'), {
        window, document: { createElement: () => ({}) },
    });
    return {
        render: data => window.renderDocumentStatus(container, data),
        texts: () => container.children.map(item => item.textContent),
    };
}

test('a fresh OCR draft is explicitly unsaved', () => {
    const ui = setup();
    ui.render({ doc_id: null, has_correction: false, updated_at: null });
    assert.deepEqual(ui.texts(), ['Original OCR', 'Not saved yet']);
});

test('saving and resaving replaces metadata while keeping the original OCR label', () => {
    const ui = setup();
    ui.render({ doc_id: 42, has_correction: true, updated_at: '2026-11-10T12:30:00', cer: 0 });
    assert.equal(ui.texts().length, 4);
    assert.deepEqual(ui.texts().slice(0, 2), ['Original OCR', 'Correction saved']);
    assert.match(ui.texts()[2], /^Last edited: /);
    assert.equal(ui.texts()[3], 'CER: 0.00%');
    const firstTime = ui.texts()[2];
    ui.render({ doc_id: 42, has_correction: true, updated_at: '2026-11-11T12:30:00', cer: 0.12 });
    assert.notEqual(ui.texts()[2], firstTime);
    assert.equal(ui.texts().length, 4);
    assert.equal(ui.texts()[3], 'CER: 12.00%');
    ui.render({ doc_id: null, has_correction: false });
    assert.deepEqual(ui.texts(), ['Original OCR', 'Not saved yet']);
});

test('existing raw-only documents and invalid timestamps do not claim a saved correction', () => {
    const ui = setup();
    ui.render({ doc_id: 9, has_correction: false, updated_at: 'invalid' });
    assert.deepEqual(ui.texts(), ['Original OCR']);
});
