# Exam Prep Quiz

A small local quiz app with instant per-answer feedback (correct/incorrect + explanation for every option), section filtering, previous/next navigation, and progress/score tracking saved in the browser.

## Run it

Browsers block `fetch()` of local JSON when you open `index.html` directly (`file://`), so serve the folder instead:

```bash
cd quiz
python -m http.server 8000
```

Then open http://localhost:8000/ in your browser.

## Adding questions

All content lives in [questions.json](questions.json) — edit it directly, no code changes needed.

```json
{
  "examTitle": "Agentic Architecture & Orchestration",
  "sections": [
    { "id": "1.1", "title": "Agentic Loops" }
  ],
  "questions": [
    {
      "id": "1.1-q3",
      "sectionId": "1.1",
      "question": "Your question text here?",
      "options": [
        { "id": "a", "text": "Option text", "correct": false, "explanation": "Why this is wrong." },
        { "id": "b", "text": "Option text", "correct": true,  "explanation": "Why this is right." }
      ]
    }
  ]
}
```

Rules:
- `sections[].id` is the label shown in the section dropdown (e.g. `1.1`) — add a new section object here before referencing it.
- Each question's `sectionId` must match a `sections[].id`.
- Each question `id` must be unique.
- Options can be any length (A, B, C, D, ...); exactly one should have `"correct": true`.
- Every option should have its own `explanation` — it's revealed for whichever option gets picked, and for all options at once so you can see why each one is right or wrong.

Progress (answers + score) is saved per-browser via `localStorage`. Use the "Reset Progress" button to clear it.
