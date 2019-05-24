#!/bin/bash
set -xeuo pipefail

SRC_DIR=$1 #  root folder of the workspace, /opt/git/workspace
BUILD_DIR=$2 # /mnt/deb-builds/${APP_NAME}-${VERSION}
APP_NAME=$3 # appName
VERSION=$4 # autogenerated timestamp

shift 4
EXTRA_ARGS="$@"

# Sagoku version number
echo "${VERSION}" > ${BUILD_DIR}/version_num

mkdir -p ${BUILD_DIR}/usr/local/src
mkdir -p ${BUILD_DIR}/etc/forum
cp -r ${SRC_DIR}/sagoku/dest/* ${BUILD_DIR}
cp -r ${SRC_DIR}/* ${BUILD_DIR}/usr/local/src

# Check for APPD_NAME and extract it.
if [[ "${EXTRA_ARGS}" =~ AppDName\=([^\ ]+) ]]; then
  APPD_NAME=${BASH_REMATCH[1]};
  cat << EOF > ${BUILD_DIR}/etc/forum/appd.conf
[agent]
app = $APPD_NAME
tier = $APP_NAME
node =

[controller]
host = Ithaka.saas.appdynamics.com
port = 443
ssl = on
account = Ithaka
accesskey = 8e51d6a16fb3
EOF

fi

# creating the main control file for this package
mkdir -p ${BUILD_DIR}/DEBIAN
cat << EOF > ${BUILD_DIR}/DEBIAN/control
Package: $APP_NAME
Version: $VERSION
Maintainer: Ithaka
Architecture: amd64
Section: main
Priority: optional
Depends: python-dev, python-pip, libjpeg-turbo8-dev, libfreetype6-dev, zlib1g-dev, liblcms2-dev, liblcms2-utils, libtiff5-dev, libwebp-dev, apache2
Description: $APP_NAME
EOF


cat << EOF > ${BUILD_DIR}/DEBIAN/postinst
#!/bin/bash
#set -xeuo pipefail
USER=loris

echo "Starting postinst"
touch /tmp/STARTED_POSTINSTALL_SCRIPT

#
## Install our Python dependencies
#
pip install -U appdynamics\<4.4
pip install uwsgi
pip install -U -r /usr/local/src/requirements.txt
pip install Pillow==2019.5.9.2 -i https://artifactory.acorn.cirrostratus.org/artifactory/api/pypi/pypi/simple

#
## Create a user to own the gust service
#
if ! getent passwd \$USER > /dev/null ; then
	adduser --quiet --ingroup bittybuffer --shell /bin/bash  \
                --gecos "User to own loris process" --disabled-password \
                \$USER
    groupadd loris
fi

#
## Configure apache
#
a2enmod headers expires
rm -f /etc/apache2/sites-enabled/*
ln -s /etc/apache2/sites-available/loris-web.conf /etc/apache2/sites-enabled/

#
## Map and mount the EFS volume for image caching
#
mkdir /cache

if [ \${SGK_ENVIRONMENT} == "prod" ]; then
  mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport fs-33fcb6d3.efs.us-east-1.amazonaws.com:/ /cache
else
  mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport fs-b6d3a757.efs.us-east-1.amazonaws.com:/ /cache
fi

mkdir -p /cache/loris
chown loris /cache
mkdir -p /mnt/loris/tmp/jp2
chown -R loris /mnt/loris

#
## Install Loris
#
cd /usr/local/src
python setup.py install


#
## Configure AppDynamics and start the proxy
#
if [ -f /etc/forum/appd.conf ]; then
    NODENAME="\$SGK_APP_SERVICE_NAME.\$SGK_INSTANCE_ID"
    sed -i -e 's/node =/node = '"\$NODENAME"'/g' /etc/forum/appd.conf
    sudo -u loris /usr/local/bin/pyagent proxy start &
fi

#
## Copying Libs
#
sudo cp bin/Linux/x86_64/* /usr/local/bin/
sudo cp lib/Linux/x86_64/* /usr/lib/



#
## Start the application
#
service apache2 start
service loris start

#
## Verify the application starts up properly
#
#exec /usr/local/bin/verify-build.sh
EOF

chmod 0755 ${BUILD_DIR}/DEBIAN/postinst
