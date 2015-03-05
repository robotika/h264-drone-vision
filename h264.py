#!/usr/bin/python
"""
  Steps to understand H.264
  usage:
       ./h264.py [-v] <frame>
"""
import sys
import struct
import os
import types

def setVerbose( val ):
  global verbose
  verbose = val

#NAL_HEADER = "".join([chr(x) for x in [0,0,0,1]])
NAL_HEADER = [0,0,0,1]
PAVE_HEADER = [ord(x) for x in "PaVE"]

WIDTH = 80 # for the first experiments hard-coded (otherwise available in SPS)
HEIGHT = 45

from bittables import coefTokenMapping01, coefTokenMapping23, coefTokenMapping4567, coefTokenMapping8andUp, coefTokenMappingOther
from bittables import levelMapping, runBeforeMapping, totalZerosMappingDC, totalZerosMapping

from bittables import makeAutomat

# experiment
coefTokenMapping01 = makeAutomat( coefTokenMapping01 )
coefTokenMapping23 = makeAutomat( coefTokenMapping23 )
coefTokenMapping4567 = makeAutomat( coefTokenMapping4567 )
coefTokenMapping8andUp = makeAutomat( coefTokenMapping8andUp )
coefTokenMappingOther = makeAutomat( coefTokenMappingOther )
levelMapping = makeAutomat( levelMapping )
for k in runBeforeMapping.keys():
  runBeforeMapping[k] = makeAutomat( runBeforeMapping[k] )
for k in totalZerosMappingDC.keys():
  totalZerosMappingDC[k] = makeAutomat( totalZerosMappingDC[k] )
for k in totalZerosMapping.keys():
  totalZerosMapping[k] = makeAutomat( totalZerosMapping[k] )
# end of experiment

class BitStream:
  def __init__( self, buf="" ):
    self.buf = buf
    self.index = 0
    self.gen = self.bitG()

  def bitG( self ):
    for x in self.buf:
      byte = ord(x)
      mask = 0x80
      while mask > 0:
        yield int((byte & mask) != 0) # what is the fastest solution??
        mask = mask >> 1

  def bit( self, info=None ):
    self.index += 1
    return self.gen.next()

  def bits( self, howMany, info=None ):
    ret = 0
    for i in xrange(howMany):
      ret = ret*2 + self.gen.next()
    self.index += howMany
    return ret

  def golomb( self, info=None ):
    zeros = 0
    while self.gen.next() == 0:
      zeros += 1
    ret = 0
    for i in xrange(zeros):
      ret = 2*ret + self.gen.next()
    self.index += 2*zeros+1
    return 2**zeros + ret - 1

  def signedGolomb( self, info=None ):
    tmp = self.golomb()
    if tmp % 2 == 0:
      return -tmp/2
    return ( tmp + 1 ) / 2


  def alignedByte( self ):
    while self.index != (self.index+7)&0xFFFFFFF8:
      self.bit()
    ret = 0
    for i in xrange(8):
      ret = (ret << 1) + self.bit()
    return ret


  def tab( self, table, maxBits=32, info=None ):
    "ce(v): context-adaptive variable-length entropy-coded syntax element"
    if type(table) != types.DictType:
      return self.bitAutomat( table, maxBits, info )
    key = ''
    for i in xrange(maxBits):
      key += str(self.bit())
      if key in table:
#        print key
        return table[key]
    print "EXIT", key, table
    #sys.exit()
    raise Exception( "Table error" )

    return None

  def bitAutomat( self, automat, maxBits=32, info=None ): # maxBits and info just for compatibility with tab call
    "future replacement of tab"
    (mapTable, endstates, lenVal) = automat
    state = 0
    while True:
      bit = self.bit()
      state = mapTable[state | bit]
      if state & 1:
        if lenVal == 1:
          return endstates[state/2]
        elif lenVal == 2:
          return (endstates[state/2], endstates[state/2+1])
        else:
          assert False, str(automat) # not supported

class VerboseWrapper:
  def __init__( self, worker, startOffset=3571530-77 ):
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

  def bitAutomat( self, table, maxBits=32, info=None ):
    addr = self.worker.index
    ret = self.worker.bitAutomat( table, maxBits )
    howMany = self.worker.index - addr
    self.printInfo( addr, "tab(%d) " % howMany + str( ret ), info )
    return ret


