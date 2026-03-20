# GanttBuddy Frontend

React + TypeScript + Vite frontend for the parallel GanttBuddy migration.

## Development

1. Start `ganttbuddy-api` on `http://127.0.0.1:8000`
2. From this folder run:

```powershell
npm install
npm run dev
```

By default the frontend uses the Vite proxy at `/api-proxy`, which forwards requests to the local backend and avoids browser CORS issues during development.

## Current MVP Scope

- Login against `/auth/login` and `/auth/me`
- Project list and create/open flow
- Snapshot-backed plan workspace using `/projects/{project_id}/snapshot`
- Manual save through `/projects/import`
- Task execution actions through `/tasks/*`
- Analytics dashboard and inching views through `/projects/{project_id}/analytics/*`

## Notes

- Planning persistence intentionally uses whole-project snapshot import/export for the first React cut.
- Streamlit can continue running in parallel while this app is developed and validated.
