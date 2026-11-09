"use strict";
// /companion is frameable only by this pinned extension (enforced by the server's CSP).
const COMPANION_PARENT = "chrome-extension://fiahbfhmngefgmcnlacogkhhhflfomoh";
let companionEnabled = false, companionImage = null, companionKey = null, companionBusy = false;
let captureRequest = null;
const captures = new Map();  // id -> resolve: captures taken on their own as part of a message, not for the drawer
const RUNG_NAMES = ["", "a general question", "a nudge for this problem", "name the pattern", "the invariant or state",
  "a skeleton with blanks", "one concrete sub-step", "the full solution"];
const companionThreads = new Map();
const COMPANION_STAGE_NAMES = ["Understand", "Find an approach", "Build it", "Check and finish"];
let companionTab = "chat", companionPreviewStage = null, companionStageSession = null;
let companionLibrary = null, companionLibraryLoading = false, companionShowAllTopics = false;
let companionPending = null;

function setCompanionTab(name) {
  if (!["chat", "stages", "learn"].includes(name)) return;
  companionTab = name;
  for (const tabName of ["chat", "stages", "learn"]) {
    const selected = name === tabName;
    $("companion-tab-" + tabName).setAttribute("aria-selected", String(selected));
    $("companion-tab-" + tabName).tabIndex = selected ? 0 : -1;
    $("companion-" + tabName).hidden = !selected;
  }
  if (name === "stages") renderCompanionStages();
  if (name === "learn") loadCompanionTheory();
}

function draftCompanionQuestion(text) {
  setCompanionTab("chat");
  const input = $("companion-question");
  // Keep a question already being composed; an explicit suggestion adds to it.
  input.value = input.value.trim() ? input.value.trimEnd() + "\n\n" + text : text;
  input.focus();
}

function browseCompanionStage(n) {
  if (!state?.live || !attempt || n < 1 || n > STAGES.length) return;
  return change(async () => {
    if (panelDirty && savePanel) await savePanel();
    if (!state?.live || !attempt) return;
    if (n > state.live.stage) companionPreviewStage = n;
    else {
      companionPreviewStage = null;
      view = n;
      renderPanel(); renderBar(); showTab("stage");
    }
    renderCompanionStages();
    const card = $("companion-stage-cards").children[n - 1];
    card.scrollIntoView({block: "nearest", inline: "nearest"});
  });
}

function renderCompanionStages() {
  if (!companionEnabled) return;
  const live = state?.live;
  $("companion-stage-overview").hidden = !live;
  if (!live) { companionPreviewStage = null; return; }
  if (companionStageSession !== live.session_id) {
    companionStageSession = live.session_id;
    companionPreviewStage = null;
  }
  if (companionPreviewStage && companionPreviewStage <= live.stage) companionPreviewStage = null;
  const selected = companionPreviewStage || view || live.stage;
  document.body.dataset.stagePreview = String(!!companionPreviewStage);
  $("companion-stage-count").textContent = `Stage ${selected} of ${STAGES.length}`;
  $("companion-stage-prev").disabled = selected === 1 || !attempt;
  $("companion-stage-next").disabled = selected === STAGES.length || !attempt;
  $("companion-stage-current").disabled = selected === live.stage && !companionPreviewStage;
  const cards = $("companion-stage-cards");
  if (!cards.children.length) {
    COMPANION_STAGE_NAMES.forEach((name, i) => {
      const card = button("", () => browseCompanionStage(i + 1));
      card.className = "stage-card";
      card.append(elem("span", String(i + 1).padStart(2, "0")), elem("strong", name), elem("small"));
      cards.append(card);
    });
  }
  [...cards.children].forEach((card, i) => {
    const n = i + 1;
    const status = n < live.stage ? "Completed" : n === live.stage ? "Current" : n === selected ? "Preview" : "Upcoming";
    card.setAttribute("aria-label", `Stage ${n}: ${COMPANION_STAGE_NAMES[i]}, ${status.toLowerCase()}`);
    card.setAttribute("aria-pressed", String(n === selected));
    if (n === live.stage) card.setAttribute("aria-current", "step"); else card.removeAttribute("aria-current");
    card.lastElementChild.textContent = status;
    card.disabled = !attempt;
  });
  const preview = $("companion-stage-preview");
  preview.hidden = !companionPreviewStage;
  if (companionPreviewStage && preview.dataset.stage !== String(selected)) {
    const tag = elem("p", "Preview · progress stays at stage " + live.stage); tag.className = "eyebrow";
    preview.replaceChildren(tag, elem("h2", STAGES[selected - 1][0]), elem("p", STAGES[selected - 1][1]),
      elem("p", "Return to the current stage to save your answer and continue."));
    preview.dataset.stage = String(selected);
  }
}

