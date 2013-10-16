"""
  convert mv vectors from H.264 codec to pygame image
  usage:
      mv2pygame.py <input file>
"""
import sys
from mv2pgm import pictureOffsetG
from collections import defaultdict
from itertools import izip

import pygame
from pygame.locals import * 

LOW_THRESHOLD = 10
THRESHOLD = 100 #50

def absPic( relList ):
  arr=[[(0,0) for i in range(45)] for j in range(80)]
  for (x,y), val in relList:
    arr[x][y] = val
  return arr

def zeroPic():
  return absPic([])

def addPic( pic1, pic2 ):
  "return sumup picture"
  pic = []
  for row1,row2 in izip(pic1,pic2):
    row = []
    for (x1,y1),(x2,y2) in izip(row1,row2):
      row.append( (x1+x2,y1+y2) )
    pic.append( row )
  return pic


def histogram( pictureArray, verbose=False ):
  hist = defaultdict(int)
  for row in pictureArray:
    for (mx,my) in row:
      hist[ (mx,my) ] += 1
      if verbose:
        print "%d\t%d" % (mx,my)
      assert mx%2 == 0 and my %2 == 0, str( (mx,my) )
  return hist

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

def printDict( d ):
  print 1000, [(k,v) for k,v in d.items() if v >= 1000]
  print 100, [(k,v) for k,v in d.items() if 1000 > v >= 100]
  print 10, [(k,v) for k,v in d.items() if 100 > v >= 10]
#  print 1, [(k,v) for k,v in d.items() if 10 > v >= 1]
  print

def scr( x, y ):
  return ( 8+x*16, 8+y*16 )

def drawArrows( foreground, left, right, up, down ):
  "arrow based on _obstacles_ statistics"
  print "ARROW", left, right, up, down
  MAX_COUNT = 1000
  MIN_STEP = 100
  assert left+right == up + down, (left, right, up, down)
  if left+right > MAX_COUNT:
    return # too red, no idea what to do
  if down > up + MIN_STEP:
    # move up
    pygame.draw.line( foreground, (0,255,0), scr(40,10), scr(45,20), 10) 
    pygame.draw.line( foreground, (0,255,0), scr(40,10), scr(35,20), 10) 
  if up > down + MIN_STEP:
    # move down
    pygame.draw.line( foreground, (0,255,0), scr(40,35), scr(45,25), 10) 
    pygame.draw.line( foreground, (0,255,0), scr(40,35), scr(35,25), 10) 
  if right > left + MIN_STEP:
    # move left
    pygame.draw.line( foreground, (0,255,0), scr(10,22), scr(20,27), 10) 
    pygame.draw.line( foreground, (0,255,0), scr(10,22), scr(20,17), 10) 
  if left > right + MIN_STEP:
    # move right
    pygame.draw.line( foreground, (0,255,0), scr(70,22), scr(60,27), 10) 
    pygame.draw.line( foreground, (0,255,0), scr(70,22), scr(60,17), 10) 


def pygameTest( picGen, filename=None ):
  size = (16*80,16*45)
  pygame.init()
  screen = pygame.display.set_mode(size)
  background = pygame.Surface(screen.get_size()) 
  background.set_colorkey((0,0,0)) 
  foreground = pygame.Surface(screen.get_size())
  foreground.set_colorkey((0,0,0)) 
  screen.blit(background, (0, 0)) 
  for pic, index in picGen: 
    foreground = pygame.image.load("m:\\git\\cvdrone\\build\\vs2008\\img_%04d.jpg" % index )
#    if index/3 == 126:
#      open("tmp126.txt", "w").write( str(pic) )
    shift = averageShift( pic )
    pic = subShift( pic, shift )
    coefs = estMovement( pic )
    print index/3, coefs[0][0], coefs[1][0]
    pic = compensateMovement( pic, coefs )
    count = 0
    left,right,up,down = 0,0,0,0 # obstacle at
    for x in xrange(80):
      for y in xrange(45):
        mx, my = pic[x][y]
        if mx != 0 and my != 0: # and x % 2 == 0 and y % 2 == 0:
          d = abs(mx)+abs(my)
          if d > THRESHOLD:
            pygame.draw.circle( foreground, (255,0,0), scr(x,y), 10 )
            count += 1
            if x < 40:
              left += 1
            else:
              right += 1
            if y < 22:
              up += 1
            else:
              down += 1
          elif d > LOW_THRESHOLD:
            pygame.draw.circle( foreground, (255,0,0), scr(x,y), 3 )

#          pygame.draw.circle( foreground, (255,0,0), scr(x-mx/64,y-my/64), 3 )
          pygame.draw.line( foreground, (255,255,0), scr(x,y), scr(x+mx/64.0,y+my/64.0),2) 
#          pygame.draw.line( foreground, (255,255,0), scr(x,y), scr(x-mx/64.0,y-my/64.0),2) 
    
    drawArrows( foreground, left, right, up, down )

    pygame.display.set_caption("Index: %d, (%d,%d) - %d" % (index/3, shift[0], shift[1], count) ) 
    if pygame.event.peek([QUIT,KEYDOWN]):
      event = pygame.event.wait()
      while event.type != KEYDOWN:
        print event
        event = pygame.event.wait()
      if event.key in [K_p]:
        print "PAUSE"
        pygame.event.wait()
        print event
        while event.type != KEYDOWN or event.key == K_p:
          print event
          event = pygame.event.wait()
        continue
      if event.type == QUIT:
        break
      if event.type == KEYDOWN:
        if event.key in (K_ESCAPE,K_q):
          break

    filename = "pic/xtest_%04d.jpg" % (index/3)
    if filename:
      pygame.image.save( foreground, filename )
    screen.blit(background, (0, 0)) 
    screen.blit(foreground, (0, 0))
    pygame.display.flip()
    pygame.time.wait(1)

def gen3pic( filename ):
  pic = zeroPic()
  for picList,index in izip(pictureOffsetG(filename), xrange(1000)):
    pic = addPic( pic, absPic( picList ) )
    if index % 3 == 2:
      yield pic, index
      pic = zeroPic()

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print __doc__
    sys.exit(2)

  filename = sys.argv[1]
  pygameTest( gen3pic(filename) )
#      pygameTest( pic, "pic/test_%04d.png" % index )
#      printDict( histogram( pic ) )


