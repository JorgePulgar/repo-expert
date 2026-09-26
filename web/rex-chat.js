/* Repo Expert chat client — vanilla JS, no build step, no dependencies.
 *
 * Usage (the host page supplies the backend URL, it is never hard-coded here):
 *
 *   <link rel="stylesheet" href="rex-chat.css">
 *   <div id="rex-chat" data-api="https://ca-repo-expert.example.azurecontainerapps.io"></div>
 *   <script src="rex-chat.js"></script>
 *
 * Optional attributes on the mount div: data-starters (JSON list of starter
 * questions) and data-hint (header hint text; empty string hides it).
 *
 * Contract (see repo-expert/src/repo_expert/api/schemas.py):
 *   POST /ask  {question, history: [{question, answer}, ...]}
 *     -> {answer, citations[], route[], grounded, fallback_used}
 *        citations[i] = {title, url, file_path?, section_path[], start_line?, end_line?}
 *        `answer` carries inline [n] markers, 1-based, into citations[n-1].
 *   POST /ask/stream  same body -> server-sent events, in order:
 *        stage {stage}      what the agent is doing: retrieve | generate | verify | widen
 *        draft {citations}  sources for the text that follows (a second one replaces it)
 *        delta {text}       answer text as the model writes it
 *        done  {...}        the full /ask response; authoritative over the deltas
 *        error {kind}       busy | content_filter | internal
 *     Used when available; a backend without it (404) falls back to /ask.
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
    emptyBody: "Responde con citas que enlazan al documento exacto. Tienes preguntas sugeridas justo debajo.",
    startersLabel: "Preguntas sugeridas",
    placeholder: "Escribe tu pregunta…",
    send: "Enviar",
    you: "Tú",
    assistant: "Repo Expert",
    thinking: "Buscando en el índice y redactando…",
    // Shown once, on the first slow request of the session: the container really
    // is asleep. After that it is awake, so repeating it would be a lie.
    waking: "Despertando el servidor (duerme cuando no se usa)…",
    waitingAgain: "No estoy roto, estoy pensando…",
    stages: {
      retrieve: "Buscando en el índice…",
      generate: "Redactando la respuesta…",
      verify: "Comprobando la respuesta con las fuentes…",
      widen: "Ampliando la búsqueda…"
    },
    sources: "Fuentes",
    noSources: "Sin fuentes citadas.",
    moreSources: function (n) { return "Ver las " + n + " fuentes ↓"; },
    fewerSources: "Ver menos ↑",
    ungrounded: "respuesta no verificada",
    fallback: "búsqueda ampliada",
    errorGeneric: "No he podido responder. Inténtalo de nuevo en unos segundos.",
    errorNetwork: "No se puede contactar con el servidor. Puede estar arrancando; reinténtalo.",
    errorTimeout: "El servidor ha tardado demasiado. Reinténtalo.",
    errorBusy: "Hay mucha demanda ahora mismo. Reinténtalo en unos segundos.",
    errorFiltered: "No puedo responder a eso. Pregúntame por la experiencia o los proyectos de Jorge.",
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

  /* Inline markdown, applied to text that is ALREADY escaped, so the result can only
     contain the tags added here. Deliberately small — bold, italics and code are what
     the model actually emits; supporting links or raw HTML would hand an LLM a way to
     put arbitrary markup on the page. */
  function renderInline(escaped) {
    return escaped
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,;:!?]|$)/g, "$1<em>$2</em>");
  }

  var BULLET = /^\s*[-*•]\s+/;
  var NUMBERED = /^\s*\d+[.)]\s+/;

  /* Render one blank-line-separated block as a list or a paragraph. The model answers
     in markdown, and a wall of literal "- " lines reads as noise. */
  function renderBlock(block) {
    var lines = block.split("\n").filter(function (l) { return l.trim() !== ""; });
    if (!lines.length) return "";

    if (lines.every(function (l) { return BULLET.test(l); })) {
      return "<ul>" + lines.map(function (l) {
        return "<li>" + renderInline(l.replace(BULLET, "")) + "</li>";
      }).join("") + "</ul>";
    }
    if (lines.every(function (l) { return NUMBERED.test(l); })) {
      return "<ol>" + lines.map(function (l) {
        return "<li>" + renderInline(l.replace(NUMBERED, "")) + "</li>";
      }).join("") + "</ol>";
    }

    // A lead-in line followed by items ("En concreto:" then bullets) is common. Split
    // it rather than forcing one shape on the whole block.
    for (var i = 0; i < lines.length; i++) {
      if (BULLET.test(lines[i]) || NUMBERED.test(lines[i])) {
        if (i === 0) break;
        return renderBlock(lines.slice(0, i).join("\n")) +
          renderBlock(lines.slice(i).join("\n"));
      }
    }
    return "<p>" + renderInline(lines.join("<br>")) + "</p>";
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
    return safe.split(/\n{2,}/).map(renderBlock).join("");
  }

  /* While text is still arriving, hide a citation marker that has not closed yet
     ("[1" of "[12]"), so it does not flash as literal text before becoming a link. */
  function trimPartialMarker(text) {
    return text.replace(/\[\d{0,2}$/, "");
  }

  /* Server-sent events parser for a fetch() body (EventSource cannot POST). Feed it
     decoded text in any chunking; it calls onEvent(name, data) per complete event. */
  function createSSEParser(onEvent) {
    var buffer = "";
    return function feed(chunk) {
      buffer += chunk.replace(/\r\n/g, "\n");
      var end;
      while ((end = buffer.indexOf("\n\n")) !== -1) {
        var block = buffer.slice(0, end);
        buffer = buffer.slice(end + 2);
        var name = "message";
        var data = [];
        block.split("\n").forEach(function (line) {
          if (line.indexOf("event:") === 0) name = line.slice(6).trim();
          else if (line.indexOf("data:") === 0) data.push(line.slice(5).replace(/^ /, ""));
        });
        if (!data.length) continue;
        var parsed;
        try {
          parsed = JSON.parse(data.join("\n"));
        } catch (err) {
          continue;  /* a malformed event is skipped, not fatal */
        }
        onEvent(name, parsed);
      }
    };
  }

  /* How many characters to reveal on the next frame. The model delivers text in
     bursts; showing each burst as it lands reads as jumps. Revealing a fraction of
     the backlog per frame gives a steady pace that speeds up when text piles up and
     never falls far behind. */
  function typingStep(backlog) {
    return Math.max(2, Math.ceil(backlog / 6));
  }

  /* Reveals streamed text into `bubble` a few characters per frame. finish() resolves
     once everything received has been shown. */
  function createTyper(bubble) {
    var target = "";
    var shown = 0;
    var citations = [];
    var frame = null;
    var whenCaughtUp = null;
    var reduceMotion = typeof window !== "undefined" && window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function paint() {
      bubble.innerHTML = renderAnswer(trimPartialMarker(target.slice(0, shown)), citations);
    }

    function tick() {
      frame = null;
      var backlog = target.length - shown;
      if (backlog > 0) {
        // Hidden tabs get no animation frames; don't leave the text stuck there.
        shown += (reduceMotion || document.hidden) ? backlog : typingStep(backlog);
        paint();
      }
      if (shown < target.length) {
        frame = requestAnimationFrame(tick);
      } else if (whenCaughtUp) {
        var resolve = whenCaughtUp;
        whenCaughtUp = null;
        resolve();
      }
    }

    function schedule() {
      if (frame === null) frame = requestAnimationFrame(tick);
    }

    return {
      started: function () { return target.length > 0; },
      reset: function (nextCitations) {
        target = "";
        shown = 0;
        citations = nextCitations || [];
        bubble.innerHTML = "";
      },
      push: function (text) {
        target += text;
        schedule();
      },
      finish: function (finalText) {
        // The final answer is authoritative; normally it equals what was streamed.
        if (finalText !== target) {
          target = finalText;
          shown = Math.min(shown, target.length);
        }
        return new Promise(function (resolve) {
          if (document.hidden) shown = target.length;
          whenCaughtUp = resolve;
          if (frame !== null) cancelAnimationFrame(frame);
          frame = null;
          tick();
        });
      }
    };
  }

  var CAN_STREAM = typeof ReadableStream !== "undefined" &&
    typeof TextDecoder !== "undefined" &&
    typeof ReadableStream.prototype.getReader === "function";

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

  function matches(query) {
    return !!(window.matchMedia && window.matchMedia(query).matches);
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
    /* The default hint describes a page that explains the chat below it. A host
       page with a different layout overrides it with data-hint; an empty value
       drops the hint altogether. */
    var hint = root.hasAttribute("data-hint") ? root.getAttribute("data-hint") : TEXT.headHint;
    if (hint) head.appendChild(el("div", "rex-head-hint", hint));

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

    /* Phones get the starters as a collapsed dropdown: open, the three full
       questions stacked take more height than the conversation itself. Wider
       screens keep them open as a row of chips. */
    var compact = matches("(max-width: 600px)");
    var startersBox = el("details", "rex-starters-box");
    startersBox.open = !compact;
    var startersLabel = el("summary", "rex-starters-label", TEXT.startersLabel);
    var starterBar = el("div", "rex-starters");
    startersBox.appendChild(startersLabel);
    startersBox.appendChild(starterBar);
    starters.forEach(function (starter) {
      var button = el("button", "rex-starter");
      button.type = "button";
      // Both labels ship; CSS shows one per breakpoint. aria-label keeps the full
      // question for screen readers regardless of which is visible.
      button.setAttribute("aria-label", starter.q);
      button.setAttribute("title", starter.q);
      button.appendChild(el("span", "rex-starter-long", starter.q));
      button.appendChild(el("span", "rex-starter-short", starter.short));
      button.addEventListener("click", function () {
        if (compact) startersBox.open = false;
        submit(starter.q);
      });
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
    root.appendChild(startersBox);
    root.appendChild(form);
    root.appendChild(status);

    var touch = matches("(pointer: coarse)");
    var busy = false;
    var hasWokenUp = false;   // the cold start only happens once per session
    // data-stream="off" forces the plain /ask request (e.g. to compare the two).
    var streamOn = CAN_STREAM && root.getAttribute("data-stream") !== "off";
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

    /* Bring the whole card into view: centred when it fits the screen, otherwise
       aligned to its bottom so the latest message and the composer both show. The
       host page's scroll-padding keeps it clear of fixed headers and bottom bars. */
    function revealCard() {
      if (!root.scrollIntoView) return;
      var fits = root.getBoundingClientRect().height <= window.innerHeight * 0.85;
      root.scrollIntoView({
        block: fits ? "center" : "end",
        behavior: matches("(prefers-reduced-motion: reduce)") ? "auto" : "smooth"
      });
    }

    function addMessage(role, roleLabel) {
      if (empty && empty.parentNode) empty.parentNode.removeChild(empty);
      // First message: from here on phones give the card the full screen height.
      root.classList.add("rex-active");
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

      var questionBubble = addMessage("user", TEXT.you);
      questionBubble.textContent = question;
      input.value = "";
      input.style.height = "";
      // On touch screens drop the keyboard, so the answer has the screen to itself.
      if (touch) input.blur();
      revealCard();
      setBusy(true);
      setStatus(TEXT.thinking, { spinner: true });

      // First slow request of the session: the container is genuinely asleep.
      // Afterwards it is awake, so say something that is still true.
      var slowMessage = hasWokenUp ? TEXT.waitingAgain : TEXT.waking;
      var wakingTimer = setTimeout(function () {
        setStatus(slowMessage, { spinner: true });
      }, DEFAULTS.wakingAfterMs);

      var controller = new AbortController();
      var timeoutTimer = setTimeout(function () { controller.abort(); }, DEFAULTS.timeoutMs);
      var body = JSON.stringify({
        question: question,
        history: turns.slice(-DEFAULTS.historyTurns)
      });

      var bubble = null;
      var typer = null;

      /* Scroll once, so the question sits at the top of the log and the answer starts
         right below it; then leave the scrolling to the reader. Following the text
         down as it arrives would move the lines they are reading out of view. */
      function startAnswer() {
        bubble = addMessage("assistant", TEXT.assistant);
        var row = questionBubble.parentNode;
        log.scrollTop = row.getBoundingClientRect().top -
          log.getBoundingClientRect().top + log.scrollTop - 8;
      }

      function awake() {
        // Any response means the container is up: stop the "waking" message.
        clearTimeout(wakingTimer);
      }

      var handlers = {
        open: awake,
        stage: function (data) {
          var message = TEXT.stages[data.stage];
          // Before the text starts, every stage is news. Once it is on screen, only
          // the check that follows it and a widened search are worth interrupting.
          if (message && (!typer || data.stage === "verify" || data.stage === "widen")) {
            setStatus(message, { spinner: true });
          }
        },
        draft: function (data) {
          if (!bubble) {
            startAnswer();
            typer = createTyper(bubble);
            log.setAttribute("aria-busy", "true");
          }
          typer.reset(data.citations);  // a second draft (widened search) replaces the first
        },
        delta: function (data) {
          if (typer) {
            if (!typer.started()) setStatus("");
            typer.push(data.text || "");
          }
        }
      };

      var answer = streamOn
        ? askStream(body, controller.signal, handlers).then(function (data) {
            if (data) return data;
            streamOn = false;  // backend predates /ask/stream: stop trying this session
            return askJson(body, controller.signal);
          })
        : askJson(body, controller.signal);

      answer
        .then(function (data) {
          awake();
          if (!bubble) startAnswer();
          var shown = typer ? typer.finish(data.answer || "") : Promise.resolve();
          return shown.then(function () {
            bubble.innerHTML = renderAnswer(data.answer || "", data.citations);
            turns.push({ question: question, answer: data.answer || "" });
            renderSources(bubble, data);
            setStatus("");
            revealCard();
          });
        })
        .catch(function (error) {
          // A half-written answer that never passed the check should not stay on
          // screen as if it were one.
          if (bubble && bubble.parentNode) bubble.parentNode.parentNode.removeChild(bubble.parentNode);
          var message = error.userMessage ||
            (error.name === "AbortError" ? TEXT.errorTimeout :
              (error instanceof TypeError ? TEXT.errorNetwork : TEXT.errorGeneric));
          setStatus(message, { error: true });
        })
        .then(function () {
          clearTimeout(wakingTimer);
          clearTimeout(timeoutTimer);
          log.removeAttribute("aria-busy");
          hasWokenUp = true;
          setBusy(false);
          // Refocusing would pop the keyboard straight back up over the answer.
          if (!touch) input.focus();
        });
    }

    function checkResponse(response) {
      if (response.status === 429) {
        var retryAfter = parseInt(response.headers.get("Retry-After") || "0", 10);
        var mins = retryAfter ? Math.ceil(retryAfter / 60) : 60;
        var err = new Error("rate-limited");
        err.userMessage = TEXT.rateLimited(mins);
        throw err;
      }
      if (!response.ok) throw new Error("HTTP " + response.status);
    }

    function askJson(body, signal) {
      return fetch(api + "/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body,
        signal: signal
      }).then(function (response) {
        checkResponse(response);
        return response.json();
      });
    }

    /* Resolves with the `done` payload, or with null when the backend has no
       streaming endpoint yet (the caller then falls back to /ask). A 404 is answered
       before the rate limiter runs, so probing costs the visitor nothing. */
    function askStream(body, signal, on) {
      return fetch(api + "/ask/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "text/event-stream" },
        body: body,
        signal: signal
      }).then(function (response) {
        if (response.status === 404 || response.status === 405) return null;
        checkResponse(response);
        on.open();

        var reader = response.body.getReader();
        var decoder = new TextDecoder();
        var final = null;
        var failure = null;
        var feed = createSSEParser(function (name, data) {
          if (name === "done") final = data;
          else if (name === "error") failure = data.kind || "internal";
          else if (on[name]) on[name](data);
        });

        function pump() {
          return reader.read().then(function (chunk) {
            if (!chunk.done) {
              feed(decoder.decode(chunk.value, { stream: true }));
              return pump();
            }
            feed(decoder.decode());
            if (failure || !final) {
              var err = new Error("stream " + (failure || "ended early"));
              err.userMessage = failure === "busy" ? TEXT.errorBusy :
                (failure === "content_filter" ? TEXT.errorFiltered : TEXT.errorGeneric);
              throw err;
            }
            return final;
          });
        }
        return pump();
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
    module.exports = {
      escapeHtml: escapeHtml, renderAnswer: renderAnswer, citationLabel: citationLabel,
      renderInline: renderInline, createSSEParser: createSSEParser,
      trimPartialMarker: trimPartialMarker, typingStep: typingStep
    };
  }
})();
