from sentence_transformers import SentenceTransformer

from app.config import settings


class EmbeddingService:
    def __init__(self) -> None:
        self._model: SentenceTransformer | None = None

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            kwargs: dict[str, str] = {}
            if settings.embedding_cache_path:
                kwargs["cache_folder"] = settings.embedding_cache_path
            self._model = SentenceTransformer(settings.embedding_model, **kwargs)
        return self._model

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of text chunks."""
        model = self._get_model()
        embeddings = model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()
