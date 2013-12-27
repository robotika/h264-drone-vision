#!/usr/bin/python
"""
  Navigation from macroblock motion vectors in H.264 codec
"""

THRESHOLD = 100 #50

def absPic( relList ):
  arr=[[(0,0) for i in range(45)] for j in range(80)]
  for (x,y), val in relList:
    arr[x][y] = val
  return arr

def averageShift( pictureArray ):
  count, sumX, sumY = 0, 0, 0
  for row in pictureArray:
    for (mx,my) in row:
      sumX += mx
      sumY += my
      count += 1
  if count > 0:
    return sumX/count, sumY/count
  return 0, 0

def subShift( pic, (shiftX, shiftY) ):
  for x in xrange(len(pic)):
    for y in xrange(len(pic[x])):
      dx,dy = pic[x][y]
      pic[x][y] = dx-shiftX, dy-shiftY
  return pic


class LeastSquare:
  def __init__( self ):
    self.sumXX = 0
    self.sumXY = 0
    self.sumX = 0
    self.sumY = 0
    self.count = 0

  def add( self, x, y ):
    self.sumXX += x*x
    self.sumXY += x*y
    self.sumX  += x
    self.sumY += y
    self.count += 1

  def coef( self ):
    det = float(self.count*self.sumXX - self.sumX*self.sumX)
    return (self.count*self.sumXY - self.sumX*self.sumY)/det, \
           (self.sumXX*self.sumY - self.sumX*self.sumXY)/det


def estMovement( pic ):
  "estimage movement from vector array"
  lsX = LeastSquare()
  lsY = LeastSquare()
  for x in xrange(len(pic)):
    for y in xrange(len(pic[x])):
      dx,dy = pic[x][y]
      lsX.add( x, dy )
      lsY.add( y, dx )
  return lsX.coef(), lsY.coef()

def compensateMovement( pic, coefs ):
  (k1x,k0x),(k1y,k0y) = coefs
  for x in xrange(len(pic)):
    for y in xrange(len(pic[x])):
      dx,dy = pic[x][y]
      pic[x][y] = int(dx-k1y*y-k0y),int(dy-k1x*x-k0x)
  return pic


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


