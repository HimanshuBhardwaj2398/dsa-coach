"use strict";
// The stepper and the checks of a built explainer page; scripts/build_explainer.py inlines this file.
// Everything shown comes from the JSON in #data, recorded by running the spec's Python. The page keeps its state in
// memory only (the learning app serves it sandboxed, where storage throws), and nothing takes focus on load.
const DATA = JSON.parse(document.getElementById("data").textContent);

function el(tag, attrs = {}, ...kids) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node[k] = v;
    else node.setAttribute(k, v);
  }
  node.append(...kids.filter((x) => x !== null && x !== undefined && x !== false));
  return node;
}
// Answers compare as tokens: "(0, 5) (0, 4)", "(0,5),(0,4)" and "[0, 5, 0, 4]" are the same answer.
const norm = (s) => String(s).toLowerCase().replace(/[\s'"()[\]{},;]+/g, ",").replace(/^,+|,+$/g, "");
const SVG = "http://www.w3.org/2000/svg";
function svg(tag, attrs = {}, text = "") {
  const node = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text !== "") node.textContent = text;
  return node;
}

// --- theme ---------------------------------------------------------------------------------------------------------
document.getElementById("theme").onclick = () => {
  const root = document.documentElement;
  const dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  root.dataset.theme = dark ? "light" : "dark";
};

// --- multiple choice: the recognition cases and the transfer questions ---------------------------------------------
function choice(item, record) {
  const box = el("div", {class: "choice"}, el("p", {class: "q", text: item.text || item.q}));
  const options = el("div", {class: "options"});
  const said = el("p", {class: "said", role: "status"});
  let first = true;
  item.options.forEach((label, i) => {
    options.append(el("button", {type: "button", text: label, onclick: (e) => {
      const right = i === item.answer;
      e.target.classList.add(right ? "right" : "wrong");
      said.textContent = (right ? "Yes. " : "Not this one. ") + (right ? item.why : (item.miss?.[i] || "Look for what the method relies on, and try again."));
      said.className = "said " + (right ? "right" : "wrong");
      if (first && record) record(right);
      first = false;
      if (right) options.querySelectorAll("button").forEach((b) => { b.disabled = true; });
    }}));
  });
  box.append(options, said);
  return box;
}
(function cases() {
  const host = document.getElementById("cases");
  const score = el("p", {class: "muted", role: "status"});
  let tried = 0, right = 0;
  const record = (ok) => {
    tried += 1; right += ok ? 1 : 0;
    score.textContent = `First pick right: ${right} of ${tried}` + (tried === DATA.spot.cases.length ? ` (all ${tried} cases).` : ".");
  };
  DATA.spot.cases.forEach((c) => host.append(choice(c, record)));
  host.append(score);
})();

// --- views: pure functions of one step's state ----------------------------------------------------------------------
function changed(view, prev) {  // indexes or names whose value differs from the same view one step back
  if (!prev || prev.t !== view.t || prev.name !== view.name) return new Set();
  const out = new Set();
  if (view.t === "array") view.items.forEach((x, i) => { if (prev.items[i] !== x) out.add(String(i)); });
  if (view.t === "vars") view.items.forEach(([k, v]) => { const p = prev.items.find((x) => x[0] === k); if (!p || p[1] !== v) out.add(k); });
  if (view.t === "map") view.entries.forEach(([k, v]) => { const p = prev.entries.find((x) => x[0] === k); if (!p || p[1] !== v) out.add(k); });
  return out;
}
const VIEWS = {
  array(v, chg) {
    const row = el("div", {class: "cells"});
    v.items.forEach((x, i) => {
      const ptrs = Object.entries(v.ptr).filter(([, j]) => j === i).map(([k]) => k).join(" ");
      row.append(el("div", {class: `cell ${v.cls[i] || ""} ${chg.has(String(i)) ? "chg" : ""}`},
        el("span", {class: "idx", text: v.labels ? v.labels[i] : String(i)}), el("span", {class: "val", text: x}),
        el("span", {class: "ptr", text: ptrs})));
    });
    const past = Object.entries(v.ptr).filter(([, j]) => j >= v.items.length || j < 0);
    if (past.length) row.append(el("div", {class: "cell ghost"}, el("span", {class: "idx", text: String(v.items.length)}),
      el("span", {class: "val", text: "·"}), el("span", {class: "ptr", text: past.map(([k]) => k).join(" ")})));
    return row;
  },
  list(v) {
    const row = el("div", {class: "chips"});
    if (!v.items.length) row.append(el("span", {class: "muted", text: "empty"}));
    v.items.forEach((x, i) => row.append(el("span", {class: `chip ${v.cls[i] || ""}`, text: x})));
    if (v.note) row.append(el("span", {class: "muted note", text: v.note}));
    return row;
  },
  map(v, chg) {
    const t = el("table", {class: "kv"});
    if (!v.entries.length) t.append(el("tr", {}, el("td", {class: "muted", text: "empty"})));
    v.entries.forEach(([k, x]) => t.append(el("tr", {class: `${k === v.hl ? "cur" : ""} ${chg.has(k) ? "chg" : ""}`},
      el("td", {text: k}), el("td", {text: x}))));
    return t;
  },
  vars(v, chg) {
    const row = el("div", {class: "chips"});
    v.items.forEach(([k, x]) => row.append(el("span", {class: `var ${chg.has(k) ? "chg" : ""}`}, el("b", {text: k}), " = ", x)));
    return row;
  },
  grid(v) {
    const t = el("table", {class: "grid"});
    if (v.colh) t.append(el("tr", {}, v.rowh ? el("th") : null, ...v.colh.map((h) => el("th", {text: String(h)}))));
    v.cells.forEach((row, r) => t.append(el("tr", {}, v.rowh ? el("th", {text: String(v.rowh[r])}) : null,
      ...row.map((x, c) => el("td", {class: v.cls[`${r},${c}`] || "", text: x})))));
    return t;
  },
  graph(v) {
    const U = 64, R = 17, pad = 30;
    const [vw, vh] = [(v.w - 1) * U + 2 * pad, (v.h - 1) * U + 2 * pad + 14];  // drawn at natural size, never wider than its box
    const s = svg("svg", {viewBox: `${-pad} ${-pad} ${vw} ${vh}`, width: vw, height: vh, class: "graph", role: "img"});
    const at = Object.fromEntries(v.nodes.map((n) => [n.id, n]));
    if (v.directed) {
      const marker = svg("marker", {id: "arrow", viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "9", markerHeight: "9",
        markerUnits: "userSpaceOnUse", orient: "auto-start-reverse"});
      marker.append(svg("path", {d: "M0,0 L10,5 L0,10 z", class: "arrowhead"}));
      const defs = svg("defs");
      defs.append(marker);
      s.append(defs);
    }
    for (const e of v.edges) {
      const a = at[e.a], b = at[e.b];
      if (!a || !b) continue;
      const [x1, y1, x2, y2] = [a.x * U, a.y * U, b.x * U, b.y * U];
      const d = Math.hypot(x2 - x1, y2 - y1) || 1;
      const [ux, uy] = [(x2 - x1) / d, (y2 - y1) / d];
      s.append(svg("line", {x1: x1 + ux * R, y1: y1 + uy * R, x2: x2 - ux * (R + 2), y2: y2 - uy * (R + 2),
        class: `edge ${e.cls || ""}`, ...(v.directed ? {"marker-end": "url(#arrow)"} : {})}));
      if (e.label !== undefined && e.label !== "") {
        s.append(svg("text", {x: (x1 + x2) / 2 - uy * 10, y: (y1 + y2) / 2 + ux * 10 + 4, class: "elabel"}, String(e.label)));
      }
    }
    for (const n of v.nodes) {
      const wide = Math.max(2 * R, 8 * String(n.label).length + 12);  // a long label gets a pill, not a circle
      s.append(wide > 2 * R
        ? svg("rect", {x: n.x * U - wide / 2, y: n.y * U - R, width: wide, height: 2 * R, rx: R, class: `node ${n.cls || ""}`})
        : svg("circle", {cx: n.x * U, cy: n.y * U, r: R, class: `node ${n.cls || ""}`}));
      s.append(svg("text", {x: n.x * U, y: n.y * U + 4, class: "nlabel"}, String(n.label)));
      if (n.tag) s.append(svg("text", {x: n.x * U, y: n.y * U + R + 13, class: "ntag"}, String(n.tag)));
    }
    return s;
  },
  bars(v) {
    const W = 320, rowH = 22, span = Math.max(1, v.hi - v.lo);
    const s = svg("svg", {viewBox: `0 0 ${W + 20} ${v.spans.length * rowH + 26}`, width: W + 20, height: v.spans.length * rowH + 26, class: "bars", role: "img"});
    const x = (t) => 10 + ((t - v.lo) / span) * W;
    v.spans.forEach(([a, b, label, cls], i) => {
      s.append(svg("rect", {x: x(a), y: i * rowH + 4, width: Math.max(3, x(b) - x(a)), height: rowH - 8, rx: 3, class: `span ${cls || ""}`}));
      const text = label || `[${a}, ${b}]`, room = 7 * text.length;  // right of the bar, else left of it, else inside
      const [tx, anchor] = x(b) + 4 + room <= W + 20 ? [x(b) + 4, "start"] : x(a) - 4 - room >= 0 ? [x(a) - 4, "end"] : [(x(a) + x(b)) / 2, "middle"];
      s.append(svg("text", {x: tx, y: i * rowH + rowH / 2 + 4, class: "slabel", "text-anchor": anchor}, text));
    });
    const axis = v.spans.length * rowH + 8;
    s.append(svg("line", {x1: x(v.lo), y1: axis, x2: x(v.hi), y2: axis, class: "axis"}));
    for (let t = v.lo; t <= v.hi; t += Math.max(1, Math.ceil(span / 10))) {
      s.append(svg("text", {x: x(t), y: axis + 14, class: "tick"}, String(t)));
    }
    return s;
  },
  text(v) { return el("p", {text: v.text}); },
};
function drawViews(step, prev) {
  const box = el("div", {class: "views"});
  step.views.forEach((v, i) => {
    const before = prev?.views[i];
    box.append(el("figure", {class: `view v-${v.t}`}, v.name ? el("figcaption", {text: v.name}) : null, VIEWS[v.t](v, changed(v, before))));
  });
  return box;
}

// --- the stepper ------------------------------------------------------------------------------------------------------
(function stepper() {
  const host = document.getElementById("stepper");
  const states = DATA.traces.map(() => ({k: 0, answers: {}}));
  let current = 0, timer = null;
  const picker = el("div", {class: "picker", role: "group", "aria-label": "Input"});
  DATA.traces.forEach((t, i) => picker.append(el("button", {type: "button", text: t.label, onclick: () => { stop(); current = i; draw(); }})));
  const about = el("p", {class: "about"});
  const back = el("button", {type: "button", text: "Back", onclick: () => go(-1)});
  const step = el("button", {type: "button", class: "primary", text: "Step", onclick: () => go(1)});
  const play = el("button", {type: "button", text: "Play", onclick: () => (timer ? stop() : start())});
  const reset = el("button", {type: "button", text: "Reset", onclick: () => { stop(); states[current] = {k: 0, answers: {}}; draw(); }});
  const end = el("button", {type: "button", text: "End", onclick: () => { stop(); while (canStep()) S().k += 1; draw(); }});
  const where = el("span", {class: "muted where"});
  const say = el("p", {class: "say", "aria-live": "polite"});
  const ask = el("div", {class: "ask"});
  const stage = el("div", {class: "stage"});
  const code = el("ol", {class: "code"});
  const table = el("table", {class: "history"});
  const record = el("p", {class: "muted"});
  host.append(picker, about, el("div", {class: "controls"}, back, step, play, reset, end, where), say, ask,
    el("div", {class: "split"}, stage, el("div", {class: "side"}, el("h3", {text: "Python · how often each line has run"}), code)),
    el("h3", {text: "History"}), el("div", {class: "scroll"}, table), record);
  if (DATA.traces.length < 2) picker.hidden = true;

  const T = () => DATA.traces[current];
  const S = () => states[current];
  const pending = () => T().steps[S().k].ask && !S().answers[S().k];
  const canStep = () => S().k < T().steps.length - 1 && !pending();
  function go(d) {
    if (d > 0 && !canStep()) return;
    S().k = Math.max(0, Math.min(T().steps.length - 1, S().k + d));
    draw();
  }
  function start() {
    play.textContent = "Pause";
    timer = setInterval(() => { if (canStep()) go(1); else stop(); }, 650);
  }
  function stop() {
    clearInterval(timer);
    timer = null;
    play.textContent = "Play";
  }
  function drawAsk(s, k) {
    ask.replaceChildren();
    if (!s.ask) return;
    const a = s.ask, given = S().answers[k];
    ask.append(el("p", {class: "q"}, el("b", {text: "Predict: "}), a.q));
    const reveal = (value) => {
      S().answers[k] = {value, right: norm(value) === norm(a.answer)};
      draw();
    };
    if (!given) {
      if (a.options) {
        ask.append(el("div", {class: "options"}, ...a.options.map((o) => el("button", {type: "button", text: String(o), onclick: () => reveal(String(o))}))));
      } else {
        const input = el("input", {type: "text", "aria-label": "Your prediction", autocomplete: "off"});
        const form = el("form", {class: "fill", onsubmit: (e) => { e.preventDefault(); if (input.value.trim()) reveal(input.value.trim()); }},
          input, el("button", {type: "submit", text: "Check"}));
        ask.append(form);
      }
      return;
    }
    ask.append(el("p", {class: `said ${given.right ? "right" : "wrong"}`},
      given.right ? `You said ${given.value}. Right.` : `You said ${given.value}. It was ${a.answer}.`, a.why ? " " + a.why : ""));
  }
  function draw() {
    const t = T(), k = S().k, s = t.steps[k];
    picker.querySelectorAll("button").forEach((b, i) => b.setAttribute("aria-pressed", String(i === current)));
    about.textContent = t.about;
    back.disabled = k === 0;
    step.disabled = !canStep();
    end.disabled = !canStep();
    where.textContent = `Step ${k + 1} of ${t.steps.length}` + (pending() ? " · predict to go on" : "");
    say.textContent = s.say || "";
    drawAsk(s, k);
    stage.replaceChildren(drawViews(s, t.steps[k - 1]));
    const runs = {};
    for (let i = 0; i < k; i++) if (!t.steps[i].ret) runs[t.steps[i].line] = (runs[t.steps[i].line] || 0) + 1;
    code.replaceChildren(...t.code.map((line, i) => el("li", {class: i + 1 === s.line ? (s.ret ? "cur ret" : "cur") : ""},
      el("span", {class: "runs", text: runs[i + 1] ? String(runs[i + 1]) : ""}), el("code", {text: line || " "}))));
    table.replaceChildren(el("tr", {}, ...t.cols.map((c) => el("th", {text: c}))),
      ...t.rows.filter((r) => r.at <= k).map((r) => el("tr", {}, ...r.cells.map((c) => el("td", {text: c})))));
    if (!t.rows.some((r) => r.at <= k)) table.append(el("tr", {}, el("td", {class: "muted", colspan: String(t.cols.length || 1), text: "Rows appear as you step."})));
    const given = Object.values(S().answers);
    record.textContent = given.length ? `Predictions on this input: ${given.filter((g) => g.right).length} of ${given.length} right.` : "";
  }
  document.addEventListener("keydown", (e) => {
    if (e.target.closest("input, textarea") || document.body.classList.contains("checking")) return;
    const rect = host.getBoundingClientRect();
    if (rect.bottom < 0 || rect.top > innerHeight) return;  // only while the stepper is on screen
    if (e.key === "ArrowRight") { e.preventDefault(); stop(); go(1); }
    if (e.key === "ArrowLeft") { e.preventDefault(); stop(); go(-1); }
  });
  draw();
})();

// --- the check with the lesson hidden -----------------------------------------------------------------------------------
(function check() {
  const c = DATA.check, quiz = document.getElementById("quiz"), hide = document.getElementById("hide");
  const inputs = c.fields.map((f) => el("input", {type: "text", autocomplete: "off", "aria-label": f.label}));
  const marks = c.fields.map(() => el("span", {class: "mark", role: "status"}));
  const fields = el("div", {class: "fields"}, ...c.fields.map((f, i) => el("label", {}, f.label, inputs[i], marks[i])));
  const checkBtn = el("button", {type: "button", class: "primary", text: "Check my trace", onclick: () => {
    c.fields.forEach((f, i) => {
      const ok = norm(inputs[i].value) === norm(f.answer);
      marks[i].textContent = ok ? "Right." : `It was ${f.answer}.`;
      marks[i].className = "mark " + (ok ? "right" : "wrong");
    });
  }});
  const own = el("textarea", {rows: "4", "aria-label": "In your own words"});
  const model = el("p", {class: "model", hidden: ""}, c.own.model);
  quiz.append(el("p", {class: "muted", text: "The traces, code, plan card and history are hidden. Work on paper if you like."}),
    el("h3", {text: "Trace a fresh input"}), el("p", {text: c.text}), fields, checkBtn,
    el("h3", {text: "Transfer"}), ...c.questions.map((q) => choice(q)),
    el("h3", {text: "In your own words"}), el("p", {text: c.own.prompt}), own,
    el("button", {type: "button", text: "Compare with the reasoning", onclick: () => { model.hidden = false; }}), model,
    el("p", {}, el("button", {type: "button", class: "ghost", text: "Return to the lesson", onclick: () => {
      document.body.classList.remove("checking"); quiz.hidden = true; hide.hidden = false;
    }})));
  hide.onclick = () => {
    document.body.classList.add("checking");
    quiz.hidden = false;
    hide.hidden = true;
    document.getElementById("check").scrollIntoView({block: "start"});
  };
})();
