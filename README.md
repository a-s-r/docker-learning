# Docker to Cloud Run — Production Learning Project

## Overview

This repository is a hands-on learning project focused on taking a simple **Python FastAPI + MySQL application from local development to a production-style cloud deployment**.

The objective was not only to deploy an API, but to understand the engineering concepts behind a modern deployment lifecycle:

**Application → Container → Local Multi-Container Environment → CI/CD → Cloud Deployment → Managed Database → Secrets & IAM → Health Checks → Logging → Monitoring → Alerting → Distributed Tracing**

The project is intentionally simple at the application layer so that the main focus remains on **containerization, cloud architecture, deployment automation, security, reliability, and observability**.

---

# Architecture

```text
Developer
    │
    │ git push
    ▼
GitHub Repository
    │
    ▼
GitHub Actions CI/CD
    │
    ├── Build Docker image
    ├── Start test environment
    ├── Test API + database
    ├── Push versioned image
    ├── Authenticate to GCP using OIDC/WIF
    ├── Deploy Cloud Run revision
    └── Verify deployment
              │
              ▼
         Google Cloud Run
              │
              ├── FastAPI
              │
              ├── Health / Readiness
              │
              ├── Structured Logging
              │
              └── OpenTelemetry
              │
              ▼
        Google Cloud SQL
             MySQL

Observability
    ├── Cloud Logging
    ├── Cloud Monitoring
    ├── Alerting
    └── Cloud Trace
```

---

# Stage 1 — FastAPI Application

The project started with a lightweight FastAPI REST API.

Implemented endpoints include:

```text
GET    /
GET    /health
GET    /ready
GET    /employees
POST   /employees
PUT    /employees/{employee_id}
DELETE /employees/{employee_id}
```

The employee APIs provide basic CRUD operations backed by MySQL.

### Concepts practiced

* REST API design
* HTTP methods and status codes
* FastAPI routing
* Pydantic request validation
* Database connectivity
* Exception handling
* Resource cleanup
* Separation of application and infrastructure configuration

The API was deliberately kept small because the purpose of this repository is infrastructure and production engineering rather than application complexity.

---

# Stage 2 — Docker Containerization

The FastAPI application was packaged as a Docker image.

The Dockerfile covers:

* Python slim base image
* Dependency installation
* Application packaging
* Non-root application user
* Uvicorn startup
* Runtime `PORT` configuration

This provided a consistent runtime environment independent of the development machine.

### Concepts practiced

```text
Source Code
    ↓
Dockerfile
    ↓
Docker Image
    ↓
Container
```

Key learning included:

* Image vs container
* Docker build layers
* Container lifecycle
* Port mapping
* Environment variables
* `.dockerignore`
* Image tagging
* Running applications as a non-root user

---

# Stage 3 — Docker Compose

The project was expanded into a multi-container environment:

```text
Docker Compose
│
├── FastAPI Container
│
└── MySQL Container
```

The API communicates with MySQL through the Docker network using the service name rather than `localhost`.

Persistent MySQL storage is provided through a Docker volume.

Database initialization is handled using an initialization SQL script.

### Concepts practiced

* Multi-container applications
* Docker networking
* Service discovery
* Environment configuration
* Persistent volumes
* Database initialization
* Service dependencies
* Container health checks

A major practical lesson was understanding that:

```text
localhost inside a container
≠
another container
```

Containers communicate through the Docker network using service names such as `db`.

---

# Stage 4 — Health Checks and Dependency Awareness

Two different application health concepts were implemented.

### Liveness

```text
GET /health
```

Answers:

> Is the FastAPI application running?

It does not depend on the database.

### Readiness

```text
GET /ready
```

Answers:

> Is the application actually ready to serve requests?

The readiness endpoint connects to MySQL and executes:

```sql
SELECT 1
```

This helped establish an important production concept:

```text
Application running
        ≠
Application ready
```

An API process may be alive while one of its critical dependencies is unavailable.

---

# Stage 5 — CI Pipeline with GitHub Actions

A GitHub Actions workflow was introduced to automatically validate every deployment.

The CI flow includes:

```text
Push to GitHub
      ↓
Checkout source
      ↓
Build application image
      ↓
Start API + MySQL with Docker Compose
      ↓
Wait for health check
      ↓
Verify database
      ↓
Test /employees
      ↓
Build deployment image
      ↓
Push image
```

The pipeline verifies both the application and database integration rather than checking only whether the Docker image builds.

When an API test previously failed with HTTP 500, container logs and database verification were added to the workflow to improve troubleshooting.

### Concepts practiced

* Continuous Integration
* Automated builds
* Integration testing
* CI failure diagnostics
* Docker inside CI
* Reproducible deployment artifacts
* Build validation before deployment

---

# Stage 6 — Docker Registry and Image Versioning

