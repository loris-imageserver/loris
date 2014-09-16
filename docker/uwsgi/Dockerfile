FROM ubuntu

MAINTAINER eliotj@princeton.edu

## Env vars for uwsgi

ENV UWSGI_BIND --http
# ENV UWSGI_BIND --socket

ENV UWSGI_BIND_ADDRESS :9090
ENV UWSGI_PROCESSES 10
ENV UWSGI_THREADS 15

# ENV UWSGI_STATS --stats 
# ENV UWSGI_STATS_ADDRESS 127.0.0.1:9191

# Update packages and install tools 
RUN apt-get update -y
RUN apt-get install -y wget git 

# Install pip and python libs
RUN apt-get install -y python-dev python-setuptools python-pip
RUN pip install --upgrade pip		
RUN pip2.7 install Werkzeug
RUN pip2.7 install uwsgi
RUN pip2.7 install configobj

# Install kakadu
WORKDIR /usr/local/lib
RUN wget --no-check-certificate https://github.com/sul-dlss/Djatoka/raw/master/lib/Linux-x86-32/libkdu_v60R.so
RUN chmod 755 libkdu_v60R.so

WORKDIR /usr/local/bin
RUN wget --no-check-certificate https://github.com/sul-dlss/Djatoka/raw/master/bin/Linux-x86-32/kdu_expand
RUN chmod 755 kdu_expand

RUN ln -s /usr/lib/`uname -i`-linux-gnu/libfreetype.so /usr/lib/
RUN ln -s /usr/lib/`uname -i`-linux-gnu/libjpeg.so /usr/lib/
RUN ln -s /usr/lib/`uname -i`-linux-gnu/libz.so /usr/lib/
RUN ln -s /usr/lib/`uname -i`-linux-gnu/liblcms.so /usr/lib/
RUN ln -s /usr/lib/`uname -i`-linux-gnu/libtiff.so /usr/lib/

RUN echo "/usr/local/lib" >> /etc/ld.so.conf && ldconfig

# Install Pillow
RUN apt-get install -y libjpeg8 libjpeg8-dev libfreetype6 libfreetype6-dev zlib1g-dev liblcms2-2 liblcms2-dev liblcms2-utils libtiff4-dev
RUN pip2.7 install Pillow

# Install loris
WORKDIR /opt

RUN git clone https://github.com/pulibrary/loris.git
RUN useradd -d /var/www/loris -s /sbin/false loris

WORKDIR /opt/loris

# Copy test images
RUN mkdir /usr/local/share/images
RUN cp -R tests/img/* /usr/local/share/images/

# ToDo: Use env vars (+ script?) to change settings in loris.conf

RUN ./setup.py install

EXPOSE 9090 9191

CMD uwsgi $UWSGI_BIND $UWSGI_BIND_ADDRESS --wsgi-file www/loris.wsgi --master --processes $UWSGI_PROCESSES --threads $UWSGI_THREADS $UWSGI_STATS $UWSGI_STATS_ADDRESS



