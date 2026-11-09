from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import SlotServiceDep, require_api_key
from app.openapi import errors
from app.schemas import ResetRequest, SlotsOut

router = APIRouter(
    dependencies=[Depends(require_api_key)],
    responses=errors(401),
)


@router.post(
    "/reset",
    response_model=SlotsOut,
    tags=["slots"],
    summary="Replace all slots",
    description=(
        "Replaces every slot with the ones in the body. Also clears all bookings, "
        "idempotency keys and rate-limit history."
    ),
    responses=errors(400),
)
def reset(payload: ResetRequest, service: SlotServiceDep) -> SlotsOut:
    return service.reset(payload)


@router.get(
    "/slots",
    response_model=SlotsOut,
    tags=["slots"],
    summary="List slots",
    description=(
        "All slots in insertion order. `available` is false once a slot has a "
        "confirmed booking."
    ),
)
def list_slots(
    service: SlotServiceDep,
    provider: Annotated[
        str | None, Query(description="Only this provider's slots (exact match)")
    ] = None,
) -> SlotsOut:
    return service.list_slots(provider)


@router.post(
    "/seed",
    response_model=SlotsOut,
    tags=["demo data"],
    summary="Replace everything with random demo data",
    description=(
        "Generates 8 doctors with first and last names, about 550 half-hour slots over "
        "the next 7 working days, and bookings on roughly a quarter of them. Different "
        "every call. Clears all existing slots and bookings first."
    ),
)
def seed(service: SlotServiceDep) -> SlotsOut:
    return service.seed()
