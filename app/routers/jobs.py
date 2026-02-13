"""
Jobs Router
Endpoints for the job board: create, read, update, deactivate, search, match
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from supabase import Client
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.database import get_db_admin
from app.models.job import (
    JobCreateRequest, JobUpdateRequest, JobResponse,
    JobListResponse, JobMatchResponse, JobMatchListResponse,
    POSTER_ROLES
)
from app.dependencies import get_current_driver
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# ── Helpers ──────────────────────────────────────────────────────────

def _check_poster_role(driver: dict):
    """Verify the driver has a role allowed to post jobs."""
    role = driver.get("role", "company_driver")
    if role not in POSTER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Role '{role}' cannot post jobs. "
                f"Allowed roles: {', '.join(POSTER_ROLES)}"
            )
        )


def _verify_fmcsa(mc_number: str = None, dot_number: str = None) -> bool:
    """
    Call FMCSA verification service.
    Returns True if the carrier is found, False otherwise.
    """
    try:
        from app.services.fmcsa_api import search_by_dot
        from app.config import settings

        web_key = getattr(settings, "fmcsa_web_key", None)
        if not web_key or not dot_number:
            return False

        result = search_by_dot(dot_number, web_key)
        return result is not None
    except ImportError:
        logger.warning("FMCSA service not available")
        return False
    except Exception as e:
        logger.error(f"FMCSA verification failed: {e}")
        return False


def _row_to_response(row: dict) -> JobResponse:
    """Convert a Supabase row dict to a JobResponse model."""
    return JobResponse(
        id=row["id"],
        posted_by=row["posted_by"],
        title=row["title"],
        company_name=row["company_name"],
        description=row.get("description"),
        how_to_apply=row["how_to_apply"],
        mc_number=row.get("mc_number"),
        dot_number=row.get("dot_number"),
        fmcsa_verified=row.get("fmcsa_verified", False),
        haul_type=row["haul_type"],
        equipment=row["equipment"],
        pay_info=row.get("pay_info"),
        requirements=row.get("requirements", []),
        regions=row.get("regions", []),
        is_active=row.get("is_active", True),
        expires_at=row.get("expires_at"),
        created_at=row["created_at"],
        updated_at=row.get("updated_at", row["created_at"]),
        poster_handle=row.get("poster_handle"),
        poster_cb_handle=row.get("poster_cb_handle"),
    )


# ── POST /api/v1/jobs ───────────────────────────────────────────────

@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreateRequest,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Create a new job posting.
    Requires role: recruiter, fleet_manager, dispatcher,
                   owner_operator, or freight_broker.
    """
    _check_poster_role(driver)

    try:
        # FMCSA verification if DOT provided
        fmcsa_verified = False
        if job_data.dot_number:
            fmcsa_verified = _verify_fmcsa(
                mc_number=job_data.mc_number,
                dot_number=job_data.dot_number
            )

        insert_data = job_data.model_dump()
        insert_data["posted_by"] = driver["id"]
        insert_data["fmcsa_verified"] = fmcsa_verified
        insert_data["haul_type"] = job_data.haul_type.value
        insert_data["equipment"] = job_data.equipment.value

        response = db.from_("job_postings").insert(insert_data).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create job posting"
            )

        logger.info(
            f"Job created by driver {driver['id']}: "
            f"'{job_data.title}' at {job_data.company_name}"
            f"{' (FMCSA verified)' if fmcsa_verified else ''}"
        )

        return _row_to_response(response.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create job posting: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job posting: {str(e)}"
        )


# ── GET /api/v1/jobs ────────────────────────────────────────────────