def removeEscape( buf ):
  "remove aligned 00 00 03 from the stream"
  return buf.replace( "\x00\x00\x03", "\x00\x00" )


def parseISlice( bs ):
#  assert ord(f.read(1)) == 0xE0 # set012 flags and reserved zero 5bits
  print [hex(bs.alignedByte()) for i in xrange(5)]


def parseSPS( bs ):
  global WIDTH
  global HEIGHT

  # 7.3.2.1, page 49
  profileIdc = bs.bits(8, "profile_idc")
  flagsSet012 = bs.bits(8)
  level = bs.bits(8, "level_idc")
  seqParameterSetId = bs.golomb()
  log2_max_frame_num_minus4 = bs.golomb()
  pic_order_cnt_type = bs.golomb()
  assert pic_order_cnt_type == 2 # i.e. not necessary to handle ordering
  numFrames = bs.golomb("num_ref_frames")
  gaps_in_frame_num_value_allowed_flag = bs.bit()
  picWidthInMbs = bs.golomb("pic_width_in_mbs_minus1")
  picWidthInMbs += 1
  if WIDTH != picWidthInMbs:
    print "picWidthInMbs", picWidthInMbs, picWidthInMbs*16
    WIDTH = picWidthInMbs
  picHeightInMbs = bs.golomb("pic_height_in_map_units_minus1")
  picHeightInMbs += 1
  if HEIGHT != picHeightInMbs:
    print "picHeightInMbs", picHeightInMbs, picHeightInMbs*16
    HEIGHT = picHeightInMbs
  frameMbsOnlyFlag = bs.bit("frameMbsOnlyFlag")
  assert frameMbsOnlyFlag # if not needs to get adaptive flag
  direct_8x8_inference_flag = bs.bit()
  frame_cropping_flag = bs.bit("frame_cropping_flag")
  if frame_cropping_flag:
    bs.golomb("frame_crop_left_offset")
    bs.golomb("frame_crop_right_offset")
    bs.golomb("frame_crop_top_offset")
    bs.golomb("frame_crop_bottom_offset")
  vui_parameters_present_flag = bs.bit("vui_parameters_present_flag")
  if vui_parameters_present_flag:
    aspect_ratio_info_present_flag = bs.bit()
    assert aspect_ratio_info_present_flag == 0
    overscan_info_present_flag = bs.bit()
    assert overscan_info_present_flag == 0
    video_signal_type_present_flag = bs.bit()
    assert video_signal_type_present_flag == 0
    chroma_loc_info_present_flag = bs.bit()
    assert chroma_loc_info_present_flag == 0
    timing_info_present_flag = bs.bit()
    if timing_info_present_flag:
      num_units_in_tick = bs.bits(32)
      time_scale = bs.bits(32)
      fixed_frame_rate_flag = bs.bit(1)
    nal_hrd_parameters_present_flag = bs.bit()
    assert nal_hrd_parameters_present_flag == 0
    vcl_hrd_parameters_present_flag = bs.bit()
    assert vcl_hrd_parameters_present_flag == 0
    pic_struct_present_flag = bs.bit()
    bitstream_restriction_flag = bs.bit()
    if bitstream_restriction_flag:
      motion_vectors_over_pic_boundaries_flag = bs.bit()
      max_bytes_per_pic_denom = bs.golomb()
      max_bits_per_mb_denom = bs.golomb()
      log2_max_mv_length_horizontal = bs.golomb()
      log2_max_mv_length_vertical = bs.golomb()
      num_reorder_frames = bs.golomb()
      max_dec_frame_buffering = bs.golomb()

def parsePPS( bs ):
  pps = [bs.alignedByte() for i in xrange(5)]
  assert pps == [0xce, 0x1, 0xa8, 0x77, 0x20], pps

