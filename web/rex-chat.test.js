/* Unit tests for the pure rendering helpers.  Run: node --test web/rex-chat.test.js
 *
 * The answer text comes from an LLM, so it is untrusted input that we turn into
 * HTML — escaping is the part worth testing.
 */

const test = require("node:test");
const assert = require("node:assert");

const {
  escapeHtml, renderAnswer, citationLabel, renderInline,
  createSSEParser, trimPartialMarker, typingStep
} = require("./rex-chat.js");

test("escapeHtml neutralises markup", () => {
  assert.strictEqual(
    escapeHtml('<img src=x onerror="alert(1)">'),
    "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"
  );
});

test("renderAnswer does not let LLM output inject HTML", () => {
  const html = renderAnswer('<script>alert(1)</script>', []);
  assert.ok(!html.includes("<script>"), "script tag must not survive");
  assert.ok(html.includes("&lt;script&gt;"));
});

test("renderAnswer links [n] markers to the matching citation", () => {
  const citations = [{ title: "README", url: "https://example.com/readme" }];
  const html = renderAnswer("Usa FastAPI [1].", citations);
  assert.ok(html.includes('href="https://example.com/readme"'));
  assert.ok(html.includes('class="rex-cite-ref"'));
  assert.ok(html.includes(">1</a>"));
});

test("renderAnswer leaves a marker as text when the citation is missing", () => {
  const html = renderAnswer("Afirmación sin fuente [7].", [{ title: "a", url: "u" }]);
  assert.ok(html.includes("[7]"), "unmatched marker stays literal");
  assert.ok(!html.includes("rex-cite-ref"));
});

test("renderAnswer escapes a malicious citation url", () => {
  const citations = [{ title: 'x" onmouseover="alert(1)', url: 'https://e.com/"x' }];
  const html = renderAnswer("Ver [1].", citations);
  assert.ok(!html.includes('onmouseover="alert(1)"'));
  assert.ok(html.includes("&quot;"));
});

test("renderAnswer splits blank lines into paragraphs", () => {
  const html = renderAnswer("uno\n\ndos", []);
  assert.strictEqual(html, "<p>uno</p><p>dos</p>");
});

test("citationLabel formats file and line range", () => {
  assert.strictEqual(
    citationLabel({ file_path: "src/app.py", start_line: 10, end_line: 20 }),
    "src/app.py · L10-20"
  );
  assert.strictEqual(
    citationLabel({ file_path: "src/app.py", start_line: 10, end_line: 10 }),
    "src/app.py · L10"
  );
  assert.strictEqual(
    citationLabel({ section_path: ["Guía", "Instalación"] }),
    "Guía › Instalación"
  );
  assert.strictEqual(citationLabel({}), "");
});

// --- markdown rendering -------------------------------------------------------
// The model answers in markdown. These run on already-escaped text, so the only
// tags that can appear are the ones the renderer adds.

test("bullet lines become a list", () => {
  assert.strictEqual(
    renderAnswer("- uno\n- dos\n- tres", []),
    "<ul><li>uno</li><li>dos</li><li>tres</li></ul>"
  );
});

test("numbered lines become an ordered list", () => {
  assert.strictEqual(renderAnswer("1. uno\n2. dos", []), "<ol><li>uno</li><li>dos</li></ol>");
});

test("a lead-in line before a list stays a paragraph", () => {
  assert.strictEqual(
    renderAnswer("En concreto:\n- uno\n- dos", []),
    "<p>En concreto:</p><ul><li>uno</li><li>dos</li></ul>"
  );
});

test("bold, italics and code render", () => {
  assert.strictEqual(renderInline("**x**"), "<strong>x</strong>");
  assert.strictEqual(renderInline("`x`"), "<code>x</code>");
  assert.strictEqual(renderInline("un *x* y"), "un <em>x</em> y");
});

test("a lone asterisk is not treated as emphasis", () => {
  assert.strictEqual(renderInline("2 * 3 = 6"), "2 * 3 = 6");
});

test("markdown cannot smuggle HTML through the renderer", () => {
  const html = renderAnswer("- <img src=x onerror=alert(1)>\n- **<script>**", []);
  assert.ok(!html.includes("<img"), "img tag must not survive");
  assert.ok(!html.includes("<script>"), "script tag must not survive");
  assert.ok(html.includes("&lt;img"));
});

test("citations still link inside list items", () => {
  const citations = [{ title: "README", url: "https://example.com/r" }];
  const html = renderAnswer("- usa FastAPI [1]", citations);
  assert.ok(html.startsWith("<ul><li>"));
  assert.ok(html.includes('href="https://example.com/r"'));
});

test("plain prose keeps its shape", () => {
  assert.strictEqual(renderAnswer("uno\n\ndos", []), "<p>uno</p><p>dos</p>");
});

/* --- streaming ---------------------------------------------------------------- */

function collect() {
  const events = [];
  const feed = createSSEParser((name, data) => events.push([name, data]));
  return { events, feed };
}

test("SSE parser reassembles events split across chunks", () => {
  const { events, feed } = collect();
  feed('event: draft\ndata: {"citations":[]}\n\nevent: del');
  feed('ta\ndata: {"text":"Ho"}\n');
  feed('\nevent: delta\ndata: {"text":"la"}\n\n');
  assert.deepStrictEqual(events, [
    ["draft", { citations: [] }], ["delta", { text: "Ho" }], ["delta", { text: "la" }]
  ]);
});

test("SSE parser keeps multibyte text and skips malformed events", () => {
  const { events, feed } = collect();
  feed('event: delta\ndata: {"text":"añadió — ✓"}\n\nevent: delta\ndata: {oops\n\n');
  feed('event: done\r\ndata: {"answer":"x"}\r\n\r\n');
  assert.deepStrictEqual(events, [["delta", { text: "añadió — ✓" }], ["done", { answer: "x" }]]);
});

test("an unfinished citation marker is hidden until it closes", () => {
  assert.strictEqual(trimPartialMarker("usa FastAPI ["), "usa FastAPI ");
  assert.strictEqual(trimPartialMarker("usa FastAPI [1"), "usa FastAPI ");
  assert.strictEqual(trimPartialMarker("usa FastAPI [1]"), "usa FastAPI [1]");
});

test("typing speeds up with the backlog but always moves", () => {
  assert.strictEqual(typingStep(1), 2);
  assert.ok(typingStep(600) >= 100);
});
