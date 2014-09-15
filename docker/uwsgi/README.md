Docker build of Loris IIIF Image Server
===========

Docker container running [Loris IIIF Image Server](https://github.com/pulibrary/loris) with uWSGI

### Use  pre-built image
Download image from docker hub.

    $ docker pull eliotjordan/docker-loris

### Build from scratch
Use local Dockerfile to build image.

    $ cd docker-loris
    $ docker build -t eliotjordan/docker-loris .

### Start the container and test

    $ docker run -d -p 9090:9090 eliotjordan/docker-loris

Point your browser to `http://<Container IP>:9090/01/02/0001.jp2/full/full/0/default.jpg>`

### Now what??
Add the images directory as a volume and mount on a Samba or sshd container. [(See svendowideit/samba)](https://registry.hub.docker.com/u/svendowideit/samba/)

    $ docker run --name loris -v /usr/local/share/images -d -p 9090:9090 eliotjordan/docker-loris
    $ docker run --rm -v /usr/local/bin/docker:/docker -v /var/run/docker.sock:/docker.sock svendowideit/samba loris

Throw this puppy behind an nginx container and share those awesome JP2s of your [medieval shoe collection](http://collections.museumoflondon.org.uk/Online/group.aspx?g=group-20518) with the world!
