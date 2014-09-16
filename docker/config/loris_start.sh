#!/bin/bash
echo "Starting Loris"
cd /opt/loris/www
echo "Gone to /opt/loris/www"
passenger start  --max-pool-size 6 --nginx-config-template nginx.conf.erb
echo "Exiting Loris"