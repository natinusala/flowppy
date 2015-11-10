# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod
import re;

class GraphDriver:

    JUMPS_REGEX_LIST = [
        "JE?CXZ|JPO|JN[ABGL]E|J[ABGLP]E|JN?[ABCEGLOPSZ]" #x86-64
    ];
    
    def __init__(self, outputmanager):
        __metaclass__ = ABCMeta;
    
        self.outputManager = outputmanager;
        
    @abstractmethod
    def get_name(self): pass;
    
    @abstractmethod
    def create_graph(self, instructions_table, vma_instructions_table): pass;
    
    def is_jump(self, instruction):
        for regex in self.JUMPS_REGEX_LIST:
            if re.match(regex, instruction.mnemonic):
                return True;    
        return False;    