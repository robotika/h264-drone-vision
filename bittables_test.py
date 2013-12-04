#!/usr/bin/python
from bittables import *
import unittest

class BittablesTest( unittest.TestCase ): 
  def testMakeAutomat( self ):
    #exampleTab = { '01':'A', '00':'B', '1':'C' } # general types not supported
    exampleTab = { '01':0, '00':1, '1':2 }
    mapTable, endstates = makeAutomat( exampleTab )


if __name__ == "__main__":
  unittest.main() 
  