@router.get("", response_model=JobListResponse)
async def list_jobs(
    haul_type: Optional[str] = Query(None, description="Filter by haul type"),
    equipment: Optional[str] = Query(None, description="Filter by equipment"),
    region: Optional[str] = Query(None, description="Filter by region"),
    requirement: Optional[str] = Query(None, description="Filter by requirement"),
    search: Optional[str] = Query(None, description="Search title/company"),
    fmcsa_verified: Optional[bool] = Query(None, description="Only FMCSA verified"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Client = Depends(get_db_admin)
):
    """
    List active job postings with optional filters.
    Public endpoint - no auth required.
    """
    try:
        query = db.from_("job_postings") \
            .select("*", count="exact") \
            .eq("is_active", True) \
            .gt("expires_at", datetime.utcnow().isoformat())

        if haul_type:
            query = query.eq("haul_type", haul_type)
        if equipment:
            query = query.eq("equipment", equipment)
        if region:
            query = query.contains("regions", [region])
        if requirement:
            query = query.contains("requirements", [requirement])
        if fmcsa_verified is True:
            query = query.eq("fmcsa_verified", True)
        if search:
            query = query.or_(
                f"title.ilike.%{search}%,"
                f"company_name.ilike.%{search}%"
            )

        query = query.order("created_at", desc=True) \
            .range(offset, offset + limit - 1)

        response = query.execute()

        jobs = [_row_to_response(row) for row in (response.data or [])]

        return JobListResponse(
            jobs=jobs,
            total=response.count or 0,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Failed to list jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list jobs"
        )


# ── GET /api/v1/jobs/me ─────────────────────────────────────────────

@router.get("/me", response_model=JobListResponse)
async def list_my_jobs(
    include_inactive: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """List current user's posted jobs."""
    try:
        query = db.from_("job_postings") \
            .select("*", count="exact") \
            .eq("posted_by", driver["id"])

        if not include_inactive:
            query = query.eq("is_active", True)

        query = query.order("created_at", desc=True) \
            .range(offset, offset + limit - 1)

        response = query.execute()
        jobs = [_row_to_response(row) for row in (response.data or [])]

        return JobListResponse(
            jobs=jobs,
            total=response.count or 0,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Failed to list my jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list your jobs"
        )


# ── GET /api/v1/jobs/matches ───────────────────────────────────────

@router.get("/matches", response_model=JobMatchListResponse)
async def get_matching_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Get active jobs that match the current driver's professional profile.
    Sorted by match_score DESC, then created_at DESC.
    """
    try:
        # Fetch driver's professional profile
        profile_query = db.from_("professional_profiles") \
            .select("*") \
            .eq("driver_id", driver["id"])

        profile_resp = profile_query.execute()
        profile = profile_resp.data[0] if profile_resp.data else {}

        driver_cdl = (profile.get("cdl_class") or "").lower()
        driver_endorsements = profile.get("endorsements", []) or []
        driver_equipment = profile.get("equipment_experience", []) or profile.get("equipment_type", []) or []
        if isinstance(driver_equipment, str):
            driver_equipment = [driver_equipment]
        driver_regions = profile.get("preferred_lanes", []) or profile.get("preferred_haul", []) or []
        driver_years_exp = profile.get("years_experience", 0) or 0

        # Fetch all active jobs
        jobs_query = db.from_("job_postings") \
            .select("*") \
            .eq("is_active", True) \
            .gt("expires_at", datetime.utcnow().isoformat()) \
            .order("created_at", desc=True) \
            .execute()

        all_jobs = jobs_query.data or []

        # Score each job
        scored = []
        for row in all_jobs:
            score = 0
            reasons = []
            reqs = row.get("requirements", []) or []
            job_regions = row.get("regions", []) or []
            job_equipment = row.get("equipment", "")

            # CDL match
            cdl_req = f"cdl_{driver_cdl}" if driver_cdl else None
            if cdl_req and cdl_req in reqs:
                score += 1
                reasons.append(f"CDL Class {driver_cdl.upper()} matches")

            # Endorsement matches
            for endorsement in driver_endorsements:
                if endorsement.lower() in reqs:
                    score += 1
                    reasons.append(f"{endorsement} endorsement matches")

            # Equipment match
            if job_equipment in driver_equipment:
                score += 1
                reasons.append(f"{job_equipment} experience matches")

            # Region overlap
            region_overlap = set(driver_regions) & set(job_regions)
            if region_overlap:
                score += len(region_overlap)
                reasons.append(f"Region overlap: {', '.join(region_overlap)}")

            # Experience match
            if driver_years_exp >= 5 and "5yr_exp" in reqs:
                score += 1
                reasons.append("5+ years experience meets requirement")
            elif driver_years_exp >= 2 and "2yr_exp" in reqs:
                score += 1
                reasons.append("2+ years experience meets requirement")
            elif driver_years_exp >= 1 and "1yr_exp" in reqs:
                score += 1
                reasons.append("1+ year experience meets requirement")

            scored.append(JobMatchResponse(
                job=_row_to_response(row),
                match_score=score,
                match_reasons=reasons
            ))

        # Sort by score desc, then created_at desc
        scored.sort(key=lambda m: (-m.match_score, m.job.created_at), reverse=False)

        # Paginate
        total = len(scored)
        page = scored[offset:offset + limit]

        return JobMatchListResponse(
            matches=page,
            total=total,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        logger.error(f"Failed to get matching jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get matching jobs"
        )


# ── GET /api/v1/jobs/{id} ──────────────────────────────────────────

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: Client = Depends(get_db_admin)
):
    """Get a single job posting by ID."""
    try:
        response = db.from_("job_postings") \
            .select("*") \
            .eq("id", str(job_id)) \
            .single() \
            .execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job posting not found"
            )

        return _row_to_response(response.data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job posting"
        )


# ── PATCH /api/v1/jobs/{id} ────────────────────────────────────────

@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: UUID,
    updates: JobUpdateRequest,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """Update a job posting. Only the poster can update."""
    try:
        # Verify ownership
        existing = db.from_("job_postings") \
            .select("id, posted_by") \
            .eq("id", str(job_id)) \
            .single() \
            .execute()

        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job posting not found"
            )

        if existing.data["posted_by"] != driver["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only edit your own job postings"
            )

        update_dict = updates.model_dump(exclude_unset=True)

        # Convert enums to values if present
        if "haul_type" in update_dict and update_dict["haul_type"]:
            update_dict["haul_type"] = update_dict["haul_type"].value \
                if hasattr(update_dict["haul_type"], "value") \
                else update_dict["haul_type"]
        if "equipment" in update_dict and update_dict["equipment"]:
            update_dict["equipment"] = update_dict["equipment"].value \
                if hasattr(update_dict["equipment"], "value") \
                else update_dict["equipment"]

        # Re-verify FMCSA if DOT changed
        if "dot_number" in update_dict:
            dot = update_dict.get("dot_number")
            mc = update_dict.get("mc_number", existing.data.get("mc_number"))
            if dot:
                update_dict["fmcsa_verified"] = _verify_fmcsa(
                    mc_number=mc, dot_number=dot
                )

        if not update_dict:
            full = db.from_("job_postings") \
                .select("*").eq("id", str(job_id)).single().execute()
            return _row_to_response(full.data)

        response = db.from_("job_postings") \
            .update(update_dict) \
            .eq("id", str(job_id)) \
            .execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update job posting"
            )

        logger.info(f"Job {job_id} updated by driver {driver['id']}")
        return _row_to_response(response.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update job posting: {str(e)}"
        )


# ── DELETE /api/v1/jobs/{id} ───────────────────────────────────────

@router.delete("/{job_id}", status_code=status.HTTP_200_OK)
async def deactivate_job(
    job_id: UUID,
    driver: dict = Depends(get_current_driver),
    db: Client = Depends(get_db_admin)
):
    """
    Deactivate (soft delete) a job posting. Only the poster can deactivate.
    """
    try:
        existing = db.from_("job_postings") \
            .select("id, posted_by") \
            .eq("id", str(job_id)) \
            .single() \
            .execute()

        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job posting not found"
            )

        if existing.data["posted_by"] != driver["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only deactivate your own job postings"
            )

        db.from_("job_postings") \
            .update({"is_active": False}) \
            .eq("id", str(job_id)) \
            .execute()

        logger.info(f"Job {job_id} deactivated by driver {driver['id']}")

        return {
            "success": True,
            "message": "Job posting deactivated",
            "job_id": str(job_id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deactivate job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate job posting"
        )
