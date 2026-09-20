"""
Ticket repository for database operations.
"""

import datetime
from typing import List, Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.ticket import Ticket, TicketMessage, SLAEvent, TicketStatus, TicketPriority
from bot.utils.logger import get_logger

logger = get_logger(__name__)


class TicketRepository:
    """Repository for ticket-related database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_ticket(
        self,
        number: int,
        guild_id: int,
        channel_id: int,
        owner_id: int,
        subject: str,
        description: str,
        ticket_type: str = "general",
        priority: str = TicketPriority.MEDIUM,
        category_id: Optional[int] = None,
        channel_name: Optional[str] = None,
    ) -> Ticket:
        """Create a new ticket."""
        now = datetime.datetime.now(datetime.timezone.utc)
        ticket = Ticket(
            number=number,
            guild_id=guild_id,
            channel_id=channel_id,
            owner_id=owner_id,
            subject=subject,
            description=description,
            ticket_type=ticket_type,
            status=TicketStatus.OPEN,
            priority=priority,
            category_id=category_id,
            channel_name=channel_name,
            last_activity=now,
            created_at=now,
            updated_at=now,
        )
        
        self.session.add(ticket)
        await self.session.flush()
        await self.session.refresh(ticket)
        
        logger.info(f"Created ticket #{number} for user {owner_id}")
        return ticket
    
    async def get_ticket_by_id(self, ticket_id: int) -> Optional[Ticket]:
        """Get a ticket by ID."""
        result = await self.session.execute(select(Ticket).where(Ticket.id == ticket_id))
        return result.scalar_one_or_none()
    
    async def get_ticket_by_number(self, number: int) -> Optional[Ticket]:
        """Get a ticket by number."""
        result = await self.session.execute(select(Ticket).where(Ticket.number == number))
        return result.scalar_one_or_none()
    
    async def get_ticket_by_channel_id(self, channel_id: int) -> Optional[Ticket]:
        """Get a ticket by Discord channel ID."""
        result = await self.session.execute(select(Ticket).where(Ticket.channel_id == channel_id))
        return result.scalar_one_or_none()
    
    async def get_tickets_by_guild(
        self,
        guild_id: int,
        status: Optional[TicketStatus] = None,
        priority: Optional[TicketPriority] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Ticket]:
        """Get tickets for a guild with optional filters."""
        query = select(Ticket).where(Ticket.guild_id == guild_id)
        
        if status:
            query = query.where(Ticket.status == status)
        if priority:
            query = query.where(Ticket.priority == priority)
        
        query = query.order_by(Ticket.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_tickets_by_owner(
        self,
        owner_id: int,
        guild_id: int,
        status: Optional[TicketStatus] = None,
    ) -> List[Ticket]:
        """Get tickets owned by a user."""
        query = select(Ticket).where(
            and_(Ticket.owner_id == owner_id, Ticket.guild_id == guild_id)
        )
        
        if status:
            query = query.where(Ticket.status == status)
        
        query = query.order_by(Ticket.created_at.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_open_tickets_count(self, owner_id: int, guild_id: int) -> int:
        """Get count of open tickets for a user."""
        result = await self.session.execute(
            select(func.count(Ticket.id))
            .where(
                and_(
                    Ticket.owner_id == owner_id,
                    Ticket.guild_id == guild_id,
                    Ticket.status == TicketStatus.OPEN
                )
            )
        )
        return result.scalar() or 0
    
    async def update_ticket(self, ticket: Ticket) -> Ticket:
        """Update a ticket."""
        ticket.updated_at = datetime.datetime.now(datetime.timezone.utc)
        await self.session.flush()
        await self.session.refresh(ticket)
        return ticket
    
    async def claim_ticket(self, ticket: Ticket, claimer_id: int) -> Ticket:
        """Claim a ticket."""
        ticket.claimed_by = claimer_id
        ticket.need_human = False
        ticket.last_activity = datetime.datetime.now(datetime.timezone.utc)
        ticket.updated_at = datetime.datetime.now(datetime.timezone.utc)
        
        await self.session.flush()
        await self.session.refresh(ticket)
        
        logger.info(f"Ticket #{ticket.number} claimed by user {claimer_id}")
        return ticket
    
    async def unclaim_ticket(self, ticket: Ticket) -> Ticket:
        """Unclaim a ticket."""
        ticket.claimed_by = None
        ticket.last_activity = datetime.datetime.now(datetime.timezone.utc)
        ticket.updated_at = datetime.datetime.now(datetime.timezone.utc)
        
        await self.session.flush()
        await self.session.refresh(ticket)
        
        logger.info(f"Ticket #{ticket.number} unclaimed")
        return ticket
    
    async def close_ticket(self, ticket: Ticket, resolved: bool = True) -> Ticket:
        """Close a ticket."""
        ticket.status = TicketStatus.CLOSED
        ticket.resolved_at = datetime.datetime.now(datetime.timezone.utc) if resolved else None
        ticket.last_activity = datetime.datetime.now(datetime.timezone.utc)
        ticket.updated_at = datetime.datetime.now(datetime.timezone.utc)
        
        await self.session.flush()
        await self.session.refresh(ticket)
        
        logger.info(f"Ticket #{ticket.number} closed (resolved: {resolved})")
        return ticket
    
    async def delete_ticket(self, ticket: Ticket) -> None:
        """Delete a ticket."""
        await self.session.delete(ticket)
        logger.info(f"Ticket #{ticket.number} deleted")
    
    async def get_next_ticket_number(self) -> int:
        """Get the next ticket number."""
        result = await self.session.execute(select(func.max(Ticket.number)))
        max_number = result.scalar() or 0
        return max_number + 1
    
    async def add_ticket_message(
        self,
        ticket_id: int,
        message_id: int,
        author_id: int,
        author_type: str,
        content: Optional[str],
        is_staff: bool,
        attachments: Optional[List[str]] = None,
    ) -> TicketMessage:
        """Add a message to a ticket."""
        message = TicketMessage(
            ticket_id=ticket_id,
            message_id=message_id,
            author_id=author_id,
            author_type=author_type,
            content=content,
            is_staff=is_staff,
            attachments=attachments or [],
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        
        return message
    
    async def get_ticket_messages(self, ticket_id: int, limit: int = 100) -> List[TicketMessage]:
        """Get messages for a ticket."""
        query = (
            select(TicketMessage)
            .where(TicketMessage.ticket_id == ticket_id)
            .order_by(TicketMessage.created_at.asc())
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def create_sla_event(
        self,
        ticket_id: int,
        event_type: str,
        target_minutes: int,
        target_time: datetime.datetime,
    ) -> SLAEvent:
        """Create an SLA event for a ticket."""
        event = SLAEvent(
            ticket_id=ticket_id,
            event_type=event_type,
            target_minutes=target_minutes,
            target_time=target_time,
            status="pending",
            breached=False,
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        
        return event
    
    async def update_sla_event(
        self,
        event: SLAEvent,
        actual_time: datetime.datetime,
        status: str,
        breached: bool,
    ) -> SLAEvent:
        """Update an SLA event."""
        event.actual_time = actual_time
        event.status = status
        event.breached = breached
        
        await self.session.flush()
        await self.session.refresh(event)
        
        return event
    
    async def get_sla_events_by_ticket(self, ticket_id: int) -> List[SLAEvent]:
        """Get SLA events for a ticket."""
        query = (
            select(SLAEvent)
            .where(SLAEvent.ticket_id == ticket_id)
            .order_by(SLAEvent.created_at.desc())
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_tickets_needing_sla_check(self, guild_id: int) -> List[Ticket]:
        """Get tickets that need SLA status checking."""
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Get open tickets with SLA events that are pending and past target time
        query = (
            select(Ticket)
            .join(SLAEvent, Ticket.id == SLAEvent.ticket_id)
            .where(
                and_(
                    Ticket.guild_id == guild_id,
                    Ticket.status == TicketStatus.OPEN,
                    SLAEvent.status == "pending",
                    SLAEvent.target_time <= now,
                )
            )
            .distinct()
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
