#!/usr/bin/python
"""
  Navigation from macroblock motion vectors in H.264 codec
"""

from mv2pygame import absPic, averageShift, subShift, estMovement, compensateMovement, THRESHOLD # TODO refactoring here

def quadrantMotion( mv ):
  "calculate average motion for each quadrant"
  # TODO move this back to h264 repository h264nav.py ??
  pic = absPic( [((x,y), (mx,my)) for x,y,mx,my in mv] )
  shift = averageShift( pic )
  pic = subShift( pic, shift )
  coefs = estMovement( pic )
  print coefs[0][0], coefs[1][0]
  pic = compensateMovement( pic, coefs )
  count = 0
  left,right,up,down = 0,0,0,0 # obstacle at
  for x in xrange(80):
    for y in xrange(45):
      mx, my = pic[x][y]
      if mx != 0 and my != 0:
        d = abs(mx)+abs(my)
        if d > THRESHOLD:
          count += 1
          if x < 40:
            left += 1
          else:
            right += 1
          if y < 22:
            up += 1
          else:
            down += 1
  return left, right, up, down # TODO revise to LT,RT,LB,RB quadrants


