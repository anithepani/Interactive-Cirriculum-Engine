"""Pipeline DAG: chains the stage tasks into the full generation flow.

ingest -> (transcribe || vision)  [parallel chord]
       -> segment -> concepts+checkpoints
       -> generate -> validate -> persist -> mark_ready
"""
from __future__ import annotations

from celery import chain, chord
from ice_worker.celery_app import celery_app


@celery_app.task(name="ice_worker.pipeline.generate_curriculum")
def generate_curriculum(video_ref: str, tenant_id: str) -> str:
    """Top-level entry: kicks off the full async pipeline. Returns curriculum_id.

    Phase 1+: implement as a chord/chain of the stage tasks in ice_worker.tasks.*.
    Per-curriculum token budget enforced in ice_worker.budgets.
    """
    # pipeline = chain(
    #     ingest.s(video_ref, tenant_id),
    #     chord(transcribe.s(), vision.s(), segment.s()),
    #     generate.s(),
    #     validate.s(),
    # )
    raise NotImplementedError("Phase 1-3 deliverable")