async function loadCompanionTheory() {
  if (companionLibrary) { renderCompanionTheory(); return; }
  if (companionLibraryLoading) return;
  companionLibraryLoading = true;
  $("companion-theory-status").textContent = "Loading your topics…";
  try {
    companionLibrary = await api("GET", "/api/map");
    renderCompanionTheory();
  } catch (error) {
    $("companion-theory-status").replaceChildren(elem("span", error.message + " "), button("Try again", loadCompanionTheory));
  } finally { companionLibraryLoading = false; }
}

function renderCompanionTheory() {
  if (!companionLibrary) return;
  const search = $("companion-theory-search").value.trim().toLowerCase();
  const live = state?.live;
  const current = live?.labeled ? live.pattern : null;
  let topics = companionLibrary.patterns.filter(p => !p.format &&
    (!search || `${p.name} ${p.cues.join(" ")}`.toLowerCase().includes(search)));
  topics.sort((a, b) => Number(b.key === current) - Number(a.key === current));
  const total = topics.length;
  if (!search && !companionShowAllTopics) topics = topics.slice(0, current ? 1 : 3);
  $("companion-theory-status").textContent = total ? (search ? `${total} topic${total === 1 ? "" : "s"}` : "") : "No matching topics. Try a pattern name such as binary search.";
  $("companion-theory-more").hidden = !!search || total <= topics.length;
  $("companion-theory-more").textContent = `Browse all ${total} topics`;
  $("companion-theory-cards").replaceChildren(...topics.map(topic => {
    const card = elem("article"); card.className = "theory-card";
    const open = Object.assign(elem("a"), {href: topic.explainer ? `/explainer/${topic.key}` : `/#/learn/${topic.key}`,
      target: "_blank", rel: "noopener"});
    open.className = "theory-open";
    const label = elem("p", topic.key === current ? "For your current pattern" : `Week ${topic.week}`); label.className = "eyebrow";
    open.append(label, elem("h3", topic.name), elem("p", topic.cues.slice(0, 2).join(" · ")),
      elem("span", topic.explainer ? "Open interactive theory ↗" : "Open theory & examples ↗"));
    const discuss = button("Explain this to me", () => {
      const context = `Theory: ${topic.name}\nCues: ${topic.cues.join("; ")}\nInvariant: ${topic.invariant}\nTemplate: ${topic.template}`;
      const text = $("captured-text");
      text.value = [text.value, context].filter(Boolean).join("\n\n").slice(-24000);
      renderAttachment();
      draftCompanionQuestion(`Help me understand ${topic.name}. Use a small example and ask me to predict the next step.`);
    });
    discuss.className = "text-action";
    card.append(open, discuss, explainerBlock(topic, reloadCompanionTheory, true));
    return card;
  }));
}

// A job that wrote or revised an explainer ended: the cards' links and actions come from fresh map data.
async function reloadCompanionTheory() {
  companionLibrary = await api("GET", "/api/map");
  renderCompanionTheory();
}

function companionIdentity() {
  return `${state?.live?.session_id || "preview"}:${state?.live?.problem || companionProblem || ""}`;
}

function renderConversation() {
  const messages = companionThreads.get(companionKey) || [];
  const pendingMessage = companionPending?.key === companionKey ? [{role: "user", text: companionPending.question}] : [];
  $("companion-welcome").hidden = messages.length > 0 || pendingMessage.length > 0;
  $("companion-messages").replaceChildren(...[...messages, ...pendingMessage].map(message => {
    const article = elem("article");
    article.className = "message-" + message.role;
    article.append(elem("strong", message.role === "user" ? "You" : "Coach"), elem("p", message.text));
    if (message.note) article.append(Object.assign(elem("small", message.note), {className: "message-note"}));
    return article;
  }));
  $("companion-scroll").scrollTop = $("companion-scroll").scrollHeight;
}

