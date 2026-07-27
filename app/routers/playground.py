from __future__ import annotations

import asyncio
from contextlib import suppress

from fastapi import APIRouter, HTTPException, Request, status

from app.core.csrf import validate_csrf
from app.core.rate_limit import limiter
from app.schemas.playground import SemanticGradePayload, SemanticGradeResponse
from app.services.playground_challenges import get_playground_challenge
from app.services.semantic_grading import grade_semantic_answer


router = APIRouter(prefix="/api/playground", tags=["playground"])
_INFERENCE_SLOT = asyncio.Semaphore(1)
_QUEUE_TIMEOUT_SECONDS = 1.5


async def _grade_in_thread(**kwargs):
    return await asyncio.to_thread(grade_semantic_answer, **kwargs)


@router.post("/semantic-grade", response_model=SemanticGradeResponse)
@limiter.limit("10/minute")
async def semantic_grade(
    request: Request,
    payload: SemanticGradePayload,
) -> SemanticGradeResponse:
    validate_csrf(request, payload.csrf_token)
    challenge = get_playground_challenge(payload.challenge_id)
    acquired = False
    grade_task: asyncio.Task | None = None
    try:
        await asyncio.wait_for(
            _INFERENCE_SLOT.acquire(),
            timeout=_QUEUE_TIMEOUT_SECONDS,
        )
        acquired = True
        grade_task = asyncio.create_task(
            _grade_in_thread(
                answer=payload.answer,
                accepted_answers=challenge.accepted_answers,
                minimum_glosses=[
                    (gloss.text, gloss.concept_evidence)
                    for gloss in challenge.minimum_glosses
                ],
                context_concepts=challenge.context_concepts,
                required_concepts=challenge.required_concepts,
                hard_negatives=challenge.hard_negatives,
            )
        )
        result = await asyncio.shield(grade_task)
    except asyncio.CancelledError:
        # ``to_thread`` work cannot be stopped once running. Keep the single
        # inference slot occupied until it actually finishes.
        if grade_task is not None:
            with suppress(Exception):
                await grade_task
        raise
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The local grader is busy. Try again in a moment.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    finally:
        if acquired:
            _INFERENCE_SLOT.release()
    return SemanticGradeResponse.model_validate(result)
