# Reyex Support Bot - Modern Discord Ticket System

A production-ready Discord support bot with enterprise-grade features, modern architecture, and web dashboard.

## 🚀 Features

### Core Bot Features
- **Ticket Management**: Create, claim, close, and manage support tickets
- **Multi-channel Support**: Private ticket channels with permission management
- **Priority System**: Track ticket priority (Low, Medium, High, Urgent)
- **Transcript Generation**: Automatic transcript creation on ticket close
- **User Management**: Add/remove users from tickets

### Automation Features
- **SLA Monitoring**: Track response and resolution times with breach detection
- **Auto-Assignment**: Multiple strategies (round-robin, least-loaded, specialization-based)
- **Escalation Rules**: Automatic ticket escalation based on conditions
- **Canned Responses**: Pre-written response templates for staff

### Translation Features
- **Auto-Translation**: Real-time message translation using LibreTranslate
- **Language Preferences**: Per-user language settings
- **Multi-language Support**: Support for 10+ languages

### Web Dashboard
- **Real-time Analytics**: Live ticket statistics and metrics
- **Staff Performance**: Track response times and resolution rates
- **Ticket Management**: View and manage tickets from web interface
- **SLA Reports**: Compliance monitoring and breach alerts

## 🏗️ Architecture

### Modern Technology Stack
- **Bot Framework**: discord.py 2.3+ with async/await
- **Database**: PostgreSQL 15+ with SQLAlchemy 2.0 ORM
- **Caching**: Redis 7+ for session management and caching
- **Web API**: FastAPI for REST API endpoints
- **Frontend**: Next.js 14+ with TypeScript and Tailwind CSS
- **Containerization**: Docker and Docker Compose for deployment

### Modular Structure
```
reyex-support/
├── bot/                  # Core bot functionality
│   ├── cogs/            # Discord command modules
│   ├── models/          # Database models
│   ├── services/        # Business logic
│   ├── database/        # Database setup
│   └── utils/           # Utilities
├── web/                 # Web dashboard
│   ├── api/             # FastAPI backend
│   └── frontend/       # Next.js frontend
├── docker/              # Docker configuration
└── scripts/             # Utility scripts
```

## 📋 Prerequisites

- Python 3.9+
- PostgreSQL 15+
- Redis 7+
- Docker and Docker Compose (for containerized deployment)
- Node.js 18+ (for web dashboard development)

## 🔧 Installation

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/itsraindev-source/Reyex-Support-Bot.git
cd Reyex-Support-Bot
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

4. **Run database migrations**
```bash
alembic upgrade head
```

5. **Start the bot**
```bash
python main.py
```

### Docker Deployment

1. **Build and start all services**
```bash
docker-compose up -d
```

2. **View logs**
```bash
docker-compose logs -f bot
```

3. **Stop services**
```bash
docker-compose down
```

## 🔌 Bot Setup

### Discord Application Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application or use existing one (Client ID: `1550588045533773884`)
3. Enable **Server Members Intent** and **Message Content Intent**
4. Generate bot token and add to `.env` as `DISCORD_TOKEN`
5. Create OAuth2 URL with permissions:
   - Manage Channels
   - Manage Roles
   - View Channels
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
   - Mention Everyone

### Bot Commands

- `/panel` - Post the support panel (admin only)
- `/setup` - Configure support role/category/transcripts (admin)
- `/close [reason]` - Close current ticket
- `/claim` - Claim current ticket (staff)
- `/unclaim` - Unclaim current ticket (staff)
- `/add @user` - Add user to ticket
- `/remove @user` - Remove user from ticket (staff)
- `/priority <level>` - Set ticket priority (staff)
- `/transcript` - Get ticket transcript
- `/language <code>` - Set language preference
- `/autotranslate <enabled>` - Enable/disable auto-translation
- `/translate <text> <language>` - Manual translation

## 🌐 Web Dashboard

### Access the Dashboard

1. Start the web API:
```bash
python -m web.api.main
```

2. Start the frontend (in separate terminal):
```bash
cd web/frontend
npm install
npm run dev
```

3. Open http://localhost:3000 in your browser

### Dashboard Features

- **Overview**: Real-time statistics and metrics
- **Tickets**: View and filter tickets by status/priority
- **Staff**: View staff performance and assignments
- **SLA**: Monitor compliance and breach alerts
- **Settings**: Configure bot settings and rules

## 🔧 Configuration

### Environment Variables

```env
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token
DISCORD_CLIENT_ID=your_discord_client_id
SUPPORT_ROLE_ID=support_role_id
ADMIN_ROLE_ID=admin_role_id

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/reyex_support

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

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
WEB_DASHBOARD_URL=http://localhost:3000
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

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bot --cov=web

# Run specific test file
pytest tests/test_ticket_service.py
```

## 📊 Monitoring

### Logging
- Structured logging with loguru
- Log files in `logs/` directory
- JSON logs for log aggregators
- Sentry integration for error tracking

### Performance
- Redis caching for frequently accessed data
- Database connection pooling
- Async operations throughout

## 🚀 Deployment

### bot-hosting.com

1. Push code to GitHub repository
2. Connect bot-hosting.com to your GitHub repo
3. Configure environment variables in hosting panel
4. Set up PostgreSQL and Redis instances
5. Deploy bot from dashboard

### Manual Deployment

1. Build Docker images:
```bash
docker build -t reyex-bot .
docker build -f Dockerfile.web -t reyex-web-api .
docker build -f Dockerfile.frontend -t reyex-web-frontend .
```

2. Run with Docker Compose:
```bash
docker-compose up -d
```

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with [discord.py](https://github.com/Rapptz/discord.py)
- Inspired by modern Discord bot architecture patterns
- Translation powered by [LibreTranslate](https://libretranslate.com)

## 📞 Support

For support and questions:
- Open an issue on GitHub
- Join our Discord server
- Contact support@reyex.com

---

**Generated with [Devin](https://devin.ai)**