function renderAttachment() {
  $("captured-image").hidden = !companionImage;
  if (companionImage) $("captured-image").src = companionImage;
  else $("captured-image").removeAttribute("src");
  const text = !!$("captured-text").value.trim();
  $("capture-clear").hidden = !companionImage && !text;
  $("companion-attachment-count").textContent = [text ? "text" : "", companionImage ? "image" : ""].filter(Boolean).join(" + ");
}

function clearAttachment() {
  companionImage = null;
  $("captured-text").value = $("captured-file").value = "";
  renderAttachment();
}

function renderCompanion() {
  if (!companionEnabled) return;
  const live = state?.live;
  const mismatch = live && companionProblem && live.problem !== companionProblem;
  const slug = live?.problem || companionProblem;
  $("companion-problem").textContent = slug ? slug.split("-").map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(" ") : "Your practice space";
  $("companion-mismatch").hidden = !mismatch;
  $("companion-mismatch").textContent = mismatch ? `LeetCode: ${companionProblem}. Your active solve is ${live.problem}. Return to it to continue.` : "";
  $("companion-stage-short").hidden = !live;
  if (live) $("companion-stage-short").textContent = `Stage ${live.stage} of ${STAGES.length} · ${COMPANION_STAGE_NAMES[live.stage - 1]} →`;
  $("companion-next-action").textContent = live ? `You’re on ${COMPANION_STAGE_NAMES[live.stage - 1].toLowerCase()}. Share your reasoning, or attach what you see in LeetCode.`
    : slug ? "Ask a question now, or start a guided solve to work through the stages." : "Open a LeetCode problem, then talk it through here.";
  $("companion-use").hidden = !companionProblem || !!live;
  $("companion-send").disabled = companionBusy || !!mismatch || !(live?.problem || companionProblem);
  $("companion-send").textContent = companionBusy ? "Thinking…" : "Send";
  const key = companionIdentity();
  if (key !== companionKey) {
    companionKey = key;
    renderConversation();
  }
  renderCompanionStages();
}

async function companionAsk(question) {
  setCompanionTab("chat");
  if (companionBusy) return;
  const live = state?.live;
  const problem = live?.problem || companionProblem;
  if (!problem) { $("companion-chat-status").textContent = "Open a LeetCode problem first."; return; }
  if (live && companionProblem && live.problem !== companionProblem) {
    $("companion-chat-status").textContent = `Return to ${live.problem} before asking about this solve.`;
    return;
  }
  const key = companionIdentity();
  const thread = companionThreads.get(key) || [];
  const prompt = question.trim();
  if (!prompt) return;
  companionBusy = true;
  companionPending = {key, question: prompt};
  $("companion-attachment").open = false;
  renderCompanion();
  renderConversation();
  try {
    // The code and the end of the page go with every message, read from the LeetCode tab as it is now.
    $("companion-chat-status").textContent = "Reading the LeetCode page…";
    const page = await captureNow("context");
    const ask = screenshot => askCoaching({
      problem, session_id: live?.session_id || null, question: prompt, code: page.code || "",
      page_text: [$("captured-text").value, page.text].filter(Boolean).join("\n\n").slice(-24000), screenshot,
      history: thread.slice(-12).map(message => ({role: message.role, text: message.text.slice(0, 10000)})),
    });
    let result = await ask(companionImage);
    if (result.look) {  // the coach asked to see the screen: take a screenshot and ask once more
      $("companion-chat-status").textContent = "Coach is looking at the page…";
      const shot = await captureNow("screenshot");
      if (shot.screenshot) result = await ask(shot.screenshot);
      if (!shot.screenshot || result.look) {
        result = {...result, reply: shot.error ? `I need to see the page. ${shot.error}`
          : "I couldn't see enough. Paste a screenshot here and ask again."};
      }
    }
    companionPending = null;
    const note = result.recorded_rung ? `Hint rung ${result.recorded_rung} recorded (${RUNG_NAMES[result.recorded_rung]}).` : "";
    thread.push({role: "user", text: prompt}, {role: "assistant", text: result.reply, note});
    companionThreads.set(key, thread.slice(-24));
    if (key === companionIdentity()) {
      if ($("companion-question").value.trim() === prompt) $("companion-question").value = "";
      renderConversation();
      $("companion-chat-status").textContent = "";
    } else $("companion-chat-status").textContent = "Reply received for the previous problem. Return to it to read the reply.";
  } catch (error) {
    $("companion-chat-status").textContent = error.message;
  } finally {
    companionBusy = false;
    companionPending = null;
    renderCompanion();
    renderConversation();
  }
}

