/* Repo Expert chat client — vanilla JS, no build step, no dependencies.
 *
 * Usage (the host page supplies the backend URL, it is never hard-coded here):
 *
 *   <link rel="stylesheet" href="rex-chat.css">
 *   <div id="rex-chat" data-api="https://ca-repo-expert.example.azurecontainerapps.io"></div>
 *   <script src="rex-chat.js"></script>
 *
 * Contract (see repo-expert/src/repo_expert/api/schemas.py):
 *   POST /ask  {question, history: [{question, answer}, ...]}
 *     -> {answer, citations[], route[], grounded, fallback_used}
 *        citations[i] = {title, url, file_path?, section_path[], start_line?, end_line?}
 *        `answer` carries inline [n] markers, 1-based, into citations[n-1].
 *   GET /health -> liveness; NOT rate-limited, so it is safe as a warm-up ping.
 *
 * The service is stateless: it keeps no conversation, so this client owns the
 * transcript and replays the recent turns with every question. That is what makes
 * follow-ups like "explícame más del primero" work, and it means any replica can
 * serve any turn.
 */

(function () {
  "use strict";

  var DEFAULTS = {
    // The backend sleeps at zero replicas; a cold start takes a few seconds.
    wakingAfterMs: 4000,
    rotateEveryMs: 6000,
    timeoutMs: 120000,
    historyTurns: 5,
    visibleSources: 3,
    starters: [
      "¿Qué experiencia tiene Jorge con sistemas RAG?",
      "¿Qué proyectos ha construido?",
      "¿Qué stack usa en producción?"
    ]
  };

  var TEXT = {
    headLabel: "Chat en vivo",
    headHint: "Pregunta aquí — debajo del chat explico cómo funciona y qué límites tiene.",
    emptyTitle: "Pregúntame sobre la experiencia y los proyectos de Jorge.",
    emptyBody: "Responde con citas que enlazan al documento exacto. Empieza por una de estas:",
    startersLabel: "Prueba con",
    placeholder: "Escribe tu pregunta…",
    send: "Enviar",
    you: "Tú",
    assistant: "Repo Expert",
    thinking: "Buscando en el índice y redactando…",
    // Shown once, on the first slow request of the session: the container really
    // is asleep. After that it is awake, so repeating it would be a lie — the
    // later messages just keep the visitor company while the model writes.
    waking: "Despertando el servidor (duerme cuando no se usa)…",
    waiting: [
      "No estoy roto, estoy pensando…",
      "Leyendo mis propios repos, dame un segundo…",
      "Buscando la cita exacta, no me gusta inventar…",
      "Esto lo escribe un modelo pequeño y barato, ten paciencia…",
      "Cruzando documentación, código y CV…",
      "Prefiero tardar y citar que responder rápido y mentir…",
      "Casi… prometo que hay una respuesta al final de esto."
    ],
    sources: "Fuentes",
    noSources: "Sin fuentes citadas.",
    moreSources: function (n) { return "Ver las " + n + " fuentes ↓"; },
    fewerSources: "Ver menos ↑",
    ungrounded: "respuesta no verificada",
    fallback: "búsqueda ampliada",
    errorGeneric: "No he podido responder. Inténtalo de nuevo en unos segundos.",
    errorNetwork: "No se puede contactar con el servidor. Puede estar arrancando; reinténtalo.",
    errorTimeout: "El servidor ha tardado demasiado. Reinténtalo.",
    rateLimited: function (mins) {
      return "Has alcanzado el límite de preguntas por hora. Vuelve a intentarlo en " +
        mins + " minuto(s).";
    },
    empty: "Escribe una pregunta primero."
  };

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  /* Answers come from an LLM, so they are untrusted text: never assign them as HTML
     without escaping first. */
  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  /* Turn inline [n] markers into links to citations[n-1]. Markers with no matching
     citation are left as plain text rather than linking somewhere wrong. */
  function renderAnswer(answer, citations) {
    var safe = escapeHtml(answer);
    safe = safe.replace(/\[(\d{1,2})\]/g, function (match, digits) {
      var index = parseInt(digits, 10) - 1;
      var citation = citations && citations[index];
      if (!citation || !citation.url) return match;
      return '<a class="rex-cite-ref" href="' + escapeHtml(citation.url) +
        '" target="_blank" rel="noopener noreferrer" title="' +
        escapeHtml(citation.title || "") + '">' + digits + "</a>";
    });
    return safe
      .split(/\n{2,}/)
      .map(function (block) { return "<p>" + block.replace(/\n/g, "<br>") + "</p>"; })
      .join("");
  }

  function citationLabel(citation) {
    var bits = [];
    if (citation.file_path) bits.push(citation.file_path);
    if (citation.start_line) {
      bits.push(
        citation.end_line && citation.end_line !== citation.start_line
          ? "L" + citation.start_line + "-" + citation.end_line
          : "L" + citation.start_line
      );
    }
    if (!bits.length && citation.section_path && citation.section_path.length) {
      bits.push(citation.section_path.join(" › "));
    }
    return bits.join(" · ");
  }

  function RexChat(root) {
    var api = (root.getAttribute("data-api") || "").replace(/\/+$/, "");
    if (!api) {
      root.appendChild(el("p", "rex-status rex-status-error",
        "rex-chat: falta el atributo data-api con la URL del backend."));
      return;
    }

    var startersAttr = root.getAttribute("data-starters");
    var starters = DEFAULTS.starters;
    if (startersAttr) {
      try {
        var parsed = JSON.parse(startersAttr);
        if (Array.isArray(parsed) && parsed.length) starters = parsed;
      } catch (err) {
        /* keep defaults when the attribute is not valid JSON */
      }
    }

    /* A starter is either a plain string, or {q, short}. The short form is what
       phones show: full questions are too wide to fit side by side, and a row
       that scrolls sideways is not discoverable on a touch screen. */
    starters = starters.map(function (s) {
      if (typeof s === "string") return { q: s, short: s };
      return { q: s.q || s.question || "", short: s.short || s.q || s.question || "" };
    }).filter(function (s) { return s.q; });

    root.classList.add("rex-chat");

    /* A header and an empty state, so the block reads as a chat within a second
       rather than as loose sentences on the page. */
    var head = el("div", "rex-head");
    var headLabel = el("div", "rex-head-label");
    headLabel.appendChild(el("span", "rex-dot"));
    headLabel.appendChild(el("span", null, TEXT.headLabel));
    head.appendChild(headLabel);
    head.appendChild(el("div", "rex-head-hint", TEXT.headHint));

    var log = el("div", "rex-log");
    log.setAttribute("role", "log");
    log.setAttribute("aria-live", "polite");
    log.setAttribute("aria-label", "Conversación");

    var empty = el("div", "rex-empty");
    empty.appendChild(el("strong", null, TEXT.emptyTitle));
    // Own class so very short viewports can drop the second line and keep the
    // composer on screen.
    empty.appendChild(el("span", "rex-empty-body", TEXT.emptyBody));
    log.appendChild(empty);

    var startersLabel = el("div", "rex-starters-label", TEXT.startersLabel);
    var starterBar = el("div", "rex-starters");
    starters.forEach(function (starter) {
      var button = el("button", "rex-starter");
      button.type = "button";
      // Both labels ship; CSS shows one per breakpoint. aria-label keeps the full
      // question for screen readers regardless of which is visible.
      button.setAttribute("aria-label", starter.q);
      button.setAttribute("title", starter.q);
      button.appendChild(el("span", "rex-starter-long", starter.q));
      button.appendChild(el("span", "rex-starter-short", starter.short));
      button.addEventListener("click", function () { submit(starter.q); });
      starterBar.appendChild(button);
    });

    var form = el("form", "rex-form");
    var input = el("textarea", "rex-input");
    input.rows = 1;
    input.placeholder = TEXT.placeholder;
    input.setAttribute("aria-label", TEXT.placeholder);
    var send = el("button", "rex-send", TEXT.send);
    send.type = "submit";
    form.appendChild(input);
    form.appendChild(send);

    var status = el("div", "rex-status");
    status.setAttribute("aria-live", "polite");

    root.appendChild(head);
    root.appendChild(log);
    root.appendChild(startersLabel);
    root.appendChild(starterBar);
    root.appendChild(form);
    root.appendChild(status);

    var busy = false;
    var hasWokenUp = false;   // the cold start only happens once per session
    // The server keeps no session, so the client owns the conversation and sends
    // the recent turns with every question. Capped to match the API's limit and to
    // keep the prompt from crowding out retrieved sources.
    var turns = [];

    function setBusy(value) {
      busy = value;
      send.disabled = value;
      input.disabled = value;
      Array.prototype.forEach.call(
        starterBar.querySelectorAll(".rex-starter"),
        function (b) { b.disabled = value; }
      );
    }

    function setStatus(message, opts) {
      status.className = "rex-status" + (opts && opts.error ? " rex-status-error" : "");
      status.textContent = "";
      if (!message) return;
      if (opts && opts.spinner) status.appendChild(el("span", "rex-spinner"));
      status.appendChild(el("span", null, message));
    }

    function addMessage(role, roleLabel) {
      if (empty && empty.parentNode) empty.parentNode.removeChild(empty);
      var wrap = el("div", "rex-msg rex-msg-" + role);
      wrap.appendChild(el("div", "rex-msg-role", roleLabel));
      var bubble = el("div", "rex-bubble");
      wrap.appendChild(bubble);
      log.appendChild(wrap);
      log.scrollTop = log.scrollHeight;
      return bubble;
    }

    function renderSources(bubble, data) {
      var citations = data.citations || [];
      var box = el("div", "rex-sources");
      box.appendChild(el("div", "rex-sources-title", TEXT.sources));
      if (!citations.length) {
        box.appendChild(el("p", "rex-source-meta", TEXT.noSources));
      } else {
        var list = document.createElement("ol");
        var hidden = [];
        citations.forEach(function (citation, index) {
          var item = document.createElement("li");
          var link = el("a", null, citation.title || citation.url);
          link.href = citation.url;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          item.appendChild(link);
          var meta = citationLabel(citation);
          if (meta) {
            item.appendChild(document.createTextNode(" "));
            item.appendChild(el("span", "rex-source-meta", "— " + meta));
          }
          // A dozen sources buries the answer above them. Show a few; the rest
          // stay one click away, and the inline [n] links always work either way.
          if (index >= DEFAULTS.visibleSources) {
            item.hidden = true;
            hidden.push(item);
          }
          list.appendChild(item);
        });
        box.appendChild(list);

        if (hidden.length) {
          var toggle = el("button", "rex-sources-toggle", TEXT.moreSources(citations.length));
          toggle.type = "button";
          toggle.setAttribute("aria-expanded", "false");
          toggle.addEventListener("click", function () {
            var expanded = toggle.getAttribute("aria-expanded") === "true";
            hidden.forEach(function (item) { item.hidden = expanded; });
            toggle.setAttribute("aria-expanded", expanded ? "false" : "true");
            toggle.textContent = expanded
              ? TEXT.moreSources(citations.length)
              : TEXT.fewerSources;
          });
          box.appendChild(toggle);
        }
      }

      var badges = el("div", "rex-badges");
      if (data.route && data.route.length) {
        badges.appendChild(el("span", "rex-badge", data.route.join(" + ")));
      }
      if (data.fallback_used) {
        badges.appendChild(el("span", "rex-badge", TEXT.fallback));
      }
      if (data.grounded === false) {
        badges.appendChild(el("span", "rex-badge rex-badge-warn", TEXT.ungrounded));
      }
      if (badges.childNodes.length) box.appendChild(badges);

      bubble.appendChild(box);
    }

    function submit(question) {
      if (busy) return;
      question = (question || "").trim();
      if (!question) {
        setStatus(TEXT.empty, { error: true });
        return;
      }

      addMessage("user", TEXT.you).textContent = question;
      input.value = "";
      setBusy(true);
      setStatus(TEXT.thinking, { spinner: true });

      // First slow request of the session: the container is genuinely asleep.
      // Afterwards it is awake, so rotate through lighter lines instead of
      // repeating a message that is no longer true.
      var messages = hasWokenUp
        ? TEXT.waiting.slice()
        : [TEXT.waking].concat(TEXT.waiting);
      var messageIndex = 0;
      var rotateTimer = null;

      var wakingTimer = setTimeout(function () {
        setStatus(messages[messageIndex], { spinner: true });
        rotateTimer = setInterval(function () {
          messageIndex = (messageIndex + 1) % messages.length;
          setStatus(messages[messageIndex], { spinner: true });
        }, DEFAULTS.rotateEveryMs);
      }, DEFAULTS.wakingAfterMs);

      var controller = new AbortController();
      var timeoutTimer = setTimeout(function () { controller.abort(); }, DEFAULTS.timeoutMs);

      fetch(api + "/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: question,
          history: turns.slice(-DEFAULTS.historyTurns)
        }),
        signal: controller.signal
      })
        .then(function (response) {
          if (response.status === 429) {
            var retryAfter = parseInt(response.headers.get("Retry-After") || "0", 10);
            var mins = retryAfter ? Math.ceil(retryAfter / 60) : 60;
            var err = new Error("rate-limited");
            err.userMessage = TEXT.rateLimited(mins);
            throw err;
          }
          if (!response.ok) throw new Error("HTTP " + response.status);
          return response.json();
        })
        .then(function (data) {
          var bubble = addMessage("assistant", TEXT.assistant);
          bubble.innerHTML = renderAnswer(data.answer || "", data.citations);
          turns.push({ question: question, answer: data.answer || "" });
          renderSources(bubble, data);
          log.scrollTop = log.scrollHeight;
          setStatus("");
        })
        .catch(function (error) {
          var message = error.userMessage ||
            (error.name === "AbortError" ? TEXT.errorTimeout :
              (error instanceof TypeError ? TEXT.errorNetwork : TEXT.errorGeneric));
          setStatus(message, { error: true });
        })
        .then(function () {
          clearTimeout(wakingTimer);
          clearInterval(rotateTimer);
          clearTimeout(timeoutTimer);
          hasWokenUp = true;
          setBusy(false);
          input.focus();
        });
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      submit(input.value);
    });

    // Enter sends, Shift+Enter makes a newline.
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        submit(input.value);
      }
    });

    // Grow the textarea with its content, up to the CSS max-height.
    input.addEventListener("input", function () {
      input.style.height = "auto";
      input.style.height = Math.min(input.scrollHeight, 144) + "px";
    });

    /* Warm-up ping: the container scales to zero, so the first real question would
       otherwise pay the cold start. /health is not rate-limited, so this is free. */
    fetch(api + "/health", { method: "GET" }).catch(function () {
      /* ignore: a failed warm-up is not worth showing, the question will report it */
    });
  }

  function init() {
    Array.prototype.forEach.call(
      document.querySelectorAll("[data-api].rex-chat, #rex-chat[data-api]"),
      RexChat
    );
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  }

  /* Exposed for unit tests under `node --test`; `module` is undefined in a browser,
     so this is inert when the file is loaded with a <script> tag. */
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { escapeHtml: escapeHtml, renderAnswer: renderAnswer, citationLabel: citationLabel };
  }
})();
