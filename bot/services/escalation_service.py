"""
Escalation service for automatic ticket escalation.
"""

import datetime
from typing import List, Optional

from bot.database.connection import get_session
from bot.database.repositories.automation_repository import AutomationRepository
from bot.database.repositories.ticket_repository import TicketRepository
from bot.models.automation import EscalationRule
from bot.models.ticket import Ticket, TicketPriority
from bot.utils.logger import get_logger

logger = get_logger(__name__)


class EscalationService:
    """Service for automatic ticket escalation based on rules."""
    
    def __init__(self):
        self.escalation_cooldowns = {}  # Track cooldowns per ticket
    
    async def check_escalation_rules(self, guild_id: int) -> List[dict]:
        """
        Check and apply escalation rules for a guild.
        
        Args:
            guild_id: Guild ID to check
            
        Returns:
            List of escalation actions taken
        """
        async with get_session() as session:
            automation_repo = AutomationRepository(session)
            ticket_repo = TicketRepository(session)
            
            # Get active escalation rules
            rules = await automation_repo.get_escalation_rules_by_guild(guild_id, active_only=True)
            
            actions_taken = []
            
            for rule in rules:
                # Get tickets that match the rule conditions
                matching_tickets = await self._get_matching_tickets(session, rule)
                
                for ticket in matching_tickets:
                    # Check cooldown
                    if self._is_on_cooldown(ticket.id, rule.id, rule.cooldown_minutes):
                        continue
                    
                    # Apply escalation actions
                    actions = await self._apply_escalation_actions(
                        session, ticket, rule, automation_repo
                    )
                    
                    if actions:
                        actions_taken.extend(actions)
                        self._set_cooldown(ticket.id, rule.id)
            
            return actions_taken
    
    async def _get_matching_tickets(self, session, rule: EscalationRule) -> List[Ticket]:
        """Get tickets that match an escalation rule's conditions."""
        ticket_repo = TicketRepository(session)
        
        # Get open tickets for the guild
        tickets = await ticket_repo.get_tickets_by_guild(
            rule.guild_id, status=TicketStatus.OPEN
        )
        
        matching_tickets = []
        now = datetime.datetime.now(datetime.timezone.utc)
        
        for ticket in tickets:
            # Check priority filter
            if rule.priority_filter and ticket.priority not in rule.priority_filter:
                continue
            
            # Check condition type
            condition_met = False
            
            if rule.condition_type == "time_unclaimed":
                # Escalate if ticket has been unclaimed for X minutes
                if not ticket.claimed_by:
                    time_since_creation = (now - ticket.created_at).total_seconds() / 60
                    if time_since_creation >= rule.condition_value.get("minutes", 30):
                        condition_met = True
            
            elif rule.condition_type == "time_since_last_response":
                # Escalate if no response for X minutes
                time_since_activity = (now - ticket.last_activity).total_seconds() / 60
                if time_since_activity >= rule.condition_value.get("minutes", 60):
                    condition_met = True
            
            elif rule.condition_type == "priority":
                # Escalate if ticket has specific priority
                if ticket.priority in rule.condition_value.get("priorities", []):
                    condition_met = True
            
            elif rule.condition_type == "custom":
                # Custom condition (would be implemented based on specific needs)
                condition_met = await self._check_custom_condition(ticket, rule.condition_value)
            
            if condition_met:
                matching_tickets.append(ticket)
        
        return matching_tickets
    
    async def _check_custom_condition(self, ticket: Ticket, condition_value: dict) -> bool:
        """Check custom escalation conditions."""
        # This would be implemented based on specific custom conditions
        # For now, return False
        return False
    
    async def _apply_escalation_actions(
        self,
        session,
        ticket: Ticket,
        rule: EscalationRule,
        automation_repo: AutomationRepository,
    ) -> List[dict]:
        """Apply escalation actions for a ticket."""
        actions_taken = []
        
        for action in rule.actions:
            action_type = action.get("type")
            
            try:
                if action_type == "ping_role":
                    await self._action_ping_role(ticket, action)
                    actions_taken.append({
                        "action": "ping_role",
                        "role_id": action.get("role_id"),
                        "ticket_number": ticket.number,
                    })
                
                elif action_type == "dm_user":
                    await self._action_dm_user(ticket, action)
                    actions_taken.append({
                        "action": "dm_user",
                        "user_id": action.get("user_id"),
                        "ticket_number": ticket.number,
                    })
                
                elif action_type == "change_priority":
                    await self._action_change_priority(ticket, action)
                    actions_taken.append({
                        "action": "change_priority",
                        "new_priority": action.get("priority"),
                        "ticket_number": ticket.number,
                    })
                
                elif action_type == "reassign":
                    await self._action_reassign(ticket, action)
                    actions_taken.append({
                        "action": "reassign",
                        "role_id": action.get("role_id"),
                        "ticket_number": ticket.number,
                    })
                
                # Log the action
                await automation_repo.log_automation(
                    guild_id=ticket.guild_id,
                    action_type="escalation",
                    details={
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "ticket_number": ticket.number,
                        "action": action_type,
                        "action_details": action,
                    },
                    triggered_by="system",
                    ticket_id=ticket.id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                )
                
            except Exception as e:
                logger.error(
                    f"Failed to apply escalation action {action_type} for ticket #{ticket.number}: {e}"
                )
                
                await automation_repo.log_automation(
                    guild_id=ticket.guild_id,
                    action_type="escalation",
                    details={
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "ticket_number": ticket.number,
                        "action": action_type,
                        "action_details": action,
                        "error": str(e),
                    },
                    triggered_by="system",
                    ticket_id=ticket.id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    success=False,
                    error_message=str(e),
                )
        
        return actions_taken
    
    async def _action_ping_role(self, ticket: Ticket, action: dict):
        """Ping a role in the ticket channel."""
        # This would use the Discord API to send a message
        # For now, this is a placeholder
        logger.info(f"Would ping role {action.get('role_id')} in ticket #{ticket.number}")
    
    async def _action_dm_user(self, ticket: Ticket, action: dict):
        """DM a user about the ticket."""
        # This would use the Discord API to send a DM
        # For now, this is a placeholder
        logger.info(f"Would DM user {action.get('user_id')} about ticket #{ticket.number}")
    
    async def _action_change_priority(self, ticket: Ticket, action: dict):
        """Change the priority of a ticket."""
        async with get_session() as session:
            ticket_repo = TicketRepository(session)
            
            new_priority = action.get("priority")
            if new_priority:
                ticket.priority = new_priority
                await ticket_repo.update_ticket(ticket)
                logger.info(f"Changed priority of ticket #{ticket.number} to {new_priority}")
    
    async def _action_reassign(self, ticket: Ticket, action: dict):
        """Reassign the ticket to a specific role or user."""
        # This would use the assignment service
        # For now, this is a placeholder
        logger.info(f"Would reassign ticket #{ticket.number} based on action: {action}")
    
    def _is_on_cooldown(self, ticket_id: int, rule_id: int, cooldown_minutes: int) -> bool:
        """Check if a ticket is on cooldown for an escalation rule."""
        cooldown_key = f"{ticket_id}:{rule_id}"
        
        if cooldown_key not in self.escalation_cooldowns:
            return False
        
        cooldown_time = self.escalation_cooldowns[cooldown_key]
        now = datetime.datetime.now(datetime.timezone.utc)
        
        return (now - cooldown_time).total_seconds() < (cooldown_minutes * 60)
    
    def _set_cooldown(self, ticket_id: int, rule_id: int):
        """Set a cooldown for a ticket and escalation rule."""
        cooldown_key = f"{ticket_id}:{rule_id}"
        self.escalation_cooldowns[cooldown_key] = datetime.datetime.now(datetime.timezone.utc)
    
    async def manually_escalate_ticket(
        self,
        ticket: Ticket,
        reason: str,
        escalated_by: int,
    ) -> bool:
        """
        Manually escalate a ticket.
        
        Args:
            ticket: The ticket to escalate
            reason: Reason for escalation
            escalated_by: ID of the user who escalated
            
        Returns:
            True if successful
        """
        async with get_session() as session:
            automation_repo = AutomationRepository(session)
            
            # Log the manual escalation
            await automation_repo.log_automation(
                guild_id=ticket.guild_id,
                action_type="manual_escalation",
                details={
                    "ticket_number": ticket.number,
                    "reason": reason,
                },
                triggered_by="user",
                triggered_by_id=escalated_by,
                ticket_id=ticket.id,
            )
            
            logger.info(
                f"Manually escalated ticket #{ticket.number} by user {escalated_by}. "
                f"Reason: {reason}"
            )
            
            return True


# Global escalation service instance
_escalation_service: Optional[EscalationService] = None


def get_escalation_service() -> EscalationService:
    """Get the global escalation service instance."""
    global _escalation_service
    if _escalation_service is None:
        _escalation_service = EscalationService()
    return _escalation_service
