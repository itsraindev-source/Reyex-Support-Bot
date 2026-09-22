"""Initial migration: Create all tables

Revision ID: 001
Revises: 
Create Date: 2025-09-20 00:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(100), nullable=True),
        sa.Column('discriminator', sa.String(10), nullable=True),
        sa.Column('global_name', sa.String(100), nullable=True),
        sa.Column('avatar', sa.String(100), nullable=True),
        sa.Column('language', sa.String(10), default='en'),
        sa.Column('auto_translate', sa.Boolean(), default=False),
        sa.Column('tickets_created', sa.Integer(), default=0),
        sa.Column('tickets_closed', sa.Integer(), default=0),
        sa.Column('is_staff', sa.Boolean(), default=False),
        sa.Column('staff_specialization', sa.String(50), nullable=True),
        sa.Column('tickets_claimed', sa.Integer(), default=0),
        sa.Column('tickets_resolved', sa.Integer(), default=0),
        sa.Column('avg_response_time_seconds', sa.Integer(), nullable=True),
        sa.Column('total_response_time_seconds', sa.Integer(), default=0),
        sa.Column('preferences', sa.JSON(), default=dict),
        sa.Column('metadata', sa.JSON(), default=dict),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=True)
    op.create_index('ix_users_is_staff', 'users', ['is_staff'])

    # Create guild_configs table
    op.create_table(
        'guild_configs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('support_role_id', sa.Integer(), nullable=True),
        sa.Column('admin_role_id', sa.Integer(), nullable=True),
        sa.Column('ticket_category_id', sa.Integer(), nullable=True),
        sa.Column('transcript_channel_id', sa.Integer(), nullable=True),
        sa.Column('max_open_tickets_per_user', sa.Integer(), default=3),
        sa.Column('ticket_prefix', sa.String(20), default='ticket-'),
        sa.Column('enable_translation', sa.Boolean(), default=True),
        sa.Column('enable_automation', sa.Boolean(), default=True),
        sa.Column('enable_auto_assignment', sa.Boolean(), default=False),
        sa.Column('auto_assignment_strategy', sa.String(50), default='round_robin'),
        sa.Column('auto_close_enabled', sa.Boolean(), default=False),
        sa.Column('auto_close_hours', sa.Integer(), default=24),
        sa.Column('ticket_types', sa.JSON(), default=dict),
        sa.Column('disabled_ticket_types', sa.JSON(), default=list),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_guild_configs_id', 'guild_configs', ['id'])

    # Create tickets table
    op.create_table(
        'tickets',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('number', sa.Integer(), nullable=False),
        sa.Column('guild_id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ticket_type', sa.String(50), nullable=False, default='general'),
        sa.Column('status', sa.String(20), nullable=False, default='open'),
        sa.Column('priority', sa.String(20), nullable=False, default='medium'),
        sa.Column('claimed_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('channel_name', sa.String(100), nullable=True),
        sa.Column('auto_close', sa.Boolean(), default=False),
        sa.Column('need_human', sa.Boolean(), default=False),
        sa.Column('locked', sa.Boolean(), default=False),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=False),
        sa.Column('first_response_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata', sa.JSON(), default=dict),
    )
    op.create_index('ix_tickets_id', 'tickets', ['id'])
    op.create_index('ix_tickets_number', 'tickets', ['number'], unique=True)
    op.create_index('ix_tickets_guild_id', 'tickets', ['guild_id'])
    op.create_index('ix_tickets_channel_id', 'tickets', ['channel_id'], unique=True)
    op.create_index('ix_tickets_owner_id', 'tickets', ['owner_id'])
    op.create_index('ix_tickets_status', 'tickets', ['status'])
    op.create_index('ix_tickets_priority', 'tickets', ['priority'])
    op.create_index('ix_tickets_claimed_by', 'tickets', ['claimed_by'])
    op.create_index('ix_tickets_created_at', 'tickets', ['created_at'])

    # Create ticket_messages table
    op.create_table(
        'ticket_messages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('tickets.id'), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('author_type', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('is_staff', sa.Boolean(), default=False),
        sa.Column('attachments', sa.JSON(), default=list),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_ticket_messages_id', 'ticket_messages', ['id'])
    op.create_index('ix_ticket_messages_ticket_id', 'ticket_messages', ['ticket_id'])
    op.create_index('ix_ticket_messages_author_id', 'ticket_messages', ['author_id'])
    op.create_index('ix_ticket_messages_created_at', 'ticket_messages', ['created_at'])

    # Create sla_events table
    op.create_table(
        'sla_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('tickets.id'), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('target_minutes', sa.Integer(), nullable=False),
        sa.Column('target_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actual_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('breached', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_sla_events_id', 'sla_events', ['id'])
    op.create_index('ix_sla_events_ticket_id', 'sla_events', ['ticket_id'])

    # Create sla_rules table
    op.create_table(
        'sla_rules',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('guild_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(20), nullable=False),
        sa.Column('ticket_type', sa.String(50), nullable=True),
        sa.Column('first_response_target', sa.Integer(), nullable=False),
        sa.Column('resolution_target', sa.Integer(), nullable=False),
        sa.Column('follow_up_target', sa.Integer(), nullable=True),
        sa.Column('alert_before_breach', sa.Integer(), default=15),
        sa.Column('alert_channel_id', sa.Integer(), nullable=True),
        sa.Column('alert_role_id', sa.Integer(), nullable=True),
        sa.Column('business_hours_only', sa.Boolean(), default=False),
        sa.Column('business_hours_start', sa.String(5), nullable=True),
        sa.Column('business_hours_end', sa.String(5), nullable=True),
        sa.Column('business_days', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_sla_rules_id', 'sla_rules', ['id'])
    op.create_index('ix_sla_rules_guild_id', 'sla_rules', ['guild_id'])
    op.create_index('ix_sla_rules_is_active', 'sla_rules', ['is_active'])

    # Create canned_responses table
    op.create_table(
        'canned_responses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('guild_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('tags', sa.JSON(), default=list),
        sa.Column('usage_count', sa.Integer(), default=0),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('required_role_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_canned_responses_id', 'canned_responses', ['id'])
    op.create_index('ix_canned_responses_guild_id', 'canned_responses', ['guild_id'])
    op.create_index('ix_canned_responses_category', 'canned_responses', ['category'])
    op.create_index('ix_canned_responses_is_active', 'canned_responses', ['is_active'])

    # Create escalation_rules table
    op.create_table(
        'escalation_rules',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('guild_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('condition_type', sa.String(50), nullable=False),
        sa.Column('condition_value', sa.JSON(), nullable=False),
        sa.Column('priority_filter', sa.JSON(), nullable=True),
        sa.Column('actions', sa.JSON(), nullable=False),
        sa.Column('escalation_level', sa.Integer(), default=1),
        sa.Column('max_escalations', sa.Integer(), default=3),
        sa.Column('cooldown_minutes', sa.Integer(), default=60),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_escalation_rules_id', 'escalation_rules', ['id'])
    op.create_index('ix_escalation_rules_guild_id', 'escalation_rules', ['guild_id'])
    op.create_index('ix_escalation_rules_is_active', 'escalation_rules', ['is_active'])

    # Create automation_logs table
    op.create_table(
        'automation_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('guild_id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=True),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=True),
        sa.Column('rule_name', sa.String(100), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('success', sa.Boolean(), default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('triggered_by', sa.String(50), nullable=False),
        sa.Column('triggered_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_automation_logs_id', 'automation_logs', ['id'])
    op.create_index('ix_automation_logs_guild_id', 'automation_logs', ['guild_id'])
    op.create_index('ix_automation_logs_ticket_id', 'automation_logs', ['ticket_id'])
    op.create_index('ix_automation_logs_created_at', 'automation_logs', ['created_at'])


def downgrade() -> None:
    op.drop_table('automation_logs')
    op.drop_table('escalation_rules')
    op.drop_table('canned_responses')
    op.drop_table('sla_rules')
    op.drop_table('sla_events')
    op.drop_table('ticket_messages')
    op.drop_table('tickets')
    op.drop_table('users')
