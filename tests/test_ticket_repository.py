"""
Tests for ticket repository.
"""

import pytest
from datetime import datetime, timezone

from bot.database.connection import get_session
from bot.database.repositories.ticket_repository import TicketRepository
from bot.models.ticket import Ticket, TicketStatus, TicketPriority


@pytest.mark.asyncio
async def test_create_ticket():
    """Test creating a new ticket."""
    async with get_session() as session:
        repo = TicketRepository(session)
        
        ticket = await repo.create_ticket(
            number=1,
            guild_id=123456789,
            channel_id=987654321,
            owner_id=111222333,
            subject="Test ticket",
            description="This is a test ticket",
            ticket_type="general",
            priority=TicketPriority.MEDIUM,
        )
        
        assert ticket.id is not None
        assert ticket.number == 1
        assert ticket.subject == "Test ticket"
        assert ticket.status == TicketStatus.OPEN
        assert ticket.priority == TicketPriority.MEDIUM


@pytest.mark.asyncio
async def test_get_ticket_by_id():
    """Test retrieving a ticket by ID."""
    async with get_session() as session:
        repo = TicketRepository(session)
        
        # Create a ticket first
        created = await repo.create_ticket(
            number=2,
            guild_id=123456789,
            channel_id=987654322,
            owner_id=111222334,
            subject="Test ticket 2",
            description="Test description",
        )
        
        # Retrieve the ticket
        retrieved = await repo.get_ticket_by_id(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.subject == "Test ticket 2"


@pytest.mark.asyncio
async def test_claim_ticket():
    """Test claiming a ticket."""
    async with get_session() as session:
        repo = TicketRepository(session)
        
        # Create a ticket
        ticket = await repo.create_ticket(
            number=3,
            guild_id=123456789,
            channel_id=987654323,
            owner_id=111222335,
            subject="Unclaimed ticket",
            description="Test",
        )
        
        # Claim the ticket
        claimer_id = 444555666
        claimed = await repo.claim_ticket(ticket, claimer_id)
        
        assert claimed.claimed_by == claimer_id
        assert claimed.need_human is False


@pytest.mark.asyncio
async def test_close_ticket():
    """Test closing a ticket."""
    async with get_session() as session:
        repo = TicketRepository(session)
        
        # Create a ticket
        ticket = await repo.create_ticket(
            number=4,
            guild_id=123456789,
            channel_id=987654324,
            owner_id=111222336,
            subject="Open ticket",
            description="Test",
        )
        
        # Close the ticket
        closed = await repo.close_ticket(ticket, resolved=True)
        
        assert closed.status == TicketStatus.CLOSED
        assert closed.resolved_at is not None


@pytest.mark.asyncio
async def test_get_open_tickets_count():
    """Test counting open tickets for a user."""
    async with get_session() as session:
        repo = TicketRepository(session)
        
        user_id = 111222337
        guild_id = 123456789
        
        # Create multiple tickets
        await repo.create_ticket(
            number=5, guild_id=guild_id, channel_id=987654325,
            owner_id=user_id, subject="Open 1", description="Test"
        )
        await repo.create_ticket(
            number=6, guild_id=guild_id, channel_id=987654326,
            owner_id=user_id, subject="Open 2", description="Test"
        )
        
        # Count open tickets
        count = await repo.get_open_tickets_count(user_id, guild_id)
        
        assert count >= 2  # May have other tickets from previous tests
