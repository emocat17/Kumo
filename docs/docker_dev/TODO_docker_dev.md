# TODO: Kumo Docker Environment

## 1. Immediate Actions (User)
- [ ] **Start the Environment**:
  ```bash
  docker-compose up -d --build
  ```
- [ ] **Verify Frontend**:
  - Open `http://localhost:6677`.
  - Check if the title is "Kumo" and the logo loads.
- [ ] **Verify Backend**:
  - Open `http://localhost:8000/docs`.
  - Confirm the title is "Kumo Backend".
- [ ] **Test Hot Reload**:
  - Edit `front/src/App.vue` or `backend/main.py` and observe changes without restarting containers.

## 2. Future Improvements
- [ ] **Production Setup**: Create `docker-compose.prod.yml` with Nginx and Gunicorn.
- [ ] **CI/CD**: Set up GitHub Actions for automated building and testing.
- [ ] **Database**: Consider migrating from SQLite to PostgreSQL for production concurrency.
