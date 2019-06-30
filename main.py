from PIL import Image, ImageDraw
from glob import glob
from os import path
from sys import argv
from sympy.geometry.polygon import Polygon, Point
from random import randint, sample
import pytess
import numpy as np
from argparse import ArgumentParser

import sys

def progressbar(it, prefix="", size=60, file=sys.stdout):
    count = len(it)
    def show(j):
        x = int(size*j/count)
        file.write("%s[%s%s] %i/%i\r" % (prefix, "#"*x, "."*(size-x), j, count))
        file.flush()        
    show(0)
    for i, item in enumerate(it):
        yield item
        show(i+1)
    file.write("\n")
    file.flush()

def getfiles():
	extensions = "jpg jpeg png".split()
	filepaths = []
	for ext in extensions:
		dirpath = path.join(SRCDIR, "**", "*." + ext)
		print(dirpath)
		filepaths += glob(dirpath, recursive=True)
	return filepaths

def polypoint(poly):
	min_x, min_y, max_x, max_y = poly.bounds

	#XXX
	return (randint(min_x, max_x), randint(min_y, max_y))
	"""
	miss = 0
	while True:
		point = (randint(min_x, max_x), randint(min_y, max_y))
		if poly.encloses_point(Point(point)):
			#print(miss)
			return point
		miss += 1
	"""

def getcolor(img, poly, samples=200):
	colors = []

	for i in range(samples):
		point = polypoint(poly)
		try:
			colors.append(img.getpixel(point))
		except IndexError:
			pass
	avg = [sum(x)/len(colors) for x in zip(*colors)]
	return avg

def randompoly(w,h,vertcount=4):
	return Polygon(*((randint(0,w-1), randint(0,h-1)) for i in range(vertcount)))

def polyverts(poly):
	return [(point.x, point.y) for point in poly.vertices]

def polycrop(img, poly):
	img = img.copy().convert("RGBA")
	arr = np.asarray(img)

	vertlist = polyverts(poly)
	
	maskimg = Image.new("RGBA", img.size, 0)
	draw = ImageDraw.Draw(maskimg)
	draw.polygon(vertlist, outline=(255,255,255,255), fill=(255,255,255,255))

	return maskimg

def poprand(items, n):
    to_delete = set(sample(range(len(items)),n))
    return [x for i,x in enumerate(items) if not i in to_delete]

def construct(inpath, outpath):

	target = Image.open(inpath).convert("RGB")

	w,h = target.size
	print(w,h)

	images = []
	avgcolors = []
	for fp in getfiles():
		#print(fp)
		img = Image.open(fp).convert("RGB")
		img = img.resize((w,h))
		images.append(img)
		avgcolors.append(getcolor(img, Polygon((0,0),(0,w),(0,h),(w,h))))
		
	print(f"{len(images)} images.")
		
	#TODO sort/index avgcolors for faster search, change images list order equally

	out = Image.new("RGBA", (w,h))

	def sample(color, poly):

		least_dist = 3*256**2
		least_img = None
		
		min_x, min_y, max_x, max_y = poly.bounds
		
		scalex = w/(max_x-min_x)
		scaley = h/(max_y-min_y)
		scaledpoly = Polygon(*[((x-min_x)*scalex, (y-min_y)*scaley) for x,y in polyverts(poly)])
		for i, img in enumerate(images):
			#change poly pos, scale, rotate?
			#s = getcolor(img, poly)
			s = avgcolors[i]
			dist = sum([(a-b)**2 for a,b in zip(s,color)])
			if dist < least_dist:
				least_dist = dist
				least_img = img

		ret = Image.new("RGBA", (w,h))
		tri = polycrop(least_img, scaledpoly)
		if tri is None:
			raise Exception("Source directory contains no images")
		ret.paste(least_img, tri)
		#return least_img, polycrop(least_img, scaledpoly)
		ret = ret.resize((max_x-min_x,max_y-min_y))
		return ret, (min_x, min_y)

	points = [(0,0), (w,0), (0,h), (w,h)]
	
	
	if CLOUD is None:
		for i in range(NUMPOINTS):
			points.append((randint(0,w-1), randint(0,h-1)))
	else:
		cloud = Image.open(CLOUD)
		for x in range(cloud.size[0]):
			for y in range(cloud.size[1]):
				if cloud.getpixel((x,y))[:3] != (255,255,255):
					points.append((x,y))

	print(f"{len(points)} points.")
	
	if len(points) > NUMPOINTS:
		n = len(points)-NUMPOINTS
		print(f"Sampling {n} down to {NUMPOINTS}.")
		points = poprand(points, n)

	ADDPOINTS = 200
	print(f"Adding {ADDPOINTS} random points.")
	for i in range(ADDPOINTS):
		points.append((randint(0,w-1), randint(0,h-1)))

	triangles = pytess.triangulate(points)
	#triangles = pytess.voronoi(points)

	try:
		for t, triangle in progressbar(list(enumerate(triangles)), "Triangles: ", 40):
			#print(f"{t}/{len(triangles)}")
			poly = Polygon(*triangle)
			targetcolor = getcolor(target, poly)
			#img, mask = sample(targetcolor, poly)
			#out.paste(img, (0,0), mask)
			
			img, coords = sample(targetcolor, poly)
			out.paste(img, coords, img)
			
			#img.save(f"conv/{t}-img.png")
			#mask.save(f"conv/{t}-mask.png")
	except KeyboardInterrupt:
		pass

	out.convert("RGB").save(outpath)

if __name__ == "__main__":

	parser = ArgumentParser(description="Tesselate images")
	parser.add_argument('srcdir', metavar='SRCDIR', type=str,
        help='The path to the source folder')
	parser.add_argument('target', metavar='TARGET', type=str,
        help='The path to the input file')
	parser.add_argument('output', metavar='OUTPUT', type=str,
        help='The path to the output file')
	parser.add_argument('--cloud', dest='cloud', type=str, nargs="?", default=None,
        help='The path to the output file')
	parser.add_argument('--points', dest='numpoints', type=int, nargs="?", default=100,
        help="The number of points in the image that are tesselated")

	args = parser.parse_args()
	
	SRCDIR = args.srcdir
	TARGET = args.target
	OUTPUT = args.output
	CLOUD = args.cloud
	NUMPOINTS = args.numpoints
	
	construct(TARGET, OUTPUT)