def residual( bs, nC ):
  "read residual block/data"
  # page 63, 7.4.5.3.1 Residual block CAVLC syntax

  if verbose:
    print "-residual .. nC = %d" % nC
  # TotalCoef and TrailingOnes (page 177)
  if nC in [0,1]:
    coefTokenMapping = coefTokenMapping01 # 0 <= nC < 2
  elif nC in [2,3]:
    coefTokenMapping = coefTokenMapping23 # 2 <= nC < 4
  elif nC in [4,5,6,7]:
     coefTokenMapping = coefTokenMapping4567 # 4 <= nC < 8
  elif nC >= 8:
    coefTokenMapping = coefTokenMapping8andUp
  elif nC == -1:
    coefTokenMapping = coefTokenMappingOther # nC == -1
  else:
    assert False, "UNSUPORTED nC=%d" % nC

  trailing1s, totalCoeff = bs.tab( coefTokenMapping )
  if verbose:
    print "total %d, trailing1s %d" % (totalCoeff, trailing1s)
  levelVLC = 0
  if totalCoeff > 10 and trailing1s < 3:
    levelVLC = 1
    #  not found, only parallel implementation http://etrij.etri.re.kr/Cyber/Download/PublishedPaper/3105/etrij.oct2009.0510.pdf  
  levelTwoOrHigher = (totalCoeff <= 3 or trailing1s != 3)
  levelLimits = [0, 3, 6, 12, 24, 48, 32768]
  for i in xrange(totalCoeff):
    if i < trailing1s:
      bs.bit( "sign bit" )
    else:
      levelPrefix = bs.tab( levelMapping,  maxBits=16, info="levelPrefix" )
      levelSuffixSize = levelVLC
      if levelPrefix == 14 and levelVLC == 0: # page 179
        levelSuffixSize = 4
      if levelPrefix == 15:
        levelSuffixSize = 12
      if levelSuffixSize > 0:
        absLevel = ((levelPrefix << levelVLC) + bs.bits( levelSuffixSize, "bits" ))/2 + 1
      else:
        absLevel = levelPrefix/2 + 1
      if levelTwoOrHigher:
        absLevel += 1
        levelTwoOrHigher = False
      if verbose:
        print "levelPrefix", levelPrefix
      if levelVLC == 0:
        levelVLC = 1
        if absLevel > 3:
          levelVLC = 2
      else:
        if absLevel > levelLimits[levelVLC]:
          levelVLC += 1
      #, "suffix", bs.bits(levelPrefix) # it is again complex - see page 179
  if totalCoeff == 0 or totalCoeff == 16 or (totalCoeff == 4 and nC==-1):
    return totalCoeff
  if nC == -1: # ChromaDC
    totalZeros = bs.tab( totalZerosMappingDC[totalCoeff], info="totalZerosDC" )
  else:
    totalZeros = bs.tab( totalZerosMapping[totalCoeff], info="totalZeros" )
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

def macroblockLayer( bs, left, up ):
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
    if mbType in [10, 11, 12, 13]:
      bitPattern = 0x10
    elif mbType < 13:
      left = [[0]*4, [0]*2, [0]*2]
      up = [[0]*4, [0]*2, [0]*2]
      return (mvdL0, mvdL1), left, up
    else:
      # for larger fake bit pattern
      bitPattern = 0xF
    if mbType in [14, 15, 16, 17]:
      bitPattern = 0x20
    if mbType in [22, 23, 24, 25]:
      bitPattern = 0x1F
    if mbType in [26, 27, 28, 29]: # frame 137, did not expect this type
      bitPattern = 0x2F
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
  # all invalid
  if a == None and b == None and c == None:
    return 0
  # one valid
  if a != None and b == None and c == None:
    return a
  if a == None and b != None and c == None:
    return b
  if a == None and b == None and c != None:
    return c
  # at most one invalid
  tmp = [x for x in [a,b,c] if x != None] + [0]
  return sorted(tmp[:3])[1]


def parsePSlice( bs, fout ):
  ret = []
