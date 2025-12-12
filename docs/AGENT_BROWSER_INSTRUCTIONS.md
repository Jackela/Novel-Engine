# Agent Browser Validation Instructions

**Role:** QA / User Simulator
**Target:** Novel-Engine Dashboard (http://localhost:3000)

## Prerequisites
1.  **Backend**: Ensure `python api_server.py` is running (Port 8000).
2.  **Frontend**: Ensure `npm run dev` is running (Port 3000).

## Mission
Perform a "Smoke Test" of the Guest Mode and Orchestration flow.

## Steps
1.  **Launch Browser**: Open `http://localhost:3000`.
2.  **Verify Guest Mode**:
    *   Look for a "Demo Mode" chip/badge in the top navigation bar.
    *   *Success Criteria*: The chip is visible.
3.  **Start Orchestration**:
    *   Locate the main action button (e.g., "Start Simulation", "Begin Story", or "Orchestrate").
    *   Click it.
4.  **Observe Real-Time Updates**:
    *   Wait for 10-20 seconds.
    *   Observe the "Narrative Log" or "Story Feed" for new text appearing.
    *   *Success Criteria*: Text updates dynamically without page reload (SSE validation).
5.  **Capture Evidence**:
    *   Take a screenshot of the generated story.
