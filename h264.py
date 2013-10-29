#!/usr/bin/python
"""
  Steps to understand H.264
  usage:
       ./h264.py <frame>
"""
import sys
import struct
import os

#NAL_HEADER = "".join([chr(x) for x in [0,0,0,1]])
NAL_HEADER = [0,0,0,1]
PAVE_HEADER = [ord(x) for x in "PaVE"]

class BitStream:
  def __init__( self, buf="" ):
    self.buf = buf
    self.index = 0

  def bit( self ):
    if ord(self.buf[self.index/8]) & 0x80>> (self.index%8):
      ret = 1
    else:
      ret = 0
    self.index += 1
    return ret

  def bits( self, howMany ):
    ret = 0
    for i in xrange(howMany):
      ret = ret*2 + self.bit()
    return ret

  def golomb( self ):
    zeros = 0
    while self.bit() == 0:
      zeros += 1
    ret = 0
    for i in xrange(zeros):
      ret = 2*ret + self.bit()
    return 2**zeros + ret - 1

  def alignedByte( self ):
    self.index = (self.index+7)&0xFFFFFFF8
    ret = ord(self.buf[self.index/8])
    self.index += 8
    return ret

  def tab( self, table, maxBits=32 ):
    "ce(v): context-adaptive variable-length entropy-coded syntax element"
    key = ''
    for i in xrange(maxBits):
      key += str(self.bit())
      if key in table:
        print key
        return table[key]
    print "EXIT", key, table
    sys.exit()

    return None

class VerboseWrapper:
  def __init__( self, worker, startOffset=1075083-40 ):
    self.worker = worker
    self.startOffset = startOffset

  def printInfo( self, addr, s ):
    print "\ntrace: @%d" % (self.startOffset + addr), s

  def binStr( self, num, places ):
    # ignore '0b' and fill zeros
    return ('0'*places+bin( num )[2:])[-places:]

  def bit( self ):
    addr = self.worker.index
    ret = self.worker.bit()
    self.printInfo( addr, "bit %d" % ret )
    return ret

  def bits( self, howMany ):
    addr = self.worker.index
    ret = self.worker.bits( howMany )
    self.printInfo( addr, ("bits(%d) " % howMany) + self.binStr( ret, howMany ) )
    return ret

  def golomb( self ):
    addr = self.worker.index
    ret = self.worker.golomb()
    howMany = self.worker.index - addr
    self.printInfo( addr, "golomb(%d) val=%d " % (howMany, ret) )
    return ret

  def alignedByte( self ):
    addr = self.worker.index
    ret = self.worker.alignedByte()
    self.printInfo( addr, "alignedByte " + self.binStr( ret, 8 ) )
    return ret

  def tab( self, table, maxBits=32 ):
    addr = self.worker.index
    ret = self.worker.tab( table, maxBits )
    howMany = self.worker.index - addr
    self.printInfo( addr, "tab(%d) " % howMany + str( ret ) )
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

def residual( bs, nC ):
  "read residual block/data"
  # page 63, 7.4.5.3.1 Residual block CAVLC syntax

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
  elif nC == -1:
    coefTokenMapping = { '01':(0,0), '000111':(0,1), '1':(1,1), '000100':(0,2), '000110':(1,2),
        '001':(2,2), '000011':(0,3), '0000011':(1,3), '0000010':(2,3), '000101':(3,3),
        '000010':(0,4), '00000011':(1,4), '00000010':(2,4), '0000000':(3,4) } # nC == -1
  else:
    assert False, "UNSUPORTED nC=%d" % nC

  trailing1s, totalCoeff = bs.tab( coefTokenMapping )
  print "total %d, trailing1s %d" % (totalCoeff, trailing1s)
  for i in xrange(totalCoeff):
    if i < trailing1s:
      print "sign bit", bs.bit()
    else:
      levelMapping = { '1':0, '01':1, '001':2, '0001':3, '00001':4, '000001':5,
          '0000001':6, '00000001':7, '000000001':8, '0000000001':9, '00000000001':10,
          '000000000001':11, '000000000000 1':12, '00000000000001':13,
          '000000000000 001':14, '0000000000000001':15 } # Tab 9-6, page 180
      levelPrefix = bs.tab( levelMapping,  maxBits=15 )
      print "levelPrefix", levelPrefix
      #, "suffix", bs.bits(levelPrefix) # it is again complex - see page 179
  if totalCoeff == 0:
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
  totalZeros = bs.tab( totalZerosMapping[totalCoeff] )
  print "totalZeros", totalZeros
  runBeforeMapping = {} # Table 9-10, page 182
  runBeforeMapping[1] = { '1':0, '0': 1 }
  runBeforeMapping[2] = { '1':0, '01': 1, '00':2 }
  runBeforeMapping[3] = { '11':0, '10': 1, '01':2, '00':3 }
  runBeforeMapping[4] = { '11':0, '10': 1, '01':2, '001':3, '000':4 }
  runBeforeMapping[5] = { '11':0, '10': 1, '011':2, '010':3, '001':4, '000':5 } 
  runBeforeMapping[6] = { '11':0, '000': 1, '001':2, '011':3, '010':4, '100':5, '100':6 }
  runBeforeMapping[7] = { '111':0, '110': 1, '101':2, '100':3, '011':4, '010':5, '001':6, '0001':7,
      '00001':8, '000001':9, '0000001':10, '00000001':11, '000000001':12, '0000000001':13, '00000000001':14}
  zerosLeft = totalZeros
  for i in xrange( totalCoeff-1 ):
    if zerosLeft == 0:
      break
    if zerosLeft < 7:
      runBefore = bs.tab( runBeforeMapping[zerosLeft] )
    else:
      runBefore = bs.tab( runBeforeMapping[7] )
    print "run", runBefore
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

