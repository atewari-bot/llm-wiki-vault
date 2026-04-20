---
title: "Docker Exec and Interactive Access"
type: concept
tags: [docker, containers, devops, shell, exec]
created: 2026-04-19
updated: 2026-04-19
sources: ["[[raw/notes/docker/Manipulating containers in Docker Client]]"]
related: ["[[wiki/tools/docker]]", "[[wiki/concepts/docker-container-lifecycle]]"]
confidence: medium
---

# Docker Exec and Interactive Access

**`docker exec`** runs a command inside an already-running container. **`docker run`** creates and starts a new container. The two are often confused when used with interactive flags.

## exec vs run — Interactive Mode

| Command | Container state | What happens |
|---|---|---|
| `docker exec -it [id] sh` | Must already be running | Opens a shell in the existing container |
| `docker run -it busybox sh` | Does not exist yet | Creates + starts a new container, opens shell immediately |

Use `exec` when you need to inspect or debug a container that is already running (e.g. a long-lived service). Use `run -it` when you want to explore an image interactively from scratch.

## The -i and -t Flags

- **`-i` (interactive)** — keeps STDIN open, allowing you to type commands
- **`-t` (tty)** — allocates a pseudo-terminal, giving readline editing and formatted output
- **`-it`** — shorthand for `-i -t`; both are needed for a usable interactive shell

Without `-i`, your keystrokes go nowhere. Without `-t`, output formatting breaks.

## Common Patterns

```bash
# Open a shell in a running container
docker exec -it [container_id] sh

# Run Redis CLI in a running Redis container
docker exec -it [container_id] redis-cli

# Start a new busybox container and explore it
docker run -it busybox sh
```

Exit any shell session with `exit` or `Ctrl+D`.

## Docker Isolation at the File Level

Each container gets its own isolated **filesystem layer** derived from the image snapshot. Two containers started from the same image do not share filesystem state — changes in one are invisible to the other. This is why:

- `docker run busybox ls` and a second `docker run busybox ls` run in separate isolated filesystems
- Files created inside a container are lost when the container is removed (unless a volume is mounted)

> [!note] File isolation is separate from process isolation. Containers share the host kernel but have separate filesystem, process, and network namespaces.

## Relationships

- part_of: [[wiki/tools/docker]]
- relates_to: [[wiki/concepts/docker-container-lifecycle]]

## See Also

- [[wiki/tools/docker]]
- [[wiki/concepts/docker-container-lifecycle]]
