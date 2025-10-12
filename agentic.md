# Agentic Feature Implementation Plan

This document outlines where and how to implement the "Multi-Agent Interview Assistant" feature within the existing `context-relay` project structure.

## High-Level Conclusion

The project is well-structured with a Python backend and a React frontend. The implementation should be divided accordingly:

1.  **Backend Logic (`/fast`):** The core agentic workflow (analysis, question generation, and the relay mechanism) will be implemented here.
2.  **Frontend UI & Visualization (`/next/app-frontend`):** The user interface for uploading documents and visualizing the agentic flow will be implemented here. The existing frontend components suggest this was the intended purpose.

---

## 1. Backend Implementation (`/fast`)

The Python/FastAPI application in the `/fast` directory is the ideal place for the core logic.

### Why here?

-   It's a server-side environment, suitable for processing file uploads and orchestrating calls to external services (like LLMs for analysis and question generation).
-   The existing structure with `services`, `api`, and `models` is designed to handle this kind of business logic.
-   The presence of `events.py` and SSE-related test features (`sse_events.feature`) indicates a real-time communication channel is already in place, which is perfect for pushing live updates to the frontend as the "context packet" evolves.

### Implementation Steps:

1.  **Create a New API Endpoint:** In `fast/app/api/endpoints/`, add a new endpoint (e.g., `interviews.py`) to handle the file upload of a resume or company profile.
2.  **Implement Agent A (Analysis):** Create a new service in `fast/app/services/` that takes the uploaded document's text, sends it to an LLM for analysis (to extract strengths, weaknesses, themes), and structures the output.
3.  **Implement Agent B (Question Generation):** Create another service that takes the structured analysis from Agent A as its input. This service will then call an LLM to generate relevant interview or investment questions.
4.  **Orchestrate the Relay:** The new endpoint will orchestrate the flow:
    -   Receive the file.
    -   Call the Agent A service.
    -   Push an "analysis complete" event via the existing SSE service.
    -   Pass the analysis context to the Agent B service.
    -   Push a "questions generated" event with the final output.

## 2. Frontend Implementation (`/next/app-frontend`)

The React/Vite application in `/next/app-frontend` will handle the user experience and visualization.

### Why here?

-   This is the user-facing part of the application.
-   The existing component names are a perfect match for the feature's requirements:
    -   `InterviewRelayFlow.tsx`: The ideal container for the entire visualization.
    -   `AgentNode.tsx`: Can be used to visually represent "Agent A" and "Agent B".
    -   `AnimatedEdge.tsx`: Can be used to draw the connection and animate the flow of the context packet between the agents.

### Implementation Steps:

1.  **Build the UI:** In the `InterviewRelayFlow.tsx` component, add a file upload element for the user to submit a resume/profile.
2.  **API Integration:** On file upload, make a `POST` request to the new backend endpoint created in the `/fast` application.
3.  **Real-time Event Handling:** Implement a client-side listener for the Server-Sent Events (SSE) stream from the backend.
4.  **Live Visualization:** As events are received from the backend:
    -   Render the "Agent A" node as "Analyzing...".
    -   When the analysis is complete, update the UI to show the key themes.
    -   Animate the context moving from Agent A to Agent B using `AnimatedEdge.tsx`.
    -   Render the "Agent B" node as "Generating Questions...".
    -   When the final questions are received, display them clearly to the user.

This approach leverages the existing architecture effectively, separating the core logic from the presentation and creating a dynamic, real-time user experience as envisioned in the concept.
