#!/usr/bin/python
"""
  Steps to understand H.264
  usage:
       ./h264.py <frame>
"""
import sys
import struct
import os

VERBOSE=False

#NAL_HEADER = "".join([chr(x) for x in [0,0,0,1]])
NAL_HEADER = [0,0,0,1]
PAVE_HEADER = [ord(x) for x in "PaVE"]

WIDTH = 80 # for the first experiments hard-coded (otherwise available in SPS)
HEIGHT = 45

class BitStream:
  def __init__( self, buf="" ):
    self.buf = buf
    self.index = 0

  def bit( self, info=None ):
    if ord(self.buf[self.index/8]) & 0x80>> (self.index%8):
      ret = 1
    else:
      ret = 0
    self.index += 1
    return ret

  def bits( self, howMany, info=None ):
    ret = 0
    for i in xrange(howMany):
      ret = ret*2 + self.bit()
    return ret

  def golomb( self, info=None ):
    zeros = 0
    while self.bit() == 0:
      zeros += 1
    ret = 0
    for i in xrange(zeros):
      ret = 2*ret + self.bit()
    return 2**zeros + ret - 1

  def signedGolomb( self, info=None ):
    tmp = self.golomb()
    if tmp % 2 == 0:
      return -tmp/2
    return ( tmp + 1 ) / 2


  def alignedByte( self ):
    self.index = (self.index+7)&0xFFFFFFF8
    ret = ord(self.buf[self.index/8])
    self.index += 8
    return ret

  def tab( self, table, maxBits=32, info=None ):
    "ce(v): context-adaptive variable-length entropy-coded syntax element"
    key = ''
    for i in xrange(maxBits):
      key += str(self.bit())
      if key in table:
#        print key
        return table[key]
    print "EXIT", key, table
    sys.exit()

    return None

class VerboseWrapper:
  def __init__( self, worker, startOffset=1875459-77 ):
    self.worker = worker
    self.startOffset = startOffset

  def printInfo( self, addr, s, info=None ):
    if info == None:
      print "\ntrace: @%d" % (self.startOffset + addr), s
    else:
      print "\ntrace: @%d" % (self.startOffset + addr), s, info

  def binStr( self, num, places ):
    # ignore '0b' and fill zeros
    return ('0'*places+bin( num )[2:])[-places:]

  def bit( self, info=None ):
    addr = self.worker.index
    ret = self.worker.bit()
    self.printInfo( addr, "bit %d" % ret, info )
    return ret

  def bits( self, howMany, info=None ):
    addr = self.worker.index
    ret = self.worker.bits( howMany )
    self.printInfo( addr, ("bits(%d) " % howMany) + self.binStr( ret, howMany ), info )
    return ret

  def golomb( self, info=None ):
    addr = self.worker.index
    ret = self.worker.golomb()
    howMany = self.worker.index - addr
    self.printInfo( addr, "golomb(%d) val=%d " % (howMany, ret), info )
    return ret

  def signedGolomb( self, info=None ):
    addr = self.worker.index
    ret = self.worker.signedGolomb()
    howMany = self.worker.index - addr
    self.printInfo( addr, "signedGolomb(%d) val=%d " % (howMany, ret), info )
    return ret

  def alignedByte( self ):
    addr = self.worker.index
    ret = self.worker.alignedByte()
#    self.printInfo( addr, "alignedByte " + self.binStr( ret, 8 ) )
    return ret

  def tab( self, table, maxBits=32, info=None ):
    addr = self.worker.index
    ret = self.worker.tab( table, maxBits )
    howMany = self.worker.index - addr
    self.printInfo( addr, "tab(%d) " % howMany + str( ret ), info )
    return ret


def parseISlice( bs ):
#  assert ord(f.read(1)) == 0xE0 # set012 flags and reserved zero 5bits
  print [hex(bs.alignedByte()) for i in xrange(5)]


