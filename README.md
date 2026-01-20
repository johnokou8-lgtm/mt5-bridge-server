# MT5 Bridge Server

This server connects MT5 Expert Advisors to mobile apps.

## Endpoints

- `GET /` - Health check
- `POST /api/mt5/update` - MT5 EA sends data
- `GET /api/mt5/status` - Mobile app fetches data
- `POST /api/mt5/command` - Mobile app sends commands
- `GET /api/mt5/commands` - EA polls for commands
