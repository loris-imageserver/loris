![loris icon](sagoku/dest/var/www/icons/loris-circle-small.png?raw=true) Loris IIIF Image Server
=============================================================================

Loris is an implementation of the [IIIF Image API 2.0](http://iiif.io/api/image/2.0/).

 * If you're looking for IIIF 1.1 support, please use the [last release in the 1.x series](https://github.com/pulibrary/loris/releases/tag/1.2.2).
 * If you're looking for IIIF 1.0 support, [this release](https://github.com/pulibrary/loris/releases/tag/0.0.9alpha) is the closest Loris ever was, but there are known flaws, deployment is tough, and it is certainly not supported at this point.

[![Build Status](https://travis-ci.org/loris-imageserver/loris.svg?branch=development)](https://travis-ci.org/loris-imageserver/loris)

Ithaka specific instructions
----------------------------
 Building a development docker image for use in PyCharm
  * Use the included Dockerfile and tag the image as loris:loris
  
        docker build . -t loris:loris
  * Setup PyCharm to use a remote Python interpreter and specify the Python in the loris:loris docker image.
  * Update PyCharm to use pytest for unit testing.

The application can be run via PyCharm by running webapp.py in the loris directory.
  

Installation Instructions
-------------------------
Loris is only supported on Python 2.7.x. If you need to use Python 2.6, Loris v2.1.0 is the last version to support it.

These instructions are known to work on Ubuntu 12.04 or greater and Python 2.7.x (but not 3.x). See below for some help with RedHat/CentOS and Debian.

**Do Not!** Run `setup.py` until you've read the following:

 * [Install Dependencies](doc/dependencies.md)
 * [Configuration Options](doc/configuration.md)
 * [Cache Maintenance](doc/cache_maintenance.md)
 * [Resolver Implementation](doc/resolver.md)
 * [Run `setup.py`](doc/setup.md)
 * [Deploy with Apache](doc/apache.md)
 * [Deploy with Docker](https://github.com/loris-imageserver/loris-docker)
 * (Optional) [Developer Notes](doc/develop.md)

You're best off working through these steps in order.

RedHat, Debian and Troubleshooting
---------------------------------
@mmcclimon has provided some excellent [instructions for deploying Loris on RedHat 6 or the equivalent CentOS](doc/redhat-install.md).

If you're running Debian and/or run into any pitfalls with the steps above, [Regis Robineau](https://github.com/regisrob) of the [Biblissima Project](http://www.biblissima-condorcet.fr/) has created an [excellent set of instructions](http://doc.biblissima-condorcet.fr/loris-setup-guide-ubuntu-debian) that may help.

As always, clarifications, notes (issues, pull requests) regarding experiences on different platforms are most welcome.

IIIF 2.0 Compliance
-------------------
Loris Implements all of the IIIF Image API level 2 features, plus nearly all of the "optional" features:

 * `sizeAboveFull`
 * `rotationArbitrary`
 * `mirroring`
 * `profileLinkHeader`
 * `webp` and `gif` formats

Validation: http://goo.gl/P1KBkU

See http://iiif.io/api/image/2.0/compliance.html for details.

License (New BSD)
-----------------

Copyright (c) 2013-2015, Jon Stroop
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

 * Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

 * Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

 * Neither the name "Loris" nor the names of its contributors may be used to
   endorse or promote products derived from this software without specific prior
   written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

### Kakadu
#### Downloadable Executables Copyright and Disclaimer

The executables available [here](http://www.kakadusoftware.com/index.php?option=com_content&task=view&id=26&Itemid=22) are made available for demonstration purposes only. Neither the author, Dr. Taubman, nor the University of New South Wales accept any liability arising from their use or re-distribution.

Copyright is owned by NewSouth Innovations Pty Limited, commercial arm of the University of New South Wales, Sydney, Australia. **You are free to trial these executables and even to re-distribute them, so long as such use or re-distribution is accompanied with this copyright notice and is not for commercial gain. Note: Binaries can only be used for non-commercial purposes.** If in doubt please [contact Dr. Taubman](http://www.kakadusoftware.com/index.php?option=com_content&task=blogcategory&id=8&Itemid=14).

For further details, please visit the [Kakadu website](http://www.kakadusoftware.com/)