#  print "P-slice"
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
        leftAvailable = True
        if (mbIndex+mbi) % WIDTH == 0:
          leftXY = (None, None)
          leftAvailable = False
        upAvailable = ( mbIndex+mbi > WIDTH )
        if (not leftAvailable or leftXY == (0,0)) or (not upAvailable or upperXY[(mbIndex+mbi) % WIDTH] == (0,0)) :
          x,y = 0,0
        else:         
          x = median(leftXY[0], upperXY[(mbIndex+mbi) % WIDTH][0], upperXY[1+ (mbIndex+mbi) % WIDTH][0])
          y = median(leftXY[1], upperXY[(mbIndex+mbi) % WIDTH][1], upperXY[1+ (mbIndex+mbi) % WIDTH][1])
          if verbose and fout != None:
            fout.write("%d %d %d %d (skip)\n" % ( (mbIndex+mbi) % WIDTH, (mbIndex+mbi) / WIDTH, x, y ) )
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
      leftXY = (None,None)

    if verbose:
      print "=============== MB:", mbIndex, "==============="
      print "UP", upperRow[mbIndex % WIDTH]
    mvd, left, up = macroblockLayer( bs, left, upperRow[mbIndex % WIDTH] )
    if verbose:
      print "LEFT/UP", mbIndex, left, up
    upperRow[mbIndex % WIDTH] = up
    if verbose:
      print "MOVE:", mbIndex % WIDTH, mbIndex / WIDTH, mvd[0], mvd[1]
    if mvd != (None,None):
      x = median(leftXY[0], upperXY[mbIndex % WIDTH][0], upperXY[1+ mbIndex % WIDTH][0]) + mvd[0]
      y = median(leftXY[1], upperXY[mbIndex % WIDTH][1], upperXY[1+ mbIndex % WIDTH][1]) + mvd[1]
      ret.append( ( mbIndex % WIDTH, mbIndex / WIDTH, x, y ) )
      if fout != None:
        if verbose:
          fout.write("%d %d %d %d (%d,%d)\n" % ( mbIndex % WIDTH, mbIndex / WIDTH, x, y, mvd[0], mvd[1] ) )
        else:
          fout.write("%d %d %d %d\n" % ( mbIndex % WIDTH, mbIndex / WIDTH, x, y ) )
        fout.flush()
    else:
      x,y = None, None
#      fout.write("%d %d None None\n" % ( mbIndex % WIDTH, mbIndex / WIDTH ) )

    leftXY = x, y
    if (2+mbIndex) % WIDTH == 0:
      # backup [-2] element for UR element
      upperXY[-1] = upperXY[mbIndex % WIDTH]
    upperXY[mbIndex % WIDTH] = x, y
    mbIndex += 1
  if verbose:
    print "THE END"
  return ret

def parseFrameInner( buf ):
  "return list of macroblock movements, None=failure"
  bs = BitStream( removeEscape( buf ) )
  if verbose:
    bs = VerboseWrapper( bs )
  if [bs.alignedByte() for i in [0,1,2,3]] != NAL_HEADER:
    print "Missing HEADER"
    return None
  c = bs.alignedByte()
  if c & 0x1F != 1:
    if verbose:
      print "Frame type", hex(c)    
    # 7 = sequence parameter set (SPS) - necessary to define number of macroblocks
    if c & 0x1F == 7:
        parseSPS( bs )
    return []
  ret = parsePSlice( bs, None )
  if verbose:
    index = bs.worker.index # :-(
  else:
    index = bs.index
  if index/8 == len(buf) or index/8+1 == len(buf):
    # it is not clear how the end bytes are aligned :(
    return ret
  print bs.index/8, len(buf),  bs.index % 8
  return None

def parseFrame( buf ):
  try:
    ret = parseFrameInner( buf )
  except KeyboardInterrupt as e:
    raise e
  except Exception as e:
    print str(e)
    return None
  return ret


def parseFrames( filename ):
  print "FRAME", parseFrame( open(filename, "rb").read() )

def parseFramesOld( filename ):
  bs = BitStream( removeEscape( open(filename, "rb").read()) )
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
          parsePSlice( bs, fout )
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


def functionalTest( path, prefix="frame" ):
  err, count = 0, 0
  for filename in os.listdir(path):
    if filename.startswith( prefix ):
      mv = parseFrame( open(path + os.sep + filename, "rb").read() )
      count += 1
      if mv == None:
        print filename, "None"
        err += 1
      else:
        print filename, len(mv)
  return err,count

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print __doc__
    sys.exit(2)

  setVerbose( '-v' in sys.argv[1:] )
  print "Verbose:", verbose
  if '-f' == sys.argv[1]:
    print functionalTest( path = sys.argv[2] )
  else:
    for filename in sys.argv[1:]:
      if filename != '-v':     
        parseFrames( filename )

