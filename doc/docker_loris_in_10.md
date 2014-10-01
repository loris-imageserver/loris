# Loris and OpenSeadragon with Docker in 10 minutes

This guide assumes that you have [Docker](https://www.docker.com/) [installed](http://docs.docker.com/installation/#installation) and the [source code for Loris](https://github.com/pulibrary/loris) cloned. The result will be a Loris cluster running three nodes. 

Hints: 
 * Add yourself to the docker group so that you can run docker commands without `sudo`.
 * Make sure nothing is running on ports 80, 5001, 5002, or 5003 on your machine.

 1. Get the image from [Docker Hub](https://registry.hub.docker.com/u/pulibrary/loris/)

    ```
    $ docker pull pulibrary/loris
    Pulling repository pulibrary/loris
    946315b95896: Pulling dependent layers 
    [...] # this could take a while depending on your connection
    ea9fd3e656a7: Download complete 
    ```

 2. Set up a [data volume container](https://docs.docker.com/userguide/dockervolumes/). This will allow you to share the images and caches between nodes:

    ```
    $ docker run --name loris_data \
        -v /path/to/loris/docker/sample_img:/usr/local/share/images \
        -v /var/cache/loris \
        -d ubuntu \
        echo Data only container for loris images and cache
    f7dd56bb5b7293b1f5e17fd4d6d6b7b42732e2aad288ada9e17b12280c03b6b8
    ```

 3. Run three instances of Loris using the shared data:

    ```
    $ docker run --name loris_server_1 --volumes-from loris_data -d pulibrary/loris
    eb25b3f631c71e0c44925e6590a56e7c2c8d8423ee3324aea149a11eaae16983
    $ docker run --name loris_server_2 --volumes-from loris_data -d pulibrary/loris
    ace34e27e376d2c2073f19df087fff304fbe6ce3cb17cf8e508e402449df89f1
    $ docker run --name loris_server_3 --volumes-from loris_data -d pulibrary/loris
    f63d1e23a9fa9b574380cd54a0cb7407f6427dd7b45f71f1069839d9f5d91f80
    ```

 4. Build an nginx container (pre-configured to work with our cluster)

    ```
    $ cd docker/nginx # this is in the loris source, wherever you cloned it
    $ docker build -t loris/nginx .
    [...] # this could take a while depending on your connection
    Successfully built df5fb4c53325
    ```

 5. Run nginx as a proxy/balancer to our three servers:

    ```
    $ docker run --name loris_proxy \
        --link loris_server_1:server1 \
        --link loris_server_2:server2 \
        --link loris_server_3:server3 \
        -d -p 80:80 loris/nginx
    e32f35d702f75142ca8592ce070d814699555c8a83062e36bfb05219dbf4df78
    ```

    (You could start more lorises and add them to the nginx config [here](https://github.com/pulibrary/loris/blob/development/docker/nginx/nginx.conf#L22-L26) )

 6. Visit:
     * [http://localhost/iiif/00000011.jp2/full/pct:10/0/default.jpg](http://localhost/iiif/00000011.jp2/full/pct:10/0/default.jpg) (for example)
     * [http://localhost/](http://localhost/)