def parseSPS( bs ):
  sps = [bs.alignedByte() for i in xrange(9)]
  assert sps == [ 0x42, 0x80, 0x1f, 0x8b, 0x68, 0x5, 0x0, 0x5b, 0x10], sps
  return

  # 7.3.2.1, page 49
  profileIdc = bs.bits(8)
  flagsSet012 = bs.bits(8)
  level = bs.bits(8)
  print "profil, level", profileIdc, level

#seq parameter set id: 0
#log2_max_frame_num_minus4: 10
#pic_order_cnt_type: 2
  seqParameterSetId = bs.golomb()
  log2_max_frame_num_minus4 = bs.golomb()
  pic_order_cnt_type = bs.golomb()
  assert pic_order_cnt_type == 2 # i.e. not necessary to handle ordering
  numFrames = bs.golomb()
  print "numFrames", numFrames
  gaps_in_frame_num_value_allowed_flag = bs.bit()
  picWidthInMbs = bs.golomb()
  picWidthInMbs += 1
  print "picWidthInMbs", picWidthInMbs, picWidthInMbs*16
  picHeightInMbs = bs.golomb()
  picHeightInMbs += 1
  print "picHeightInMbs", picHeightInMbs, picHeightInMbs*16
  frameMbsOnlyFlag = bs.bit()
  print "frameMbsOnlyFlag", frameMbsOnlyFlag
  assert frameMbsOnlyFlag # if not needs to get adaptive flag
#    mbAdaptiveFrameFlag, it = bits( it, 1 )
  direct_8x8_inference_flag = bs.bit()
  frame_cropping_flag = bs.bit()
  print "frame_cropping_flag", frame_cropping_flag
  assert frame_cropping_flag == 0 # otherwise read cropping
  vui_parameters_present_flag = bs.bit()
  print "vui_parameters_present_flag", vui_parameters_present_flag
  assert vui_parameters_present_flag == 0

def parsePPS( bs ):
  pps = [bs.alignedByte() for i in xrange(5)]
  assert pps == [0xce, 0x1, 0xa8, 0x77, 0x20], pps

