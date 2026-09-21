
"""
Extra credit: short-term conversational memory.

Stores recent successful question-and-answer exchanges
during an interactive terminal session.
"""

from dataclasses import dataclass, field


@dataclass
class ConversationMemory:
    max_turns: int = 3
    history: list[tuple[str, str]] = field(default_factory=list)

    def add(self, question: str, answer: str) -> None:
        """Save a successful question and answer."""
        self.history.append((question, answer))

        # Keep only the most recent exchanges.
        self.history = self.history[-self.max_turns:]

    def clear(self) -> None:
        """Remove the current conversation history."""
        self.history.clear()

    def contextualize(self, question: str) -> str:
        """Create a retrieval query using recent questions."""

        if not self.history:
            return question

        previous_questions = [
            previous_question
            for previous_question, _ in self.history
        ]

        context = " ".join(previous_questions)

        return (
            f"Previous conversation topic: {context}\n"
            f"Current question: {question}"
        )