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

  def testSignedGolomb( self ):
    self.assertEqual( BitStream('\xFF').signedGolomb(), 0 )
    self.assertEqual( BitStream(binData('010')).signedGolomb(), 1 )
    self.assertEqual( BitStream(binData('011')).signedGolomb(), -1 )
    self.assertEqual( BitStream(binData('0001000')).signedGolomb(), 4 )

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
    #self.assertEqual( bs.tab( table, maxBits=4 ), None ) # disabled, tired of removing sys.exit()

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

    # failing "sector 51"
    bs = BitStream( buf=binData("00110 000 1 11 0010 011 11 11 11" ) )
    self.assertEqual( residual( bs, nC=3 ), 5 )
    self.assertEqual( bs.index, 1077959-1077935 )

    # uncompleted table MB=115 (was bug in  runBeforeMapping[6])
    bs = BitStream( buf=binData("011 10 0100 101 1" ) )
    self.assertEqual( residual( bs, nC=3 ), 2 )
    self.assertEqual( bs.index, 1082430-1082418 )

    # extra shift MB=2085
    bs = BitStream( buf=binData("000000111 01 11 0010 111 1 0 " ) )
    self.assertEqual( residual( bs, nC=1 ), 3 )
    self.assertEqual( bs.index, 1191109-1191087 )

  def testLevelTabs( self ):
    """
@1877578 Luma # c & tr.1s vlc=1 #c=7 #t1=3                      000100 (  4) 
@1877584 Luma trailing ones sign (2,0)                             001 (  1) 
@1877587 Luma lev (2,0) k=3 vlc=0                                   01 (  1) 
@1877589 Luma lev (2,0) k=2 vlc=1                                 0010 (  2) 
@1877593 Luma lev (2,0) k=1 vlc=1                                00010 (  2) 
@1877598 Luma lev (2,0) k=0 vlc=2                                 0110 (  6) 
@1877602 Luma totalrun (2,0) vlc=6                                 011 (  3) 
@1877605 Luma run (6,0) k=6 vlc=3                                   11 (  3) 
@1877607 Luma run (5,0) k=5 vlc=3                                   10 (  2) 
@1877609 Luma run (4,0) k=4 vlc=2                                   01 (  1) 
@1877611 Luma run (3,0) k=3 vlc=0                                    1 (  1) 
@1877612 Luma run (2,0) k=2 vlc=0                                    1 (  1) 
@1877613 Luma run (1,0) k=1 vlc=0                                    0 (  0) """    
    bs = VerboseWrapper( BitStream( buf=binData("000100 001 01 0010 00010 0110 011 11 10 01 1 1 0" ) ), 1877578 )
    self.assertEqual( residual( bs, nC=2 ), 7 )
    self.assertEqual( bs.worker.index, 1877614-1877578 )
    
  def testLevelTabs2( self ):
    """ frame0091.bin MB: 3582
@1557490 Luma # c & tr.1s vlc=0 #c=6 #t1=3                    00000100 (  4) 
@1557498 Luma trailing ones sign (2,3)                             100 (  4) 
@1557501 Luma lev (2,3) k=2 vlc=0                               000001 (  1) 
@1557507 Luma lev (2,3) k=1 vlc=1                                   11 (  3) 
@1557509 Luma lev (2,3) k=0 vlc=1                                  010 (  2) 
@1557512 Luma totalrun (2,3) vlc=5                                 101 (  5) 
@1557515 Luma run (5,3) k=5 vlc=3                                  000 (  0) """
    bs = VerboseWrapper( BitStream( buf=binData("00000100 100 000001 11 010 101 000" ) ), 1557490 )
    self.assertEqual( residual( bs, nC=1 ), 6 )
    self.assertEqual( bs.worker.index, 1557518-1557490 )
    """
@1557518 Luma # c & tr.1s vlc=1 #c=3 #t1=0                     0000111 (  7) 
@1557525 Luma lev (3,3) k=2 vlc=0                               000001 (  1) 
@1557531 Luma lev (3,3) k=1 vlc=2                                  100 (  4) 
@1557534 Luma lev (3,3) k=0 vlc=2                                 0100 (  4)
@1557538 Luma totalrun (3,3) vlc=2                                0101 (  5) """
    bs = VerboseWrapper( BitStream( buf=binData("0000111 000001 100 0100 0101" ) ), 1557518 )
    self.assertEqual( residual( bs, nC=3 ), 3 )
    self.assertEqual( bs.worker.index, 1557542-1557518 )


  def testMedian( self ):
    self.assertEqual( median( None, None, None), 0 )
    self.assertEqual( median( 3, None, None), 3 )
    self.assertEqual( median( 3, 13, 5), 5 )
    self.assertEqual( median( -3, 11, None), 0 )


  def testLum16DC( self ):
    """
*********** POC: 2 (I/P) MB: 48 Slice: 0 Type 0 **********
@1184157 mb_skip_run                                                 1 (  0) 
@1184158 mb_type                                               0001000 (  7) 
@1184165 intra_chroma_pred_mode                                    010 (  1) 
@1184168 mb_qp_delta                                                 1 (  0) 
@1184169 Lum16DC # c & tr.1s vlc=0 #c=4 #t1=3                   000011 (  3) 
@1184175 Lum16DC trailing ones sign (0,0)                          111 (  7) 
@1184178 Lum16DC lev (0,0) k=0 vlc=0                                01 (  1) 
@1184180 Lum16DC totalrun (0,0) vlc=3                              100 (  4) 
@1184183 Lum16DC run (3,0) k=3 vlc=5                                11 (  3) 
@1184185 Lum16DC run (2,0) k=2 vlc=5                               000 (  0) 
@1184188 Lum16DC run (1,0) k=1 vlc=4                               011 (  3) """
    bs = VerboseWrapper( BitStream( buf=binData("0001000 010 1 000011 111 01 100 11 000 011" ) ), startOffset=1184158 ) # without skip
    left = [[None]*4, [None]*2, [None]*2]
    up = [[None]*4, [None]*2, [None]*2]
    print "testLum16DC START"
    macroblockLayer( bs, left, up, verbose=True )
    print "testLum16DC END"
    self.assertEqual( bs.worker.index, 1184191-1184158 )

    """
*********** POC: 2 (I/P) MB: 206 Slice: 0 Type 0 **********
@1198123 mb_skip_run                                                 1 (  0) 
@1198124 mb_type                                                 00111 (  6) 
@1198129 intra_chroma_pred_mode                                    011 (  2) 
@1198132 mb_qp_delta                                             00101 ( -2) 
@1198137 Lum16DC # c & tr.1s vlc=0 #c=5 #t1=3                  0000100 (  4) 
@1198144 Lum16DC trailing ones sign (0,0)                          011 (  3) 
@1198147 Lum16DC lev (0,0) k=1 vlc=0                                 1 (  1) 
@1198148 Lum16DC lev (0,0) k=0 vlc=1                                11 (  3) 
@1198150 Lum16DC totalrun (0,0) vlc=4                             0100 (  4) 
@1198154 Lum16DC run (4,0) k=4 vlc=0                                 1 (  1) 
@1198155 Lum16DC run (3,0) k=3 vlc=0                                 1 (  1) 
@1198156 Lum16DC run (2,0) k=2 vlc=0                                 1 (  1) 
@1198157 Lum16DC run (1,0) k=1 vlc=0                                 0 (  0) """
    bs = VerboseWrapper( BitStream( buf=binData("00111 011 00101 0000100 011  1 11 0100 1 1 1  0" ) ), startOffset=1198124 ) # without skip
    left = [[None]*4, [None]*2, [None]*2]
    up = [[None]*4, [None]*2, [None]*2]
    print "testLum16DC START"
    macroblockLayer( bs, left, up, verbose=True )
    print "testLum16DC END"
    self.assertEqual( bs.worker.index, 1198158-1198124 )


    """
*********** POC: 2 (I/P) MB: 368 Slice: 0 Type 0 **********
@1211250 mb_skip_run                                                 1 (  0) 
@1211251 mb_type                                             000010101 ( 20) 
@1211260 intra_chroma_pred_mode                                    011 (  2) 
@1211263 mb_qp_delta                                             00101 ( -2) 
@1211268 Lum16DC # c & tr.1s vlc=0 #c=4 #t1=3                   000011 (  3) 
@1211274 Lum16DC trailing ones sign (0,0)                          100 (  4) 
@1211277 Lum16DC lev (0,0) k=0 vlc=0                                01 (  1) 
@1211279 Lum16DC totalrun (0,0) vlc=3                              110 (  6) 
@1211282 Lum16DC run (3,0) k=3 vlc=3                                10 (  2) 
@1211284 Lum16DC run (2,0) k=2 vlc=2                                11 (  3) 
@1211286 Lum16DC run (1,0) k=1 vlc=2                                10 (  2) 
@1211288 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1211289 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1211290 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1211291 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1211292 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1211293 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1211294 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1211295 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1211296 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1211297 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1211298 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1211299 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1211300 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1211301 Lum16AC # c & tr.1s vlc=0 #c=1 #t1=1                       01 (  1) 
@1211303 Lum16AC trailing ones sign (3,2)                            1 (  1) 
@1211304 Lum16AC totalrun (3,2) vlc=0                                1 (  1) 
@1211305 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1211306 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1)"""
    print "Lum16AC START"
    bs = VerboseWrapper( BitStream( buf=binData("000010101 011 00101 000011 100 01 110 10 11 10 1 1 1 1 1 1 1 1 1 1 1 1 1 01 1 1 1 1" ) ),
        startOffset=1211251 ) # without skip
    left = [[None]*4, [None]*2, [None]*2]
    up = [[None]*4, [None]*2, [None]*2]
    macroblockLayer( bs, left, up, verbose=True )
    self.assertEqual( bs.worker.index, 1211307-1211251 )
    print "Lum16AC END"

    """
*********** POC: 2 (I/P) MB: 1250 Slice: 0 Type 0 **********
@1283940 mb_skip_run                                                 1 (  0) 
@1283941 mb_type                                             000011010 ( 25) 
@1283950 intra_chroma_pred_mode                                      1 (  0) 
@1283951 mb_qp_delta                                                 1 (  0) 
@1283952 Lum16DC # c & tr.1s vlc=0 #c=5 #t1=3                  0000100 (  4) 
@1283959 Lum16DC trailing ones sign (0,0)                          101 (  5) 
@1283962 Lum16DC lev (0,0) k=1 vlc=0                                 1 (  1) 
@1283963 Lum16DC lev (0,0) k=0 vlc=1                                11 (  3) 
@1283965 Lum16DC totalrun (0,0) vlc=4                              110 (  6) 
@1283968 Lum16DC run (4,0) k=4 vlc=3                                01 (  1) 
@1283970 Lum16DC run (3,0) k=3 vlc=1                                 1 (  1) 
@1283971 Lum16DC run (2,0) k=2 vlc=1                                00 (  0) 
@1283973 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1283974 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1283975 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1283976 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1283977 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1283978 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1283979 Lum16AC # c & tr.1s vlc=0 #c=1 #t1=1                       01 (  1) 
@1283981 Lum16AC trailing ones sign (2,1)                            0 (  0) 
@1283982 Lum16AC totalrun (2,1) vlc=0                              011 (  3) 
@1283985 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1283986 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1283987 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1283988 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1283989 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1283990 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1283991 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1283992 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1283993 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1283994 ChrDC # c & tr.1s  #c=0 #t1=0                              01 (  1) 
@1283996 ChrDC # c & tr.1s  #c=1 #t1=1                               1 (  1) 
@1283997 ChrDC trailing ones sign (0,0)                              0 (  0) 
@1283998 ChrDC totalrun (0,0) vlc=0                                001 (  1) """
    print "Lum16ACDC START"
    bs = VerboseWrapper( BitStream( buf=binData("000011010 1 1 0000100 101 1 11 110 01 1 00 1 1 1 1 1 1 01 0 011 1 1 1 1 1 1 1 1 1 01 1 0 001" ) ),
        startOffset=1283941 ) # without skip
    left = [[None]*4, [None]*2, [None]*2]
    up = [[None]*4, [None]*2, [None]*2]
    macroblockLayer( bs, left, up, verbose=True )
    self.assertEqual( bs.worker.index, 1284001-1283941 )
    print "Lum16ACDC END"

  def testLum16DCWithLeftUp( self ):
    """
*********** POC: 2 (I/P) MB: 1292 Slice: 0 Type 0 **********
@1285939 mb_skip_run                                                 1 (  0) 
@1285940 mb_type                                             000010011 ( 18) 
@1285949 intra_chroma_pred_mode                                    011 (  2) 
@1285952 mb_qp_delta                                             00100 (  2) 
@1285957 Lum16DC # c & tr.1s vlc=0 #c=8 #t1=1            0000000001010 ( 10) 
@1285970 Lum16DC trailing ones sign (0,0)                            0 (  0) 
@1285971 Lum16DC lev (0,0) k=6 vlc=0                                01 (  1) 
@1285973 Lum16DC lev (0,0) k=5 vlc=1                                11 (  3) 
@1285975 Lum16DC lev (0,0) k=4 vlc=1                                10 (  2) 
@1285977 Lum16DC lev (0,0) k=3 vlc=1                                11 (  3) 
@1285979 Lum16DC lev (0,0) k=2 vlc=1                                10 (  2) 
@1285981 Lum16DC lev (0,0) k=1 vlc=1                                11 (  3) 
@1285983 Lum16DC lev (0,0) k=0 vlc=1                               011 (  3) 
@1285986 Lum16DC totalrun (0,0) vlc=7                               10 (  2) 
@1285988 Lum16DC run (7,0) k=7 vlc=4                               000 (  0) 
@1285991 Lum16AC # c & tr.1s vlc=0 #c=1 #t1=1                       01 (  1) 
@1285993 Lum16AC trailing ones sign (0,0)                            1 (  1) 
@1285994 Lum16AC totalrun (0,0) vlc=0                                1 (  1) 
@1285995 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1285996 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1285997 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1285998 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1285999 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1286000 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1286001 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1286002 Lum16AC # c & tr.1s vlc=0 #c=1 #t1=1                       01 (  1) 
@1286004 Lum16AC trailing ones sign (0,2)                            0 (  0) 
@1286005 Lum16AC totalrun (0,2) vlc=0                              011 (  3) 
@1286008 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1286009 Lum16AC # c & tr.1s vlc=1 #c=2 #t1=2                      011 (  3) 
@1286012 Lum16AC trailing ones sign (0,3)                           10 (  2) 
@1286014 Lum16AC totalrun (0,3) vlc=1                              100 (  4) 
@1286017 Lum16AC run (1,3) k=1 vlc=2                                11 (  3) 
@1286019 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1286020 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1286021 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1286022 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@1286023 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) """
# NOTE - When parsing for Intra16x16DCLevel, the values nA and nB are based on the number of non-zero 
# transform coefficient levels in adjacent 4x4 blocks and not on the number of non-zero DC transform coefficient 
# levels in adjacent 16x16 blocks. 
# ... that's probably it (???). Sum?
    print "Lum16AC-2 START"
    bs = VerboseWrapper( BitStream( buf=binData("000010011 011 00100 0000000001010 1 01 11 10 11 10 11 011 10 000 01 1 1 1 1 1 1 1 1 1\
        01 0 011 1 011 10 100 11 1 1 1 1 1" ) ),
        startOffset=1285940 ) # without skip
    left = [[0, 0, 0, 3], [0, 0], [0, 0]]
    up = [[0, 0, 0, 0], [0, 0], [0, 0]] # maybe it is not correct??
    # mb_type 18 = I_16x16_1_1_1 Intra_16x16  1  1  15
    macroblockLayer( bs, left, up, verbose=True )
    self.assertEqual( bs.worker.index, 1286024-1285940 )
    print "Lum16AC-2 END"


if __name__ == "__main__":
  unittest.main() 
  
