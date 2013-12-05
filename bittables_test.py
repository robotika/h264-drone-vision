#!/usr/bin/python
from bittables import *
import unittest

class BittablesTest( unittest.TestCase ): 
  def testMakeAutomat( self ):
    #exampleTab = { '01':'A', '00':'B', '1':'C' } # general types not supported
    #exampleTab = { '01':0, '00':1, '1':2 }
    exampleTab = { '01':(1,2), '00':(3,4), '1':(5,6) }
    mapTable, endstates = makeAutomat( exampleTab )
    self.assertEqual( endstates, array('i', [5, 6, 3, 4, 1, 2]) )
    self.assertEqual( mapTable, array('i',[2, 1, 3, 5]) )


if __name__ == "__main__":
  unittest.main() 
  
