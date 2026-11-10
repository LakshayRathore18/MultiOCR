// Run with: node --test tests/test_similar_documents.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Element {
    constructor(tag = 'div') {
        this.tag = tag;
        this.children = [];
        this.textContent = '';
        this.hidden = false;
        this.style = {};
        this.listeners = {};
        this.attributes = {};
    }
    append(child) { this.children.push(child); }
    replaceChildren(...children) { this.children = children; }
    setAttribute(name, value) { this.attributes[name] = value; }
    addEventListener(event, handler) { this.listeners[event] = handler; }
    set innerHTML(value) { throw new Error('Reference text must not be parsed as HTML'); }
}

function setup(fetcher) {
    const nodes = Object.fromEntries(['similarDocuments', 'similarDocumentsStatus',
        'similarDocumentsList', 'retrySimilarDocuments', 'moreSimilarDocuments'].map(id => [id, new Element()]));
    const copied = [];
    const calls = [];
    const window = {};
    const sandbox = {
        window, AbortController,
        document: { getElementById: id => nodes[id], createElement: tag => new Element(tag) },
        navigator: { clipboard: { writeText: async text => { copied.push(text); } } },
        fetch: async (...args) => { calls.push(args); return fetcher(...args); },
        setTimeout: () => {},
    };
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../web/static/similar_documents.js'), 'utf8'), sandbox);
    return { window, nodes, copied, calls };
}

const response = matches => ({ ok: true, json: async () => ({ success: true, similar_docs: matches }) });
const match = (source, correction = 'धर्मः "saved"\n<script>saved</script>') => ({
    doc_id: 42, score: 0.9, matched_on: source, similarity_method: 'cosine',
    ocr_text: 'धर्म "OCR"\n<script>raw</script>', corrected_text: correction,
});