def residual( bs, nC, verbose=VERBOSE ):
  "read residual block/data"
  # page 63, 7.4.5.3.1 Residual block CAVLC syntax
  
  if verbose:
    print "-residual .. nC = %d" % nC
  # TotalCoef and TrailingOnes (page 177)
  if nC in [0,1]:
    coefTokenMapping = { '1':(0,0), '000101':(0,1), '01':(1,1), '00000111':(0,2), '000100':(1,2), '001':(2,2),
        '000000111':(0,3), '00000110':(1,3), '0000101':(2,3), '00011':(3,3), '0000000111':(0,4), '000000110':(1,4),
        '00000101':(2,4), '000011':(3,4), '00000000111':(0,5), '0000000110':(1,5), '000000101':(2,5), '0000100':(3,5),
        '0000000001111':(0,6), '00000000110':(1,6), '0000000101':(2,6), '00000100':(3,6), '0000000001011':(0,7),
        '0000000001110':(1,7), '00000000101':(2,7), '000000100':(3,7), '0000000001000':(0,8), '0000000001010':(1,8),
        '0000000001101':(2,8), '0000000100':(3,8), '00000000001111':(0,9), '00000000001110':(1,9), '0000000001001':(2,9),
        '00000000100':(3,9), '00000000001011':(0,10), '00000000001010':(1,10), '00000000001101':(2,10), '0000000001100':(3,10),
        '000000000001111':(0,11), '000000000001110':(1,11), '00000000001001':(2,11), '00000000001100':(3,11),
        '000000000001011':(0,12), '000000000001010':(1,12), '000000000001101':(2,12), '00000000001000':(3,12),
        '0000000000001111':(0,13), '000000000000001':(1,13), '000000000001001':(2,13), '000000000001100':(3,13),
        '0000000000001011':(0,14), '0000000000001110':(1,14), '0000000000001101':(2,14), '000000000001000':(3,14),
        '0000000000000111':(0,15), '0000000000001010':(1,15), '0000000000001001':(2,15), '0000000000001100':(3,15),
        '0000000000000100':(0,16), '0000000000000110':(1,16), '0000000000000101':(2,16), '0000000000001000':(3,16) } # 0 <= nC < 2
  elif nC in [2,3]:
    coefTokenMapping = { '11':(0,0), '001011':(0,1), '10':(1,1), '000111':(0,2), '00111':(1,2), '011':(2,2),
        '0000111':(0,3), '001010':(1,3), '001001':(2,3), '0101':(3,3), '00000111':(0,4), '000110':(1,4),
        '000101':(2,4), '0100':(3,4), '00000100':(0,5), '0000110':(1,5), '0000101':(2,5), '00110':(3,5),
        '000000111':(0,6), '00000110':(1,6), '00000101':(2,6), '001000':(3,6), '00000001111':(0,7),
        '000000110':(1,7), '000000101':(2,7), '000100':(3,7), '00000001011':(0,8), '00000001110':(1,8),
        '00000001101':(2,8), '0000100':(3,8), '000000001111':(0,9), '00000001010':(1,9), '00000001001':(2,9),
        '000000100':(3,9), '000000001011':(0,10), '000000001110':(1,10), '000000001101':(2,10), '00000001100':(3,10),
        '000000001000':(0,11), '000000001010':(1,11), '000000001001':(2,11), '00000001000':(3,11), '0000000001111':(0,12),
        '0000000001110':(1,12), '0000000001101':(2,12), '000000001100':(3,12), '0000000001011':(0,13),
        '0000000001010':(1,13), '0000000001001':(2,13), '0000000001100':(3,13), '0000000000111':(0,14),
        '00000000001011':(1,14), '0000000000110':(2,14), '0000000001000':(3,14), '00000000001001':(0,15),
        '00000000001000':(1,15), '00000000001010':(2,15), '0000000000001':(3,15), '00000000000111':(0,16),
        '00000000000110':(1,16), '00000000000101':(2,16), '00000000000100':(3,16) } # 2 <= nC < 4
  elif nC in [4,5,6,7]:
     coefTokenMapping = { '1111':(0,0), '001111':(0,1), '1110':(1,1), '001011':(0,2), '01111':(1,2), '1101':(2,2),
         '001000':(0,3), '01100':(1,3), '01110':(2,3), '1100':(3,3), '0001111':(0,4), '01010':(1,4), '01011':(2,4),
         '1011':(3,4), '0001011':(0,5), '01000':(1,5), '01001':(2,5), '1010':(3,5), '0001001':(0,6), '001110':(1,6),
         '001101':(2,6), '1001':(3,6), '0001000':(0,7), '001010':(1,7), '001001':(2,7), '1000':(3,7), '00001111':(0,8),
         '0001110':(1,8), '0001101':(2,8), '01101':(3,8), '00001011':(0,9), '00001110':(1,9), '0001010':(2,9), '001100':(3,9),
         '000001111':(0,10), '00001010':(1,10), '00001101':(2,10), '0001100':(3,10), '000001011':(0,11), '000001110':(1,11),
         '00001001':(2,11), '00001100':(3,11), '000001000':(0,12), '000001010':(1,12), '000001101':(2,12), '00001000':(3,12),
         '0000001101':(0,13), '000000111':(1,13), '000001001':(2,13), '000001100':(3,13), '0000001001':(0,14), '0000001100':(1,14),
         '0000001011':(2,14), '0000001010':(3,14), '0000000101':(0,15), '0000001000':(1,15), '0000000111':(2,15),
         '0000000110':(3,15), '0000000001':(0,16), '0000000100':(1,16), '0000000011':(2,16), '0000000010':(3,16) } # 4 <= nC < 8
  elif nC >= 8:
    coefTokenMapping = { '000011':(0,0), '000000':(0,1), '000001':(1,1), '000100':(0,2), '000101':(1,2), '000110':(2,2),
        '001000':(0,3), '001001':(1,3), '001010':(2,3), '001011':(3,3), '001100':(0,4), '001101':(1,4), '001110':(2,4),
        '001111':(3,4), '010000':(0,5), '010001':(1,5), '010010':(2,5), '010011':(3,5), '010100':(0,6), '010101':(1,6),
        '010110':(2,6), '010111':(3,6), '011000':(0,7), '011001':(1,7), '011010':(2,7), '011011':(3,7), '011100':(0,8),
        '011101':(1,8), '011110':(2,8), '011111':(3,8), '100000':(0,9), '100001':(1,9), '100010':(2,9), '100011':(3,9),
        '100100':(0,10), '100101':(1,10), '100110':(2,10), '100111':(3,10), '101000':(0,11), '101001':(1,11), '101010':(2,11),
        '101011':(3,11), '101100':(0,12), '101101':(1,12), '101110':(2,12), '101111':(3,12), '110000':(0,13), '110001':(1,13),
        '110010':(2,13), '110011':(3,13), '110100':(0,14), '110101':(1,14), '110110':(2,14), '110111':(3,14), '111000':(0,15),
        '111001':(1,15), '111010':(2,15), '111011':(3,15), '111100':(0,16), '111101':(1,16), '111110':(2,16), '111111':(3,16) }
  elif nC == -1:
    coefTokenMapping = { '01':(0,0), '000111':(0,1), '1':(1,1), '000100':(0,2), '000110':(1,2),
        '001':(2,2), '000011':(0,3), '0000011':(1,3), '0000010':(2,3), '000101':(3,3),
        '000010':(0,4), '00000011':(1,4), '00000010':(2,4), '0000000':(3,4) } # nC == -1
  else:
    assert False, "UNSUPORTED nC=%d" % nC

  trailing1s, totalCoeff = bs.tab( coefTokenMapping )
  if verbose:
    print "total %d, trailing1s %d" % (totalCoeff, trailing1s)
  levelVLC = 0
  if totalCoeff > 10 and trailing1s < 3:
    levelVLC = 1
  levelMapping = { '1':0, '01':1, '001':2, '0001':3, '00001':4, '000001':5,
      '0000001':6, '00000001':7, '000000001':8, '0000000001':9, '00000000001':10,
      '000000000001':11, '000000000000 1':12, '00000000000001':13,
      '000000000000 001':14, '0000000000000001':15 } # Tab 9-6, page 180
    #  not found, only parallel implementation http://etrij.etri.re.kr/Cyber/Download/PublishedPaper/3105/etrij.oct2009.0510.pdf
  for i in xrange(totalCoeff):
    if i < trailing1s:
      bs.bit( "sign bit" )
    else:
      levelPrefix = bs.tab( levelMapping,  maxBits=15, info="levelPrefix" )
      if levelPrefix == 14 and levelVLC == 0: # page 179
        levelVLC = 4
      if levelPrefix == 15:
        levelVLC = 12
      if levelVLC > 0:
        bs.bits( levelVLC, "bits" )
      if verbose:
        print "levelPrefix", levelPrefix
      if levelVLC == 0:
        levelVLC = 1
      else:
        if levelVLC == 2 and levelPrefix >= 6:
          assert False, "NOT (YET) SUPPORTED LEVEL level=%d prefix=%d" % (level, levelPrefix)
        if levelPrefix >= 3:
          levelVLC = 2
      #, "suffix", bs.bits(levelPrefix) # it is again complex - see page 179
  if totalCoeff == 0 or totalCoeff == 16 or (totalCoeff == 4 and nC==-1):
    return totalCoeff
  totalZerosMapping = {} # Table 9-7, page 181
  if nC == -1: # ChromaDC
    totalZerosMapping[1] = { '1':0, '01':1, '001':2, '000':3 }
    totalZerosMapping[2] = { '1':0, '01':1, '00':2 }
    totalZerosMapping[3] = { '1':0, '0':1 }
  else:
    totalZerosMapping[1] = { '1':0, '011':1, '010':2, '0011':3, '0010':4, '00011':5, '00010':6, '000011':7,
        '000010':8, '0000011':9, '0000010':10, '00000011':11, '00000010':12, '000000011':13, '000000010':14, '000000001':15 }
    totalZerosMapping[2] = { '111':0, '110':1, '101':2, '100':3, '011':4, '0101':5, '0100':6, 
        '0011':7, '0010':8, '00011':9, '00010':10, '000011':11, '000010':12, '000001':13, '000000':14}
    totalZerosMapping[3] = { '0101':0, '111':1, '110':2, '101':3, '0100':4, '0011':5, '100':6,
        '011':7, '0010':8, '00011':9, '00010':10, '000001':11, '00001':12, '000000':13 }
    totalZerosMapping[4] = { '00011':0, '111':1, '0101':2, '0100':3, '110':4, '101':5, '100':6,
        '0011':7, '011':8, '0010':9, '00010':10, '00001':11, '00000':12 }
    totalZerosMapping[5] = { '0101':0, '0100':1, '0011':2, '111':3, '110':4, '101':5, '100':6,
        '011':7, '0010':8, '00001':9, '0001':10, '00000':11 }
    totalZerosMapping[6] = { '000001':0, '00001':1, '111':2, '110':3, '101':4, '100':5, '011':6,
        '010':7, '0001':8, '001':9, '000000':10 }
    totalZerosMapping[7] = { '000001':0, '00001':1, '101':2, '100':3, '011':4, '11':5, '010':6, '0001':7, '001':8, '000000':9 }
    totalZerosMapping[8] = { '000001':0, '0001':1, '00001':2, '011':3, '11':4, '10':5, '010':6, '001':7, '000000':8 } 
    totalZerosMapping[9] = { '000001':0, '000000':1, '0001':2, '11':3, '10':4, '001':5, '01':6, '00001':7 }
    totalZerosMapping[10] = { '00001':0, '00000':1, '001':2, '11':3, '10':4, '01':5, '0001':6 }
    totalZerosMapping[11] = { '0000':0, '0001':1, '001':2, '010':3, '1':4, '011':5 }
    totalZerosMapping[12] = { '0000':0, '0001':1, '01':2, '1':3, '001':4 }
    totalZerosMapping[13] = { '000':0, '001':1, '1':2, '01':3 }
    totalZerosMapping[14] = { '00':0, '01':1, '1':2 }
    totalZerosMapping[15] = { '0':0, '1':1 }
  totalZeros = bs.tab( totalZerosMapping[totalCoeff], info="totalZeros" )
  runBeforeMapping = {} # Table 9-10, page 182
  runBeforeMapping[1] = { '1':0, '0': 1 }
  runBeforeMapping[2] = { '1':0, '01': 1, '00':2 }
  runBeforeMapping[3] = { '11':0, '10': 1, '01':2, '00':3 }
  runBeforeMapping[4] = { '11':0, '10': 1, '01':2, '001':3, '000':4 }
  runBeforeMapping[5] = { '11':0, '10': 1, '011':2, '010':3, '001':4, '000':5 } 
  runBeforeMapping[6] = { '11':0, '000': 1, '001':2, '011':3, '010':4, '101':5, '100':6 }
  runBeforeMapping[7] = { '111':0, '110': 1, '101':2, '100':3, '011':4, '010':5, '001':6, '0001':7,
      '00001':8, '000001':9, '0000001':10, '00000001':11, '000000001':12, '0000000001':13, '00000000001':14}
  zerosLeft = totalZeros
  for i in xrange( totalCoeff-1 ):
    if zerosLeft == 0:
      break
    if zerosLeft < 7:
      runBefore = bs.tab( runBeforeMapping[zerosLeft], info="run" )
    else:
      runBefore = bs.tab( runBeforeMapping[7], info="run" )
    zerosLeft -= runBefore
  return totalCoeff

