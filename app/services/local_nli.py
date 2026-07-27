from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import logging
import os
from pathlib import Path
from threading import Lock

import numpy as np
import onnxruntime as ort

from app.core.config import settings


LOGGER = logging.getLogger(__name__)

MODEL_NAME = "multilingual-MiniLMv2-L6-mnli-xnli-int8"
MODEL_FILE = "model_int8.onnx"
MAX_PAIR_TOKENS = 192
PAD_TOKEN_ID = 1


@dataclass(frozen=True, slots=True)
class NliScores:
    entailment: float
    neutral: float
    contradiction: float


class LocalNliVerifier:
    """Lazy CPU-only multilingual entailment/contradiction verifier."""

    def __init__(self, model_dir: str | Path) -> None:
        self.model_dir = Path(model_dir)
        self._session: ort.InferenceSession | None = None
        self._tokenizer = None
        self._load_attempted = False
        self._lock = Lock()

    @property
    def configured(self) -> bool:
        return (
            settings.offline_nli_model_enabled
            and (self.model_dir / "tokenizer.json").is_file()
            and (self.model_dir / MODEL_FILE).is_file()
        )

    @property
    def available(self) -> bool:
        return self._ensure_loaded()

    def _ensure_loaded(self) -> bool:
        if self._session is not None and self._tokenizer is not None:
            return True
        if not settings.offline_nli_model_enabled:
            return False
        # Do not treat another thread's in-progress load as a failed load. It
        # waits on this lock, then observes the fully initialized session.
        with self._lock:
            if self._session is not None and self._tokenizer is not None:
                return True
            if self._load_attempted:
                return False
            self._load_attempted = True
            tokenizer_path = self.model_dir / "tokenizer.json"
            model_path = self.model_dir / MODEL_FILE
            if not tokenizer_path.exists() or not model_path.exists():
                LOGGER.info(
                    "Offline NLI model is not installed at %s",
                    self.model_dir,
                )
                return False
            try:
                from tokenizers import Tokenizer

                tokenizer = Tokenizer.from_file(str(tokenizer_path))
                options = ort.SessionOptions()
                options.intra_op_num_threads = min(2, max(1, os.cpu_count() or 1))
                options.inter_op_num_threads = 1
                options.enable_cpu_mem_arena = False
                options.enable_mem_pattern = False
                session = ort.InferenceSession(
                    str(model_path),
                    sess_options=options,
                    providers=["CPUExecutionProvider"],
                )
            except Exception:
                LOGGER.exception(
                    "Unable to load offline NLI model from %s",
                    self.model_dir,
                )
                return False
            self._tokenizer = tokenizer
            self._session = session
            return True

    def score(
        self,
        *,
        premise: str,
        hypotheses: list[str],
    ) -> tuple[list[NliScores] | None, bool]:
        """Return NLI probabilities and whether any pair exceeded the token cap."""

        if not hypotheses or not self._ensure_loaded():
            return None, False
        assert self._tokenizer is not None and self._session is not None

        encodings = [
            self._tokenizer.encode(premise, pair=hypothesis)
            for hypothesis in hypotheses
        ]
        overflow = any(len(encoding.ids) > MAX_PAIR_TOKENS for encoding in encodings)
        if overflow:
            return None, True

        max_length = max(len(encoding.ids) for encoding in encodings)

        def padded(values: list[int], fill: int = 0) -> list[int]:
            return values + [fill] * (max_length - len(values))

        input_ids = np.asarray(
            [padded(encoding.ids, PAD_TOKEN_ID) for encoding in encodings],
            dtype=np.int64,
        )
        attention_mask = np.asarray(
            [padded(encoding.attention_mask) for encoding in encodings],
            dtype=np.int64,
        )
        logits = self._session.run(
            None,
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
            },
        )[0]
        shifted = logits - logits.max(axis=1, keepdims=True)
        probabilities = np.exp(shifted)
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        return [
            NliScores(
                entailment=float(row[0]),
                neutral=float(row[1]),
                contradiction=float(row[2]),
            )
            for row in probabilities
        ], False


@lru_cache(maxsize=1)
def get_local_nli_verifier() -> LocalNliVerifier:
    return LocalNliVerifier(settings.offline_nli_model_dir)
