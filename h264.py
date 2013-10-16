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

def residual( bs ):
  "read residual block/data"
  # page 63, 7.4.5.3.1 Residual block CAVLC syntax
  # L40 T0 n8 s28 P0 

#  for i in xrange(21):
#    print bs.bit(),
#  print
#  print "BS:", bs.index-40
#  return

  print "residual uknown", bs.golomb()
  # TotalCoef and TrailingOnes (page 177)
  coefTokenMapping = { '01' : (1,1) } # 0 <= nC < 2
  print "BS:", bs.index-40
  totalCoeff, trailing1s = bs.tab( coefTokenMapping )
  print "total %d, trailing1s %d" % (totalCoeff, trailing1s)
  for i in xrange(totalCoeff):
    if i < trailing1s:
      print "sign bit", bs.bit()
    else:
      levelMapping = { '1':0, '01':1, '001':2 } # TODO
      levelPrefix = bs.tab( levelMapping,  maxBits=15 )
      print "levelPrefix", levelPrefix, "suffix", bs.bits(levelPrefix)
  print "BS:", bs.index-40
  totalZerosMapping = {}
  totalZerosMapping[1] = { '1':0, '011':1, '010':2, '0011':3, '0010':4, '00011':5} # TODO
  totalZeros = bs.tab( totalZerosMapping[totalCoeff] )
  print "totalZeros", totalZeros
  print "BS:", bs.index-40
  runBeforeMapping = {}
  runBeforeMapping[1] = { '1':0, '0': 1 }
  runBeforeMapping[2] = { '1':0, '01': 1, '00':2 }
  runBeforeMapping[3] = { '11':0, '10': 1 } # TODO
  runBeforeMapping[4] = { '11':0, '10': 1 } # TODO
  runBeforeMapping[5] = { '11':0, '10': 1 } # TODO
  zerosLeft = totalZeros
  for i in xrange( totalCoeff-1 ):
    runBefore = bs.tab( runBeforeMapping[zerosLeft] )
    print "run", runBefore
    zerosLeft -= runBefore
    if zerosLeft == 0:
      break
  print "residual uknownEnd", bs.golomb()
  print "BS:", bs.index-40



def macroblockLayer( bs ):
  print "macroblockLayer" # page 59
  print "==BS:", bs.index-40
  print "  mb_type", bs.golomb() # for P-slice, Table 7-10, page 91
  # md_type, name, NumMbPart, MbPartPredMode
  # 0 P_L0_16x16 1 Pred_L0 na 16 16
  # P_L0_16x16: the samples of the macroblock are predicted with one luma macroblock partition of size 16x16 luma
  # samples and associated chroma samples.
  # mb_pred( mb_type )
  print "  ref_idx_l0", bs.golomb()  # MbPartPredMode( mb_type, mbPartIdx ) != Pred_L1
#  print "  ref_idx_l1", bs.golomb()
  print "  mvd_l0", bs.golomb()
#  print "  mvd_l1", bs.golomb()
  print "BS:", bs.index-40
  print "CBP  coded_block_pattern", bs.golomb()  #         cbp= get_ue_golomb(&h->gb);
  print "BS:", bs.index-40
  print "dquant= get_se_golomb(&h->gb);", bs.golomb()

  residual( bs )
  residual( bs ) # chroma?
  print "residual uknownEnd2", bs.bits(3)

def parsePSlice( bs ):
  print "P-slice"
  print "BS:", bs.index-40
  print "first_mb_in_slice", bs.golomb()
  print "slice_type", bs.golomb()
  print "pic_parameter_set_id", bs.golomb()
  print "BS:", bs.index-40
  print "frame_num", bs.bits(14) # HACK! should use parameter from SPS
  print "BS:", bs.index-40
# redundant_pic_cnt_present_flag: 0 (PPS)
  print "num_ref_idx_active_override_flag", bs.bit()
  print "h->ref_count[0]", bs.golomb()+1
  print "ref_pic_list_reordering_flag_l0", bs.bit()
# weighted_pred_flag: 0
# nal_ref_idc = 3
  print "adaptive_ref_pic_marking_mode_flag", bs.bit()
# entropy_coding_mode_flag: 0
  print "BS:", bs.index-40
  print "slice_qp_delta", bs.golomb()
  print "BS:", bs.index-40
# deblocking_filter_control_present_flag: 1
  if True:
    print "disable_deblocking_filter_idc", bs.golomb()
    if True: # != 1
      print "slice_alpha_c0_offset_div2", bs.golomb()
      print "slice_beta_offset_div2", bs.golomb()
# num_slice_groups_minus1: 0

  # SLICE DATA
  print "mb_skip_flag", bs.golomb() # 0 -> MoreData=True
  for i in xrange(2):
    macroblockLayer( bs )



def parseFrame( filename ):
  bs = BitStream( open(filename, "rb").read() )
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