Application images are published to Docker Hub.

Instead of relying only on:

```text
latest
```

the CI/CD pipeline generates an immutable image version based on the Git commit SHA.

Example:

```text
my-fastapi-app:37db159
```

This creates traceability between:

```text
Git Commit
    ↓
Docker Image
    ↓
Cloud Deployment
```

### Concepts practiced

* Container registries
* Image versioning
* Immutable deployment artifacts
* Git SHA tagging
* Release traceability
* Difference between `latest` and version-specific images

---

# Stage 7 — Secure GitHub-to-GCP Authentication

The CI/CD pipeline deploys to Google Cloud without storing a long-lived Google Cloud service-account JSON key.

Authentication uses:

**GitHub Actions → OIDC → Workload Identity Federation → Google Cloud Service Account**

```text
GitHub Actions
      │
      │ OIDC token
      ▼
GCP Workload Identity Federation
      │
      ▼
Deployment Service Account
      │
      ▼
Cloud Run
```

The identity provider is restricted to the intended GitHub repository.

### Concepts practiced

* IAM
* Service accounts
* OIDC
* Workload Identity Federation
* Short-lived credentials
* Least-privilege thinking
* Avoiding long-lived cloud credentials in CI/CD

This was an important security improvement compared with storing a downloadable service-account key as a GitHub secret.

---

# Stage 8 — Continuous Deployment to Cloud Run

After CI validation and image publishing, GitHub Actions automatically deploys the specific image version to Google Cloud Run.

The deployment flow is:

```text
git push
    ↓
GitHub Actions
    ↓
Tests
    ↓
Docker image
    ↓
Docker Hub
    ↓
OIDC authentication
    ↓
Cloud Run deployment
    ↓
Post-deployment verification
```

The pipeline verifies the deployed application using:

```text
/health
/ready
```

A successful pipeline therefore verifies more than image creation—it validates the deployed service.

---

# Stage 9 — Cloud Run Revisions and Rollback

Cloud Run revisions were explored by deploying application changes and switching traffic between revisions.

This helped clarify the distinction between:

```text
Docker Image
    =
Packaged application version

Cloud Run Revision
    =
Deployed application + configuration version

Traffic
    =
Which revision receives requests
```

A rollback exercise was completed by switching traffic to an earlier revision and then restoring the latest revision.

### Concepts practiced

* Deployment revisions
* Immutable releases
* Traffic management
* Rollback
* Deployment safety
* Foundation for canary/gradual deployment strategies

---

# Stage 10 — Managed MySQL with Cloud SQL

The local MySQL container was replaced in the cloud environment with Google Cloud SQL for MySQL.

Architecture:

```text
Local
FastAPI Container
      ↓
MySQL Container

Cloud
Cloud Run
      ↓
Cloud SQL
      ↓
MySQL
```

The same application supports both environments through configuration.

Locally:

```text
DB_HOST=db
```

In Cloud Run:

```text
Cloud SQL Unix Socket
```

### Concepts practiced

* Managed databases
* Environment-specific connectivity
* Cloud SQL
* Database service accounts
* Application/database separation
* Local vs cloud configuration

---

# Stage 11 — Secret Management

Database passwords are not embedded in application source code or Docker images.

Production database credentials are stored using Google Secret Manager and exposed securely to the Cloud Run service.

```text
Application
     ↓
Runtime Service Account
     ↓
Secret Manager
     ↓
Database Credential
```

### Concepts practiced

* Secret management
* Runtime secrets
* IAM-controlled access
* Avoiding credentials in Git
* Avoiding credentials inside container images
* Separation between configuration and code

---

# Stage 12 — Structured Application Logging

Application logging was changed from simple text messages to structured JSON logs.

Example:

```json
{
  "severity": "INFO",
  "event": "employees_fetched",
  "request_id": "...",
  "count": 4
}
```

Google Cloud Logging can interpret these fields as structured `jsonPayload` data.

### Concepts practiced

* Structured logging
* Log severity
* Searchable log fields
* Production troubleshooting
* Machine-readable logs
* Application events vs raw text messages

---

# Stage 13 — Correlation IDs

Each incoming request receives a unique request ID.

```text
Request
   ↓
request_id
   ↓
request_started
   ↓
business/database logs
   ↓
request_completed
```

The same ID is included in related application logs and returned through the `X-Request-ID` response header.

This makes it possible to follow one request through multiple log events.

### Concepts practiced

* Request correlation
* Troubleshooting distributed applications
* Middleware
* Request lifecycle
* Log correlation

---

# Stage 14 — Cloud Monitoring and Metrics

Google Cloud Monitoring was used to observe Cloud Run request metrics.

This introduced the distinction between logs and metrics:

```text
Logs
→ What happened?

Metrics
→ How much / how often?
```

