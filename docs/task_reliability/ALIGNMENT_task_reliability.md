# ALIGNMENT: Task Reliability (Retry & Timeout)

## 1. Context
Current Task system (Phase 1) is functional but lacks robustness.
- **Problem**: If a network glitch occurs or a process hangs, the task fails permanently or blocks resources indefinitely.
- **Goal**: Implement "Task Reliability" features as per Roadmap Phase 2.

## 2. Requirements

### 2.1 Retry Mechanism
- **Logic**: If a task fails (non-zero exit code) or times out, automatically retry.
- **Configuration**:
  - `retry_count`: Maximum number of retries (e.g., 3).
  - `retry_delay`: Seconds to wait before retrying (e.g., 60s).
- **State**: Track `attempt` number in `TaskExecution`.

### 2.2 Timeout Mechanism
- **Logic**: If a task runs longer than `timeout` seconds, terminate it.
- **Configuration**:
  - `timeout`: Maximum execution duration in seconds (e.g., 3600s).
- **Action**: Kill subprocess, mark as "timeout".

## 3. Technical Design

### 3.1 Database (Backend)
- **Table**: `tasks`
  - `retry_count` (Integer, default=0)
  - `retry_delay` (Integer, default=60)
  - `timeout` (Integer, default=3600)
- **Table**: `task_executions`
  - `attempt` (Integer, default=1)

### 3.2 Logic (TaskManager)
- Update `run_task_execution(task_id, attempt=1)`:
  - Use `subprocess.Popen.wait(timeout=task.timeout)`.
  - Handle `TimeoutExpired`: Kill process, status="timeout".
  - Handle Failure/Timeout:
    - If `attempt <= task.retry_count`:
      - Calculate `run_date = now + retry_delay`.
      - Schedule `run_task_execution(task_id, attempt+1)` at `run_date`.

### 3.3 Frontend (Vue)
- **Tasks.vue**: Add fields to Create/Edit modal.
  - "重试次数" (Retry Count)
  - "重试间隔(秒)" (Retry Delay)
  - "超时时间(秒)" (Timeout)

## 4. API Contract
- `GET /tasks` & `POST /tasks`: Include new fields in Schema.
- `GET /executions`: Include `attempt`.

## 5. Verification
- Create a task with `command="python -c 'import time; time.sleep(10)'"`, `timeout=5`. Result: Status="timeout".
- Create a task with `command="python -c 'exit(1)'"`, `retry_count=2`. Result: 3 executions (1 initial + 2 retries).
