# Introduction
**UNDER DEVELOPMENT**<br>
RAT application written in Python, this is still in the early development phase. It was never and will never be meant
for production use, it is only coded for educational purposes and hence will never be production ready.
At this moment in time, it does not have a GUI, everything is done in the command line.<br>
I try to write code compatible with Python 3 and Python 2 as much as I can, but I focus on version 3 right now,
in the future I will make it 100% compatible with version 2.

The features implemented at this time are:
- Reverse Shell
- List Processes
- Download Files
- Upload Files
- List files from directory
- Desktop streaming

This uses the socket API in blocking mode. This RAT is also implemented in other programming languages:
Java, C++, etc. If you are interested on them, look at my Github repositories.  

# TODO
- GUI
- Check if a packet is expected or not
- In ConsoleMediator when I receive a packet from a client
I have to make sure the current_view is still pointing to the appropiate one
otherwise app may crash if user has changed the view to let's say camera
but received Filesystem info
- Synchronization: read-write locks in UiMediator for active client, Server for list of clients
- Handling commands in an insensitive way
- Camera
- Encryption