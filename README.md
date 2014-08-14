![loris icon](www/icons/loris-icon-name.png?raw=true) Loris IIIF Image Server
=============================================================================

__If you're looking for a stable version, please use the [latest release](https://github.com/pulibrary/loris/releases/tag/1.2.2). The development branch is working toward [IIIF Image API 2.0](http://iiif.io/api/image/2.0/).__

[![Build Status](https://travis-ci.org/pulibrary/loris.png)](https://travis-ci.org/pulibrary/loris.png)

Demos
-----
 * [Mentelin Bible, l. 1r](http://libimages.princeton.edu/loris/pudl0001%2F5138415%2F00000011.jp2/full/full/0/default.jpg) (link is broken until PUL is running IIIF 2.0 instance. See [here](http://libimages.princeton.edu/loris/pudl0001%2F5138415%2F00000011.jp2/full/full/0/native.jpg) for 1.1 compliant demo image)
 * [Serving Images for OpenSeadragon](http://libimages.princeton.edu/osd-demo)

Installation Instructions
-------------------------
Theses instructions are known to work on Ubuntu 12.04 or greater and Python 2.6.3 or greater (but less than 3.0.0). See below for some help with RedHat/CentOS and Debian.
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

IIIF 1.1 Compliance
-------------------
See [doc/compliance.md](doc/compliance.md)

License
-------
### Loris
Copyright (C) 2013-4 Jon Stroop

This program is free software: you can redistribute it and/or modify it 
under the terms of the GNU General Public License as published by the Free 
Software Foundation, either version 3 of the License, or (at your option) 
any later version.

This program is distributed in the hope that it will be useful, but WITHOUT 
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or 
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for 
more details.

You should have received a copy of the GNU General Public License along 
with this program. If not, see <http://www.gnu.org/licenses/>.

### Kakadu
#### Downloadable Executables Copyright and Disclaimer

The executables available [here](http://www.kakadusoftware.com/index.php?option=com_content&task=view&id=26&Itemid=22) are made available for demonstration purposes only. Neither the author, Dr. Taubman, nor the University of New South Wales accept any liability arising from their use or re-distribution.

Copyright is owned by NewSouth Innovations Pty Limited, commercial arm of the University of New South Wales, Sydney, Australia. **You are free to trial these executables and even to re-distribute them, so long as such use or re-distribution is accompanied with this copyright notice and is not for commercial gain. Note: Binaries can only be used for non-commercial purposes.** If in doubt please [contact Dr. Taubman](http://www.kakadusoftware.com/index.php?option=com_content&task=blogcategory&id=8&Itemid=14).

For further details, please visit the [Kakadu website](http://www.kakadusoftware.com/)
