# Deployment Guide

This guide covers deploying the Reyex Support Bot to various platforms, with specific instructions for bot-hosting.com.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [bot-hosting.com Deployment](#bot-hostingcom-deployment)
- [Docker Deployment](#docker-deployment)
- [Manual Deployment](#manual-deployment)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before deploying, ensure you have:

- A Discord bot token and application set up
- A GitHub repository with your code
- PostgreSQL database access (or use hosting provider's database)
- Redis instance (or use hosting provider's Redis)
- Environment variables configured

## Environment Setup

### Required Environment Variables

```env
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token
DISCORD_CLIENT_ID=your_discord_client_id
SUPPORT_ROLE_ID=support_role_id
ADMIN_ROLE_ID=admin_role_id

# Database Configuration
DATABASE_URL=postgresql://user:password@host:port/database

# Redis Configuration
REDIS_URL=redis://host:port/db

# Bot Configuration
BOT_NAME=Reyex Support
BRAND_COLOR=5865F2
TICKET_PREFIX=ticket-
MAX_OPEN_TICKETS_PER_USER=3

# Feature Flags
ENABLE_TRANSLATION=true
ENABLE_AUTOMATION=true
ENABLE_WEB_DASHBOARD=true

# Translation Configuration
LIBRETRANSLATE_URL=https://libretranslate.de
LIBRETRANSLATE_API_KEY=  # Optional

# Monitoring
SENTRY_DSN=  # Optional for error tracking
LOG_LEVEL=INFO

# Web Dashboard
WEB_API_HOST=0.0.0.0
WEB_API_PORT=8000
WEB_DASHBOARD_URL=https://your-dashboard-url.com
DISCORD_OAUTH_CLIENT_ID=  # For web dashboard auth
DISCORD_OAUTH_CLIENT_SECRET=  # For web dashboard auth

# SLA Configuration (in minutes)
SLA_FIRST_RESPONSE_URGENT=15
SLA_FIRST_RESPONSE_HIGH=30
SLA_FIRST_RESPONSE_MEDIUM=60
SLA_FIRST_RESPONSE_LOW=120
SLA_RESOLUTION_URGENT=240
SLA_RESOLUTION_HIGH=480
SLA_RESOLUTION_MEDIUM=1440
SLA_RESOLUTION_LOW=2880
```

## bot-hosting.com Deployment

### Step 1: Prepare Your Repository

1. Ensure your code is pushed to GitHub
2. Verify your repository has the necessary files:
   - `requirements.txt` (Python dependencies)
   - `.env.example` (Environment template)
   - `main.py` or entry point file
   - No `.env` file (committed secrets are security risk)

### Step 2: Create Account on bot-hosting.com

1. Go to [bot-hosting.net](https://bot-hosting.net)
2. Sign up/login with Discord
3. Earn coins using the free coin generator (10 coins/day, up to 100/day)

### Step 3: Create Server

1. Click "Create Server" in the navbar
2. Enter server details:
   - **Name**: Reyex Support Bot
   - **Language**: Python
3. Select a plan based on your needs
4. Choose billing cycle (weekly recommended)

### Step 4: Configure Server

#### Basic Settings
- **Entry File**: `main.py` (or your entry point)
- **Working Directory**: `/` (root of project)

#### Environment Variables
Add all required environment variables from the Environment Setup section:
- `DISCORD_TOKEN`: Your Discord bot token
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- Other required variables

#### Database Setup
1. Go to the "Databases" tab
2. Create a PostgreSQL database
3. Create a Redis instance
4. Copy the connection strings to your environment variables

#### File Upload
1. Go to the "Files" tab
2. Upload your project files (excluding `.env`, `__pycache__`, etc.)
3. Or use GitHub integration:
   - Go to "Settings" → "Git Integration"
   - Connect your GitHub repository
   - Enable auto-deploy on push

### Step 5: Start the Server

1. Click "Start" in the server control panel
2. Monitor the console output for startup messages
3. Check that the bot connects to Discord successfully

### Step 6: Verify Deployment

1. Check that your bot appears online in Discord
2. Test basic commands like `/panel` or `/stats`
3. Verify database connections are working
4. Check logs for any errors

## Docker Deployment

### Prerequisites

- Docker installed on your server
- Docker Compose installed
- PostgreSQL and Redis instances (or use Docker services)

### Deployment Steps

1. **Clone your repository** on the server:
```bash
git clone https://github.com/your-username/Reyex-Support-Bot.git
cd Reyex-Support-Bot
```

2. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Build and start services**:
```bash
docker-compose up -d
```

4. **Run database migrations**:
```bash
docker-compose exec bot alembic upgrade head
```

5. **Check logs**:
```bash
docker-compose logs -f bot
```

### Production Docker Compose

For production, modify `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  bot:
    build: .
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

## Manual Deployment

### System Requirements

- Python 3.9+
- PostgreSQL 15+
- Redis 7+
- Systemd (for service management)

### Deployment Steps

1. **Install system dependencies**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip postgresql redis-server nginx

# CentOS/RHEL
sudo yum install python3 python3-pip postgresql-server redis nginx
```

2. **Create user and directory**:
```bash
sudo useradd -m -s /bin/bash reyex
sudo su - reyex
cd ~
git clone https://github.com/your-username/Reyex-Support-Bot.git
cd Reyex-Support-Bot
```

3. **Install Python dependencies**:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. **Configure environment**:
```bash
cp .env.example .env
nano .env  # Add your configuration
```

5. **Run database migrations**:
```bash
alembic upgrade head
```

6. **Create systemd service**:
```bash
sudo nano /etc/systemd/system/reyex-bot.service
```

Add the following:
```ini
[Unit]
Description=Reyex Support Bot
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=reyex
WorkingDirectory=/home/reyex/Reyex-Support-Bot
Environment="PATH=/home/reyex/Reyex-Support-Bot/venv/bin"
ExecStart=/home/reyex/Reyex-Support-Bot/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

7. **Enable and start service**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable reyex-bot
sudo systemctl start reyex-bot
sudo systemctl status reyex-bot
```

## Web Dashboard Deployment

### Option A: Host Separately (Recommended)

**Frontend (Vercel/Netlify):**
1. Build the Next.js frontend:
```bash
cd web/frontend
npm install
npm run build
```

2. Deploy to Vercel:
```bash
npm install -g vercel
vercel
```

**Backend (Railway/Render):**
1. Deploy the FastAPI backend with your PostgreSQL and Redis

### Option B: All-in-One Docker

The `docker-compose.yml` includes both bot and web dashboard services. Simply run:
```bash
docker-compose up -d
```

### Option C: Include in bot-hosting.com

Note: bot-hosting.com may not support web applications. Check their documentation for web app hosting capabilities.

## Troubleshooting

### Common Issues

#### Bot Won't Start
- Check environment variables are set correctly
- Verify Discord token is valid
- Check database connection string
- Review logs for specific error messages

#### Database Connection Errors
- Verify PostgreSQL is running
- Check connection string format
- Ensure database exists
- Verify user permissions

#### Redis Connection Errors
- Verify Redis is running
- Check Redis connection string
- Test Redis connectivity: `redis-cli ping`

#### Permissions Errors
- Verify bot has required Discord permissions
- Check support role ID is correct
- Ensure bot has "Manage Channels" permission

#### Web Dashboard Not Loading
- Check API server is running
- Verify CORS configuration
- Check frontend environment variables
- Test API endpoints directly

### Debug Mode

Enable debug logging by setting:
```env
LOG_LEVEL=DEBUG
```

### Health Checks

Test bot health:
```bash
curl http://localhost:8000/health
```

Test database connection:
```bash
docker-compose exec bot python -c "from bot.database.connection import init_db; import asyncio; asyncio.run(init_db())"
```

## Monitoring

### Logs

- **Application logs**: `logs/reyex_YYYY-MM-DD.log`
- **Error logs**: `logs/errors_YYYY-MM-DD.log`
- **Structured logs**: `logs/structured_YYYY-MM-DD.json`

### Metrics

Use the built-in stats command:
```
/stats
```

Or access the web dashboard for detailed analytics.

### Error Tracking

If configured, Sentry will automatically capture and report errors.

## Scaling

### Horizontal Scaling

For high-volume deployments:
1. Use a load balancer (nginx, HAProxy)
2. Run multiple bot instances
3. Use Redis for shared state
4. Use PostgreSQL for shared data

### Database Optimization

- Increase connection pool size
- Enable connection pooling
- Use read replicas for read-heavy operations
- Implement database indexing

## Security

### Best Practices

1. **Never commit secrets** to version control
2. **Use environment variables** for all sensitive data
3. **Rotate API keys** regularly
4. **Use HTTPS** for all web connections
5. **Implement rate limiting** for API endpoints
6. **Keep dependencies updated**

### Bot Security

- Limit bot permissions to minimum required
- Use role-based access control
- Implement proper input validation
- Sanitize user inputs
- Rate limit API calls

## Backup Strategy

### Database Backups

```bash
# Manual backup
pg_dump reyex_support > backup_$(date +%Y%m%d).sql

# Automated backup (cron)
0 2 * * * pg_dump reyex_support > /backups/daily_$(date +\%Y\%m\%d).sql
```

### Redis Backups

```bash
# Manual backup
redis-cli BGSAVE

# Automated backup
0 3 * * * redis-cli BGSAVE
```

## Updates and Maintenance

### Updating the Bot

1. Pull latest changes from Git
2. Update dependencies: `pip install -r requirements.txt --upgrade`
3. Run migrations: `alembic upgrade head`
4. Restart the service

### Scheduled Maintenance

- Weekly dependency updates
- Monthly database maintenance
- Quarterly log cleanup
- Annual security audit

## Support

For deployment issues:
- Check the [GitHub Issues](https://github.com/itsraindev-source/Reyex-Support-Bot/issues)
- Review the [Troubleshooting section](#troubleshooting)
- Contact support if issues persist

---

**Generated with [Devin](https://devin.ai)**
