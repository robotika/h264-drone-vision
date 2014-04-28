"""
  I-Frame shift decoded from P-frames (camera pointing down to ground)
  usage:
      img_shift.py <frames directory> [TODO use video file instead]
"""
import sys
import os
from h264 import parseFrame, setVerbose
from collections import defaultdict

verbose=False

def histogram( arr, size=10 ):
  d = defaultdict( int )
  for x in arr:
    d[x/size] += 1
  return d


if __name__ == "__main__":
  if len(sys.argv) < 2:
    print __doc__
    sys.exit(2)

  setVerbose(False)
#  for filename in os.listdir( sys.argv[1] ):
  for i in xrange(150,165):
    filename = "frame%04d.bin" % i
    frameData = open( sys.argv[1] + os.sep + filename, "rb" ).read()
    arr = parseFrame( frameData )
    if arr != None and arr != []:
      x = [mx for x,y,mx,my in arr]
      xRange = min( x ), max( x )
      print filename, len(arr), xRange, histogram(x)

