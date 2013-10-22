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
    print "EXIT", key
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
    coefTokenMapping = { '1':(0,0), '01' : (1,1), '001':(2,2), '00011':(3,3) } # 0 <= nC < 2 # TODO
  elif nC in [2,3]:
    coefTokenMapping = { '11':(0,0) } # 2 <= nC < 4 # TODO
  elif nC == -1:
    coefTokenMapping = { '01':(0,0), '1':(1,1) } # nC == -1
  else:
    assert False, "UNSUPORTED nC=%d" % nC

  totalCoeff, trailing1s = bs.tab( coefTokenMapping )
  print "total %d, trailing1s %d" % (totalCoeff, trailing1s)
  for i in xrange(totalCoeff):
    if i < trailing1s:
      print "sign bit", bs.bit()
    else:
      levelMapping = { '1':0, '01':1, '001':2 } # TODO
      levelPrefix = bs.tab( levelMapping,  maxBits=15 )
      print "levelPrefix", levelPrefix, "suffix", bs.bits(levelPrefix)
  if totalCoeff == 0:
    return totalCoeff
  totalZerosMapping = {}
  totalZerosMapping[1] = { '1':0, '011':1, '010':2, '0011':3, '0010':4, '00011':5} # TODO page 181
  totalZerosMapping[2] = { '111':0, '110':1, '101':2, '110':3, '011':4, '0101':5, '0100':6, 
      '0011':7, '0010':8, '00011':9, '00010':10, '000011':11, '000010':12, '000001':13, '000000':14}
  totalZerosMapping[3] = { '0101':0, '111':1, '110':2, '101':3, '0100':4, '0011':5, '100':6,
      '011':7, '0010':8, '00011':9, '00010':10, '000001':11, '00001':12, '000000':13 }
  totalZeros = bs.tab( totalZerosMapping[totalCoeff] )
  print "totalZeros", totalZeros
  runBeforeMapping = {} # Table 9-10, page 182
  runBeforeMapping[1] = { '1':0, '0': 1 }
  runBeforeMapping[2] = { '1':0, '01': 1, '00':2 }
  runBeforeMapping[3] = { '11':0, '10': 1, '01':2, '00':3 }
  runBeforeMapping[4] = { '11':0, '10': 1, '01':2, '001':3, '001':4 }
  runBeforeMapping[5] = { '11':0, '10': 1, '011':2, '010':3, '001':4, '000':5 } 
  runBeforeMapping[6] = { '11':0, '000': 1, '001':2, '011':3, '010':4, '100':5, '100':6 }
  runBeforeMapping[7] = { '111':0, '110': 1, '101':2, '100':3, '011':4, '010':5, '001':6, '0001':7,
      '00001':8, '000001':9, '0000001':10, '00000001':11, '000000001':12, '0000000001':13, '00000000001':14}
  zerosLeft = totalZeros
  for i in xrange( totalCoeff-1 ):
    if zerosLeft < 7:
      runBefore = bs.tab( runBeforeMapping[zerosLeft] )
    else:
      runBefore = bs.tab( runBeforeMapping[7] )
    print "run", runBefore
    zerosLeft -= runBefore
    if zerosLeft == 0:
      break
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
  print "CBP  coded_block_pattern", cbp  #         cbp= get_ue_golomb(&h->gb);
  print "mb_qp_delta", bs.golomb()

  # TODO use conversion table, page 174, column Inter
  cbpInter = [ 0, 16, 1, 2, 4, 8, 32, 3, 5, 10,  # 0-9
           12, 15, 47, 7, 11, 13, 14, 6, 9, 31, 
           35, 37, 42, 44, 33, 34, 36, 40, 39, 43,
           45, 46, 17, 18, 20, 24, 19, 21, 26, 28,
           23, 27, 29, 30, 22, 25, 38, 41 ]
  bitPattern = cbpInter[ cbp ]
  nC = [0]*16
  #### LUMA ####
  # 0 1 4 5
  # 2 3 6 7
  # 8 9 C D
  # A B E F
  if bitPattern & 0x1: # upper left
    nC[0] = residual( bs, mix(left[0], up[0]) ) # Luma only 4x
    nC[1] = residual( bs, mix(nC[0], up[1]) ) # left
    nC[2] = residual( bs, mix(left[1], nC[0]) ) # up
    nC[3] = residual( bs, mix(nC[2],nC[1]) ) # left+up/2
  if bitPattern & 0x2: # upper right
    nC[4] = residual( bs, mix(nC[1], up[2]) )
    nC[5] = residual( bs, mix(nC[4], up[3]) )
    nC[6] = residual( bs, mix(nC[3], nC[4]) )
    nC[7] = residual( bs, mix(nC[6], nC[5]) )
  if bitPattern & 0x4: # lower left
    nC[8] = residual( bs, mix(left[2], nC[6]) )
    nC[9] = residual( bs, mix(nC[8], nC[7]) )
    nC[10] = residual( bs, mix(left[3], nC[8]) )
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
      hack = nC[:]
      nC = [0]*8
      nC[0] = residual( bs, nC=0 ) # ChrAC
      nC[1] = residual( bs, nC=nC[0] ) # left
      nC[2] = residual( bs, nC=nC[0] ) # up
      nC[3] = residual( bs, (nC[1]+nC[2]+1)/2 ) # left+up/2
      nC[4] = residual( bs, nC=nC[1] ) # left
      nC[5] = residual( bs, nC=nC[4] ) # left
      nC[6] = residual( bs, nC=nC[4] ) # up
      nC[7] = residual( bs, nC=(nC[6]+nC[5]+1)/2 ) # up
      nC = hack
  left = [nC[5], nC[7], nC[13], nC[15]]
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
  left = [None]*4
  up = [None]*4
  for i in xrange(7):
    skip = bs.golomb()
    mbIndex += skip
    print "mb_skip_flag", skip # 0 -> MoreData=True
    print "=============== MB:", mbIndex, "==============="
    left, up = macroblockLayer( bs, left, up )
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


