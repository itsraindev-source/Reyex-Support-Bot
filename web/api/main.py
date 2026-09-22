"""
FastAPI web backend for Reyex Support Bot dashboard.
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from bot.config import get_settings
from bot.database.connection import init_db, close_db, get_session
from bot.database.redis_client import get_redis_client, close_redis
from bot.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Security
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting FastAPI web backend...")
    await init_db()
    redis_client = get_redis_client()
    await redis_client.get_client()  # Initialize connection
    logger.info("Web backend started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down web backend...")
    await close_db()
    await close_redis()
    logger.info("Web backend shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Reyex Support Bot API",
    description="REST API for Reyex Support Bot dashboard",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "reyex-support-api",
        "version": "2.0.0"
    }


# API Routes
@app.get("/api/v1/stats")
async def get_stats():
    """Get basic statistics."""
    async with get_session() as session:
        from bot.database.repositories.ticket_repository import TicketRepository
        from bot.database.repositories.user_repository import UserRepository
        from sqlalchemy import select, func
        from bot.models.ticket import Ticket, TicketStatus
        
        ticket_repo = TicketRepository(session)
        user_repo = UserRepository(session)
        
        # Get ticket counts
        from bot.models.ticket import Ticket, TicketStatus
        from bot.models.user import User
        
        total_tickets_result = await session.execute(select(func.count(Ticket.id)))
        total_tickets = total_tickets_result.scalar() or 0
        
        open_tickets_result = await session.execute(
            select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.OPEN)
        )
        open_tickets = open_tickets_result.scalar() or 0
        
        # Get user counts
        total_users_result = await session.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar() or 0
        
        staff_users_result = await session.execute(
            select(func.count(User.id)).where(User.is_staff == True)
        )
        staff_users = staff_users_result.scalar() or 0
        
        return {
            "tickets": {
                "total": total_tickets,
                "open": open_tickets,
                "closed": total_tickets - open_tickets,
            },
            "users": {
                "total": total_users,
                "staff": staff_users,
            },
        }


@app.get("/api/v1/tickets")
async def get_tickets(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    priority: Optional[str] = None,
):
    """Get tickets with optional filtering."""
    async with get_session() as session:
        from bot.database.repositories.ticket_repository import TicketRepository
        from bot.models.ticket import TicketStatus, TicketPriority
        
        ticket_repo = TicketRepository(session)
        
        # Convert string parameters to enums if provided
        status_enum = TicketStatus(status) if status else None
        priority_enum = TicketPriority(priority) if priority else None
        
        tickets = await ticket_repo.get_tickets_by_guild(
            guild_id=0,  # This would be filtered by actual guild ID in production
            status=status_enum,
            priority=priority_enum,
            limit=limit,
            offset=offset,
        )
        
        return {
            "tickets": [
                {
                    "id": ticket.id,
                    "number": ticket.number,
                    "subject": ticket.subject,
                    "status": ticket.status,
                    "priority": ticket.priority,
                    "owner_id": ticket.owner_id,
                    "claimed_by": ticket.claimed_by,
                    "created_at": ticket.created_at.isoformat(),
                    "updated_at": ticket.updated_at.isoformat(),
                }
                for ticket in tickets
            ],
            "total": len(tickets),
            "limit": limit,
            "offset": offset,
        }


@app.get("/api/v1/tickets/{ticket_id}")
async def get_ticket(ticket_id: int):
    """Get a specific ticket by ID."""
    async with get_session() as session:
        from bot.database.repositories.ticket_repository import TicketRepository
        
        ticket_repo = TicketRepository(session)
        ticket = await ticket_repo.get_ticket_by_id(ticket_id)
        
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        return {
            "id": ticket.id,
            "number": ticket.number,
            "guild_id": ticket.guild_id,
            "channel_id": ticket.channel_id,
            "owner_id": ticket.owner_id,
            "subject": ticket.subject,
            "description": ticket.description,
            "ticket_type": ticket.ticket_type,
            "status": ticket.status,
            "priority": ticket.priority,
            "claimed_by": ticket.claimed_by,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat(),
        }


@app.get("/api/v1/staff")
async def get_staff():
    """Get staff members with statistics."""
    async with get_session() as session:
        from bot.database.repositories.user_repository import UserRepository
        
        user_repo = UserRepository(session)
        staff = await user_repo.get_staff_members(guild_id=0)  # Would be filtered by guild
        
        return {
            "staff": [
                {
                    "id": staff_member.id,
                    "name": staff_member.display_name,
                    "specialization": staff_member.staff_specialization,
                    "tickets_claimed": staff_member.tickets_claimed,
                    "tickets_resolved": staff_member.tickets_resolved,
                    "avg_response_time": staff_member.avg_response_time_seconds,
                }
                for staff_member in staff
            ]
        }


@app.get("/api/v1/sla/summary")
async def get_sla_summary(days: int = 30):
    """Get SLA compliance summary."""
    from bot.services.sla_service import get_sla_service
    
    sla_service = get_sla_service()
    summary = await sla_service.get_sla_summary(guild_id=0, days=days)  # Would be filtered by guild
    
    return summary


@app.get("/api/v1/sla/compliance")
async def get_sla_compliance(guild_id: int = 0, days: int = 30):
    """Get detailed SLA compliance metrics."""
    async with get_session() as session:
        from bot.database.repositories.ticket_repository import TicketRepository
        from bot.models.ticket import Ticket, TicketStatus, SLAEvent
        from sqlalchemy import select, func, and_
        
        ticket_repo = TicketRepository(session)
        
        # Get total tickets in period
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        
        total_result = await session.execute(
            select(func.count(Ticket.id)).where(
                and_(
                    Ticket.guild_id == guild_id,
                    Ticket.created_at >= cutoff_date
                )
            )
        )
        total_tickets = total_result.scalar() or 0
        
        # Get SLA events
        events_result = await session.execute(
            select(SLAEvent).where(
                and_(
                    SLAEvent.ticket_id.in_(
                        select(Ticket.id).where(
                            and_(
                                Ticket.guild_id == guild_id,
                                Ticket.created_at >= cutoff_date
                            )
                        )
                    ),
                    SLAEvent.created_at >= cutoff_date
                )
            )
        )
        events = list(events_result.scalars().all())
        
        # Calculate compliance
        total_events = len(events)
        met_events = [e for e in events if e.status == "met"]
        breached_events = [e for e in events if e.status == "breached"]
        
        # Break down by event type
        by_event_type = {}
        for event in events:
            if event.event_type not in by_event_type:
                by_event_type[event.event_type] = {"total": 0, "met": 0, "breached": 0}
            by_event_type[event.event_type]["total"] += 1
            if event.status == "met":
                by_event_type[event.event_type]["met"] += 1
            elif event.status == "breached":
                by_event_type[event.event_type]["breached"] += 1
        
        return {
            "period_days": days,
            "total_tickets": total_tickets,
            "total_events": total_events,
            "met_events": len(met_events),
            "breached_events": len(breached_events),
            "compliance_rate": (len(met_events) / total_events * 100) if total_events > 0 else 100,
            "by_event_type": by_event_type,
        }


@app.get("/api/v1/sla/breaches")
async def get_sla_breaches(guild_id: int = 0, limit: int = 50):
    """Get recent SLA breaches."""
    async with get_session() as session:
        from bot.models.ticket import Ticket, SLAEvent
        from sqlalchemy import select, and_
        
        query = (
            select(Ticket, SLAEvent)
            .join(SLAEvent, Ticket.id == SLAEvent.ticket_id)
            .where(
                and_(
                    Ticket.guild_id == guild_id,
                    SLAEvent.breached == True
                )
            )
            .order_by(SLAEvent.created_at.desc())
            .limit(limit)
        )
        
        result = await session.execute(query)
        breaches = result.all()
        
        return {
            "breaches": [
                {
                    "ticket_number": ticket.number,
                    "ticket_id": ticket.id,
                    "subject": ticket.subject,
                    "priority": ticket.priority,
                    "event_type": event.event_type,
                    "target_time": event.target_time.isoformat(),
                    "actual_time": event.actual_time.isoformat() if event.actual_time else None,
                    "breached_at": event.created_at.isoformat(),
                }
                for ticket, event in breaches
            ],
            "total": len(breaches),
        }


@app.get("/api/v1/analytics/ticket-trends")
async def get_ticket_trends(guild_id: int = 0, days: int = 30):
    """Get ticket creation trends over time."""
    async with get_session() as session:
        from bot.models.ticket import Ticket
        from sqlalchemy import select, func, and_
        import datetime
        
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        
        # Get tickets created per day
        result = await session.execute(
            select(
                func.date(Ticket.created_at).label('date'),
                func.count(Ticket.id).label('count')
            )
            .where(
                and_(
                    Ticket.guild_id == guild_id,
                    Ticket.created_at >= cutoff_date
                )
            )
            .group_by(func.date(Ticket.created_at))
            .order_by(func.date(Ticket.created_at))
        )
        
        trends = [{"date": str(row.date), "count": row.count} for row in result]
        
        return {
            "period_days": days,
            "trends": trends,
            "total": sum(t["count"] for t in trends),
        }


@app.get("/api/v1/analytics/staff-performance")
async def get_staff_performance(guild_id: int = 0, days: int = 30):
    """Get staff performance metrics."""
    async with get_session() as session:
        from bot.models.user import User
        from bot.models.ticket import Ticket
        from sqlalchemy import select, func, and_
        import datetime
        
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        
        # Get staff with their performance metrics
        result = await session.execute(
            select(User)
            .where(User.is_staff == True)
            .order_by(User.tickets_resolved.desc())
        )
        
        staff = result.scalars().all()
        
        performance_data = []
        for staff_member in staff:
            # Get tickets resolved by this staff in the period
            tickets_result = await session.execute(
                select(func.count(Ticket.id)).where(
                    and_(
                        Ticket.guild_id == guild_id,
                        Ticket.claimed_by == staff_member.id,
                        Ticket.resolved_at >= cutoff_date
                    )
                )
            )
            resolved_in_period = tickets_result.scalar() or 0
            
            performance_data.append({
                "id": staff_member.id,
                "name": staff_member.display_name,
                "specialization": staff_member.staff_specialization,
                "tickets_claimed": staff_member.tickets_claimed,
                "tickets_resolved": staff_member.tickets_resolved,
                "resolved_in_period": resolved_in_period,
                "avg_response_time_seconds": staff_member.avg_response_time_seconds,
            })
        
        return {
            "period_days": days,
            "staff": performance_data,
            "total_staff": len(staff),
        }


@app.get("/api/v1/analytics/priority-distribution")
async def get_priority_distribution(guild_id: int = 0, days: int = 30):
    """Get ticket distribution by priority."""
    async with get_session() as session:
        from bot.models.ticket import Ticket, TicketPriority
        from sqlalchemy import select, func, and_
        import datetime
        
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        
        result = await session.execute(
            select(Ticket.priority, func.count(Ticket.id))
            .where(
                and_(
                    Ticket.guild_id == guild_id,
                    Ticket.created_at >= cutoff_date
                )
            )
            .group_by(Ticket.priority)
        )
        
        distribution = {row[0]: row[1] for row in result}
        
        return {
            "period_days": days,
            "distribution": distribution,
            "total": sum(distribution.values()),
        }


@app.get("/api/v1/analytics/type-breakdown")
async def get_type_breakdown(guild_id: int = 0, days: int = 30):
    """Get ticket breakdown by type."""
    async with get_session() as session:
        from bot.models.ticket import Ticket
        from sqlalchemy import select, func, and_
        import datetime
        
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        
        result = await session.execute(
            select(Ticket.ticket_type, func.count(Ticket.id))
            .where(
                and_(
                    Ticket.guild_id == guild_id,
                    Ticket.created_at >= cutoff_date
                )
            )
            .group_by(Ticket.ticket_type)
        )
        
        breakdown = {row[0]: row[1] for row in result}
        
        return {
            "period_days": days,
            "breakdown": breakdown,
            "total": sum(breakdown.values()),
        }


@app.get("/api/v1/analytics/hourly-activity")
async def get_hourly_activity(guild_id: int = 0, days: int = 7):
    """Get ticket activity by hour of day."""
    async with get_session() as session:
        from bot.models.ticket import Ticket
        from sqlalchemy import select, func, and_, extract
        import datetime
        
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        
        result = await session.execute(
            select(
                extract('hour', Ticket.created_at).label('hour'),
                func.count(Ticket.id).label('count')
            )
            .where(
                and_(
                    Ticket.guild_id == guild_id,
                    Ticket.created_at >= cutoff_date
                )
            )
            .group_by(extract('hour', Ticket.created_at))
            .order_by(extract('hour', Ticket.created_at))
        )
        
        activity = {int(row.hour): row.count for row in result}
        
        # Fill in missing hours with 0
        for hour in range(24):
            if hour not in activity:
                activity[hour] = 0
        
        return {
            "period_days": days,
            "hourly_activity": activity,
            "total": sum(activity.values()),
        }


# Discord OAuth2 integration (placeholder)
@app.post("/api/v1/auth/discord")
async def discord_auth(code: str):
    """Handle Discord OAuth2 authentication."""
    # This would implement the full OAuth2 flow
    # For now, return a placeholder response
    return {
        "access_token": "placeholder_token",
        "user_id": 123456789,
        "username": "placeholder_user",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "web.api.main:app",
        host=settings.web_api_host,
        port=settings.web_api_port,
        reload=True,
    )
