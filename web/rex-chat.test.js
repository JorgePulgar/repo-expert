/* Unit tests for the pure rendering helpers.  Run: node --test web/
 *
 * The answer text comes from an LLM, so it is untrusted input that we turn into
 * HTML — escaping is the part worth testing.
 */

const test = require("node:test");
const assert = require("node:assert");

const { escapeHtml, renderAnswer, citationLabel } = require("./rex-chat.js");

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