async function askCoaching(body) {
  $("companion-chat-status").textContent = "Coach is thinking…";
  const started = await api("POST", "/api/coaching", body);
  const deadline = Date.now() + 200000;
  while (true) {
    await new Promise(resolve => setTimeout(resolve, 1000));
    const result = await api("GET", "/api/coaching?id=" + encodeURIComponent(started.id));
    if (result.state === "error") throw new Error(result.error);
    if (result.state === "done") return result;
    if (Date.now() > deadline) throw new Error("The coach did not finish. Check the local server and try again.");
  }
}

// --- Finishing in the panel: the coach reviews the evidence, then he saves the attempt it proposes ---------------
const MISTAKE_NAMES = {comp: "misread the problem", pattern: "picked the wrong pattern", invariant: "the invariant broke",
  boundary: "off-by-one or loop bounds", edge: "a missed edge case", pytrap: "a Python pitfall",
  complexity: "complexity wrong or missing", impl: "an implementation slip", process: "skipped a stage", comm: "an unclear explanation"};
let finishReview = null;  // {session, answers, review}: the latest review, for the answers it saw

function finishAnswers(finish) {
  return {outcome: finish.outcome.value, lesson: finish.lesson.value.trim(), outside_help: finish.help.value === "yes"};
}

function pageText(page) {
  return [$("captured-text").value, page.text].filter(Boolean).join("\n\n").slice(-24000);
}

async function pollJob(path) {
  const deadline = Date.now() + 200000;
  while (true) {
    await new Promise(resolve => setTimeout(resolve, 1000));
    const result = await api("GET", path);
    if (result.state === "error") throw new Error(result.error);
    if (result.state === "done") return result;
    if (Date.now() > deadline) throw new Error("The coach did not finish. Check the local server and try again.");
  }
}

// Stage 4's Review attempt: his notes are saved by then. Reads LeetCode, asks for the review, shows it.
async function reviewAttempt(finish) {
  const live = state.live, area = finish.review;
  finishReview = null;
  area.replaceChildren(elem("p", "Reading the LeetCode page…"));
  const page = await captureNow("context");
  const answers = finishAnswers(finish);
  area.replaceChildren(elem("p", "The coach is checking your evidence…"));
  try {
    const started = await api("POST", "/api/finish/review", {session_id: live.session_id, problem: live.problem,
      ...answers, code: page.code || "", page_text: pageText(page)});
    const result = await pollJob("/api/finish/review?id=" + encodeURIComponent(started.id));
    if (state?.live?.session_id !== live.session_id) return;
    finishReview = {session: live.session_id, answers: JSON.stringify(answers), review: result.review};
    renderReview(finish, result, page.error);
  } catch (error) {
    area.replaceChildren(elem("p", error.message), button("Try again", () => reviewAttempt(finish), true));
  }
}

function renderReview(finish, result, captureError) {
  const r = result.review, area = finish.review;
  const parts = [elem("h3", r.recordable ? "Ready to save" : "One more thing first"), elem("p", r.feedback)];
  if (captureError) parts.push(Object.assign(elem("p", `LeetCode couldn't be read (${captureError}), so the review used only your notes and attached text.`), {className: "hint"}));
  if (result.recorded_rung) parts.push(Object.assign(elem("p", `Hint rung ${result.recorded_rung} recorded (${RUNG_NAMES[result.recorded_rung]}).`), {className: "hint"}));
  if (!r.recordable) {
    const list = document.createElement("ul");
    for (const m of r.missing) list.append(elem("li", m));
    parts.push(list, Object.assign(elem("p", "Add it to your notes or the chat, run the case in LeetCode if needed, then review again."), {className: "hint"}));
  } else {
    const record = document.createElement("dl");
    const rows = [["Outcome", r.outcome], ["Evidence", r.evidence], ["Hints", state.live.rung ? `up to rung ${state.live.rung}` : "none"],
      ["Outside help", finish.help.value === "yes" ? "yes, so it counts as assisted" : "no"],
      ["Complexity", r.complexity_stated ? "stated with a reason" : "not credited this time"],
      ["To watch", r.mistakes.length ? r.mistakes.map(m => MISTAKE_NAMES[m] || m).join(", ") : "nothing noted"]];
    for (const [k, v] of rows) record.append(elem("dt", k), elem("dd", v));
    const save = button("Save attempt", () => saveAttempt(finish), true);
    save.className = "primary";
    save.gate = () => { save.disabled = !reviewIsCurrent(finish); };
    for (const control of [finish.outcome, finish.lesson, finish.help]) control.addEventListener("input", save.gate);
    for (const control of [finish.outcome, finish.help]) control.addEventListener("change", save.gate);
    parts.push(record, Object.assign(elem("p", "Saving logs this attempt and schedules the next review. Change an answer and the coach reviews again."), {className: "hint"}), save);
  }
  area.replaceChildren(...parts);
}

