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


  def testLevelTabs3( self ):
    """ frame0183.bin MB: 40
@972253 Luma # c & tr.1s vlc=2 #c=6 #t1=1                       001110 ( 14) 
@972259 Luma trailing ones sign (3,0)                                1 (  1) 
@972260 Luma lev (3,0) k=4 vlc=0                                    01 (  1) 
@972262 Luma lev (3,0) k=3 vlc=1                                   010 (  2) 
@972265 Luma lev (3,0) k=2 vlc=1                                 00010 (  2) 
@972270 Luma lev (3,0) k=1 vlc=2                                  0100 (  4) 
@972274 Luma lev (3,0) k=0 vlc=2                                000110 (  6) 
@972280 Luma totalrun (3,0) vlc=5                                  111 (  7) 
@972283 Luma run (5,0) k=5 vlc=1                                    01 (  1) 
@972285 Luma run (4,0) k=4 vlc=0                                     1 (  1) 
@972286 Luma run (3,0) k=3 vlc=0                                     0 (  0) """
    bs = BitStream( buf=binData("001110 1 01 010 00010 0100 000110 111 01 1 0" ) )
    self.assertEqual( residual( bs, nC=4 ), 6 )
    self.assertEqual( bs.index, 972287-972253 )   


  def testLevelTabs4( self ):
    """ frame0187.bin MB: 24
@1365333 Luma # c & tr.1s vlc=1 #c=1 #t1=0                      001011 ( 11) 
@1365339 Luma lev (0,0) k=0 vlc=0                      0000000000000010001 ( 17) 
@1365358 Luma totalrun (0,0) vlc=0                                   1 (  1) """
    bs = BitStream( buf=binData("001011 0000000000000010001 1" ) )
    self.assertEqual( residual( bs, nC=2 ), 1 )
    self.assertEqual( bs.index, 1365359-1365333 )   

  def testLevelTabs5( self ):
    """ frame0228.bin MB: 30
@2742801 Luma # c & tr.1s vlc=2 #c=6 #t1=3                        1001 (  9) 
@2742805 Luma trailing ones sign (3,0)                             111 (  7) 
@2742808 Luma lev (3,0) k=2 vlc=0                      0000000000000010010 ( 18) 
@2742827 Luma lev (3,0) k=1 vlc=2                                  110 (  6) 
@2742830 Luma lev (3,0) k=0 vlc=2                              0000100 (  4) 
@2742837 Luma totalrun (3,0) vlc=5                                 110 (  6) 
@2742840 Luma run (5,0) k=5 vlc=2                                   11 (  3) 
@2742842 Luma run (4,0) k=4 vlc=2                                   10 (  2) 
@2742844 Luma run (3,0) k=3 vlc=1                                   00 (  0) """
    bs = BitStream( buf=binData("1001 111 0000000000000010010 110 0000100 110 11 10 00" ) )
    self.assertEqual( residual( bs, nC=7 ), 6 )
    self.assertEqual( bs.index, 2742846-2742801 )   

  def testLevelTabs15( self ):
    """ frame0305.bin MB: 71
@2007284 Luma # c & tr.1s vlc=2 #c=5 #t1=3                        1010 ( 10) 
@2007288 Luma trailing ones sign (3,0)                             011 (  3) 
@2007291 Luma lev (3,0) k=1 vlc=0                                    1 (  1) 
@2007292 Luma lev (3,0) k=0 vlc=1                      0000000000000001000000000001 (4097) 
@2007320 Luma totalrun (3,0) vlc=4                                0100 (  4) 
@2007324 Luma run (4,0) k=4 vlc=0                                    1 (  1) 
@2007325 Luma run (3,0) k=3 vlc=0                                    0 (  0)"""
    bs = BitStream( buf=binData("1010 011 1 0000000000000001000000000001 0100 1 0" ) )
    self.assertEqual( residual( bs, nC=4 ), 5 )
    self.assertEqual( bs.index, 2007326-2007284 )   

  def testMedian( self ):
    self.assertEqual( median( None, None, None), 0 )
    self.assertEqual( median( 3, None, None), 3 )
    self.assertEqual( median( 3, 13, 5), 5 )
    self.assertEqual( median( -3, 11, None), 0 )
    self.assertEqual( median( None, 4, None), 4 ) # frame=113, x=0, y=16
    self.assertEqual( median( None, None, 13), 13 ) # not detected yet
    self.assertEqual( median( None, 0, 0), 0 ) # bug
    self.assertEqual( median( None, 14, 16), 14 )


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
    macroblockLayer( bs, left, up )
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
    macroblockLayer( bs, left, up )
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
    macroblockLayer( bs, left, up )
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
    macroblockLayer( bs, left, up )
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
    macroblockLayer( bs, left, up )
    self.assertEqual( bs.worker.index, 1286024-1285940 )
    print "Lum16AC-2 END"

  def testBlockType22( self ):
    # no idea why it required ChrDC at the end
    """
*********** POC: 56 (I/P) MB: 1201 Slice: 0 Type 0 **********
@4601750 mb_skip_run                                                 1 (  0) 
@4601751 mb_type                                             000010111 ( 22) 
@4601760 intra_chroma_pred_mode                                    011 (  2) 
@4601763 mb_qp_delta                                         000010110 ( 11) 
@4601772 Lum16DC # c & tr.1s vlc=1 #c=4 #t1=3                     0100 (  4) 
@4601776 Lum16DC trailing ones sign (0,0)                          001 (  1) 
@4601779 Lum16DC lev (0,0) k=0 vlc=0                                 1 (  1) 
@4601780 Lum16DC totalrun (0,0) vlc=3                             0010 (  2) 
@4601784 Lum16DC run (3,0) k=3 vlc=6                               011 (  3) 
@4601787 Lum16DC run (2,0) k=2 vlc=4                                10 (  2) 
@4601789 Lum16DC run (1,0) k=1 vlc=3                                11 (  3) 
@4601791 Lum16AC # c & tr.1s vlc=1 #c=1 #t1=1                       10 (  2) 
@4601793 Lum16AC trailing ones sign (0,0)                            1 (  1) 
@4601794 Lum16AC totalrun (0,0) vlc=0                            00011 (  3) 
@4601799 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@4601800 Lum16AC # c & tr.1s vlc=0 #c=2 #t1=2                      001 (  1) 
@4601803 Lum16AC trailing ones sign (0,1)                           10 (  2) 
@4601805 Lum16AC totalrun (0,1) vlc=1                             0101 (  5) 
@4601809 Lum16AC run (1,1) k=1 vlc=4                               001 (  1) 
@4601812 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@4601813 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@4601814 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@4601815 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@4601816 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@4601817 Lum16AC # c & tr.1s vlc=0 #c=3 #t1=3                    00011 (  3) 
@4601822 Lum16AC trailing ones sign (0,2)                          100 (  4) 
@4601825 Lum16AC totalrun (0,2) vlc=2                              101 (  5) 
@4601828 Lum16AC run (2,2) k=2 vlc=2                                11 (  3) 
@4601830 Lum16AC run (1,2) k=1 vlc=2                                00 (  0) 
@4601832 Lum16AC # c & tr.1s vlc=1 #c=0 #t1=0                       11 (  3) 
@4601834 Lum16AC # c & tr.1s vlc=1 #c=0 #t1=0                       11 (  3) 
@4601836 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@4601837 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@4601838 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@4601839 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@4601840 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@4601841 ChrDC # c & tr.1s  #c=1 #t1=1                               1 (  1) 
@4601842 ChrDC trailing ones sign (0,0)                              1 (  1) 
@4601843 ChrDC totalrun (0,0) vlc=0                                  1 (  1) 
@4601844 ChrDC # c & tr.1s  #c=0 #t1=0                              01 (  1) """
    bs = VerboseWrapper( BitStream( buf=binData("000010111 011 000010110 0100 001 1 0010 011 10 11 10 1 00011 1 001 10 0101 001\
        1 1 1 1 1 00011 100 101 11 00 11 11 1 1 1 1 1 1 1 1 01" ) ),
        startOffset=4601751 ) # without skip
    left = [[0, 0, 0, 0], [0, 0], [0, 0]]
    up = [[3, 0, 0, 0], [0, 0], [0, 0]] # maybe it is not correct??
    # mb_type 18 = I_16x16_1_1_1 Intra_16x16  1  1  15
    macroblockLayer( bs, left, up )
    self.assertEqual( bs.worker.index, 4601846-4601751 )

  def testMbType26( self ):
    # frame0137.bin
    """
*********** POC: 44 (I/P) MB: 959 Slice: 0 Type 0 **********
@2429880 mb_skip_run                                                 1 (  0) 
@2429881 mb_type                                             000011011 ( 26) 
@2429890 intra_chroma_pred_mode                                      1 (  0) 
@2429891 mb_qp_delta                                             00110 (  3) 
@2429896 Lum16DC # c & tr.1s vlc=0 #c=9 #t1=2            0000000001001 (  9) 
@2429909 Lum16DC trailing ones sign (0,0)                           01 (  1) 
@2429911 Lum16DC lev (0,0) k=6 vlc=0                                 1 (  1) 
@2429912 Lum16DC lev (0,0) k=5 vlc=1                               011 (  3) 
@2429915 Lum16DC lev (0,0) k=4 vlc=1                                11 (  3) 
@2429917 Lum16DC lev (0,0) k=3 vlc=1                                10 (  2) 
@2429919 Lum16DC lev (0,0) k=2 vlc=1                               010 (  2) 
@2429922 Lum16DC lev (0,0) k=1 vlc=1                               011 (  3) 
@2429925 Lum16DC lev (0,0) k=0 vlc=1                                11 (  3) 
@2429927 Lum16DC totalrun (0,0) vlc=8                            00001 (  1) 
@2429932 Lum16DC run (8,0) k=8 vlc=6                               111 (  7) 
@2429935 Lum16DC run (7,0) k=7 vlc=6                               110 (  6) 
@2429938 Lum16DC run (6,0) k=6 vlc=5                               010 (  2) 
@2429941 Lum16DC run (5,0) k=5 vlc=1                                 1 (  1) 
@2429942 Lum16DC run (4,0) k=4 vlc=1                                 1 (  1) 
@2429943 Lum16DC run (3,0) k=3 vlc=1                                 1 (  1) 
@2429944 Lum16DC run (2,0) k=2 vlc=1                                01 (  1) 
@2429946 Lum16DC run (1,0) k=1 vlc=0                                 0 (  0) 
@2429947 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@2429948 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@2429949 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@2429950 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@2429951 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@2429952 Lum16AC # c & tr.1s vlc=0 #c=3 #t1=3                    00011 (  3) 
@2429957 Lum16AC trailing ones sign (3,0)                          001 (  1) 
@2429960 Lum16AC totalrun (3,0) vlc=2                              101 (  5) 
@2429963 Lum16AC run (2,0) k=2 vlc=2                                11 (  3) 
@2429965 Lum16AC run (1,0) k=1 vlc=2                                00 (  0) 
@2429967 Lum16AC # c & tr.1s vlc=0 #c=1 #t1=0                   000101 (  5) 
@2429973 Lum16AC lev (2,1) k=0 vlc=0                                 1 (  1) 
@2429974 Lum16AC totalrun (2,1) vlc=0                                1 (  1) 
@2429975 Lum16AC # c & tr.1s vlc=1 #c=2 #t1=2                      011 (  3) 
@2429978 Lum16AC trailing ones sign (3,1)                           11 (  3) 
@2429980 Lum16AC totalrun (3,1) vlc=1                              111 (  7) 
@2429983 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@2429984 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@2429985 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@2429986 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@2429987 Lum16AC # c & tr.1s vlc=0 #c=0 #t1=0                        1 (  1) 
@2429988 Lum16AC # c & tr.1s vlc=0 #c=2 #t1=2                      001 (  1) 
@2429991 Lum16AC trailing ones sign (3,2)                           11 (  3) 
@2429993 Lum16AC totalrun (3,2) vlc=1                              111 (  7) 
@2429996 Lum16AC # c & tr.1s vlc=0 #c=1 #t1=1                       01 (  1) 
@2429998 Lum16AC trailing ones sign (2,3)                            0 (  0) 
@2429999 Lum16AC totalrun (2,3) vlc=0                                1 (  1) 
@2430000 Lum16AC # c & tr.1s vlc=1 #c=3 #t1=2                   001001 (  9) 
@2430006 Lum16AC trailing ones sign (3,3)                           00 (  0) 
@2430008 Lum16AC lev (3,3) k=0 vlc=0                                01 (  1) 
@2430010 Lum16AC totalrun (3,3) vlc=2                              111 (  7) 
@2430013 Lum16AC run (2,3) k=2 vlc=0                                 1 (  1) 
@2430014 Lum16AC run (1,3) k=1 vlc=0                                 0 (  0) 
@2430015 ChrDC # c & tr.1s  #c=0 #t1=0                              01 (  1) 
@2430017 ChrDC # c & tr.1s  #c=2 #t1=2                             001 (  1) 
@2430020 ChrDC trailing ones sign (0,0)                             10 (  2) 
@2430022 ChrDC totalrun (0,0) vlc=1                                  1 (  1) 
@2430023 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                          1 (  1) 
@2430024 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                          1 (  1) 
@2430025 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                          1 (  1) 
@2430026 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                          1 (  1) 
@2430027 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                          1 (  1) 
@2430028 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                          1 (  1) 
@2430029 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                          1 (  1) 
@2430030 ChrAC # c & tr.1s vlc=0 #c=1 #t1=1                         01 (  1) 
@2430032 ChrAC trailing ones sign (3,5)                              1 (  1) 
@2430033 ChrAC totalrun (3,5) vlc=0                                  1 (  1) 

*********** POC: 44 (I/P) MB: 960 Slice: 0 Type 0 **********
@2430034 mb_skip_run """
    bs = VerboseWrapper( BitStream( buf=binData("000011011 1 00110 0000000001001 01 1 011 11 10 010 011 11 00001 111 110 010 1 1 1 01 0 1 1 1 1 1\
        00011 001 101 11 00 000101 1 1 011 11 111 1 1 1 1 1 001 11 111 01 0 1 001001 00 01 111 1 0 01 001 10 1 1 1 1 1 1 1 1 01 1 1" ) ),
        startOffset=2429881 ) # without skip
    left = [[0, 0, 0, 0], [0, 0], [0, 0]]
    up = [[0, 0, 0, 0], [0, 0], [0, 0]]
    macroblockLayer( bs, left, up )
    self.assertEqual( bs.worker.index, 2430034-2429881 )
  
  def testMbType12( self ):
    # frame0141.bin
    """
*********** POC: 52 (I/P) MB: 2950 Slice: 0 Type 0 **********
@2871689 mb_skip_run                                                 1 (  0) 
@2871690 mb_type                                               0001101 ( 12) 
@2871697 intra_chroma_pred_mode                                      1 (  0) 
@2871698 mb_qp_delta                                             00111 ( -3) 
@2871703 Lum16DC # c & tr.1s vlc=0 #c=7 #t1=3                000000100 (  4) 
@2871712 Lum16DC trailing ones sign (0,0)                          101 (  5) 
@2871715 Lum16DC lev (0,0) k=3 vlc=0                                 1 (  1) 
@2871716 Lum16DC lev (0,0) k=2 vlc=1                                11 (  3) 
@2871718 Lum16DC lev (0,0) k=1 vlc=1                                10 (  2) 
@2871720 Lum16DC lev (0,0) k=0 vlc=1                               010 (  2) 
@2871723 Lum16DC totalrun (0,0) vlc=6                              100 (  4) 
@2871726 Lum16DC run (6,0) k=6 vlc=2                                11 (  3) 
@2871728 Lum16DC run (5,0) k=5 vlc=2                                11 (  3) 
@2871730 Lum16DC run (4,0) k=4 vlc=2                                01 (  1) 
@2871732 Lum16DC run (3,0) k=3 vlc=0                                 0 (  0) 
@2871733 ChrDC # c & tr.1s  #c=0 #t1=0                              01 (  1) 
@2871735 ChrDC # c & tr.1s  #c=1 #t1=1                               1 (  1) 
@2871736 ChrDC trailing ones sign (0,0)                              1 (  1) 
@2871737 ChrDC totalrun (0,0) vlc=0                                  1 (  1) """
    bs = VerboseWrapper( BitStream( buf=binData("0001101 1 00111 000000100 101 1 11 10 010 100 11 11 01 0 01 1 1 1 " ) ),
        startOffset=2871689 ) # without skip
    left = [[0, 0, 0, 0], [0, 0], [0, 0]]
    up = [[0, 0, 0, 0], [0, 0], [0, 0]]
    macroblockLayer( bs, left, up )
    self.assertEqual( bs.worker.index, 2871738- 2871690 )



  def testMbType10( self ):
    # frame0147.bin
    """
*********** POC: 4 (I/P) MB: 3426 Slice: 0 Type 0 **********
@606828 mb_skip_run                                                  1 (  0) 
@606829 mb_type                                                0001011 ( 10) 
@606836 intra_chroma_pred_mode                                     011 (  2) 
@606839 mb_qp_delta                                                  1 (  0) 
@606840 Lum16DC # c & tr.1s vlc=0 #c=5 #t1=3                   0000100 (  4) 
@606847 Lum16DC trailing ones sign (0,0)                           001 (  1) 
@606850 Lum16DC lev (0,0) k=1 vlc=0                                 01 (  1) 
@606852 Lum16DC lev (0,0) k=0 vlc=1                                 11 (  3) 
@606854 Lum16DC totalrun (0,0) vlc=4                              0010 (  2) 
@606858 Lum16DC run (4,0) k=4 vlc=6                               0001 (  1) 
@606862 Lum16DC run (3,0) k=3 vlc=0                                  1 (  1) 
@606863 Lum16DC run (2,0) k=2 vlc=0                                  1 (  1) 
@606864 Lum16DC run (1,0) k=1 vlc=0                                  1 (  1) 
@606865 ChrDC # c & tr.1s  #c=1 #t1=1                                1 (  1) 
@606866 ChrDC trailing ones sign (0,0)                               1 (  1) 
@606867 ChrDC totalrun (0,0) vlc=0                                   1 (  1) 
@606868 ChrDC # c & tr.1s  #c=1 #t1=1                                1 (  1) 
@606869 ChrDC trailing ones sign (0,0)                               0 (  0) 
@606870 ChrDC totalrun (0,0) vlc=0                                   1 (  1) """
    bs = VerboseWrapper( BitStream( buf=binData("0001011 011 1 0000100 001 01 11 0010 0001 1 1 1 1 1 1 1 0 1 " ) ),
        startOffset=2871689 ) # without skip
    left = [[0, 0, 0, 0], [0, 0], [0, 0]]
    up = [[0, 0, 0, 0], [0, 0], [0, 0]]
    macroblockLayer( bs, left, up )
    self.assertEqual( bs.worker.index, 606871-606829 )


  def testMbType14( self ):
    # frame0148.bin
    """
*********** POC: 6 (I/P) MB: 2613 Slice: 0 Type 0 **********
@707572 mb_skip_run                                                  1 (  0) 
@707573 mb_type                                                0001111 ( 14) 
@707580 intra_chroma_pred_mode                                     010 (  1) 
@707583 mb_qp_delta                                              00100 (  2) 
@707588 Lum16DC # c & tr.1s vlc=0 #c=8 #t1=3                0000000100 (  4) 
@707598 Lum16DC trailing ones sign (0,0)                           001 (  1) 
@707601 Lum16DC lev (0,0) k=4 vlc=0                                  1 (  1) 
@707602 Lum16DC lev (0,0) k=3 vlc=1                                 10 (  2) 
@707604 Lum16DC lev (0,0) k=2 vlc=1                                 10 (  2) 
@707606 Lum16DC lev (0,0) k=1 vlc=1                                 10 (  2) 
@707608 Lum16DC lev (0,0) k=0 vlc=1                                011 (  3) 
@707611 Lum16DC totalrun (0,0) vlc=7                                10 (  2) 
@707613 Lum16DC run (7,0) k=7 vlc=4                                011 (  3) 
@707616 Lum16DC run (6,0) k=6 vlc=2                                 10 (  2) 
@707618 Lum16DC run (5,0) k=5 vlc=1                                 01 (  1) 
@707620 Lum16DC run (4,0) k=4 vlc=0                                  1 (  1) 
@707621 Lum16DC run (3,0) k=3 vlc=0                                  0 (  0) 
@707622 ChrDC # c & tr.1s  #c=1 #t1=1                                1 (  1) 
@707623 ChrDC trailing ones sign (0,0)                               0 (  0) 
@707624 ChrDC totalrun (0,0) vlc=0                                  01 (  1) 
@707626 ChrDC # c & tr.1s  #c=0 #t1=0                               01 (  1) 
@707628 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@707629 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@707630 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@707631 ChrAC # c & tr.1s vlc=0 #c=1 #t1=1                          01 (  1) 
@707633 ChrAC trailing ones sign (1,5)                               0 (  0) 
@707634 ChrAC totalrun (1,5) vlc=0                                   1 (  1) 
@707635 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@707636 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@707637 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@707638 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) """
    bs = VerboseWrapper( BitStream( buf=binData("0001111 010 00100 0000000100 001 1 10 10 10 011 10 011 10 01 1 0 1 0 01 01 1 1 1 01 0 1 1 1 1 1 " ) ),
        startOffset=2871689 ) # without skip
    left = [[0, 0, 0, 0], [0, 0], [0, 0]]
    up = [[0, 0, 0, 0], [0, 0], [0, 0]]
    macroblockLayer( bs, left, up )
    self.assertEqual( bs.worker.index, 707639-707573 )

  def testMbType16( self ):
    # frame0149.bin
    """
*********** POC: 8 (I/P) MB: 2896 Slice: 0 Type 0 **********
@873939 mb_skip_run                                                  1 (  0) 
@873940 mb_type                                              000010001 ( 16) 
@873949 intra_chroma_pred_mode                                   00100 (  3) 
@873954 mb_qp_delta                                                011 ( -1) 
@873957 Lum16DC # c & tr.1s vlc=0 #c=3 #t1=3                     00011 (  3) 
@873962 Lum16DC trailing ones sign (0,0)                           110 (  6) 
@873965 Lum16DC totalrun (0,0) vlc=2                               101 (  5) 
@873968 Lum16DC run (2,0) k=2 vlc=2                                 00 (  0) 
@873970 ChrDC # c & tr.1s  #c=0 #t1=0                               01 (  1) 
@873972 ChrDC # c & tr.1s  #c=0 #t1=0                               01 (  1) 
@873974 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@873975 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@873976 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@873977 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@873978 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@873979 ChrAC # c & tr.1s vlc=0 #c=1 #t1=1                          01 (  1) 
@873981 ChrAC trailing ones sign (3,4)                               0 (  0) 
@873982 ChrAC totalrun (3,4) vlc=0                                 011 (  3) 
@873985 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@873986 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) """
    bs = VerboseWrapper( BitStream( buf=binData("000010001 00100 011 00011 110 101 00 01 01 1 1 1 1 1 01 0 011 1 1 " ) ),
        startOffset=2871689 ) # without skip
    left = [[0, 0, 0, 0], [0, 0], [0, 0]]
    up = [[0, 0, 0, 0], [0, 0], [0, 0]]
    macroblockLayer( bs, left, up )
    self.assertEqual( bs.worker.index, 873987-873940 )


  def testMbType17( self ):
    # frame0150.bin
    """
*********** POC: 10 (I/P) MB: 2704 Slice: 0 Type 0 **********
@980878 mb_skip_run                                                  1 (  0) 
@980879 mb_type                                              000010010 ( 17) 
@980888 intra_chroma_pred_mode                                       1 (  0) 
@980889 mb_qp_delta                                              00110 (  3) 
@980894 Lum16DC # c & tr.1s vlc=0 #c=5 #t1=3                   0000100 (  4) 
@980901 Lum16DC trailing ones sign (0,0)                           001 (  1) 
@980904 Lum16DC lev (0,0) k=1 vlc=0                                  1 (  1) 
@980905 Lum16DC lev (0,0) k=0 vlc=1                                 11 (  3) 
@980907 Lum16DC totalrun (0,0) vlc=4                               111 (  7) 
@980910 Lum16DC run (4,0) k=4 vlc=2                                 10 (  2) 
@980912 Lum16DC run (3,0) k=3 vlc=1                                 01 (  1) 
@980914 Lum16DC run (2,0) k=2 vlc=0                                  0 (  0) 
@980915 ChrDC # c & tr.1s  #c=0 #t1=0                               01 (  1) 
@980917 ChrDC # c & tr.1s  #c=1 #t1=1                                1 (  1) 
@980918 ChrDC trailing ones sign (0,0)                               0 (  0) 
@980919 ChrDC totalrun (0,0) vlc=0                                   1 (  1) 
@980920 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@980921 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@980922 ChrAC # c & tr.1s vlc=0 #c=1 #t1=1                          01 (  1) 
@980924 ChrAC trailing ones sign (0,5)                               1 (  1) 
@980925 ChrAC totalrun (0,5) vlc=0                                   1 (  1) 
@980926 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@980927 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@980928 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@980929 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@980930 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) """
    bs = VerboseWrapper( BitStream( buf=binData("000010010 1 00110 0000100 001 1 11 111 10 01 0 01 1 0 1 1 1 01 1 1 1 1 1 1 1 " ) ),
        startOffset=2871689 ) # without skip
    left = [[0, 0, 0, 0], [0, 0], [0, 0]]
    up = [[0, 0, 0, 0], [0, 0], [0, 0]]
    macroblockLayer( bs, left, up )
    self.assertEqual( bs.worker.index, 980931-980879 )

  def testMbType15( self ):
    # frame0150.bin
    """
*********** POC: 10 (I/P) MB: 2871 Slice: 0 Type 0 **********
@989455 mb_skip_run                                                  1 (  0) 
@989456 mb_type                                              000010000 ( 15) 
@989465 intra_chroma_pred_mode                                     010 (  1) 
@989468 mb_qp_delta                                                  1 (  0) 
@989469 Lum16DC # c & tr.1s vlc=0 #c=4 #t1=3                    000011 (  3) 
@989475 Lum16DC trailing ones sign (0,0)                           111 (  7) 
@989478 Lum16DC lev (0,0) k=0 vlc=0                                001 (  1) 
@989481 Lum16DC totalrun (0,0) vlc=3                              0010 (  2) 
@989485 Lum16DC run (3,0) k=3 vlc=6                                001 (  1) 
@989488 Lum16DC run (2,0) k=2 vlc=2                                 11 (  3) 
@989490 Lum16DC run (1,0) k=1 vlc=2                                 00 (  0) 
@989492 ChrDC # c & tr.1s  #c=2 #t1=2                              001 (  1) 
@989495 ChrDC trailing ones sign (0,0)                              01 (  1) 
@989497 ChrDC totalrun (0,0) vlc=1                                  01 (  1) 
@989499 ChrDC run (1,0) k=1 vlc=0                                    0 (  0) 
@989500 ChrDC # c & tr.1s  #c=0 #t1=0                               01 (  1) 
@989502 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@989503 ChrAC # c & tr.1s vlc=0 #c=1 #t1=1                          01 (  1) 
@989505 ChrAC trailing ones sign (1,4)                               0 (  0) 
@989506 ChrAC totalrun (1,4) vlc=0                                 011 (  3) 
@989509 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@989510 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@989511 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@989512 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@989513 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@989514 ChrAC # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) """
    bs = VerboseWrapper( BitStream( buf=binData("000010000 010 1 000011 111 001 0010 001 11 00 001 01 01 0 01 1 01 0 011 1 1 1 1 1 1 " ) ),
        startOffset=2871689 ) # without skip
    left = [[0, 0, 0, 0], [0, 0], [0, 0]]
    up = [[0, 0, 0, 0], [0, 0], [0, 0]]
    macroblockLayer( bs, left, up )
    self.assertEqual( bs.worker.index, 989515-989456 )


  def testDCError( self ):
    # frame0380.bin - this was in reality problem due to unhandled ESCAPE sequence
    """
*********** POC: 50 (I/P) MB: 244 Slice: 0 Type 0 **********
@3584943 mb_skip_run                                                 1 (  0) 
@3584944 mb_type                                                     1 (  0) 
@3584945 mvd0_l0                                           00000100000 ( 16) 
@3584956 mvd1_l0                                                     1 (  0) 
@3584957 coded_block_pattern                               00000100011 ( 20) 
@3584968 mb_qp_delta                                             00101 ( -2) 
@3584973 Luma # c & tr.1s vlc=0 #c=1 #t1=1                          01 (  1) 
@3584975 Luma trailing ones sign (0,2)                               1 (  1) 
@3584976 Luma totalrun (0,2) vlc=0                                   1 (  1) 
@3584977 Luma # c & tr.1s vlc=0 #c=0 #t1=0                           1 (  1) 
@3584978 Luma # c & tr.1s vlc=0 #c=1 #t1=1                          01 (  1) 
@3584980 Luma trailing ones sign (0,3)                               1 (  1) 
@3584981 Luma totalrun (0,3) vlc=0                                 011 (  3) 
@3584984 Luma # c & tr.1s vlc=0 #c=1 #t1=1                          01 (  1) 
@3584986 Luma trailing ones sign (1,3)                               0 (  0) 
@3584987 Luma totalrun (1,3) vlc=0                                   1 (  1) 
@3584988 ChrDC # c & tr.1s  #c=4 #t1=3                         0000000 (  0) 
@3584995 ChrDC trailing ones sign (0,0)                            000 (  0) 
@3584998 ChrDC lev (0,0) k=0 vlc=0                      00000000000001 (  1) 
@3585012 ChrDC # c & tr.1s  #c=0 #t1=0                              01 (  1) """
    bs = VerboseWrapper( BitStream( buf=binData("1 00000100000 1 00000100011 00101 01 1 1 1 01 1 011 01 0 1 0000000 000 00000000000001 01 " ) ),
        startOffset=3584944 ) # without skip
    left = [[0, 0, 0, 0], [0, 1], [0, 0]]
    up = [[0, 0, 0, 1], [0, 0], [0, 0]]
    macroblockLayer( bs, left, up )
    self.assertEqual( bs.worker.index, 3585014-3584944 )

  def testRemoveEscape( self ):
    buf = "".join( [chr(x) for x in [0x04, 0x65, 0x7B, 0x6A, 0x00, 0x00, 0x03, 0x02, 0xE0, 0xD0, 0x0A]] )
    self.assertEqual( removeEscape( buf ), "".join( [chr(x) for x in [0x04, 0x65, 0x7B, 0x6A, 0x00, 0x00, 0x02, 0xE0, 0xD0, 0x0A]] ) )


  def testDroneSPS( self ):
    bs = BitStream( buf = "".join( [chr(x) for x in [0x42, 0x80, 0x1f, 0x8b, 0x68, 0x5, 0x0, 0x5b, 0x10]] ) )
    self.assertEqual( bs.bits(8), 66 ) # profileIdc ... 66 = Baseline profile
    bs.bits(8) # flag set 012
    self.assertEqual( bs.bits(8), 31 ) # level

if __name__ == "__main__":
  setVerbose( False )
  unittest.main() 
  
