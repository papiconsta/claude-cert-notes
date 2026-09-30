(function () {
  "use strict";

  const STORAGE_KEY = "claudeCertQuiz.progress.v1";

  const el = {
    examTitle: document.getElementById("exam-title"),
    sectionSelect: document.getElementById("section-select"),
    resetBtn: document.getElementById("reset-btn"),
    progressFill: document.getElementById("progress-fill"),
    progressText: document.getElementById("progress-text"),
    scoreText: document.getElementById("score-text"),
    card: document.getElementById("quiz-card"),
    sectionBadge: document.getElementById("section-badge"),
    questionText: document.getElementById("question-text"),
    optionsContainer: document.getElementById("options-container"),
    emptyState: document.getElementById("empty-state"),
    loadError: document.getElementById("load-error"),
    prevBtn: document.getElementById("prev-btn"),
    nextBtn: document.getElementById("next-btn"),
    questionList: document.getElementById("question-list"),
    resetModal: document.getElementById("reset-modal"),
    resetCancelBtn: document.getElementById("reset-cancel-btn"),
    resetConfirmBtn: document.getElementById("reset-confirm-btn"),
  };

  /** @type {{examTitle:string, sections:{id:string,title:string}[], questions:any[]}} */
  let data = null;
  let sectionsById = new Map();
  let filteredQuestions = [];
  let currentIndex = 0;
  let currentFilter = "all";

  /** questionId -> optionId the user picked */
  let answers = loadProgress();

  function loadProgress() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      return {};
    }
  }

  function saveProgress() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(answers));
    } catch (e) {
      /* ignore (private browsing, quota, etc.) */
    }
  }

  function init(loadedData) {
    data = loadedData;
    sectionsById = new Map(data.sections.map((s) => [s.id, s]));
    el.examTitle.textContent = data.examTitle || "Exam Prep Quiz";

    buildSectionOptions();
    applyFilter("all");

    el.sectionSelect.addEventListener("change", () => {
      applyFilter(el.sectionSelect.value);
    });

    el.prevBtn.addEventListener("click", () => goTo(currentIndex - 1));
    el.nextBtn.addEventListener("click", () => goTo(currentIndex + 1));

    el.resetBtn.addEventListener("click", openResetModal);
    el.resetCancelBtn.addEventListener("click", closeResetModal);
    el.resetConfirmBtn.addEventListener("click", () => {
      answers = {};
      saveProgress();
      optionOrderCache.clear();
      closeResetModal();
      render();
    });
    el.resetModal.addEventListener("click", (e) => {
      if (e.target === el.resetModal) closeResetModal();
    });

    document.addEventListener("keydown", (e) => {
      if (!el.resetModal.hidden) {
        if (e.key === "Escape") closeResetModal();
        return;
      }
      const tag = (document.activeElement && document.activeElement.tagName) || "";
      if (tag === "SELECT" || tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === "ArrowRight") goTo(currentIndex + 1);
      if (e.key === "ArrowLeft") goTo(currentIndex - 1);
    });
  }

  function openResetModal() {
    el.resetModal.hidden = false;
    el.resetConfirmBtn.focus();
  }

  function closeResetModal() {
    el.resetModal.hidden = true;
    el.resetBtn.focus();
  }

  function buildSectionOptions() {
    el.sectionSelect.innerHTML = "";
    const countBySection = new Map();
    for (const q of data.questions) {
      countBySection.set(q.sectionId, (countBySection.get(q.sectionId) || 0) + 1);
    }

    const allOpt = document.createElement("option");
    allOpt.value = "all";
    allOpt.textContent = `All Sections (${data.questions.length})`;
    el.sectionSelect.appendChild(allOpt);

    for (const section of data.sections) {
      const opt = document.createElement("option");
      opt.value = section.id;
      const count = countBySection.get(section.id) || 0;
      opt.textContent = `${section.id} · ${section.title} (${count})`;
      el.sectionSelect.appendChild(opt);
    }
  }

  function shuffle(array) {
    for (let i = array.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
  }

  /** questionId -> shuffled options array, cached so the A/B/C/D order stays
   *  stable while a question is on screen (incl. after answering it), but is
   *  re-randomized fresh each time the app loads or progress is reset. */
  const optionOrderCache = new Map();

  function getOptionOrder(question) {
    let order = optionOrderCache.get(question.id);
    if (!order) {
      order = shuffle(question.options.slice());
      optionOrderCache.set(question.id, order);
    }
    return order;
  }

  function applyFilter(filterValue) {
    currentFilter = filterValue;
    filteredQuestions =
      filterValue === "all"
        ? shuffle(data.questions.slice())
        : data.questions.filter((q) => q.sectionId === filterValue);
    currentIndex = 0;
    render();
  }

  function goTo(index) {
    if (index < 0 || index >= filteredQuestions.length) return;
    currentIndex = index;
    render();
  }

  function currentQuestion() {
    return filteredQuestions[currentIndex] || null;
  }

  function render() {
    renderProgress();
    renderSidebar();

    const question = currentQuestion();

    if (!question) {
      el.card.hidden = true;
      el.emptyState.hidden = false;
      el.prevBtn.disabled = true;
      el.nextBtn.disabled = true;
      return;
    }

    el.card.hidden = false;
    el.emptyState.hidden = true;

    const section = sectionsById.get(question.sectionId);
    el.sectionBadge.textContent = section ? `${section.id} · ${section.title}` : question.sectionId;
    el.questionText.textContent = question.question;

    renderOptions(question);

    el.prevBtn.disabled = currentIndex === 0;
    el.nextBtn.disabled = currentIndex === filteredQuestions.length - 1;
  }

  function renderSidebar() {
    el.questionList.innerHTML = "";

    filteredQuestions.forEach((q, i) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "question-item";
      if (i === currentIndex) item.classList.add("current");

      const dot = document.createElement("span");
      dot.className = "status-dot";
      const chosenId = answers[q.id];
      if (chosenId) {
        const chosen = q.options.find((o) => o.id === chosenId);
        const isCorrect = Boolean(chosen && chosen.correct);
        dot.classList.add(isCorrect ? "correct" : "incorrect");
        dot.textContent = isCorrect ? "✓" : "✕";
      }

      const label = document.createElement("span");
      label.textContent = `Q${i + 1}`;

      item.appendChild(dot);
      item.appendChild(label);
      item.addEventListener("click", () => goTo(i));

      el.questionList.appendChild(item);
    });
  }

  function renderOptions(question) {
    el.optionsContainer.innerHTML = "";
    const selectedOptionId = answers[question.id];
    const answered = Boolean(selectedOptionId);
    const letters = "ABCDEFGH";
    const orderedOptions = getOptionOrder(question);

    orderedOptions.forEach((option, i) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "option";
      btn.disabled = answered;

      const isSelected = option.id === selectedOptionId;

      if (answered) {
        btn.classList.add("revealed");
        if (option.correct) {
          btn.classList.add("correct");
        } else if (isSelected) {
          btn.classList.add("incorrect");
        } else {
          btn.classList.add("dimmed");
        }
      }

      const row = document.createElement("div");
      row.className = "option-row";

      const letterEl = document.createElement("div");
      letterEl.className = "option-letter";
      letterEl.textContent = letters[i] || String(i + 1);

      const body = document.createElement("div");
      body.className = "option-body";

      const textEl = document.createElement("div");
      textEl.className = "option-text";
      textEl.textContent = option.text;

      const explanationEl = document.createElement("div");
      explanationEl.className = "option-explanation";
      explanationEl.textContent = option.explanation || "";

      body.appendChild(textEl);
      body.appendChild(explanationEl);
      row.appendChild(letterEl);
      row.appendChild(body);
      btn.appendChild(row);

      btn.addEventListener("click", () => selectAnswer(question, option));

      el.optionsContainer.appendChild(btn);
    });
  }

  function selectAnswer(question, option) {
    if (answers[question.id]) return; // already answered, locked
    answers[question.id] = option.id;
    saveProgress();
    render();
  }

  function renderProgress() {
    const total = filteredQuestions.length;
    const currentNum = total === 0 ? 0 : currentIndex + 1;
    el.progressText.textContent = `Question ${currentNum} of ${total}`;

    let answeredCount = 0;
    let correctCount = 0;
    for (const q of filteredQuestions) {
      const chosenId = answers[q.id];
      if (chosenId) {
        answeredCount++;
        const chosen = q.options.find((o) => o.id === chosenId);
        if (chosen && chosen.correct) correctCount++;
      }
    }

    el.scoreText.textContent = `Score: ${correctCount} / ${answeredCount}`;
    const pct = total === 0 ? 0 : (answeredCount / total) * 100;
    el.progressFill.style.width = pct + "%";
  }

  function showLoadError(message) {
    el.card.hidden = true;
    el.loadError.hidden = false;
    el.loadError.textContent = message;
  }

  fetch("questions.json")
    .then((res) => {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    })
    .then(init)
    .catch((err) => {
      showLoadError(
        "Couldn't load questions.json (" + err.message + "). " +
        "If you opened this file directly (file://), your browser is blocking local file loading. " +
        "Serve this folder instead, e.g. run: python -m http.server  --then open http://localhost:8000/"
      );
    });
})();
