"""
SLA (Service Level Agreement) monitoring service.
"""

import datetime
from typing import Optional

from bot.config import get_settings
from bot.database.connection import get_session
from bot.database.repositories.automation_repository import AutomationRepository
from bot.database.repositories.ticket_repository import TicketRepository
from bot.models.ticket import Ticket, TicketPriority, SLAEvent
from bot.utils.logger import get_logger

logger = get_logger(__name__)

settings = get_settings()


class SLAService:
    """Service for SLA monitoring and compliance."""
    
    def __init__(self):
        self.default_sla_targets = {
            TicketPriority.URGENT: {
                "first_response": settings.sla_first_response_urgent,
                "resolution": settings.sla_resolution_urgent,
            },
            TicketPriority.HIGH: {
                "first_response": settings.sla_first_response_high,
                "resolution": settings.sla_resolution_high,
            },
            TicketPriority.MEDIUM: {
                "first_response": settings.sla_first_response_medium,
                "resolution": settings.sla_resolution_medium,
            },
            TicketPriority.LOW: {
                "first_response": settings.sla_first_response_low,
                "resolution": settings.sla_resolution_low,
            },
        }
    
    async def get_sla_target(self, guild_id: int, priority: str, event_type: str) -> int:
        """
        Get SLA target time for a specific priority and event type.
        
        Args:
            guild_id: Guild ID
            priority: Ticket priority
            event_type: Event type ('first_response', 'resolution', 'follow_up')
            
        Returns:
            Target time in minutes
        """
        async with get_session() as session:
            automation_repo = AutomationRepository(session)
            
            # Check for custom SLA rule
            sla_rule = await automation_repo.get_sla_rule_by_priority(guild_id, priority)
            
            if sla_rule:
                if event_type == "first_response":
                    return sla_rule.first_response_target
                elif event_type == "resolution":
                    return sla_rule.resolution_target
                elif event_type == "follow_up" and sla_rule.follow_up_target:
                    return sla_rule.follow_up_target
            
            # Use default targets
            priority_enum = TicketPriority(priority.lower())
            default_targets = self.default_sla_targets.get(priority_enum, {})
            
            if event_type == "first_response":
                return default_targets.get("first_response", 60)
            elif event_type == "resolution":
                return default_targets.get("resolution", 1440)
            elif event_type == "follow_up":
                return default_targets.get("follow_up", 60)
            
            return 60  # Default fallback
    
    async def create_sla_events_for_ticket(self, ticket: Ticket) -> list[SLAEvent]:
        """
        Create SLA events for a new ticket.
        
        Args:
            ticket: The ticket to create SLA events for
            
        Returns:
            List of created SLA events
        """
        async with get_session() as session:
            ticket_repo = TicketRepository(session)
            automation_repo = AutomationRepository(session)
            
            events = []
            now = datetime.datetime.now(datetime.timezone.utc)
            
            # Create first response SLA event
            first_response_target = await self.get_sla_target(
                ticket.guild_id, ticket.priority, "first_response"
            )
            first_response_time = now + datetime.timedelta(minutes=first_response_target)
            
            first_response_event = await automation_repo.create_sla_event(
                ticket_id=ticket.id,
                event_type="first_response",
                target_minutes=first_response_target,
                target_time=first_response_time,
            )
            events.append(first_response_event)
            
            # Create resolution SLA event
            resolution_target = await self.get_sla_target(
                ticket.guild_id, ticket.priority, "resolution"
            )
            resolution_time = now + datetime.timedelta(minutes=resolution_target)
            
            resolution_event = await automation_repo.create_sla_event(
                ticket_id=ticket.id,
                event_type="resolution",
                target_minutes=resolution_target,
                target_time=resolution_time,
            )
            events.append(resolution_event)
            
            logger.info(
                f"Created SLA events for ticket #{ticket.number}: "
                f"first_response={first_response_target}min, resolution={resolution_target}min"
            )
            
            return events
    
    async def record_first_response(self, ticket: Ticket) -> Optional[SLAEvent]:
        """
        Record the first response time for a ticket.
        
        Args:
            ticket: The ticket to record first response for
            
        Returns:
            The updated SLA event, or None if not found
        """
        async with get_session() as session:
            ticket_repo = TicketRepository(session)
            automation_repo = AutomationRepository(session)
            
            # Get the first response SLA event
            events = await automation_repo.get_sla_events_by_ticket(ticket.id)
            first_response_event = None
            
            for event in events:
                if event.event_type == "first_response" and event.status == "pending":
                    first_response_event = event
                    break
            
            if not first_response_event:
                logger.warning(f"No pending first_response SLA event found for ticket #{ticket.number}")
                return None
            
            # Update the event
            now = datetime.datetime.now(datetime.timezone.utc)
            breached = now > first_response_event.target_time
            status = "breached" if breached else "met"
            
            updated_event = await automation_repo.update_sla_event(
                event=first_response_event,
                actual_time=now,
                status=status,
                breached=breached,
            )
            
            # Update ticket
            ticket.first_response_at = now
            await ticket_repo.update_ticket(ticket)
            
            logger.info(
                f"Recorded first response for ticket #{ticket.number}: "
                f"status={status}, breached={breached}"
            )
            
            return updated_event
    
    async def record_resolution(self, ticket: Ticket) -> Optional[SLAEvent]:
        """
        Record the resolution time for a ticket.
        
        Args:
            ticket: The ticket to record resolution for
            
        Returns:
            The updated SLA event, or None if not found
        """
        async with get_session() as session:
            ticket_repo = TicketRepository(session)
            automation_repo = AutomationRepository(session)
            
            # Get the resolution SLA event
            events = await automation_repo.get_sla_events_by_ticket(ticket.id)
            resolution_event = None
            
            for event in events:
                if event.event_type == "resolution" and event.status == "pending":
                    resolution_event = event
                    break
            
            if not resolution_event:
                logger.warning(f"No pending resolution SLA event found for ticket #{ticket.number}")
                return None
            
            # Update the event
            now = datetime.datetime.now(datetime.timezone.utc)
            breached = now > resolution_event.target_time
            status = "breached" if breached else "met"
            
            updated_event = await automation_repo.update_sla_event(
                event=resolution_event,
                actual_time=now,
                status=status,
                breached=breached,
            )
            
            logger.info(
                f"Recorded resolution for ticket #{ticket.number}: "
                f"status={status}, breached={breached}"
            )
            
            return updated_event
    
    async def check_sla_compliance(self, guild_id: int) -> list[dict]:
        """
        Check SLA compliance for all tickets in a guild.
        
        Args:
            guild_id: Guild ID to check
            
        Returns:
            List of dictionaries with SLA compliance information
        """
        async with get_session() as session:
            ticket_repo = TicketRepository(session)
            
            # Get tickets that need SLA checking
            tickets = await ticket_repo.get_tickets_needing_sla_check(guild_id)
            
            results = []
            
            for ticket in tickets:
                # Get SLA events for this ticket
                events = await ticket_repo.get_sla_events_by_ticket(ticket.id)
                
                for event in events:
                    if event.status == "pending":
                        now = datetime.datetime.now(datetime.timezone.utc)
                        breached = now > event.target_time
                        
                        if breached:
                            # Update the event
                            await ticket_repo.update_sla_event(
                                event=event,
                                actual_time=now,
                                status="breached",
                                breached=True,
                            )
                            
                            results.append({
                                "ticket_number": ticket.number,
                                "ticket_id": ticket.id,
                                "event_type": event.event_type,
                                "target_time": event.target_time,
                                "breached": True,
                                "priority": ticket.priority,
                            })
                            
                            logger.warning(
                                f"SLA breach detected: ticket #{ticket.number}, "
                                f"event={event.event_type}, priority={ticket.priority}"
                            )
            
            return results
    
    async def get_sla_summary(self, guild_id: int, days: int = 30) -> dict:
        """
        Get SLA compliance summary for a guild.
        
        Args:
            guild_id: Guild ID
            days: Number of days to look back
            
        Returns:
            Dictionary with SLA summary statistics
        """
        async with get_session() as session:
            automation_repo = AutomationRepository(session)
            
            # Get recent automation logs for SLA events
            logs = await automation_repo.get_automation_logs_by_guild(
                guild_id=guild_id,
                action_type="sla_breach",
                limit=1000
            )
            
            # Calculate statistics
            total_events = len(logs)
            breaches = [log for log in logs if log.details.get("breached", False)]
            breach_count = len(breaches)
            
            summary = {
                "total_events": total_events,
                "breach_count": breach_count,
                "compliance_rate": ((total_events - breach_count) / total_events * 100) if total_events > 0 else 100,
                "days": days,
            }
            
            return summary


# Global SLA service instance
_sla_service: Optional[SLAService] = None


def get_sla_service() -> SLAService:
    """Get the global SLA service instance."""
    global _sla_service
    if _sla_service is None:
        _sla_service = SLAService()
    return _sla_service
