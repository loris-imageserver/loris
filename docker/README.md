Docker build of Loris IIIF Image Server
===========

Docker container running [Loris IIIF Image Server](https://github.com/pulibrary/loris) with Passenger

### Use  pre-built image
Download image from docker hub.

    $ docker pull pulibrary/loris

### Build from scratch
Use local Dockerfile to build image.

    $ docker build -t your_image_name .

### Start the container and test

    $ docker run -d -p 3000:3000 pulibrary/loris

Point your browser to `http://<Host or Container IP>:3000/01/02/0001.jp2/full/full/0/default.jpg`

### Use samba to load images
Add the images directory as a volume and mount on a Samba or sshd container. [(See svendowideit/samba)](https://registry.hub.docker.com/u/svendowideit/samba/)

    $ docker run --name loris -v /usr/local/share/images -d -p 3000:3000 pulibrary/loris
    $ docker run --rm -v /usr/local/bin/docker:/docker -v /var/run/docker.sock:/docker.sock svendowideit/samba loris
    

### Create loris cluster
Create data volume container

    $ docker run --name loris_data -v /usr/local/share/images -v /var/cache/loris -d ubuntu echo Data only container for loris images and cache

Create two loris server containers with shared image and cache volumes    

    $ docker run --name loris_server_1 --volumes-from loris_data -d pulibrary/loris
    $ docker run --name loris_server_2 --volumes-from loris_data -d pulibrary/loris
    
Build nginx image with custom config

    $ cd nginx
    $ docker build -t loris/nginx .

Run nginx proxy

    $ docker run --name loris_proxy  --link loris_server_1:server1 --link loris_server_2:server2 -d -p 80:80 loris/nginx    
    
Load test images via sshd

    $ cd ../sshd/
    $ docker build -t loris/sshd .
    $ docker run --name loris_sshd --volumes-from loris_data  -d -p 8022:22 loris/sshd
    $ scp -P 8022 -rp ../../tests/img/ root@<Host or Container IP>:/usr/local/share/images  # (password: root)