test('either winning source shows both literal texts with independent copy buttons', async () => {
    for (const source of ['raw', 'corrected']) {
        const doc = match(source);
        const { window, nodes, copied, calls } = setup(async () => response([doc]));
        await window.loadSimilarDocuments('fresh output', 7);
        assert.equal(nodes.similarDocuments.hidden, false);
        assert.deepEqual(JSON.parse(calls[0][1].body), { text: 'fresh output', doc_id: 7 });
        const card = nodes.similarDocumentsList.children[0];
        const [raw, saved] = card.children[2].children;
        assert.equal(raw.children[0].textContent, 'Original OCR');
        assert.equal(saved.children[0].textContent, 'Saved Correction');
        assert.equal(raw.children[1].textContent, doc.ocr_text);
        assert.equal(saved.children[1].textContent, doc.corrected_text);
        for (const section of [raw, saved]) {
            assert.equal(section.children[1].attributes.tabindex, '0');
            assert.equal(section.children[1].attributes.role, 'region');
            assert.match(section.children[1].attributes['aria-label'], /Document #42/);
        }
        await raw.children[2].listeners.click();
        await saved.children[2].listeners.click();
        assert.deepEqual(copied, [doc.ocr_text, doc.corrected_text]);
        assert.equal(card.children[3].href, '/review/42');
        assert.equal(nodes.similarDocuments.attributes['aria-busy'], 'false');
    }
});

test('missing correction remains visible without a correction copy button', async () => {
    const { window, nodes } = setup(async () => response([match('raw', null)]));
    await window.loadSimilarDocuments('fresh output');
    const saved = nodes.similarDocumentsList.children[0].children[2].children[1];
    assert.equal(saved.children[1].textContent, 'No saved correction');
    assert.equal(saved.children.length, 2);
});

test('loading and no-match states appear without changing OCR', async () => {
    let finish;
    const { window, nodes } = setup(() => new Promise(resolve => { finish = resolve; }));
    const pending = window.loadSimilarDocuments('fresh output');
    assert.match(nodes.similarDocumentsStatus.textContent, /Finding similar/);
    assert.equal(nodes.similarDocuments.attributes['aria-busy'], 'true');
    finish(response([]));
    await pending;
    assert.equal(nodes.similarDocumentsStatus.textContent, 'No similar documents found.');
    assert.equal(nodes.similarDocumentsList.children.length, 0);
});

test('failure offers retry and a later search can succeed', async () => {
    let fail = true;
    const { window, nodes, calls } = setup(async () => {
        if (fail) throw new Error('offline');
        return response([match('raw')]);
    });
    await window.loadSimilarDocuments('fresh output');
    assert.match(nodes.similarDocumentsStatus.textContent, /Could not load/);
    assert.equal(nodes.retrySimilarDocuments.hidden, false);
    fail = false;
    // The retry listener starts the same async search automatically.
    nodes.retrySimilarDocuments.listeners.click();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(calls.length, 2);
    assert.equal(nodes.retrySimilarDocuments.hidden, true);
    assert.equal(nodes.similarDocumentsList.children.length, 1);
});

test('old responses cannot replace references for a newer upload', async () => {
    const pending = [];
    const { window, nodes, calls } = setup(() => new Promise(resolve => pending.push(resolve)));
    const oldSearch = window.loadSimilarDocuments('old upload');
    const newSearch = window.loadSimilarDocuments('new upload');
    assert.equal(calls[0][1].signal.aborted, true);
    pending[1](response([match('corrected')]));
    await newSearch;
    pending[0](response([]));
    await oldSearch;
    assert.equal(nodes.similarDocumentsList.children.length, 1);
    window.clearSimilarDocuments();
    assert.equal(nodes.similarDocuments.hidden, true);
    assert.equal(nodes.similarDocumentsList.children.length, 0);
});

test('clearing the upload discards a still-running search and empty text stays hidden', async () => {
    let finish;
    const { window, nodes, calls } = setup(() => new Promise(resolve => { finish = resolve; }));
    const pending = window.loadSimilarDocuments('old upload');
    window.clearSimilarDocuments();
    finish(response([match('raw')]));
    await pending;
    assert.equal(nodes.similarDocuments.hidden, true);
    assert.equal(nodes.similarDocumentsList.children.length, 0);
    await window.loadSimilarDocuments(' ');
    assert.equal(calls.length, 1);
});

test('top three retain ranking, view more adds three, and view less restores the top three', async () => {
    const matches = Array.from({ length: 7 }, (_, index) => ({ ...match('raw'), doc_id: 70 - index }));
    const { window, nodes } = setup(async () => response(matches));
    await window.loadSimilarDocuments('fresh output');
    const ids = () => nodes.similarDocumentsList.children.map(card => card.children[0].children[0].textContent);
    assert.deepEqual(ids(), ['Document #70', 'Document #69', 'Document #68']);
    assert.equal(nodes.moreSimilarDocuments.hidden, false);
    assert.equal(nodes.moreSimilarDocuments.attributes['aria-expanded'], 'false');
    nodes.moreSimilarDocuments.listeners.click();
    assert.equal(nodes.similarDocumentsList.children.length, 6);
    assert.equal(nodes.moreSimilarDocuments.textContent, 'View more');
    nodes.moreSimilarDocuments.listeners.click();
    assert.equal(nodes.similarDocumentsList.children.length, 7);
    assert.equal(nodes.moreSimilarDocuments.textContent, 'View less');
    assert.equal(nodes.moreSimilarDocuments.attributes['aria-expanded'], 'true');
    nodes.moreSimilarDocuments.listeners.click();
    assert.deepEqual(ids(), ['Document #70', 'Document #69', 'Document #68']);
    assert.equal(nodes.moreSimilarDocuments.textContent, 'View more');
    window.clearSimilarDocuments();
    assert.equal(nodes.moreSimilarDocuments.hidden, true);
    await window.loadSimilarDocuments('another upload');
    assert.equal(nodes.similarDocumentsList.children.length, 3);
});

test('view more stays hidden when there are at most three matches', async () => {
    for (const count of [0, 1, 2, 3]) {
        const matches = Array.from({ length: count }, () => match('raw'));
        const { window, nodes } = setup(async () => response(matches));
        await window.loadSimilarDocuments('fresh output');
        assert.equal(nodes.similarDocumentsList.children.length, count);
        assert.equal(nodes.moreSimilarDocuments.hidden, true);
    }
});
