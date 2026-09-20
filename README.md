# Reyex Support — Discord Ticket Bot

Support/ticket bot with button panel, private ticket channels, claim/close/transcript, and staff config.

## 1. Invite the bot
1. Go to https://discord.com/developers/applications → your app (Client ID `1550588045533773884`)
2. **Bot** → enable **Server Members Intent** + **Message Content Intent**
3. **OAuth2 → URL Generator**: scopes `bot` + `applications.commands`, permissions:
   Manage Channels, Manage Roles, View Channels, Send Messages, Embed Links,
   Attach Files, Read Message History, Mention Everyone
4. Open the generated URL and invite to your server.

## 2. Run
```bash
pip install -r requirements.txt
python bot.py
```
Token is read from `.env` (`DISCORD_TOKEN`).

## 3. Setup (in Discord)
```
/setup support_role:@Staff category:#tickets transcript_channel:#transcripts
/panel channel:#support support_role:@Staff
```
- `/panel` posts the "Create Ticket" button.
- Users click it → fill in subject/description → private channel `ticket-0001` is made.
- Inside a ticket: buttons **Claim / Transcript / Close**, plus:
  - `/claim`, `/close [reason]`, `/transcript`
  - `/add @user`, `/remove @user`

Config lives in `config.json`. Open-ticket state lives in `data.json`.
