---
description: Test the full orchestration flow from dashboard trigger to backend execution and real-time updates.
---

# Test Orchestration Flow

This workflow guides you through testing the "Start Orchestration" feature.

1.  **Prerequisites**
    - Ensure Backend is running: `python api_server.py`
    - Ensure Frontend is running: `npm run dev`
    - Ensure Guest Mode is enabled (or you are logged in).

2.  **Trigger Orchestration**
    - Navigate to `http://localhost:3000/dashboard`.
    - Open the "Insights" panel (right side).
    - Click the **Play** icon (Start orchestration).

3.  **Verify Backend Execution**
    - Check the terminal running `api_server.py`.
    - You should see logs indicating:
        - `Starting real orchestration with characters...`
        - `Executing turn 1/X`
        - `Received action from ...`

4.  **Verify Frontend Updates**
    - **Turn Pipeline**: Should show "Turn 1 of X" and progress bar updates.
    - **Activity Stream**: Should show new events appearing in real-time:
        - "Turn 1 Begins"
        - "Character X performed Action Y"

5.  **Troubleshooting**
    - If no updates appear:
        - Check browser console for SSE errors.
        - Check backend logs for `EventBus` emission logs.