def mix( up, left ):
  if up == None:
    if left == None:
      return 0
    else:
      return left
  else:
    if left == None:
      return up
    return (left+up+1)/2

def macroblockLayer( bs, left, up, verbose=VERBOSE ):
  "input is BitStream, extra left column, and extra upper row"
  if verbose:
    print "macroblockLayer" # page 59
  mbType = bs.golomb( "  mb_type" ) # for P-slice, Table 7-10, page 91
  # md_type, name, NumMbPart, MbPartPredMode
  # 0 P_L0_16x16 1 Pred_L0 na 16 16
  # P_L0_16x16: the samples of the macroblock are predicted with one luma macroblock partition of size 16x16 luma
  # samples and associated chroma samples.
  # mb_pred( mb_type )
#  print "  ref_idx_l0", bs.golomb()  # MbPartPredMode( mb_type, mbPartIdx ) != Pred_L1
#  print "  ref_idx_l1", bs.golomb()
  if mbType > 0:
    mvdL0 = None # not defined, ignore previous predictions
    mvdL1 = None
    cbp = bs.golomb( "intra_chroma_pred_mode" ) # page 94
    bs.golomb( "mb_qp_delta" )
    noIdea = residual( bs, mix( left[0][0], up[0][0]) ) # Lum16DC - TODO proper nC/table selection
    if mbType < 13:
      return (mvdL0, mvdL1), left, up
    # for larger fake bit pattern
    bitPattern = 0xF
    if mbType == 25:
      bitPattern = 0x1F
  else: # 0
    mvdL0 = bs.signedGolomb( "  mvd_l0" )
    mvdL1 = bs.signedGolomb( "  mvd_l1" )
    cbp = bs.golomb( "CBP  coded_block_pattern" )
    # TODO use conversion table, page 174, column Inter
    cbpInter = [ 0, 16, 1, 2, 4, 8, 32, 3, 5, 10,  # 0-9
           12, 15, 47, 7, 11, 13, 14, 6, 9, 31, 
           35, 37, 42, 44, 33, 34, 36, 40, 39, 43,
           45, 46, 17, 18, 20, 24, 19, 21, 26, 28,
           23, 27, 29, 30, 22, 25, 38, 41 ]
    bitPattern = cbpInter[ cbp ]
    if cbp > 0: # example ref. MB=43
      bs.golomb( "mb_qp_delta" )
  if verbose:
    print cbp, bin(bitPattern)


  nC = [0]*16
  n2C = [0]*8 # twice ChrAC, separated
  #### LUMA ####
  # 0 1 4 5
  # 2 3 6 7
  # 8 9 C D
  # A B E F
  if bitPattern & 0x1: # upper left
    nC[0] = residual( bs, mix(left[0][0], up[0][0]) ) # Luma only 4x
    nC[1] = residual( bs, mix(nC[0], up[0][1]) ) # left
    nC[2] = residual( bs, mix(left[0][1], nC[0]) ) # up
    nC[3] = residual( bs, mix(nC[2],nC[1]) ) # left+up/2
  if bitPattern & 0x2: # upper right
    nC[4] = residual( bs, mix(nC[1], up[0][2]) )
    nC[5] = residual( bs, mix(nC[4], up[0][3]) )
    nC[6] = residual( bs, mix(nC[3], nC[4]) )
    nC[7] = residual( bs, mix(nC[6], nC[5]) )
  if bitPattern & 0x4: # lower left
    nC[8] = residual( bs, mix(left[0][2], nC[2]) )
    nC[9] = residual( bs, mix(nC[8], nC[3]) )
    nC[10] = residual( bs, mix(left[0][3], nC[8]) )
    nC[11] = residual( bs, mix(nC[10], nC[9]) )
  if bitPattern & 0x8: # lower right
    nC[12] = residual( bs, mix(nC[9],nC[6]) )
    nC[13] = residual( bs, mix(nC[12],nC[7]) )
    nC[14] = residual( bs, mix(nC[11],nC[12]) )
    nC[15] = residual( bs, mix(nC[14],nC[13]) )
  if bitPattern >= 16:
    residual( bs, nC=-1 ) # ChrDC
    residual( bs, nC=-1 ) # ChrDC
    if bitPattern >= 32:
      n2C[0] = residual( bs, mix(left[1][0], up[1][0]) ) # ChrAC
      n2C[1] = residual( bs, mix(n2C[0], up[1][1]) )
      n2C[2] = residual( bs, mix(left[1][1], n2C[0]) )
      n2C[3] = residual( bs, mix(n2C[2],n2C[1]) )

      n2C[4] = residual( bs, mix(left[2][0], up[2][0]) )
      n2C[5] = residual( bs, mix(n2C[4], up[2][1]) )
      n2C[6] = residual( bs, mix(left[2][1], n2C[4]) )
      n2C[7] = residual( bs, mix(n2C[5], n2C[6]) )

  left = [[nC[5], nC[7], nC[13], nC[15]],[n2C[1],n2C[3]],[n2C[5],n2C[7]]]
  up = [[nC[10], nC[11], nC[14], nC[15]],[n2C[2],n2C[3]],[n2C[6],n2C[7]]]
