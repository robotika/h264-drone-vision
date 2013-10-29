#!/usr/bin/python
from h264 import *
import unittest

def binData( s ):
  "convert 0/1/<space> string into byte buffer string"
  ret = ""
  mask = 1<<7
  val = 0
  for c in s:
    if c == ' ':
      continue
    if c == '1':
      val += mask
    mask /= 2
    if mask == 0:
      ret += chr(val)
      val = 0
      mask = 1<<7
  if mask != 1<<7:
    ret += chr(val)
  return ret


  return "\xca"

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

  def testBinStr( self ):
    tmp = VerboseWrapper( None )
    self.assertEqual( len(tmp.binStr(2, 14)), 14 )

  def testMix( self ):
    self.assertEqual( mix(None, None), 0 )
    self.assertEqual( mix(13, None), 13 )
    self.assertEqual( mix(None, 5), 5 )
    self.assertEqual( mix(13, 5), 9 )
    self.assertEqual( mix(1, 4), 3 ) # round-up

  def testBinData( self ):
    self.assertEqual( binData("11 0 0 101 0"), "\xCA" )
    self.assertEqual( binData("111"), "\xE0" )

  def testResidual( self ):
    bs = BitStream( buf=binData("01 " ) )
    self.assertEqual( residual( bs, nC=-1 ), 0 )
    self.assertEqual( bs.index, 2 )

    bs = BitStream( buf=binData("11 " ) )
    self.assertEqual( residual( bs, nC=3 ), 0 )
    self.assertEqual( bs.index, 2 )


if __name__ == "__main__":
  unittest.main() 
  
