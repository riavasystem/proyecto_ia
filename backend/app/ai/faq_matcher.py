import unicodedata

from app.models.faq import FAQ

_STOPWORDS = {
    "el", "la", "los", "las", "de", "del", "un", "una", "y", "o", "a",
    "en", "que", "es", "por", "para", "con", "se", "su", "mi", "tu",
}  # fmt: skip

MATCH_THRESHOLD = 0.5


def _significant_words(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    folded = "".join(c for c in normalized if not unicodedata.combining(c))
    words = {w.strip("¿?¡!.,") for w in folded.split()}
    return words - _STOPWORDS


def find_best_faq_match(message: str, faqs: list[FAQ]) -> FAQ | None:
    """Match simple por superposición de palabras significativas entre el
    mensaje y la pregunta de cada FAQ. Sin embeddings: es una heurística de
    palabras, no búsqueda semántica."""
    message_words = _significant_words(message)
    if not message_words:
        return None

    best_faq: FAQ | None = None
    best_score = 0.0
    for faq in faqs:
        question_words = _significant_words(faq.question)
        if not question_words:
            continue
        overlap = message_words & question_words
        score = len(overlap) / len(question_words)
        if score > best_score:
            best_score = score
            best_faq = faq

    return best_faq if best_score >= MATCH_THRESHOLD else None