def macroblockLayer( bs, left, up ):
  "input is BitStream, extra left column, and extra upper row"
  print "macroblockLayer" # page 59
  print "  mb_type", bs.golomb() # for P-slice, Table 7-10, page 91
  # md_type, name, NumMbPart, MbPartPredMode
  # 0 P_L0_16x16 1 Pred_L0 na 16 16
  # P_L0_16x16: the samples of the macroblock are predicted with one luma macroblock partition of size 16x16 luma
  # samples and associated chroma samples.
  # mb_pred( mb_type )
#  print "  ref_idx_l0", bs.golomb()  # MbPartPredMode( mb_type, mbPartIdx ) != Pred_L1
#  print "  ref_idx_l1", bs.golomb()
  print "  mvd_l0", bs.golomb()
  print "  mvd_l1", bs.golomb()
  cbp = bs.golomb()
  # TODO use conversion table, page 174, column Inter
  cbpInter = [ 0, 16, 1, 2, 4, 8, 32, 3, 5, 10,  # 0-9
           12, 15, 47, 7, 11, 13, 14, 6, 9, 31, 
           35, 37, 42, 44, 33, 34, 36, 40, 39, 43,
           45, 46, 17, 18, 20, 24, 19, 21, 26, 28,
           23, 27, 29, 30, 22, 25, 38, 41 ]
  bitPattern = cbpInter[ cbp ]
  print "CBP  coded_block_pattern", cbp, bin(bitPattern)

  if cbp > 0: # example ref. MB=43
    print "mb_qp_delta", bs.golomb()

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
  print "REST", nC
  return left, up

def parsePSlice( bs ):
  print "P-slice"
  print "first_mb_in_slice", bs.golomb()
  print "slice_type", bs.golomb()
  print "pic_parameter_set_id", bs.golomb()
  print "frame_num", bs.bits(14) # HACK! should use parameter from SPS
# redundant_pic_cnt_present_flag: 0 (PPS)
  print "num_ref_idx_active_override_flag", bs.bit()
  print "h->ref_count[0]", bs.golomb()+1
  print "ref_pic_list_reordering_flag_l0", bs.bit()
# weighted_pred_flag: 0
# nal_ref_idc = 3
  print "adaptive_ref_pic_marking_mode_flag", bs.bit()
# entropy_coding_mode_flag: 0
  print "slice_qp_delta", bs.golomb()
# deblocking_filter_control_present_flag: 1
  if True:
    print "disable_deblocking_filter_idc", bs.golomb()
    if True: # != 1
      print "slice_alpha_c0_offset_div2", bs.golomb()
      print "slice_beta_offset_div2", bs.golomb()
# num_slice_groups_minus1: 0
  print "-------------------------"

  # SLICE DATA
  mbIndex = 0
  left = [[None]*4, [None]*2, [None]*2]
  up = [[None]*4, [None]*2, [None]*2]
  for i in xrange(80):
    skip = bs.golomb()
    mbIndex += skip
    print "mb_skip_flag", skip # 0 -> MoreData=True
    print "=============== MB:", mbIndex, "==============="
    left, up = macroblockLayer( bs, left, up )
    print "LEFT", mbIndex, left
    mbIndex += 1
  print "THE END"
  sys.exit(0)


def parseFrame( filename ):
  bs = VerboseWrapper( BitStream( open(filename, "rb").read() ) )
  header = [None, None, None, None]
  while True:  
    try:
      c = bs.alignedByte()
    except IndexError:
      break
    if header == NAL_HEADER:
      print hex(c)
      if c & 0x1F == 1:
        parsePSlice( bs )
      elif c & 0x1F == 5:
        parseISlice( bs )
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


