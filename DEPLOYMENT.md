# Deployment Guide for bot-hosting.com

This guide provides step-by-step instructions for deploying the Reyex Support Bot to bot-hosting.com.

## Prerequisites

1. **GitHub Repository**
   - Ensure your code is pushed to GitHub
   - Repository should be public or accessible by bot-hosting.com
   - Current repository: https://github.com/itsraindev-source/Reyex-Support-Bot.git

2. **Discord Bot Configuration**
   - Bot token ready
   - Bot intents enabled (Server Members, Message Content)
   - Proper permissions set up

3. **Database Credentials**
   - PostgreSQL connection string
   - Redis connection string

## Step 1: Prepare Environment Variables

Create the following environment variables in bot-hosting.com:

### Required Variables
```env
DISCORD_TOKEN=your_bot_token_here
DISCORD_CLIENT_ID=1550588045533773884
DATABASE_URL=postgresql://username:password@host:port/database
REDIS_URL=redis://host:port/0
```

### Optional Variables
```env
# Bot Configuration
BOT_NAME=Reyex Support
BRAND_COLOR=5865F2
TICKET_PREFIX=ticket-
MAX_OPEN_TICKETS_PER_USER=3

# Feature Flags
ENABLE_TRANSLATION=true
ENABLE_AUTOMATION=true
ENABLE_WEB_DASHBOARD=false  # Set to false on bot-hosting.com

# Translation
LIBRETRANSLATE_URL=https://libretranslate.de
LIBRETRANSLATE_API_KEY=

# SLA Configuration
SLA_FIRST_RESPONSE_URGENT=15
SLA_FIRST_RESPONSE_HIGH=30
SLA_FIRST_RESPONSE_MEDIUM=60
SLA_FIRST_RESPONSE_LOW=120
SLA_RESOLUTION_URGENT=240
SLA_RESOLUTION_HIGH=480
SLA_RESOLUTION_MEDIUM=1440
SLA_RESOLUTION_LOW=2880

# Monitoring
LOG_LEVEL=INFO
```

## Step 2: Connect Repository to bot-hosting.com

1. Log in to bot-hosting.com
2. Navigate to your dashboard
3. Click "Add Bot" or "Connect Repository"
4. Select "GitHub" as the source
5. Authorize bot-hosting.com to access your GitHub account
6. Select the repository: `itsraindev-source/Reyex-Support-Bot`
7. Choose the branch (usually `main`)

## Step 3: Configure Deployment Settings

### Basic Configuration
- **Bot Name**: Reyex Support
- **Bot Type**: Discord Bot
- **Python Version**: 3.9+
- **Auto-Restart**: Enabled
- **Auto-Update**: Enabled (optional)

### Dependencies
The bot will automatically install dependencies from `requirements.txt`.

### Startup Command
```bash
python main.py
```

### Working Directory
```
/
```

## Step 4: Set Up Database

### PostgreSQL
1. In bot-hosting.com dashboard, navigate to Database section
2. Create a new PostgreSQL database
3. Note the connection string
4. Add to environment variables as `DATABASE_URL`

### Redis
1. In bot-hosting.com dashboard, navigate to Redis section
2. Create a new Redis instance
3. Note the connection string
4. Add to environment variables as `REDIS_URL`

## Step 5: Configure Environment Variables

In the bot-hosting.com dashboard:
1. Navigate to Environment Variables section
2. Add all required and optional variables from Step 1
3. Ensure no sensitive data is exposed
4. Save the configuration

## Step 6: Deploy the Bot

1. Click "Deploy" or "Start Bot"
2. Monitor the deployment logs
3. Wait for the bot to start successfully
4. Check that the bot appears online in Discord

## Step 7: Initial Setup in Discord

Once the bot is online:

1. **Configure the bot in your server**:
   ```
   /setup support_role:@SupportRole category:#Tickets transcript_channel:#Transcripts
   ```

2. **Post the support panel**:
   ```
   /panel #support-channel
   ```

3. **Configure staff members**:
   ```
   /staff @StaffMember billing
   ```

4. **Enable auto-assignment** (optional):
   ```
   /autoassign enable true
   /autoassign strategy least_loaded
   ```

## Step 8: Verify Deployment

Check the following:
- ✅ Bot is online in Discord
- ✅ `/panel` command works
- ✅ Tickets can be created
- ✅ Database is being populated
- ✅ Redis is connected (if enabled)
- ✅ Background tasks are running

## Troubleshooting

### Bot Won't Start
- Check deployment logs for errors
- Verify environment variables are set correctly
- Ensure database is accessible
- Check Python version compatibility

### Database Connection Issues
- Verify DATABASE_URL format
- Check database is running
- Ensure credentials are correct
- Test connection locally first

### Commands Not Working
- Ensure bot has proper permissions
- Check that intents are enabled
- Verify slash commands are synced
- Check bot log for errors

### Memory Issues
- Monitor resource usage in dashboard
- Adjust worker processes if needed
- Check for memory leaks in code
- Consider optimizing database queries

## Maintenance

### Regular Tasks
- Monitor bot logs for errors
- Check database storage usage
- Review SLA compliance reports
- Update dependencies regularly
- Backup database periodically

### Updates
1. Push new code to GitHub
2. Bot-hosting.com will auto-detect changes
3. Click "Redeploy" in dashboard
4. Monitor deployment logs

### Scaling
If needed:
- Increase database resources
- Add Redis for better caching
- Scale worker processes
- Consider load balancing

## Support

For bot-hosting.com specific issues:
- Check bot-hosting.com documentation
- Contact bot-hosting.com support
- Review their community forums

For bot-specific issues:
- Check GitHub issues
- Review bot logs
- Test locally first

## Security Best Practices

1. **Never commit secrets** to GitHub
2. **Use environment variables** for all sensitive data
3. **Rotate tokens** regularly
4. **Monitor access logs**
5. **Keep dependencies updated**
6. **Use HTTPS** for all external connections
7. **Implement rate limiting** (built-in)
8. **Validate all user inputs**

## Performance Optimization

1. **Enable Redis caching** for frequently accessed data
2. **Use database connection pooling** (configured)
3. **Monitor query performance**
4. **Optimize expensive operations**
5. **Use async operations** throughout (implemented)
6. **Implement pagination** for large datasets

## Monitoring and Alerts

Set up monitoring for:
- Bot uptime
- Database connectivity
- Redis connectivity
- Error rates
- Response times
- Resource usage

Consider using:
- bot-hosting.com built-in monitoring
- Sentry for error tracking (configure with SENTRY_DSN)
- Custom logging and alerting

## Backup Strategy

1. **Database Backups**
   - Regular automated backups
   - Point-in-time recovery
   - Off-site storage

2. **Configuration Backups**
   - Save environment variables securely
   - Document custom configurations
   - Version control for config changes

3. **Code Backups**
   - GitHub provides code history
   - Tag releases for major versions
   - Feature branches for experimental changes

## Rollback Procedure

If deployment fails:
1. Check deployment logs
2. Identify the issue
3. Fix the issue in code
4. Push fix to GitHub
5. Redeploy from dashboard
6. If needed, revert to previous commit

For critical issues:
1. Stop the bot in dashboard
2. Fix the issue locally
3. Test thoroughly
4. Redeploy when fixed

## Additional Resources

- [bot-hosting.com Documentation](https://bot-hosting.com/docs)
- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
