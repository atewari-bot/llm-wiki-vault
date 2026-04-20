---
processed: 2026-04-19
---

1. docker run
	- docker run [image_name]
	- docker create + docker start
	- creating container
		- copy file system snapshot to prep for use
		- docker create hello-world
			- print id of the container
	- start container
		- start the image and run the startup command of image
		- docker start -a [image_id]
			- run and -a would watch the image output on console
		- docker start [image_id]
			- show image id
			- run the container
2. docker run busybox ls
3. docker run busybox echo Hi Ajay!
4. docker ps
	- Listing running docker containers
	- docker ps --all
		- Show all containers we ever created
		- Rerun of exited container would start the container
5. docker run busybox ping google.com
6. docker prune
	- docker system prune
		- remove stopped containers
		- remove build cache (from docker hub)
		- remove dangling images
		- remove networks with no attached container
7. docker logs
	- Log container output the logs to inspect
	- docker logs [image_id]
8. Stop/kill long running container
	- stop container by passing SIGTERM command to shut it down by its own
		- docker stop [container_name]
		- docker would fallback to kill if container did not stop in 10 secs
	- kill container issues SIGKill command to stop right now
		- docker kill [container_name]
9. Executing commands in container
	- docker exec -it [container_id] {command}
	- docker exec -it [container_id] redis_cli
		- -it: allow for user input
		- -it => -i -t
		- -i: attach STDIN
		- -t: provide nice formatting to STDOUT
10. Working with docker shell
	- docker exec -it [container_id] sh
	- sh: name of program; command processor or shell
	- docker run -it busybox sh
	- Type exit or ctrl+D to exit of shell
	- #llm What is the difference between exec -it and run -it commands?
11. Docker isolation is there at file level

#llm-reprocess