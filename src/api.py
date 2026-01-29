from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from .odoo_client import odoo_client
from .config import ODOO_DB, ODOO_EMAIL, ODOO_PASSWORD, logger
import html

router = APIRouter()

# Data Models
class PRItem(BaseModel):
    id: int
    name: str
    state: str
    date_start: str
    requested_by: str
    amount: float

class PRDetail(PRItem):
    description: str
    assigned_to: str
    lines: List[dict]

# Helper to authenticate
def get_uid():
    try:
        return odoo_client.authenticate(ODOO_DB, ODOO_EMAIL, ODOO_PASSWORD)
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

@router.get("/api/prs", response_model=List[PRItem])
async def get_prs(state: Optional[str] = None, q: Optional[str] = None):
    try:
        uid = get_uid()
        domain = []
        if state and state != 'all':
            domain.append(('state', '=', state))
        
        if q:
            # Search by name or requester (ilike is case insensitive)
            # Appending a block like ['|', A, B] acts as AND(..., OR(A, B))
            domain.append('|')
            domain.append(('name', 'ilike', q))
            domain.append(('requested_by', 'ilike', q))

        # Default sort by date desc is handled by Odoo default usually, or we can enforce
        prs = odoo_client.search_prs(ODOO_DB, uid, ODOO_PASSWORD, domain, limit=80)
        
        result = []
        for pr in prs:
            # Parse requested_by safely
            req_val = pr.get('requested_by')
            requester = req_val[1] if isinstance(req_val, list) else str(req_val)
            
            result.append(PRItem(
                id=pr['id'],
                name=pr.get('name', 'N/A'),
                state=pr.get('state', 'unknown'),
                date_start=str(pr.get('date_start', '')),
                requested_by=requester,
                amount=pr.get('estimated_cost', 0.0)
            ))
        return result
    except Exception as e:
        logger.error(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/pr/{pr_id}", response_model=PRDetail)
async def get_pr_detail(pr_id: int):
    try:
        uid = get_uid()
        pr = odoo_client.get_pr_details(ODOO_DB, uid, ODOO_PASSWORD, pr_id)
        if not pr:
            raise HTTPException(status_code=404, detail="PR not found")
            
        # Parse fields
        req_val = pr.get('requested_by')
        requester = req_val[1] if isinstance(req_val, list) else str(req_val)
        
        assign_val = pr.get('assigned_to')
        assigned = assign_val[1] if isinstance(assign_val, list) else (assign_val or "Unassigned")

        return PRDetail(
            id=pr['id'],
            name=pr.get('name', 'N/A'),
            state=pr.get('state', 'unknown'),
            date_start=str(pr.get('date_start', '')),
            requested_by=requester,
            amount=pr.get('estimated_cost', 0.0),
            description=str(pr.get('description') or ''),
            assigned_to=assigned,
            lines=pr.get('lines', [])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
