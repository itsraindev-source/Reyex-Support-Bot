# Environment Variables Configuration

This document describes all environment variables used by the Reyex Support Bot.

## Required Variables

These variables must be set for the bot to function:

### Discord Configuration
```env
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_CLIENT_ID=your_discord_client_id_here
```

- `DISCORD_TOKEN`: The bot token from Discord Developer Portal
- `DISCORD_CLIENT_ID`: The application client ID from Discord Developer Portal

### Database Configuration
```env
DATABASE_URL=postgresql://username:password@host:port/database_name
```

- PostgreSQL connection string in SQLAlchemy format
- Example: `postgresql://reyex:password@localhost:5432/reyex_support`

### Redis Configuration
```env
REDIS_URL=redis://host:port/database
```

- Redis connection string
- Example: `redis://localhost:6379/0`

## Optional Variables

These variables have defaults but can be customized:

### Bot Configuration
```env
BOT_NAME=Reyex Support
BRAND_COLOR=5865F2
TICKET_PREFIX=ticket-
MAX_OPEN_TICKETS_PER_USER=3
```

- `BOT_NAME`: Display name for the bot
- `BRAND_COLOR`: Hex color for embeds (default: Discord blurple)
- `TICKET_PREFIX`: Prefix for ticket channel names
- `MAX_OPEN_TICKETS_PER_USER`: Maximum concurrent tickets per user

### Feature Flags
```env
ENABLE_TRANSLATION=true
ENABLE_AUTOMATION=true
ENABLE_WEB_DASHBOARD=true
```

- `ENABLE_TRANSLATION`: Enable translation features
- `ENABLE_AUTOMATION`: Enable SLA monitoring and auto-assignment
- `ENABLE_WEB_DASHBOARD`: Enable web dashboard (requires additional setup)

### Translation Configuration
```env
LIBRETRANSLATE_URL=https://libretranslate.de
LIBRETRANSLATE_API_KEY=
```

- `LIBRETRANSLATE_URL`: LibreTranslate API endpoint
- `LIBRETRANSLATE_API_KEY`: Optional API key for paid LibreTranslate instances

### Monitoring & Error Tracking
```env
SENTRY_DSN=
LOG_LEVEL=INFO
```

- `SENTRY_DSN`: Sentry DSN for error tracking and monitoring
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Web Dashboard Configuration
```env
WEB_API_HOST=0.0.0.0
WEB_API_PORT=8000
WEB_DASHBOARD_URL=http://localhost:3000
DISCORD_OAUTH_CLIENT_ID=
DISCORD_OAUTH_CLIENT_SECRET=
```

- `WEB_API_HOST`: Host for web API server
- `WEB_API_PORT`: Port for web API server
- `WEB_DASHBOARD_URL`: Public URL of web dashboard
- `DISCORD_OAUTH_CLIENT_ID`: OAuth2 client ID for dashboard authentication
- `DISCORD_OAUTH_CLIENT_SECRET`: OAuth2 client secret for dashboard authentication

### SLA Configuration (in minutes)
```env
SLA_FIRST_RESPONSE_URGENT=15
SLA_FIRST_RESPONSE_HIGH=30
SLA_FIRST_RESPONSE_MEDIUM=60
SLA_FIRST_RESPONSE_LOW=120
SLA_RESOLUTION_URGENT=240
SLA_RESOLUTION_HIGH=480
SLA_RESOLUTION_MEDIUM=1440
SLA_RESOLUTION_LOW=2880
```

- SLA target times for first response and resolution by priority level
- Values are in minutes

## Validation

The bot will validate:
- `DISCORD_TOKEN` must be present and non-empty
- `DISCORD_CLIENT_ID` must be present and non-empty
- `DATABASE_URL` must be a valid PostgreSQL connection string
- `REDIS_URL` must be a valid Redis connection string
- `LOG_LEVEL` must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `BRAND_COLOR` must be a valid hex color (0x000000 to 0xFFFFFF)

## Security Considerations

1. **Never commit `.env` file** to version control
2. **Use `.env.example`** as a template
3. **Rotate tokens regularly** for security
4. **Use strong passwords** for database
5. **Limit permissions** for database users
6. **Use environment-specific configs** for dev/staging/production

## Docker Environment

When using Docker Compose, environment variables are set in:
- `docker-compose.yml` for services
- `.env` file (not committed to git)
- Docker build arguments if needed

## bot-hosting.com Environment

When deploying to bot-hosting.com:
- Set variables in the hosting dashboard
- Do not include `.env` file in repository
- Use their database and Redis services
- Set `ENABLE_WEB_DASHBOARD=false` for bot-only deployment

## Testing Environment

For local testing, you can use:
```env
DATABASE_URL=postgresql://reyex:reyex@localhost:5432/reyex_support_test
REDIS_URL=redis://localhost:6379/1
LOG_LEVEL=DEBUG
```

## Production Environment

For production, ensure:
- Use strong, unique passwords
- Enable monitoring (Sentry)
- Set appropriate log levels (INFO or WARNING)
- Use production-grade database and Redis
- Enable all required feature flags
- Configure proper SLA targets

## Troubleshooting

### Connection Issues
- Verify database and Redis are running
- Check connection strings are correct
- Ensure ports are accessible
- Check firewall settings

### Permission Issues
- Verify bot has Discord permissions
- Check database user has required privileges
- Ensure Redis user has required access

### Feature Issues
- Check feature flags are set correctly
- Verify external services are accessible (LibreTranslate)
- Check API keys are valid if using paid services

## Environment-Specific Files

Create these files for different environments:

### `.env.local` (development)
```env
LOG_LEVEL=DEBUG
ENABLE_WEB_DASHBOARD=true
```

### `.env.production` (production)
```env
LOG_LEVEL=INFO
ENABLE_WEB_DASHBOARD=false
SENTRY_DSN=your_sentry_dsn
```

### `.env.testing` (testing)
```env
LOG_LEVEL=DEBUG
DATABASE_URL=postgresql://reyex:reyex@localhost:5432/reyex_support_test
REDIS_URL=redis://localhost:6379/1
```

## Startup Validation

The bot performs these checks on startup:
1. Required environment variables are present
2. Database connection is successful
3. Redis connection is successful (if enabled)
4. Discord token is valid
5. Configuration values are valid

If any check fails, the bot will log an error and exit with a helpful message.
