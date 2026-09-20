"""
Auto-assignment service for ticket distribution.
"""

import random
from typing import Optional, List

from bot.database.connection import get_session
from bot.database.repositories.ticket_repository import TicketRepository
from bot.database.repositories.user_repository import UserRepository
from bot.models.ticket import Ticket
from bot.utils.logger import get_logger

logger = get_logger(__name__)


class AssignmentService:
    """Service for automatic ticket assignment."""
    
    def __init__(self):
        self.assignment_strategies = {
            "round_robin": self._round_robin_assignment,
            "least_loaded": self._least_loaded_assignment,
            "specialization": self._specialization_assignment,
            "random": self._random_assignment,
        }
    
    async def auto_assign_ticket(
        self,
        ticket: Ticket,
        strategy: str = "least_loaded",
        specialization: Optional[str] = None,
    ) -> Optional[int]:
        """
        Automatically assign a ticket to a staff member.
        
        Args:
            ticket: The ticket to assign
            strategy: Assignment strategy ('round_robin', 'least_loaded', 'specialization', 'random')
            specialization: Optional specialization filter
            
        Returns:
            ID of the assigned staff member, or None if no suitable staff found
        """
        async with get_session() as session:
            ticket_repo = TicketRepository(session)
            user_repo = UserRepository(session)
            
            # Get the assignment function
            assignment_func = self.assignment_strategies.get(strategy, self._least_loaded_assignment)
            
            # Find suitable staff member
            staff_id = await assignment_func(ticket, user_repo, specialization)
            
            if staff_id:
                # Assign the ticket
                await ticket_repo.claim_ticket(ticket, staff_id)
                
                logger.info(
                    f"Auto-assigned ticket #{ticket.number} to staff {staff_id} "
                    f"using strategy: {strategy}"
                )
                
                return staff_id
            else:
                logger.warning(f"No suitable staff found for ticket #{ticket.number}")
                return None
    
    async def _round_robin_assignment(
        self,
        ticket: Ticket,
        user_repo: UserRepository,
        specialization: Optional[str] = None,
    ) -> Optional[int]:
        """Round-robin assignment strategy."""
        # Get all staff members
        if specialization:
            staff = await user_repo.get_staff_by_specialization(specialization)
        else:
            staff = await user_repo.get_staff_members(ticket.guild_id)
        
        if not staff:
            return None
        
        # Simple round-robin: assign to the staff member with the fewest total claims
        # In a real implementation, this would use a more sophisticated round-robin
        return min(staff, key=lambda s: s.tickets_claimed).id
    
    async def _least_loaded_assignment(
        self,
        ticket: Ticket,
        user_repo: UserRepository,
        specialization: Optional[str] = None,
    ) -> Optional[int]:
        """Least-loaded assignment strategy (assign to staff with fewest active tickets)."""
        # Get staff member with least active tickets
        staff = await user_repo.get_staff_with_least_active_tickets(ticket.guild_id)
        
        if staff:
            return staff.id
        
        return None
    
    async def _specialization_assignment(
        self,
        ticket: Ticket,
        user_repo: UserRepository,
        specialization: Optional[str] = None,
    ) -> Optional[int]:
        """Specialization-based assignment strategy."""
        if not specialization:
            # Use ticket type as specialization
            specialization = ticket.ticket_type
        
        # Get staff with matching specialization
        staff = await user_repo.get_staff_by_specialization(specialization)
        
        if not staff:
            # Fallback to least loaded
            return await self._least_loaded_assignment(ticket, user_repo, None)
        
        # Assign to the least loaded among specialized staff
        return min(staff, key=lambda s: s.tickets_claimed).id
    
    async def _random_assignment(
        self,
        ticket: Ticket,
        user_repo: UserRepository,
        specialization: Optional[str] = None,
    ) -> Optional[int]:
        """Random assignment strategy."""
        # Get all staff members
        if specialization:
            staff = await user_repo.get_staff_by_specialization(specialization)
        else:
            staff = await user_repo.get_staff_members(ticket.guild_id)
        
        if not staff:
            return None
        
        # Random selection
        return random.choice(staff).id
    
    async def reassign_ticket(
        self,
        ticket: Ticket,
        new_staff_id: int,
        reason: str = "Manual reassignment",
    ) -> bool:
        """
        Reassign a ticket to a different staff member.
        
        Args:
            ticket: The ticket to reassign
            new_staff_id: ID of the new staff member
            reason: Reason for reassignment
            
        Returns:
            True if successful
        """
        async with get_session() as session:
            ticket_repo = TicketRepository(session)
            user_repo = UserRepository(session)
            
            # Verify new staff member is actually staff
            new_staff = await user_repo.get_user(new_staff_id)
            if not new_staff or not new_staff.is_staff:
                logger.error(f"User {new_staff_id} is not staff, cannot reassign ticket")
                return False
            
            # Unassign from current claimer
            if ticket.claimed_by:
                await ticket_repo.unclaim_ticket(ticket)
            
            # Assign to new staff member
            await ticket_repo.claim_ticket(ticket, new_staff_id)
            
            logger.info(
                f"Reassigned ticket #{ticket.number} from {ticket.claimed_by} to {new_staff_id}. "
                f"Reason: {reason}"
            )
            
            return True
    
    async def get_assignment_suggestions(
        self,
        ticket: Ticket,
        limit: int = 5,
    ) -> List[dict]:
        """
        Get suggested staff members for ticket assignment.
        
        Args:
            ticket: The ticket to get suggestions for
            limit: Maximum number of suggestions
            
        Returns:
            List of dictionaries with staff member information
        """
        async with get_session() as session:
            user_repo = UserRepository(session)
            
            # Get staff members
            staff = await user_repo.get_staff_members(ticket.guild_id)
            
            # Sort by least loaded (fewest active tickets)
            staff_sorted = sorted(staff, key=lambda s: s.tickets_claimed)
            
            suggestions = []
            for staff_member in staff_sorted[:limit]:
                suggestions.append({
                    "id": staff_member.id,
                    "name": staff_member.display_name,
                    "specialization": staff_member.staff_specialization,
                    "active_tickets": staff_member.tickets_claimed,
                    "resolved_tickets": staff_member.tickets_resolved,
                    "avg_response_time": staff_member.avg_response_time_seconds,
                })
            
            return suggestions


# Global assignment service instance
_assignment_service: Optional[AssignmentService] = None


def get_assignment_service() -> AssignmentService:
    """Get the global assignment service instance."""
    global _assignment_service
    if _assignment_service is None:
        _assignment_service = AssignmentService()
    return _assignment_service
