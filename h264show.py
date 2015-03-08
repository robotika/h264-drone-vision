#!/usr/bin/python
"""
  Play video together with H264 motion vectors
  usage:
     ./h264show.py <pave video> [<delay=100>]
"""
import sys
from h264 import parseFrame, setVerbose

import cvideo  # Heidi project
import cv2
import numpy as np

# where to move this?!
sys.path.append( "../heidi" ) 
#from pave import PaVE, isIFrame, frameEncodedWidth, frameEncodedHeight

# fake PaVE
class PaVE:
  def __init__( self ):
    self.buf = ""

  def append( self, data ):
    self.buf += data

  def extract( self ):
    if len(self.buf) < 5:
      return "", ""
    assert self.buf[:4] == "\0\0\0\x01", [hex(ord(x)) for x in self.buf[:4]]
    frameType = 0x1F & ord(self.buf[4])
    for i in xrange(1, len(self.buf)-4):
      if self.buf[i:i+4] == "\0\0\0\x01": # ignoring escape char for a moment
        print hex(ord(self.buf[i+4]))        
        if frameType in [1, 5]:
          break
        frameType = 0x1F & ord(self.buf[i+4])
    else:
      return "", ""
    ret = self.buf[:i]
    sys.stderr.write( "%d\n" % len(ret) )
    self.buf = self.buf[i:]
    return (640, 368, 1), ret # HACK, parseSPS required


def frameEncodedWidth(header):
  return header[0]

def frameEncodedHeight(header):
  return header[1]

def isIFrame(header):
  return header[2]



def h264show( filenames ):
  print cvideo.init()
  img = np.zeros([720,1280,3], dtype=np.uint8)
  missingIFrame = True
  pave = PaVE()
  for filename in filenames:
    pave.append( open( filename, "rb" ).read() )
  header,payload = pave.extract()
  while len(header) > 0:
    w,h = frameEncodedWidth(header), frameEncodedHeight(header)
    if img.shape[0] != h or img.shape[1] != w:
      print img.shape, (w,h)
      img = np.zeros([h,w,3], dtype=np.uint8)
    missingIFrame = missingIFrame and not isIFrame(header)
    if not missingIFrame:
      arr = parseFrame( payload )
      assert cvideo.frame( img, isIFrame(header) and 1 or 0, payload )
      if arr:
        for x,y,mx,my in arr:
          cv2.line( img, (16*x+8,16*y+8), (16*x+8+mx/4,16*y+8+my/4), (0,0,255), 1 )
    cv2.imshow('image', img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
      break
    header,payload = pave.extract()

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print __doc__
    sys.exit(2)
  setVerbose( False )
  filenames = sys.argv[1:]
  h264show( filenames )

