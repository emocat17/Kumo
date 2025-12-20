# Alignment: Docker Development Environment

## 1. Project Context
- **Project**: Spider_front (Vue 3 Frontend + FastAPI Backend).
- **Goal**: Containerize the application for development using Docker Compose.
- **Constraints**: 
    - Real-time file mapping (Hot Reload).
    - Backend container name: `backend`.
    - Frontend container name: `front`.
    - Support for Python/Conda environment management within the backend.

## 2. Requirements Understanding
- User wants a "meticulous" guide and setup.
- Focus on *Development* (not Production yet).
- Persistence for Data, Logs, and Projects is required.
- Environment: 
    - Backend needs `conda` support.
    - Frontend needs `node` environment.

## 3. Architecture Decision
- **Base Images**:
    - Backend: `continuumio/miniconda3` (to support `is_conda` features).
    - Frontend: `node:20-alpine`.
- **Orchestration**: `docker-compose.yml` version 3.8.
- **Networking**: Bridge network `spider-net`.
- **Volumes**: Extensive mapping to host for DX (Developer Experience).
- **Git Strategy**: Optimized `.gitignore` to handle runtime artifacts (`logs`, `envs`, `data`) while keeping the repo clean.
- **Hot Reload**:
    - Backend: Use `uvicorn main:app --reload` (overriding default python execution).
    - Frontend: Use `npm run dev` with standard Vite HMR.

## 4. Consensus
- The detailed implementation plan is documented in `docs/docker_dev/DEVELOPMENT_GUIDE.md`.
- **Status**: Finalized.
- **Next Steps**: User to execute the creation of Docker files as per the guide.