For example, Cloud Run's request count can be grouped or filtered using HTTP response classes such as:

```text
2xx
4xx
5xx
```

This converts individual runtime events into measurable service behavior.

---

# Stage 15 — Production Alerting

A Cloud Monitoring alert policy was created for Cloud Run HTTP 5xx errors.

Conceptually:

```text
Cloud Run Request
       ↓
5xx response
       ↓
Request Count Metric
       ↓
5-minute rolling window
       ↓
5xx SUM > 0
       ↓
Alert FIRING
       ↓
Email notification
```

A controlled failure was introduced to test the policy.

The test successfully produced:

```text
FIRING
```

and after the error condition disappeared:

```text
RECOVERED
```

This validated the complete monitoring and notification path.

### Concepts practiced

* Monitoring policies
* Metric filters
* Rolling windows
* Threshold conditions
* Incident firing
* Incident recovery
* Notification channels
* Controlled production testing

---

# Stage 16 — Distributed Tracing with OpenTelemetry

The final observability stage introduced distributed tracing.

Cloud Run automatically provides request-level tracing. OpenTelemetry custom spans were then added around database operations.

The `/employees` request now provides visibility similar to:

```text
/employees
   │
   ├── db.connect
   │
   └── db.query
```

A real observed trace showed approximately:

```text
Total request     74 ms
Application span  19.087 ms
db.connect        10.205 ms
db.query           1.561 ms
```

This demonstrates why tracing provides information that logs and metrics alone cannot provide.

For example, instead of only knowing:

```text
Request was slow
```

we can investigate:

```text
Was database connection slow?

Was SQL execution slow?

Was application processing slow?

Was another downstream dependency responsible?
```

Only safe database metadata is attached to custom spans. Raw SQL statements are intentionally not stored as span attributes.

### Trace Context Propagation

Cloud Run's incoming trace context is extracted using the W3C trace context standard and attached to the OpenTelemetry context.

This allows custom application spans to participate in the same request trace:

```text
Cloud Run Request
       │
       └── FastAPI
              │
              ├── db.connect
              └── db.query
```

The Cloud Run runtime service account has permission to export custom trace data to Google Cloud Trace.

### Concepts practiced

* Distributed tracing
* Trace IDs
* Spans
* Parent/child spans
* OpenTelemetry
* Context propagation
* W3C trace context
* Cloud Trace
* Latency investigation
* Trace security considerations

---

# Observability Model Learned

The project helped establish a simple mental model for production observability:

```text
LOGS
What happened?

METRICS
How much / how often?

ALERTS
Tell us when something is wrong.

TRACES
Where was the time spent?
```

Together:

```text
             Application
                  │
        ┌─────────┼─────────┐
        │         │         │
      Logs      Metrics   Traces
        │         │         │
        └──── Monitoring ───┘
                  │
                Alerts
```

---

# Security Practices Applied

Security was treated as part of the architecture rather than a later addition.

Implemented practices include:

* Non-root Docker user
* No production passwords committed to Git
* Google Secret Manager for sensitive configuration
* Dedicated runtime service account
* Dedicated deployment service account
* IAM-based Cloud SQL access
* OIDC/Workload Identity Federation for GitHub Actions
* No long-lived GCP JSON key in CI/CD
* Repository-restricted workload identity
* Controlled Cloud Trace permissions
* Avoiding sensitive SQL/data in trace attributes

---

# Reliability Practices Applied

The project currently includes:

* Container health checks
* Application liveness endpoint
* Database-aware readiness endpoint
* CI integration tests
* Post-deployment verification
* Immutable image versions
* Cloud Run revisions
* Rollback capability
* Structured error logging
* 5xx monitoring
* Alerting and recovery notifications
* Request correlation
* Distributed tracing

---

# End-to-End Production Flow

The completed workflow currently looks like:

```text
Developer changes code
        │
        ▼
Git Push
        │
        ▼
GitHub Actions
        │
        ├── Build
        ├── Start test environment
        ├── Health check
        ├── Database verification
        └── API integration test
        │
        ▼
Versioned Docker Image
        │
        ▼
Docker Hub
        │
        ▼
OIDC / Workload Identity Federation
        │
        ▼
Cloud Run Revision
        │
        ├── Secret Manager
        ├── Runtime IAM
        └── Cloud SQL
        │
        ▼
Production API
        │
        ├── Health
        ├── Readiness
        ├── Structured Logs
        ├── Correlation IDs
        ├── Metrics
        ├── Alerts
        └── Distributed Traces
```

---

# Key Engineering Lessons

This project was useful for understanding that production engineering is not simply:

```text
Write code → deploy code
```

A more realistic lifecycle is:

