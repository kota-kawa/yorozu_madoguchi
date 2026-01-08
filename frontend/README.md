# React frontend (よろずの窓口)

The React client consumes the Flask API (`/travel_send_message`, `/travel_submit_plan`, `/complete`) to provide the travel chat UI.

## Development

```bash
cd frontend
npm install        # already run once during scaffolding
npm run dev        # starts http://localhost:5173 with proxy to http://localhost:5000
```

## API base URL

Requests are sent to the same origin by default. When your API is on a different host, set an environment variable before building or running dev:

```bash
VITE_API_BASE_URL=http://localhost:5000
```

For production builds:

```bash
npm run build
```

The static assets will be output to `frontend/dist/`.