function reviewIsCurrent(finish) {
  return !!finishReview && finishReview.session === state?.live?.session_id && finishReview.answers === JSON.stringify(finishAnswers(finish));
}

async function saveAttempt(finish) {
  const live = state.live;
  if (!reviewIsCurrent(finish)) { finish.review.replaceChildren(elem("p", "Your answers changed since the review. Review the attempt again.")); return; }
  const page = await captureNow("context");  // the server checks the code is the code that was reviewed
  if (page.error) throw new Error(`Couldn't read LeetCode to check your code is unchanged: ${page.error}`);
  const out = await api("POST", "/api/finish/save", {session_id: live.session_id, problem: live.problem,
    ...finishAnswers(finish), code: page.code || ""});
  finishReview = null;
  draftData = null;  // the attempt is in the notebook now: no draft or rescue of its answers
  panelDirty = false;
  try { localStorage.removeItem(draftKey(state.notebook_id, live.session_id)); } catch {}
  solveGone();
  const r = out.receipt;
  banner(`Attempt recorded: ${r.problem}, ${r.outcome} (${r.kind}). Next re-solve due ${r.next_due}. No new solve starts until you choose one.`,
    [["Continue practice", async () => { setCompanionTab("stages"); await refresh(); }]], "receipt");
  await refresh();
}

// A capture the coach needs right now. It never fails the message: on any problem it resolves with {error}.
function captureNow(kind) {
  if (!companionProblem) return Promise.resolve({error: "No LeetCode problem is open in this window."});
  const id = crypto.randomUUID(), problem = companionProblem;
  return new Promise(resolve => {
    const done = data => { captures.delete(id); resolve(data); };
    captures.set(id, data => done(data.error ? {error: data.error}
      : data.slug !== problem || companionProblem !== problem ? {error: "The problem changed."} : data));
    setTimeout(() => { if (captures.has(id)) done({error: "The LeetCode tab didn't answer."}); }, 10000);
    window.parent.postMessage({type: "dsa-coach:capture", id, kind}, COMPANION_PARENT);
  });
}

function requestCapture(kind) {
  if (captureRequest) return;
  const id = crypto.randomUUID();
  captureRequest = {id, problem: companionProblem};
  $("companion-chat-status").textContent = "Capturing the LeetCode tab…";
  window.parent.postMessage({type: "dsa-coach:capture", id, kind}, COMPANION_PARENT);
  setTimeout(() => {
    if (captureRequest?.id !== id) return;
    captureRequest = null;
    $("companion-chat-status").textContent = "Capture did not finish. Try again or paste your context.";
  }, 10000);
}

function attachImage(file) {
  if (!file || !["image/png", "image/jpeg"].includes(file.type) || file.size > 4_000_000) {
    $("companion-chat-status").textContent = "Choose a PNG or JPEG under 4 MB.";
    return;
  }
  const key = companionIdentity();
  const reader = new FileReader();
  reader.onload = () => {
    if (key !== companionIdentity()) return;
    companionImage = reader.result;
    renderAttachment();
    $("companion-attachment").open = true;
  };
  reader.readAsDataURL(file);
}

