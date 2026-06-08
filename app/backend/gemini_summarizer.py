"""Wrapper untuk Google Gemini summarization."""

from __future__ import annotations

import os
import json
import urllib.request
import urllib.error
from threading import Lock
from typing import Optional


_PROMPT_TEMPLATE = (
    "Anda adalah asisten peringkas berita berbahasa Indonesia. "
    "Ringkas teks berikut menjadi {n_sentences} poin penting. "
    "Format ringkasan Anda wajib menggunakan daftar penomoran angka (contoh: 1. ..., 2. ..., 3. ...). "
    "Setiap poin harus berupa kalimat yang padat, informatif, dan sesuai fakta teks. "
    "Tulis dalam bahasa Indonesia baku dan hindari basa-basi.\n\n"
    "TEKS:\n{text}\n\nRINGKASAN POIN-POIN:"
)


class GeminiSummarizer:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None, base_url: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = model_name or os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash").strip()
        self.base_url = base_url or os.getenv("GEMINI_BASE_URL", "").strip()
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
            "has_base_url": bool(self.base_url),
            "loaded": self._model is not None or bool(self.base_url),
            "error": self._error,
        }

    # ------------------------------------------------------------------ load
    def _load(self) -> None:
        if self.base_url:
            # Jika menggunakan base_url kustom, kita tidak perlu memuat SDK resmi
            return

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
    def summarize(self, text: str, n_sentences: int = 3, custom_prompt: Optional[str] = None) -> str:
        text = (text or "").strip()
        if not text:
            return ""
        self._load()

        if custom_prompt:
            prompt = custom_prompt.format(n_sentences=n_sentences, text=text)
        else:
            prompt = _PROMPT_TEMPLATE.format(n_sentences=n_sentences, text=text)

        # Jika base_url di-set, panggil endpoint OpenAI-compatible custom via urllib
        if self.base_url:
            url = f"{self.base_url.rstrip('/')}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    result = res_data["choices"][0]["message"]["content"]
                    return (result or "").strip()
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8")
                raise RuntimeError(f"API Custom HTTP {e.code}: {err_body}")
            except Exception as e:
                raise RuntimeError(f"Gagal memanggil API Custom: {e}")

        # Jika tidak, gunakan SDK resmi google-generativeai
        assert self._model is not None
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
