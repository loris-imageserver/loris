[Slides](https://docs.google.com/presentation/d/1HcEWr5lWO0lCywbHOigFW7k7MmRz0Y44Aw202x5YG1k)

Meet Loris
==========

Loris is an Implementation of the [IIIF (International Image Interoperability Framework) Image API](http://www-sul.stanford.edu/iiif/image-api) specification. Loris is designed to work w/ JPEG2000 files, but this is not part of the spec.

IIIF defines a Syntax for accessing images:

```
/identifier/region/size/rotation/quality(.format)?
```
and a bit of metadata about them:
```
/identifier/info(.(xml)|(json))?
```

One of the goals is to have a persistent and cool URI not just for the image but regions and other derivatives thereof, so that you can make statements about those regions or derivatives.

The Parts
---------
[identifier](https://gist.github.com/jpstroop/4771145#identifier) | [region](https://gist.github.com/jpstroop/4771145#region) | [size](https://gist.github.com/jpstroop/4771145#size) | [rotation](https://gist.github.com/jpstroop/4771145#rotation) | [quality](https://gist.github.com/jpstroop/4771145#quality)

### Identifier

Loris ships w/ a simple ID resolver that just takes a slice of a filesystem path
and resolves it to a file. This is isolated in [`resolver.py`](https://github.com/pulibrary/loris/blob/master/loris/resolver.py) and is designed to be changed to suit different environments.

e.g.:

```
/fs/path/region/size/rotation/quality(.format)?
/fs/path/info(.(xml)|(json))?
```

Get the full image
[/full/full/0/native.jpg](http://lorisimg.princeton.edu/loris/pudl0001/4609321/s42/00000001/full/full/0/native.jpg)

### Region
Region can be specified by pixel or percent:

[/930,1450,800,700/full/0/native.jpg](http://lorisimg.princeton.edu/loris/pudl0001/4609321/s42/00000001/930,1450,800,700/full/0/native.jpg)

### Size
Again as percent:

[/930,1450,800,700/pct:50/0/native.jpg](http://lorisimg.princeton.edu/loris/pudl0001/4609321/s42/00000001/930,1450,800,700/pct:50/0/native.jpg)

or pixel (`w,`, `w,h`, or `,h`):

[/930,1450,800,700/120,/0/native.jpg](http://lorisimg.princeton.edu/loris/pudl0001/4609321/s42/00000001/930,1450,800,700/120,/0/native.jpg)

### Rotation
Multiples of 90.

[/full/pct:40/90/native.jpg](http://lorisimg.princeton.edu/loris/pudl0001/4609321/s42/00000001/full/pct:40/90/native.jpg)

### Quality
Can be `native`, `color`, `grey` or `bitonal`. Which are available (color or not) is available from `info` service.

[/full/pct:40/0/grey.jpg](http://lorisimg.princeton.edu/loris/pudl0001/4609321/s42/00000004/full/pct:40/0/grey.jpg)

### Format:
Loris does jpg and png and the moment. The only feature missing from making this a IIIF level impl is that it won't return a jp2. You can define a default in config file, and use content negotiation rather than a file ext as well.

Ask for a `png`: [/full/120,/0/native.png](http://lorisimg.princeton.edu/loris/pudl0001/4609321/s42/00000001/full/120,/0/native.png)

Use the default: [/full/120,/0/native](http://lorisimg.princeton.edu/loris/pudl0001/4609321/s42/00000001/full/120,/0/native)

Use Conneg:
```
curl -v \
  -H "Accept: image/png" \
  "http://lorisimg.princeton.edu/loris/pudl0001/4609321/s42/00000001/full/120,/0/native" \
  -o /tmp/a.png
```

Info
----
Basically just enough metadata to drive a UI.
 * [/info.xml](http://lorisimg.princeton.edu/loris/pudl0001/4609321/s42/00000001/info.xml)
 * [/info.json](http://lorisimg.princeton.edu/loris/pudl0001/4609321/s42/00000001/info.json)

Caching
-------
### Server
Cache is built on the FS mirroring the path in the URI, so each request looks there first. We just use a cron to check that it's not bigger than we want, and clear out LRU files until the size is acceptable. A sample copy of the cron is in the code repo. It could be smarter if you needed it to be.

### Client
As expected, will send a `304` if client sends an `If-Modified-Since` header (and it hasn't been).

Errors
------
IIIF also defines a syntax for the HTTP message body when something goes wrong.  

 * [Bad ID](http://lorisimg.princeton.edu/loris/pudl0001/4609321/s32/00000001/info.xml)
 * [Bad Region](http://lorisimg.princeton.edu/loris/pudl0001/4609321/s42/00000001/256/full/0/native.jpg)
 * etc.

You obviously you get a 4xx/5xx as well.

Viewers
-------
Not much until last week! [Chris Thatcher / OpenSeadragon](https://github.com/thatcher/openseadragon) Just added [support for IIIF syntax](http://thatcher.github.com/openseadragon/examples/tilesource-iiif/).

Loris on Github
---------------
https://github.com/pulibrary/loris
