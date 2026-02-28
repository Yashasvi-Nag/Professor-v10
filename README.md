# 🧠 Professor v10 — Enterprise Codebase-Aware Architecture Intelligence

> A deterministic reasoning system that transforms distributed, evolving enterprise codebases into machine-reasonable architectural intelligence — acting as your **Principal Architect**.

[![CI](https://github.com/Yashasvi-Nag/Professor-v10/actions/workflows/ci.yml/badge.svg)](https://github.com/Yashasvi-Nag/Professor-v10/actions/workflows/ci.yml)

---

## Table of Contents

- [Overview](#overview)
- [The Problem](#the-problem)
- [Key Challenges](#key-challenges)
- [Desired Capability](#desired-capability)
- [System Scope (Phase 1)](#system-scope-phase-1)
- [High-Level Architecture](#high-level-architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Formal Problem Definition](#formal-problem-definition)
- [Why This Problem Is Hard](#why-this-problem-is-hard)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

In a large enterprise workspace spanning **multiple repositories**, **languages**, and **platforms** — understanding the full impact of a single feature change is extraordinarily difficult.

Professor v10 aims to solve this by building a system that can:

1. Accept high-level feature ideas from non-technical stakeholders.
2. Identify missing details and refine the PRD through structured clarification.
3. Understand the **entire** codebase across languages and services.
4. Produce a **validated, evidence-backed** architectural solution document.
5. Ensure no contract, service, or dependency is overlooked.

### Target Workspace Profile

| Layer | Technology |
|---|---|
| Backend | Java (Spring Boot microservices) |
| Mobile | Flutter (Dart) |
| Admin UI | Angular (TypeScript) |
| Messaging | Kafka |
| Caching | Redis / Aerospike |
| Inter-service | Feign clients, shared DTO libraries |

---

## The Problem

When a Project Manager proposes _"We want to add X feature"_, the organization must manually determine:

- What **services** are affected?
- What **APIs** change?
- What **DTOs** must evolve?
- What **downstream services** break?
- What **cache keys** become invalid?
- What **frontend models** must be updated?
- What **rollout strategy** is needed?
- What **risks** exist?

Today this process is **manual**, **time-consuming**, **knowledge-dependent**, **error-prone**, and relies on **senior engineers' tribal memory**.

---

## Key Challenges

### 1. Multi-Repository Cognitive Fragmentation

Services, shared libraries, Feign clients, Kafka topics, caching layers, Flutter models, and Angular contracts are physically separated, independently versioned, and weakly coupled but logically interdependent. There is **no single place** where all service relationships are visible or impact propagation is calculable.

### 2. Hidden Architectural Coupling

Large systems accumulate implicit dependencies, historical design decisions, workarounds, and feature-flag-driven behavior — rarely documented formally. This creates **knowledge concentration risk**.

### 3. PRD Ambiguity

Stakeholders provide business intent but not technical constraints, backward compatibility requirements, cache impact considerations, cross-platform implications, or multi-country rollout constraints. Without structured clarification, scope creeps and contracts break unexpectedly.

### 4. Change Impact Uncertainty

Even a small change (e.g., _"add `estimatedSavings` to feed"_) triggers a cascade of questions:

- Is the feed response cached?
- Is coupon-engine providing this field?
- Is the frontend already expecting it?
- Does the admin UI use the same DTO?
- Does the database schema need updating?
- Does any consumer assume response immutability?

There is **no automated impact propagation model** today.

### 5. Hallucination & Trust Risk

Naive AI application invents APIs, suggests non-existent services, misses critical dependencies, and ignores caching layers. Enterprise usage demands **deterministic, evidence-backed reasoning** over actual code.

### 6. Cross-Language Semantic Alignment

Java, Dart, and TypeScript each have different structures, patterns, and dependency models — yet features span all of them. There is no shared machine-readable representation of controllers, models, service boundaries, or communication contracts.

### 7. Lack of Formalized Architecture Graph

No structured graph exists mapping:

```
Service → Service
Service → API
API → DTO
DTO → Frontend Model
Service → Cache
Service → Database
```

Without this, change analysis cannot be automated and architectural drift cannot be detected.

### 8. Organizational Knowledge Risk

- Architectural knowledge resides in **individuals** — if they leave, system understanding degrades.
- Solution documents are manually written, vary in quality, and are rarely validated against code.
- Manual architecture reasoning **does not scale** as codebases, teams, and regions grow.

---

## Desired Capability

```
Feature Idea (natural language)
        │
        ▼
┌─────────────────────────┐
│   PRD Clarification      │  ← Identifies missing details
│   & Refinement           │    through structured questions
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Codebase Intelligence  │  ← Parses multi-repo, multi-lang
│   & Dependency Graph     │    source into architecture graph
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Impact Analysis        │  ← Maps feature intent to affected
│   & Change Propagation   │    services, APIs, DTOs, caches
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Validated Architecture │  ← Evidence-backed, no hallucination
│   Change Document        │    no omitted dependencies
└─────────────────────────┘
```

---

## System Scope (Phase 1)

| In Scope | Out of Scope |
|---|---|
| Static source code analysis | Runtime telemetry |
| Multi-repo, multi-language parsing | Log analysis |
| Architecture graph construction | Kubernetes topology |
| PRD clarification & refinement | Performance signals |
| Impact propagation modeling | |
| Validated solution documentation | |

> Even within this limited scope, the core difficulty remains: **extract reliable architectural intelligence from static multi-repo source code.**

---

## Formal Problem Definition

```
Given:
  - A large multi-language, multi-service enterprise codebase
  - Unstructured feature proposals from non-technical stakeholders
  - Distributed architectural knowledge

Build:
  A deterministic reasoning system that can:
  - Clarify requirements
  - Map feature intent to code components
  - Identify all impacted artifacts
  - Produce validated architectural change documentation

Without:
  - Hallucination
  - Omitted dependencies
  - Contract drift
  - Architectural blind spots
```

---

## Why This Problem Is Hard

Professor v10 unifies disciplines that most tools only solve in isolation:

| Discipline | Role in System |
|---|---|
| **Program Analysis** | Parse and understand code across languages |
| **Knowledge Graphs** | Model service/contract/dependency relationships |
| **Natural Language Understanding** | Interpret ambiguous feature requests |
| **Change Impact Modeling** | Propagate change effects across the graph |
| **Software Architecture Governance** | Enforce consistency and completeness |
| **Human-in-the-Loop Refinement** | Clarify requirements iteratively |

---

## The Meta-Problem

> Turn a distributed, evolving codebase into a **continuously updated architectural knowledge system** that supports **deterministic reasoning**.

This requires solving six sub-problems:

1. **Representation** — How to model the codebase as a graph.
2. **Retrieval** — How to surface relevant code for a given feature.
3. **Dependency Modeling** — How to map implicit and explicit coupling.
4. **PRD Formalization** — How to turn vague ideas into structured specs.
5. **Change Propagation** — How to trace impact across services and languages.
6. **Trust Validation** — How to guarantee outputs are evidence-backed.

---

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        Professor v10                           │
│                                                                │
│  ┌──────────────┐    ┌───────────────┐    ┌────────────────┐  │
│  │  Multi-Repo  │    │  Architecture │    │  PRD           │  │
│  │  Code        │───▶│  Graph        │◀───│  Clarification │  │
│  │  Parsers     │    │  (Central     │    │  Engine        │  │
│  │  Java/Dart/  │    │   Data Store) │    │                │  │
│  │  TypeScript  │    └───────┬───────┘    └────────────────┘  │
│  └──────────────┘            │                                │
│                              ▼                                │
│                    ┌─────────────────┐                        │
│                    │  Impact         │                        │
│                    │  Analysis &     │                        │
│                    │  Propagation    │                        │
│                    └────────┬────────┘                        │
│                             │                                 │
│                             ▼                                 │
│                    ┌─────────────────┐                        │
│                    │  Validated      │                        │
│                    │  Architecture   │                        │
│                    │  Document       │                        │
│                    └─────────────────┘                        │
└────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Location | Description |
|---|---|---|
| **Code Parsers** | `src/parsers/` | Language-specific AST parsers for Java, Dart, TypeScript |
| **Architecture Graph** | `src/graph/` | Central graph data model, builder, store, and query engine |
| **Impact Analysis** | `src/analysis/` | Change impact propagation and contract checking |
| **PRD Clarifier** | `src/prd/` | Structured requirement clarification engine |
| **Document Generator** | `src/output/` | Validated architectural change document generation |
| **Validators** | `src/validators/` | Evidence-backed reasoning and confidence scoring |

---

## Project Structure

```
Professor-v10/
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── .gitignore
├── pyproject.toml
├── Makefile
├── docs/
│   ├── design/
│   │   ├── 00-system-overview.md
│   │   ├── 01-code-graph-extraction.md
│   │   ├── 02-cross-language-schema-alignment.md
│   │   ├── 03-dependency-modeling.md
│   │   ├── 04-prd-clarification-engine.md
│   │   ├── 05-change-impact-propagation.md
│   │   └── 06-trust-validation.md
│   └── adr/
│       ├── 001-python-as-orchestration-language.md
│       ├── 002-graph-first-architecture.md
│       ├── 003-static-analysis-only-phase1.md
│       ├── 004-multi-parser-strategy.md
│       └── 005-evidence-backed-reasoning.md
├── src/
│   ├── config/
│   ├── parsers/
│   ├── graph/
│   ├── analysis/
│   ├── prd/
│   ├── output/
│   └── validators/
├── tests/
│   ├── test_parsers/
│   ├── test_graph/
│   ├── test_analysis/
│   └── test_prd/
└── examples/
    ├── sample_feature_request.md
    ├── sample_impact_report.md
    └── sample_repo_config.yaml
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

```bash
# Clone the repository
git clone https://github.com/Yashasvi-Nag/Professor-v10.git
cd Professor-v10

# Create virtual environment and install dependencies
make setup

# Verify installation
make test
```

### Development Setup

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run linter
make lint

# Run tests
make test

# Run formatter
make format
```

### Running the System

```bash
# Coming in Phase 1 implementation
# make run --config examples/sample_repo_config.yaml
```

---
## Formal Problem Definition

```
Given:
  - A large multi-language, multi-service enterprise codebase
  - Unstructured feature proposals from non-technical stakeholders
  - Distributed architectural knowledge

Build:
  A deterministic reasoning system that can:
  - Clarify requirements
  - Map feature intent to code components
  - Identify all impacted artifacts
  - Produce validated architectural change documentation

Without:
  - Hallucination
  - Omitted dependencies
  - Contract drift
  - Architectural blind spots
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
