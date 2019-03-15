#!/bin/bash
#
# Stor Dockerfile
#
#

# Pull base image.
FROM ubuntu:18.04

RUN apt-get update && \
apt-get -y install python-dev \
                python-pip \
                libjpeg-turbo8-dev \
                libfreetype6-dev \
                zlib1g-dev \
                liblcms2-dev \
                liblcms2-utils \
                libtiff5-dev \
                libwebp-dev \
                apache2 \
                libapache2-mod-wsgi \
                build-essential \
                libfuse-dev \
                libxml2-dev \
                mime-support \
                libcurl4-openssl-dev \
                automake \
                libtool \
                wget \
                tar

WORKDIR /data

COPY requirements.txt ./

COPY sagoku/* /

#RUN mkdir -p /cache && mkdir -p /var/log/loris && mkdir -p /tmp/loris/tmp && mkdir -p /var/www/loris

RUN pip install -r requirements.txt

# Define mountable directories.
#VOLUME ["/data"]

#ENV CELERY_CONFIG celery-test.cfg
EXPOSE 5004

#ENTRYPOINT ["/docker-entrypoint.sh"]