#  print "REST", nC
  return (mvdL0, mvdL1), left, up


def median( a, b, c ):
  if a == None: # and b == None and c == None:
    return 0
  if a != None and b != None:
    if c == None:
      return sorted([a,b,0])[1]
    else:
      return sorted([a,b,c])[1]
  return a



def parsePSlice( bs, fout, verbose=False ):
  print "P-slice"
  bs.golomb( "first_mb_in_slice" )
  bs.golomb( "slice_type" )
  bs.golomb( "pic_parameter_set_id" )
  bs.bits( 14, info="frame_num" ) # HACK! should use parameter from SPS
# redundant_pic_cnt_present_flag: 0 (PPS)
  bs.bit( "num_ref_idx_active_override_flag" )
  bs.golomb( "h->ref_count[0]" )
  bs.bit( "ref_pic_list_reordering_flag_l0" )
# weighted_pred_flag: 0
# nal_ref_idc = 3
  bs.bit( "adaptive_ref_pic_marking_mode_flag" )
# entropy_coding_mode_flag: 0
  bs.golomb( "slice_qp_delta" )
# deblocking_filter_control_present_flag: 1
  if True:
    bs.golomb( "disable_deblocking_filter_idc" )
    if True: # != 1
      bs.golomb( "slice_alpha_c0_offset_div2" )
      bs.golomb( "slice_beta_offset_div2" )
