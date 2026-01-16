# Twitch Bot Handler

Stabiler Twitch-Bot für Chat-Nachrichten und Events mit n8n-Integration.

## Features

- 🔌 Permanente IRC-Verbindung zum Twitch Chat
- 🔄 Auto-Reconnect bei Verbindungsabbrüchen
- 📨 Webhook-Integration mit n8n
- 🛡️ Rate-Limiting nach Twitch-Vorgaben
- 📊 EventSub Support für Follows, Subs, Channel Points
- 🏥 Health-Check Endpoint

## Setup

### 1. Repository klonen

```bash
git clone https://github.com/omen4impact/twitch-bot.git
cd twitch-bot
```

### 2. Virtual Environment erstellen

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Konfiguration

```bash
cp .env.example .env
nano .env  # Deine Twitch Credentials eintragen
```

### 4. Starten

```bash
cd handler
python -m main
```

## Deployment auf VPS

Siehe [VPS Setup Guide](docs/vps-setup.md) für die vollständige Anleitung.

## Architektur

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Twitch Chat   │◄───►│  Python Handler │◄───►│      n8n        │
│    (IRC)        │     │   (FastAPI)     │     │  (Workflows)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │   PostgreSQL    │
                                                └─────────────────┘
```

## Endpoints

| Endpoint | Method | Beschreibung |
|----------|--------|--------------|
| `/health` | GET | Verbindungsstatus |
| `/send` | POST | Nachricht an Chat senden |

## Lizenz

MIT
