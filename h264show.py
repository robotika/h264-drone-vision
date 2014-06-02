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
from pave import PaVE, isIFrame, frameEncodedWidth, frameEncodedHeight

def h264show( filename ):
  print cvideo.init()
  img = np.zeros([720,1280,3], dtype=np.uint8)
  missingIFrame = True
  pave = PaVE()
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
  filename = sys.argv[1]
  h264show( filename )

