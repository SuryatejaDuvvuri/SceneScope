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
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
            Clarifying Questions
          </h3>
          {questions.map((q, i) => {
            const text = typeof q === "string" ? q : q.question;
            const suggestion = typeof q === "object" && q.suggestion;
            return (
              <div key={i}>
                <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                  {text}
                </label>
                {suggestion && (
                  <div className="text-xs text-blue-500 dark:text-blue-300 mb-1 pl-1">{suggestion}</div>
                )}
                <input
                  type="text"
                  value={answers[text] || ""}
                  onChange={(e) => handleAnswer(text, e.target.value)}
                  disabled={disabled}
                  placeholder="Your answer..."
                  className="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                />
              </div>
            );
          })}
        </div>
      )}

      {/* ── Free-text Feedback ── */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">
          Additional Feedback
        </label>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          disabled={disabled}
          rows={2}
          placeholder="Too bright, should be moodier..."
          className="w-full px-3 py-1.5 text-sm bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 resize-none"
        />
      </div>

      {/* ── Submit ── */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400 dark:text-gray-500">
          {remainingAttempts} refinement{remainingAttempts !== 1 ? "s" : ""} remaining
        </span>
        <button
          onClick={handleSubmit}
          disabled={disabled || !hasInput}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Refine Sketch
        </button>
      </div>
    </div>
  );
}