# num_slice_groups_minus1: 0
  if verbose:
    print "-------------------------"

  # SLICE DATA
  mbIndex = 0
  left = [[None]*4, [None]*2, [None]*2]
  upperRow = [[[None]*4, [None]*2, [None]*2]] * WIDTH
  leftXY = None,None
  upperXY = [(None,None)] * (WIDTH+1) # to have available frameUR
  for i in xrange(4000):
    skip = bs.golomb("mb_skip_flag")
    if skip > 0:
      # just guessing that left should be cleared
      left = [[0]*4, [0]*2, [0]*2]
      for mbi in xrange(skip):
        upperRow[(mbIndex+mbi) % WIDTH] = [[0]*4, [0]*2, [0]*2]
        if leftXY in [(0,0), (None,None)] or upperXY[(mbIndex+mbi) % WIDTH] in [(0,0), (None,None)] :
          x,y = 0,0
        else:         
          x = median(leftXY[0], upperXY[(mbIndex+mbi) % WIDTH][0], upperXY[1+ (mbIndex+mbi) % WIDTH][0])
          y = median(leftXY[1], upperXY[(mbIndex+mbi) % WIDTH][1], upperXY[1+ (mbIndex+mbi) % WIDTH][1])
        if (2+mbIndex+mbi) % WIDTH == 0:
          # backup [-2] element for UR element
          upperXY[-1] = upperXY[(mbIndex+mbi) % WIDTH]
        leftXY = (x,y)
        upperXY[(mbIndex+mbi) % WIDTH] = (x,y)
    mbIndex += skip
    if mbIndex >= WIDTH*HEIGHT:
      break
    if mbIndex % WIDTH == 0:
      left = [[None]*4, [None]*2, [None]*2]
      leftXY = (0, 0)

    if verbose:
      print "=============== MB:", mbIndex, "==============="
      print "UP", upperRow[mbIndex % WIDTH]
    mvd, left, up = macroblockLayer( bs, left, upperRow[mbIndex % WIDTH], verbose=verbose )
    if verbose:
      print "LEFT/UP", mbIndex, left, up
    upperRow[mbIndex % WIDTH] = up
    if verbose:
      print "MOVE:", mbIndex % WIDTH, mbIndex / WIDTH, mvd[0], mvd[1]
    if mvd != (None,None):
      x = median(leftXY[0], upperXY[mbIndex % WIDTH][0], upperXY[1+ mbIndex % WIDTH][0]) + mvd[0]
      y = median(leftXY[1], upperXY[mbIndex % WIDTH][1], upperXY[1+ mbIndex % WIDTH][1]) + mvd[1]
      fout.write("%d %d %d %d\n" % ( mbIndex % WIDTH, mbIndex / WIDTH, x, y ) )
    else:
      x,y = 0,0

    fout.flush()
    leftXY = x, y
    if (2+mbIndex) % WIDTH == 0:
      # backup [-2] element for UR element
      upperXY[-1] = upperXY[mbIndex % WIDTH]
    upperXY[mbIndex % WIDTH] = x, y
    mbIndex += 1
  if verbose:
    print "THE END"
  fout.flush()
