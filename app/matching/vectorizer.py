"""Vectorization utilities for job text."""
from __future__ import annotations

from typing import Sequence

import numpy as np
from numpy.typing import NDArray
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import strip_accents_ascii


class TextVectorizer:
    """Wrapper around scikit-learn TF-IDF vectorizer for job matching."""

    def __init__(self) -> None:
        self._vectorizer = TfidfVectorizer(
            stop_words="english", strip_accents=strip_accents_ascii
        )
        self._job_matrix: NDArray[np.float64] | None = None

    def fit_jobs(self, documents: Sequence[str]) -> NDArray[np.float64]:
        """Fit the vectorizer on job documents and store the matrix in memory."""

        if not documents:
            self._job_matrix = np.zeros((0, 0), dtype=np.float64)
            return self._job_matrix
        matrix = self._vectorizer.fit_transform(documents)
        self._job_matrix = matrix.toarray().astype(np.float64)
        return self._job_matrix

    def transform_jobs(self, documents: Sequence[str]) -> NDArray[np.float64]:
        """Transform job documents using the fitted model."""

        if not getattr(self._vectorizer, "vocabulary_", None):
            return self.fit_jobs(documents)
        matrix = self._vectorizer.transform(documents)
        return matrix.toarray().astype(np.float64)

    def job_vector(self, index: int) -> NDArray[np.float64]:
        """Return the stored vector for a job at the given index."""

        if self._job_matrix is None:
            raise RuntimeError("Vectorizer has not been fitted with job documents.")
        if index < 0 or index >= self._job_matrix.shape[0]:
            raise IndexError("Job index out of range for stored vectors.")
        return self._job_matrix[index]

    def transform_profile(self, profile_text: str) -> NDArray[np.float64]:
        """Transform a single profile text into a dense vector."""

        if not getattr(self._vectorizer, "vocabulary_", None):
            raise RuntimeError("Vectorizer must be fitted before transforming profiles.")
        vector = self._vectorizer.transform([profile_text])
        return vector.toarray()[0].astype(np.float64)
