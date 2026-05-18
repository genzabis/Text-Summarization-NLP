"""Wrapper untuk Google Gemini summarization."""

from __future__ import annotations

import os
from threading import Lock
from typing import Optional


_PROMPT_TEMPLATE = (
    "Anda adalah asisten peringkas berita berbahasa Indonesia. "
    "Ringkas teks berikut menjadi {n_sentences} kalimat yang padat, "
    "informatif, dan tetap mempertahankan fakta inti. "
    "Tulis ringkasan dalam bahasa Indonesia yang baku, hindari basa-basi, "
    "dan jangan tambahkan informasi yang tidak ada di teks.\n\n"
    "TEKS:\n{text}\n\nRINGKASAN:"
)


class GeminiSummarizer:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash") -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = model_name
        self._model = None
        self._lock = Lock()
        self._error: Optional[str] = None

    # ---------------------------------------------------------------- status
    def is_ready(self) -> bool:
        return bool(self.api_key) and self._error is None

    def status(self) -> dict:
        return {
            "ready": self.is_ready(),
            "model_name": self.model_name,
            "has_api_key": bool(self.api_key),
            "loaded": self._model is not None,
            "error": self._error,
        }

    # ------------------------------------------------------------------ load
    def _load(self) -> None:
        with self._lock:
            if self._model is not None:
                return
            if not self.api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY belum di-set. Salin .env.example menjadi .env "
                    "lalu isi API key dari https://aistudio.google.com/app/apikey."
                )
            try:
                import google.generativeai as genai  # noqa: WPS433 (lazy import)
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError(
                    "Library google-generativeai belum terpasang. "
                    "Jalankan: pip install google-generativeai"
                ) from exc

            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.model_name)

    # --------------------------------------------------------------- predict
    def summarize(self, text: str, n_sentences: int = 3) -> str:
        text = (text or "").strip()
        if not text:
            return ""
        self._load()
        assert self._model is not None

        prompt = _PROMPT_TEMPLATE.format(n_sentences=n_sentences, text=text)
        response = self._model.generate_content(prompt)
        # google-generativeai mengekspos atribut .text untuk respon teks.
        result = getattr(response, "text", None)
        if result is None:
            # Fallback bila SDK mengembalikan candidates secara terstruktur.
            try:
                result = response.candidates[0].content.parts[0].text  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                result = ""
        return (result or "").strip()