```text
Design
  ↓
Build
  ↓
Package
  ↓
Test
  ↓
Version
  ↓
Secure
  ↓
Deploy
  ↓
Verify
  ↓
Observe
  ↓
Alert
  ↓
Diagnose
  ↓
Recover
```

Another important lesson is that each technology solves a different problem.

Docker provides consistent application packaging.

Docker Compose provides local multi-service orchestration.

GitHub Actions automates build, test, and deployment workflows.

Docker Hub stores versioned deployment artifacts.

OIDC and Workload Identity Federation provide secure CI/CD authentication.

Cloud Run provides managed container execution and scaling.

Cloud SQL provides managed relational database infrastructure.

Secret Manager protects sensitive runtime configuration.

Cloud Logging provides event visibility.

Cloud Monitoring provides measurable operational signals.

Alerting turns monitoring signals into actionable notifications.

Cloud Trace and OpenTelemetry show how time is spent inside requests.

---

# Current Technology Stack

```text
Application
├── Python
├── FastAPI
├── Pydantic
└── Uvicorn

Database
├── MySQL 8.4
└── Google Cloud SQL

Containers
├── Docker
└── Docker Compose

CI/CD
└── GitHub Actions

Container Registry
└── Docker Hub

Google Cloud
├── Cloud Run
├── Cloud SQL
├── Secret Manager
├── IAM
├── Workload Identity Federation
├── Cloud Logging
├── Cloud Monitoring
└── Cloud Trace

Observability
├── Structured JSON Logging
├── Correlation IDs
├── Metrics
├── Alerting
└── OpenTelemetry
```

---

# Upcoming Learning Roadmap

The next major stage is **Kubernetes**.

The goal is not simply to deploy the same application again, but to understand what Kubernetes is managing explicitly compared with the abstractions provided by Cloud Run.

Planned topics include:

```text
Docker Container
      ↓
Kubernetes Pod
      ↓
Deployment
      ↓
Replica Management
      ↓
Service
      ↓
ConfigMap / Secret
      ↓
Liveness Probe
      ↓
Readiness Probe
      ↓
Resource Requests / Limits
      ↓
Rolling Deployment
      ↓
Rollback
      ↓
Horizontal Pod Autoscaling
      ↓
Persistent / External Services
      ↓
Kubernetes Observability
```

The existing concepts provide a direct foundation:

| Current Concept             | Kubernetes Direction                 |
| --------------------------- | ------------------------------------ |
| Docker container            | Container inside Pod                 |
| Cloud Run service           | Kubernetes Deployment + Service      |
| Cloud Run revision          | Deployment / ReplicaSet revision     |
| `/health`                   | Liveness probe                       |
| `/ready`                    | Readiness probe                      |
| Environment variables       | ConfigMap / Secret                   |
| Secret Manager              | Kubernetes/cloud-integrated secrets  |
| Cloud Run autoscaling       | Horizontal Pod Autoscaler            |
| Cloud Run traffic/revisions | Rolling deployment / rollback        |
| Cloud Logging               | Cluster/workload logging             |
| Cloud Monitoring            | Kubernetes metrics/monitoring        |
| OpenTelemetry               | Distributed tracing across workloads |

Future stages can also extend into:

* Google Kubernetes Engine (GKE)
* Kubernetes networking and Ingress
* Resource management
* Autoscaling
* Rolling and canary deployment strategies
* Infrastructure as Code
* Terraform
* Kubernetes security/RBAC
* Advanced CI/CD
* Production observability
* Message-driven architecture such as Kafka
* Caching with Redis
* Resilience patterns
* Load/performance testing

These will be added incrementally rather than introducing infrastructure only for technology coverage.

---

# Project Philosophy

This repository follows a **learn by implementing and validating** approach.

Each major concept is introduced through a working implementation and then verified through an observable result—for example:

```text
Docker        → run the container
Compose       → API communicates with MySQL
CI            → automated tests pass
CD            → Cloud Run revision deployed
Cloud SQL     → production API retrieves records
Readiness     → dependency health verified
Logging       → structured events visible
Monitoring    → service metrics visible
Alerting      → controlled 5xx triggers notification
Recovery      → alert automatically resolves
Tracing       → database operations visible as spans
Rollback      → previous revision serves traffic
```

The objective is to build practical understanding of the **reason each production component exists, how the components interact, and the trade-offs involved**, rather than treating individual tools as isolated technologies.

---

## Current Status

**Completed:** FastAPI → MySQL → Docker → Docker Compose → CI/CD → Docker Registry → OIDC/WIF → Cloud Run → Cloud SQL → Secret Management → Health/Readiness → Structured Logging → Correlation IDs → Monitoring → Alerting → OpenTelemetry/Cloud Trace → Revision Rollback

**Next:** Kubernetes fundamentals and deployment of the same application using Kubernetes.

The Kubernetes stage will be documented in this repository after implementation and validation.
