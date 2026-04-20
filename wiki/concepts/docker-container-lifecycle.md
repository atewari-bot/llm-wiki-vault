---
title: Docker Container Lifecycle
type: concept
tags:
  - docker
  - containers
  - devops
  - lifecycle
created: 2026-04-19
updated: 2026-04-19
sources:
  - "[[Manipulating containers in Docker Client]]"
related:
  - "[[wiki/tools/docker]]"
confidence: medium
---

# Docker Container Lifecycle

A **Docker container** moves through a defined lifecycle from creation to removal. Understanding this lifecycle is key to managing containers effectively.

## Lifecycle Stages

```
Image → [docker create] → Created → [docker start] → Running → [docker stop / kill] → Stopped
```

1. **Created** — `docker create [image]` allocates the container and copies the image filesystem snapshot. The container exists but is not running. Docker prints the container ID.
2. **Running** — `docker start [id]` executes the image's default startup command. Use `-a` to attach stdout.
3. **Stopped** — The container exits (process completes, or stopped manually). It is not deleted — it persists in `docker ps --all` and can be restarted.
4. **Removed** — `docker system prune` permanently deletes stopped containers along with other unused resources.

> [!note] `docker run` is a convenience shorthand for `docker create` + `docker start` in one step.

## Stopping vs Killing

| Method | Signal | When to use |
|---|---|---|
| `docker stop` | SIGTERM → SIGKILL (after 10 s) | Graceful shutdown; lets process clean up |
| `docker kill` | SIGKILL immediately | Force-stop a hung container |

**SIGTERM** asks the process to shut itself down cleanly. **SIGKILL** terminates it unconditionally at the OS level.

## Relationships

- part_of: [[wiki/tools/docker]]

## See Also

- [[wiki/tools/docker]]
