# E-commerce Real-time Marketing System - Project Instructions

## Project Context
A dual-track real-time decision system for e-commerce marketing.
- **Fast Track (Java/Spring Boot):** Kafka Consumer -> Window Aggregation -> Redis -> High-Value Signal Production.
- **Slow Track (Python/LangGraph):** High-Value Signal -> Agent -> RAG/LLM -> Marketing Action.
- **Infrastructure:** Kafka (KRaft), Redis, MySQL 8.0, ChromaDB (Dockerized).

---

## MANDATORY: Agent Workflow

Every new agent session MUST follow this workflow:

### Step 1: Initialize & Verify Infrastructure
1. **Check Environment Variables**: Ensure `.env` exists (copy from `.env.example` if needed).
2. **Check Docker Containers**: 
   - Command: `docker-compose ps`
   - If services are down: `docker-compose up -d`
   - **WAIT**: Ensure MySQL/Kafka ports are actually accepting connections before running code.
3. **Context Switching (CRITICAL)**: 
   - **Java Tasks**: ALWAYS verify you are in `./backend-java` before running `mvn`.
   - **Python Tasks**: ALWAYS verify you are in `./agent-python` before running `pip/python`.
   - *Rule*: Before running any command, check your current directory with `pwd`.

### Step 2: Select Next Task
Read `task.json` and select ONE task to work on.
Selection criteria (in order of priority):
1. Choose a task where `passes: false`.
2. Consider dependencies (Infrastructure -> Java Ingestion -> Python Agent).
3. Pick the highest-priority incomplete task.

### Step 3: Implement the Task
1. Read the task description carefully.
2. Implement functionality following the **Coding Conventions** below.
3. **Mock External Services**: When writing *Unit Tests*, NEVER connect to real Kafka, Redis, or LLM APIs. Use Mockito (Java) or unittest.mock (Python).

### Step 4: Test Thoroughly (MANDATORY)
Since this is a backend system, **NO BROWSER TESTING** is required.
You must verify functionality using **Unit Tests** and **Integration Checks**.

**Testing Requirements:**
- **Java Code**:
  - Must pass: `mvn test`
  - Use `Mockito` for unit tests. Use `@EmbeddedKafka` only for specific integration tests.
- **Python Code**:
  - Must pass: `pytest`
  - Use `unittest.mock` to mock LLM responses and Database calls.
- **Infrastructure/Integration**:
  - Check container logs: `docker logs [container_name]`
  - Use `curl` or scripts to test REST/Kafka endpoints.

**Validation Checklist:**
- [ ] Code compiles/interprets without errors.
- [ ] Unit tests pass (Green).
- [ ] No "Connection Refused" errors in logs.
- [ ] Logic fulfills the `task.json` requirements.

### Step 5: Update Progress
Write your work to `progress.txt`:

```text
## [Date] - Task: [task description]

### What was done:
- [specific classes/files created or modified]

### Testing:
- [Command used, e.g., mvn test]
- [Result, e.g., All 5 tests passed]

### Notes:
- [Any config changes or environment variables added]
```

### Step 6: Commit Changes
**IMPORTANT**: All changes (Code + `task.json` + `progress.txt`) must be in the **SAME** commit.

1. Update `task.json`: change `passes: false` to `true`.
2. Update `progress.txt`.
3. Commit:
   ```bash
   git add .
   git commit -m "[Task ID] [Description] - completed"
   ```

---

## ⚠️ Blocking Issues (阻塞处理)
If a task cannot be completed (e.g., missing API keys, strange Docker errors), you must STOP and report.

**DO NOT:**
- ❌ Fake the test results.
- ❌ Mark `passes: true` if tests failed.
- ❌ Submit broken code.

**DO:**
- ✅ Write the issue in `progress.txt`.
- ✅ Output a structured "BLOCKING ISSUE" message (see below).
- ✅ Stop and wait for human intervention.

**Blocking Report Format:**
```text
🚫 TASK BLOCKED - HUMAN INTERVENTION REQUIRED

**Current Task**: [Task Name]

**Completed Work**:
- [What is done so far]

**Blocking Reason**:
- [Specific error or missing config]

**Required Actions**:
1. [Step 1 user needs to do, e.g., Add OPENAI_API_KEY to agent-python/.env]
2. [Step 2...]

**To Continue**:
- Run [Command] after fixing.
```

---

## Project Structure & Commands

### 📂 Root Directory
Contains orchestration and docs.
- `docker-compose up -d`: Start Infra.
- `docker-compose down`: Stop Infra.

### ☕ Java Backend (`./backend-java`)
Stack: Java 21, Spring Boot 3.2, Maven, Lombok.
**Commands (Run inside `backend-java/`):**
- `mvn clean install -DskipTests`: Build project.
- `mvn test`: Run unit tests (**Primary Verification Method**).
- `mvn spring-boot:run`: Run the app locally.

### 🐍 Python Agent (`./agent-python`)
Stack: Python 3.10+, LangChain, LangGraph, Pydantic.
**Commands (Run inside `agent-python/`):**
- `pip install -r requirements.txt`: Install deps.
- `pytest`: Run tests (**Primary Verification Method**).
- `python src/main.py`: Run the agent manually.

###  **🐳 Infrastructure (Configuration & Data)**
- **Docker Configuration**: Located in the root directory as `docker-compose.yml`.
- **MySQL Initialization Script**: `Config/infrastructure/mysql/init/01_schema.sql`.
- **Data Persistence Directory**: `Config/data/` (Contains binary data for MySQL, Redis, Kafka, and Chroma).
  - **Note**: These are directories automatically mounted by Docker; manual modification or deletion of files within them is **strictly prohibited**.

---

## Coding Conventions

### Java
- **Style**: Standard Spring Boot architecture (Controller -> Service -> Repository).
- **Lombok**: Use `@Data`, `@Slf4j`, `@RequiredArgsConstructor`.
- **Testing**: **Prioritize Mockito**. Only use Integration Tests for Kafka/DB layers.
- **Logs**: Structured logging (`log.info`).

### Python
- **Style**: Type hinting is **MANDATORY** (`def process(data: dict) -> bool:`).
- **Environment**: Load keys from `.env` using `python-dotenv`.
- **Testing**: Use `pytest` fixtures and mocks. Do not call real LLMs in tests.

### General
- **No Hardcoding**: Never put passwords or API keys in code. Use Environment Variables.
- **No GUI**: Do not write any HTML/CSS/React code.

## Key Rules

1. **One Task Per Session**: Focus on completing exactly ONE task from `task.json`.
2. **Context Awareness**: ALWAYS check your directory (`pwd`) before running build commands to avoid mixing Java/Python contexts.
3. **No Browser Tests**: This is a backend project. Do not use Playwright or Puppeteer. Use `mvn test` and `pytest`.
4. **Mock First**: Avoid calling real external APIs in unit tests.
5. **Atomic Commits**: Code, `task.json`, and `progress.txt` MUST be committed together.
6. **Immutable Task List**: Never remove tasks from `task.json`. Only change `passes: false` to `true`.
7. **Stop If Blocked**: If you encounter an issue requiring human input (e.g., API keys), stop immediately and report.