document.addEventListener("DOMContentLoaded", () => {
  if (location.pathname !== "/companion") return;
  companionEnabled = true;
  if (location.hash !== "#/solve") location.hash = "#/solve";
  document.body.classList.add("companion");
  $("companion-tabs").hidden = $("companion-context").hidden = false;
  $("companion-stages").append($("start"), $("solve"));
  $("companion-focus-block").append($("timer"), $("block-btn"), $("rung"));
  $("tab-stage").textContent = "Answer";
  $("tab-notes").textContent = "Saved notes";
  $("tab-desc").textContent = "Problem";
  $("tab-stage").parentElement.append($("tab-stage"), $("tab-notes"), $("tab-desc"));
  // Alerts remain visible above the active tab, without the full app's duplicate toolbar.
  $("companion-context").after($("banner"), $("rescue"), $("recovery"));
  for (const tabButton of document.querySelectorAll("[data-companion-tab]")) {
    tabButton.onclick = () => setCompanionTab(tabButton.dataset.companionTab);
  }
  $("companion-stage-short").onclick = () => setCompanionTab("stages");
  $("companion-stage-prev").onclick = () => browseCompanionStage((companionPreviewStage || view || state.live.stage) - 1);
  $("companion-stage-next").onclick = () => browseCompanionStage((companionPreviewStage || view || state.live.stage) + 1);
  $("companion-stage-current").onclick = () => browseCompanionStage(state.live.stage);
  $("companion-stage-cards").onkeydown = event => {
    if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
    const cards = [...$("companion-stage-cards").children];
    const i = cards.indexOf(event.target);
    const next = cards[i + (event.key === "ArrowRight" ? 1 : -1)];
    if (next) { event.preventDefault(); next.focus(); next.click(); }
  };
  $("companion-get-started").onclick = () => draftCompanionQuestion("Help me get started. Ask me the first question without giving away the solution.");
  $("companion-check-thinking").onclick = () => draftCompanionQuestion("Check my thinking. Here is my approach: ");
  $("companion-theory-search").oninput = renderCompanionTheory;
  $("companion-theory-more").onclick = () => { companionShowAllTopics = true; renderCompanionTheory(); };
  $("companion-use").onclick = () => {
    if (state?.live || !companionProblem) return;
    $("slug").value = companionProblem;
    setCompanionTab("stages");
    location.hash = "#/solve";
    gateStart();
    $("confidence").focus();
  };
  $("capture-text").onclick = () => requestCapture("text");
  $("capture-screen").onclick = () => requestCapture("screenshot");
  $("capture-clear").onclick = clearAttachment;
  $("captured-text").oninput = renderAttachment;
  $("captured-file").onchange = event => attachImage(event.target.files[0]);
  $("companion-chat").addEventListener("paste", event => {
    const image = [...(event.clipboardData?.files || [])].find(file => file.type.startsWith("image/"));
    if (image) { event.preventDefault(); attachImage(image); }
  });
  $("companion-form").onsubmit = event => { event.preventDefault(); companionAsk($("companion-question").value); };
  $("companion-question").onkeydown = event => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && !$("companion-send").disabled) {
      event.preventDefault(); $("companion-form").requestSubmit();
    }
  };
  window.addEventListener("message", event => {
    if (event.source !== window.parent || event.origin !== COMPANION_PARENT) return;
    if (event.data?.type === "dsa-coach:problem") {
      const slug = event.data.slug;
      if (slug !== null && (typeof slug !== "string" || !/^[a-z0-9][a-z0-9-]{0,254}$/.test(slug))) return;
      if (slug !== companionProblem) clearAttachment();
      companionProblem = slug;
      renderCompanion();
      if (state && !state.live) renderStart();
    } else if (event.data?.type === "dsa-coach:activity") {
      touchActivity();
    } else if (event.data?.type === "dsa-coach:captured" && captures.has(event.data.id)) {
      captures.get(event.data.id)(event.data);
    } else if (event.data?.type === "dsa-coach:captured" && event.data.id === captureRequest?.id) {
      const requested = captureRequest;
      captureRequest = null;
      if (event.data.error) { $("companion-chat-status").textContent = event.data.error; return; }
      if (event.data.slug !== companionProblem || requested.problem !== companionProblem) {
        $("companion-chat-status").textContent = "The problem changed. Capture again."; return;
      }
      if (event.data.text) $("captured-text").value = event.data.text;
      if (event.data.screenshot) companionImage = event.data.screenshot;
      renderAttachment();
      $("companion-attachment").open = true;
      $("companion-chat-status").textContent = "Context attached. Review it, then ask your coach.";
    }
  });
  renderCompanion();
  setCompanionTab("chat");
  window.parent.postMessage({type: "dsa-coach:ready"}, COMPANION_PARENT);
});
