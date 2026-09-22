"""
Main entry point for the Reyex Support Bot.
Uses the modern modular architecture with PostgreSQL and Redis.
"""

from bot.bot import run_bot

if __name__ == "__main__":
    run_bot()
