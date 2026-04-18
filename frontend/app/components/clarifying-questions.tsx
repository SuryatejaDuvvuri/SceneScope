import { useState } from "react";

type ClarifyingQuestion = string | { question: string; suggestion?: string };
interface ClarifyingQuestionsProps {
  questions: ClarifyingQuestion[];
  onSubmit: (answers: Record<string, string>, feedback: string) => void;
  disabled: boolean;
  remainingAttempts: number;
}

export function ClarifyingQuestions({
  questions,
  onSubmit,
  disabled,
  remainingAttempts,
}: ClarifyingQuestionsProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState("");

  function handleAnswer(question: string, value: string) {
    setAnswers((prev) => ({ ...prev, [question]: value }));
  }

  function handleSubmit() {
    onSubmit(answers, feedback);
    setAnswers({});
    setFeedback("");
  }

  const hasInput = Object.values(answers).some((a) => a.trim()) || feedback.trim();

  return (
    <div className="space-y-4">
      {/* ── Questions ── */}
      {questions.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-display text-sand-700 tracking-wider">
            Clarifying Questions
          </h3>
          {questions.map((q, i) => {
            const text = typeof q === "string" ? q : q.question;
            const suggestion = typeof q === "object" && q.suggestion;
            return (
              <div key={i}>
                <label className="block text-sm text-stone-600 mb-1">
                  {text}
                </label>
                {suggestion && (
                  <div className="text-xs text-sand-600 mb-1 pl-1">{suggestion}</div>
                )}
                <input
                  type="text"
                  value={answers[text] || ""}
                  onChange={(e) => handleAnswer(text, e.target.value)}
                  disabled={disabled}
                  placeholder="Your answer..."
                  className="w-full px-3 py-1.5 text-sm bg-white/70 border border-sand-600/25 rounded text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-1 focus:ring-sand-500/40 focus:border-sand-500/40 disabled:opacity-50"
                />
              </div>
            );
          })}
        </div>
      )}

      {/* ── Free-text Feedback ── */}
      <div>
        <label className="block text-sm font-display text-sand-700 tracking-wider mb-1">
          Additional Feedback
        </label>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          disabled={disabled}
          rows={2}
          placeholder="Too bright, should be moodier..."
          className="w-full px-3 py-1.5 text-sm bg-white/70 border border-sand-600/25 rounded text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-1 focus:ring-sand-500/40 focus:border-sand-500/40 disabled:opacity-50 resize-none"
        />
      </div>

      {/* ── Submit ── */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-stone-500 font-mono">
          {remainingAttempts} refinement{remainingAttempts !== 1 ? "s" : ""} remaining
        </span>
        <button
          onClick={handleSubmit}
          disabled={disabled || !hasInput}
          className="px-4 py-2 bg-sand-700 text-white border border-sand-600 text-sm rounded font-display hover:bg-sand-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Refine Sketch
        </button>
      </div>
    </div>
  );
}