#  sys.exit(0)


def parseFrame( filename, verbose=VERBOSE ):
  bs = BitStream( open(filename, "rb").read() )
  if verbose:
    bs = VerboseWrapper( bs )
  frameIndex = 0
  fout = open("mv_out.txt", "w")
  header = [None, None, None, None]
  while True:  
    try:
      c = bs.alignedByte()
    except IndexError:
      break
    if header == NAL_HEADER:
      print hex(c)
      if c & 0x1F == 1:
#        try:
          fout.write( "Frame %d\n" % frameIndex )
          print "Frame %d\n" % frameIndex
          parsePSlice( bs, fout, verbose=verbose )
          frameIndex += 1
#        except:
#          sys.stderr.write( "ERROR parsing P slice\n" )
#          sys.exit(-1)
      elif c & 0x1F == 5:
        print "Frame %d\n" % frameIndex
        parseISlice( bs )
        frameIndex += 1
      # 7 = sequence parameter set (SPS)
      elif c & 0x1F == 7:
        parseSPS( bs )
      # 8 = picture parameter set (PPS)
      elif c & 0x1F == 8:
        parsePPS( bs )

    if header == PAVE_HEADER:
      # print "PaVE"
      # already read in c #f.read(1) # print "version", ord(f.read(1))
      bs.alignedByte() # print "codec", ord(f.read(1))
      headerSize = struct.unpack_from("H", chr(bs.alignedByte())+chr(bs.alignedByte()))[0]
      #print "header size", headerSize
#      payloadSize = struct.unpack_from("I", f.read(4))[0]
      payloadSize = bs.bits(32)
      #print "payload size", payloadSize
      for i in xrange(headerSize-12+1):
        c = bs.alignedByte()
    header = header[1:] + [c]
  fout.close()

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print __doc__
    sys.exit(2)
  for filename in sys.argv[1:]:
    parseFrame( filename )
#  path = sys.argv[1]
#  for filename in os.listdir(path):
#    if filename.startswith("video_rec"):
#      parseFrame( path + os.sep + filename )


