#!/usr/bin/python
from h264 import *
import unittest

class H264Test( unittest.TestCase ): 
  def testBit( self ):
    self.assertEqual( BitStream('\xFF').bit(), 1 )

  def testGolomb( self ):
    self.assertEqual( BitStream('\xFF').golomb(), 0 )
    self.assertEqual( BitStream('\x5F' ).golomb(), 1 ) 
    self.assertEqual( BitStream('\x0F\x00' ).golomb(), 29 ) 

  def testBitStream( self ):
    bs = BitStream( buf='\xBF' )
    self.assertEqual( bs.bits( 2 ), 2 )
    self.assertEqual( bs.bits( 3 ), 7 )
    self.assertEqual( bs.golomb(), 0 )
    self.assertEqual( bs.bit(), 1 )

  def testAlignedByte( self ):
    bs = BitStream( buf="AHOJ" )
    self.assertEqual( bs.alignedByte(), ord('A') )
    bs.bit()
    self.assertEqual( bs.alignedByte(), ord('O') )

  def testTab( self ):
    bs = BitStream( buf='\x50' )
    table = { '01':"test01" }
    self.assertEqual( bs.tab( table ), "test01" )
    self.assertEqual( bs.tab( table ), "test01" )
    self.assertEqual( bs.tab( table, maxBits=4 ), None )

if __name__ == "__main__":
  unittest.main() 
  