from logging import Logger
import os
import logging
from datetime import datetime

class LogHelper:
    
    _indentationLevel: int = 0
    _indentationWidth: int = 2
    _logger: Logger = None
    
    def __init__(self, logLevel: int = logging.ERROR):
        # Set log file's name and clear the file
        logFile = os.path.join(self.basedir, "logs", datetime.strftime(datetime.today, "%Y-%m-%d"))
        
        with open(logFile, "a"):
            pass
    
        self.setLogger(logging.getLogger("GitHub-Update-Checker"))
        self._logger.setLevel(logLevel)
        logFileHandler = logging.FileHandler(logFile)
        logFileHandler.setLevel(self.logger.level)
        logFileHandler.setFormatter(logging.Formatter(fmt='%(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        self._logger.addHandler(logFileHandler)
        
        
    def setLogger(self, logger: Logger):
        self._logger = logger
        
        
    def _checkLogger(self):
        if self._logger is None: raise ValueError("Logger is not initialized, set logger to your Logger instance")
    
            
    def _tabs(self):
        return " " * self._indentationLevel * self._indentationWidth
    
    def indent(self):
        self.setIndentationLevel(self._indentationLevel + 1)
        
    def outdent(self):
        if self._indentationLevel > 0:
            self.setIndentationLevel(self._indentationLevel - 1)
        
    def setIndentationLevel(self, indentationLevel):
        if self._indentationLevel < 0:
            raise ValueError(f"Indentation level for the log cannot be negative, the value passed is {indentationLevel}")
        
        self._indentationLevel = indentationLevel
        
    def getIndentationLevel(self):
        return self._indentationLevel
    
    def setIndentationWidth(self, width: int):
        if width < 0:
            raise ValueError(f"Indentation width for the log cannot be negative, the value passed is {width}")
        
        self._indentationWidth = width
        
    def error(self, msg: str):
        self._checkLogger()
        self._logger.error(self._tabs() + "[ERROR] " + msg)
        # Print on the Console in red and don't forget to restore white when done
        print(self._tabs() + "\033[0;31;40m" + msg + "\033[0;37;40m")
        
    def errorInto(self, msg: str):
        self.indent()
        self.error(msg)
        self.outdent()
    
        
    def warn(self, msg: str):
        self._checkLogger()
        self._logger.warn(self._tabs() + "[WARN] " + msg)
        # Print on the Console in green and don't forget to restore white when done
        print(self._tabs() + "\033[0;33;40m" + msg + "\033[0;37;40m")
        
    def warnInto(self, msg: str):
        self.indent()
        self.warn(msg)
        self.outdent()
    
        
    def info(self, msg: str):
        self._checkLogger()
        self._logger.info(self._tabs() + msg)
        # Remove to save the world from a mass of messages
        # Print on the Console in grey and don't forget to restore white when done
        print("\033[1;37;40m " + self._tabs() + msg + "\033[1;37;40m ")
        
    def infoInto(self, msg: str):
        self.indent()
        self.info(msg)
        self.outdent()
                
        
    def debug(self, msg: str):
        self._checkLogger()
        self._logger.debug(self._tabs() + msg)
        
    def debugInto(self, msg: str):
        self.indent()
        self.debug(msg)
        self.outdent()
    
    def printAnyway(self, msg: str):
        self._checkLogger()
        self._logger.error(self._tabs() + msg)
    