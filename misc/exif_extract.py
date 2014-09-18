# sudo apt-get install libexiv2-dev gir1.2-gexiv2-0.10
# cd virtualenv
# $ cd lib/python2.7/
# $ ln -s /usr/lib/python2.7/dist-packages/gi

# The only docs: 
#   https://github.com/GNOME/gexiv2/blob/master/GExiv2.py
#   https://wiki.gnome.org/Projects/gexiv2/PythonSupport


from gi.repository import GExiv2
# md = GExiv2.Metadata('../tests/img/ecodicies.jpg')
md = GExiv2.Metadata('/tmp/loris/cache/links/ecodicies.jpg/full/full/0/default.jpg')
tags = filter(lambda t: 'iptc' in t, md.get_xmp_tags()) + md.get_iptc_tags()
kvs = ['%s: %s\n' % (t, md[t]) for t in tags]
print kvs

# for tag in md.get_iptc_tags() 
#     print '%s: %s' % (tag, md[tag])
# for tag in filter(lambda t: 'iptc' in t, md.get_xmp_tags()):
#     print '%s: %s' % (tag, md[tag])
