---
title: Docker
type: tool
tags:
  - docker
  - containers
  - devops
  - virtualization
created: 2026-04-19
updated: 2026-04-19
sources:
  - "[[Manipulating containers in Docker Client]]"
related:
  - "[[wiki/concepts/docker-container-lifecycle]]"
confidence: medium
---

# Docker

**Docker** is a platform for building, running, and managing lightweight isolated environments called **containers**. Containers package an application with its filesystem snapshot so it runs consistently across environments.

## Core Concepts

- **Image** — a read-only filesystem snapshot pulled from a registry (e.g. Docker Hub). The blueprint for a container.
- **Container** — a running instance of an image. Multiple containers can run from the same image.

## Essential Commands

### Running Containers

| Command | What it does |
|---|---|
| `docker run [image]` | Create + start a container (shorthand for `create` + `start`) |
| `docker run busybox ls` | Run a one-off command inside a container |
| `docker run busybox echo Hi` | Run a container with a custom command |
| `docker create [image]` | Create container, print its ID, do not start |
| `docker start -a [id]` | Start container; `-a` attaches stdout to terminal |
| `docker start [id]` | Start container silently, print container ID |

### Inspecting Containers

| Command | What it does |
|---|---|
| `docker ps` | List currently running containers |
| `docker ps --all` | List all containers ever created (including stopped) |
| `docker logs [id]` | Print all output a container has emitted |

### Stopping Containers

| Command | Signal | Behavior |
|---|---|---|
| `docker stop [name]` | SIGTERM | Graceful shutdown; falls back to SIGKILL after 10 s |
| `docker kill [name]` | SIGKILL | Immediate termination |

### Cleanup

| Command | What it removes |
|---|---|
| `docker system prune` | Stopped containers, build cache, dangling images, unused networks |

> [!note] Stopped containers are not deleted automatically — use `docker system prune` or `docker ps --all` to find and rerun them.

## Relationships

- relates_to: [[wiki/concepts/docker-container-lifecycle]]

## See Also

- [[wiki/concepts/docker-container-lifecycle]]
