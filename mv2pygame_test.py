from mv2pygame import *
import unittest

class Mv2PygameTest( unittest.TestCase ): 
  def testAddPic( self ):
    pic1 = [[(1,1),(2,3)]]
    self.assertEqual( addPic(pic1,pic1), [[(2,2),(4,6)]])

  def testEstMovement( self ):
    pic = [[(0,0), (-1,0)],[(0,1),(0,0)]]
    self.assertEqual( estMovement(pic), ((0.5,0), (-0.5,0)) )

  def testLeastQuare( self ):
    pic = eval(open("tmp126.txt").read())
    (k1x,k0x),(k1y,k0y) = estMovement( pic )
#    print -16*k0x/k1x, -16*k0y/k1y

  def testCompensateMovement( self ):
    self.assertEqual( compensateMovement( [[(0,1),(2,3)]], ((0,0),(0,0)) ),
        [[(0,1),(2,3)]] )
#    self.assertEqual( compensateMovement( [[(0,1),(2,3)]], ((2,1),(3,-1)) ),
#        [[(1,1-1),(2+2+1,3)]] )

  def testAverageShift( self ):
    self.assertEqual( averageShift( [[(1,2),(3,4)]] ), (2,3) )
    self.assertEqual( subShift( [[(1,2),(3,4)]], (2,3) ), [[(-1,-1),(1,1)]] )
    

if __name__ == "__main__":
  unittest.main() 

