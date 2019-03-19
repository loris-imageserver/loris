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
Depends: python-dev, python-pip, libjpeg-turbo8-dev, libfreetype6-dev, zlib1g-dev, liblcms2-dev, liblcms2-utils, libtiff5-dev, libwebp-dev, apache2, libapache2-mod-wsgi
Description: $APP_NAME
EOF


cat << EOF > ${BUILD_DIR}/DEBIAN/preinst
#!/bin/bash
rm /etc/apache2/mods-available/wsgi.load
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
pip install Pillow
ln -s /usr/local/lib/python2.7/dist-packages/appdynamics/scripts/wsgi.py /var/www/loris/appd.wsgi

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

if [ \${SGK_ENVIRONMENT} == "test" ]; then
  mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport fs-b6d3a757.efs.us-east-1.amazonaws.com:/ /cache
else
  echo 'No production yet';
  #mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport fs-edeb3ca6.efs.us-east-1.amazonaws.com:/ /cache
fi

mkdir -p /cache/loris
chown loris /cache


apt-get install -y libapache2-mod-wsgi

#
## Install s3fs for mounting AWS S3 filesystems as local storage
#
#cd /tmp
#git clone https://github.com/s3fs-fuse/s3fs-fuse.git
#cd s3fs-fuse
#./autogen.sh
#./configure --prefix=/usr
#make
#make install

#
## Map and mount the S3 filesystem as local storage
#
#mkdir /images

#if [ \${SGK_ENVIRONMENT} == "test" ]; then
#  s3fs forum-data-cache /images -o iam_role='test-ForumTeamInstRole' -o allow_other -o umask=0222
#else
#  echo 'No production yet';
  #mount -t nfs4 -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport fs-edeb3ca6.efs.us-east-1.amazonaws.com:/ /cache
#fi

chown loris /cache

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
## Start the application
#
a2enmod wsgi
service apache2 start

#
## Verify the application starts up properly
#
#exec /usr/local/bin/verify-build.sh
EOF

chmod 0755 ${BUILD_DIR}/DEBIAN/postinst
chmod 0755 ${BUILD_DIR}/DEBIAN/preinst
