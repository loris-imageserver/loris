from PIL import Image

a_jpeg = '../tests/img/01/03/0001.jpg'

meth = 'NONE'

im = Image.open(a_jpeg)
im = im.convert(mode='1', dither=Image.NONE)
# im = im.convert(mode='1', dither=Image.FLOYDSTEINBERG)
im.show()
