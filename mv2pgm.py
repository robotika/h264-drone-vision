"""
  convert mv vectors from H.264 codec to PGM
  usage:
      mv2pgm.py <input file> <output file>
"""
import sys

def generator( filename ):
  prev = 0
  for line in open( filename ):
    if "Frame" in line:
      continue
    x,y,mx,my = [int(i) for i in line.split()]
    seek = x+y*80
    if seek < prev:
      yield -1,-1,0,0
    yield x,y,mx,my
    prev = seek
  yield -1,-1,0,0

def pictureOffsetG( filename ):
  arr = []
  for x,y,mx,my in generator( filename ):
    if x < 0:
      yield arr
      arr = []
    else:
      arr.append( ((x,y), (mx,my)) )

def mv2pgm( gen, outFile, numFrames ):
  arr=[[0 for i in range(45)] for j in range(80)]
  count = 0
  for x,y,mx,my in gen:
    if x == -1:
      assert x==-1 and y==-1 # separator
      count += 1
      if count == numFrames:
        break
    else:
      arr[x][y] += abs(mx)+abs(my)
  m = 1
  for x in xrange(80):
    m = max([m]+arr[x])
  for y in xrange(45):
    for x in xrange(80):
      arr[x][y] = arr[x][y]*255/m
  f = open( outFile, "w" )
  f.write( "P2\n80 45\n255\n" )
  for y in xrange(45):
    for x in xrange(80):
      f.write( "%d " % arr[x][y] )
    f.write( "\n" )
  f.close()


def combinePgm( prefix, columns, rows, scale=3 ):
  out = open( prefix+"_%dx%d.pgm" % (columns, rows), "w" )
  out.write( "P2\n%d %d\n255\n" % (80*columns*scale,45*rows*scale) )

  for row in xrange(rows):
    farr = [open( prefix + "%03d.pgm" % (index+columns*row,) ) for index in range(columns)]
    for header in xrange(3):
      for f in farr:
        print f.readline().strip()

    for y in xrange(45):
      scan = []
      for f in farr:
        scan += f.readline().split()
      for i in xrange(scale):
        for s in scan:
          for j in xrange(scale):
            out.write( s+" " )
        out.write('\n')

  out.close()


if __name__ == "__main__":
  if len(sys.argv) < 3:
    print __doc__
    sys.exit(2)

  filename = sys.argv[1]
  prefix = sys.argv[2]
  step = 7
  gen = generator( filename )
  for index in xrange(16):
    print index
    mv2pgm( gen, prefix+"%03d.pgm" % index, step )

  combinePgm( prefix, 4, 4 )

