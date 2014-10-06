![loris icon](www/icons/loris-icon-name.png?raw=true) Loris IIIF Image Server
=============================================================================

 * Loris 2, which is in alpha release at the moment, supports the [IIIF Image API 2.0](http://iiif.io/api/image/2.0/). The best thing to do is either choose the [latest alpha release](https://github.com/pulibrary/loris/releases) or build from the development branch.
 * If you're looking for IIIF 1.1 support, please use the [last release in the 1.x series](https://github.com/pulibrary/loris/releases/tag/1.2.2).
 * If you're looking for IIIF 1.0 support, [this release](https://github.com/pulibrary/loris/releases/tag/0.0.9alpha) is the closest Loris ever was, but there are known flaws, deployment is tough, and it is certainly not supported at this point.

[![Build Status](https://travis-ci.org/pulibrary/loris.png)](https://travis-ci.org/pulibrary/loris.png)

Demos
-----
IIIF 2.0 Compliance:
 * [Mentelin Bible, l. 1r](http://libimages.princeton.edu/loris2/pudl0001%2F5138415%2F00000011.jp2/full/full/0/default.jpg)

IIIF 1.1 Compliance:

 * [Mentelin Bible, l. 1r](http://libimages.princeton.edu/loris/pudl0001%2F5138415%2F00000011.jp2/full/full/0/native.jpg)
 * [Serving Images for OpenSeadragon](http://libimages.princeton.edu/osd-demo)

Installation Instructions
-------------------------
These instructions are known to work on Ubuntu 12.04 or greater and Python 2.6.3 or greater (but less than 3.0.0). See below for some help with RedHat/CentOS and Debian.

**Do Not!** Run `setup.py` until you've read the following:

 * [Install Dependencies](doc/dependencies.md)
 * [Configuration Options](doc/configuration.md)
 * [Cache Maintenance](doc/cache_maintenance.md)
 * [Resolver Implementation](doc/resolver.md)
 * [Run `setup.py`](doc/setup.md)
 * [Deploy with Apache](doc/apache.md)
 * [Deploy with Docker](docker/README.md)
 * (Optional) [Developer Notes](doc/develop.md)

You're best off working through these steps in order.

RedHat, Debian and Troubleshooting
---------------------------------
[mmcclimon](https://github.com/mmcclimon) has provided some excellent [instructions for deploying Loris on RedHat 6 or the equivalent CentOS](doc/redhat-install.md). 

If you're running Debian and/or run into any pitfalls with the steps above, [Regis Robineau](https://github.com/regisrob) of the [Biblissima Project](http://www.biblissima-condorcet.fr/) has created an [excellent set of instructions](http://doc.biblissima-condorcet.fr/loris-setup-guide-ubuntu-debian) that may help.

As always, clarifications, notes (issues, pull requests) regarding experiences on different platforms are most welcome.

IIIF 2.0 Compliance
-------------------
Loris Implements all of the IIIF Image API level 2 features, plus nearly all of the "optional" features:

 * `sizeAboveFull`
 * `rotationArbitrary`
 * `mirroring`
 * `mirroring`
 * `profileLinkHeader`
 * `webp` and `gif` formats 

Validation: http://goo.gl/P1KBkU
 
See http://iiif.io/api/image/2.0/compliance.html for details.

License
-------
Copyright 2013-14 Jon Stroop

Additional copyright may be held by others, as reflected in the commit log. 
Kakadu and OpenJPEG are included under the terms of their own respecitve 
licenses (see LICENSE-Kakadu.txt and LICENSE-OpenJPEG.txt).

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

### Kakadu
#### Downloadable Executables Copyright and Disclaimer

The executables available [here](http://www.kakadusoftware.com/index.php?option=com_content&task=view&id=26&Itemid=22) are made available for demonstration purposes only. Neither the author, Dr. Taubman, nor the University of New South Wales accept any liability arising from their use or re-distribution.

Copyright is owned by NewSouth Innovations Pty Limited, commercial arm of the University of New South Wales, Sydney, Australia. **You are free to trial these executables and even to re-distribute them, so long as such use or re-distribution is accompanied with this copyright notice and is not for commercial gain. Note: Binaries can only be used for non-commercial purposes.** If in doubt please [contact Dr. Taubman](http://www.kakadusoftware.com/index.php?option=com_content&task=blogcategory&id=8&Itemid=14).

For further details, please visit the [Kakadu website](http://www.kakadusoftware.com/)

### OpenJPEG

(Copied from http://www.openjpeg.org/BSDlicense.txt)

Copyright (c) 2002-2007, Communications and Remote Sensing Laboratory, Universite catholique de Louvain (UCL), Belgium
Copyright (c) 2002-2007, Professor Benoit Macq
Copyright (c) 2001-2003, David Janssens
Copyright (c) 2002-2003, Yannick Verschueren
Copyright (c) 2003-2007, Francois-Olivier Devaux and Antonin Descampe
Copyright (c) 2005, Herve Drolon, FreeImage Team
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

 1. Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
 2. Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS `AS IS'
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.


