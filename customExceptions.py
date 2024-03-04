# T1nk-R's GitHub Update Checker // customExceptions.py
#
# This module is responsible for implementing application-specific exceptions
#
# Module authored by T1nk-R (https://github.com/gusztavj/)
#
# PURPOSE & USAGE *****************************************************************************************************************
#
# This Flask-based web server application works as a middleware or proxy between a Python module/application and GitHub and can
# be used to perform checking for updates using your personal GitHub API key without disclosing it to the public and without
# flooding GitHub. For the latter, this proxy stores fresh release (version) information in its cache and serves requests from
# the cache until it expires or direct checking is forced.
#
# Help, support, updates and anything else: https://github.com/gusztavj/GitHub-Update-Checker/
#
# COPYRIGHT ***********************************************************************************************************************
#
# ** MIT License **
# 
# Copyright (c) 2024, T1nk-R (Gusztáv Jánvári)
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, 
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE 
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# 
# ** Commercial Use **
# 
# I would highly appreciate to get notified via [janvari.gusztav@imprestige.biz](mailto:janvari.gusztav@imprestige.biz) about 
# any such usage. I would be happy to learn this work is of your interest, and to discuss options for commercial support and 
# other services you may need.
#
# DISCLAIMER **********************************************************************************************************************
# This application is provided as-is. Use at your own risk. No warranties, no guarantee, no liability,
# no matter what happens.
#
# You may learn more about legal matters on page https://github.com/gusztavj/GitHub-Update-Checker/

# Imports #########################################################################################################################

# Third-party imports -------------------------------------------------------------------------------------------------------------
from flask import jsonify, make_response, Response, g


# Base custom exception to support debugging ######################################################################################
class StructuredErrorInfo(Exception):
    """
    Error information with separate log message and response information to centralize processing.
    """
    
    # Properties ==================================================================================================================
    responseMessage: str
    """The message to return to the caller."""
    
    responseCode: int
    """The HTTP response code to return."""
    
    logEntries: list = []
    """Lines to write to the log in one transaction so that they appear in one block as a string list."""
    
    innerException: Exception
    """The original exception triggering this one to be registered."""

    # Public methods ==============================================================================================================
    
    # Get response ----------------------------------------------------------------------------------------------------------------
    def response(self) -> Response:
        """The response to return for an error."""
        responseJson = {"error": self.responseMessage}
        return make_response(jsonify(responseJson), self.responseCode)
    
    # Lifecycle management ========================================================================================================
    def __init__(self, responseMessage: str, responseCode: int, logEntries: None, innerException: Exception = None):
        """Register a new error.

        Args:
            responseMessage (str): The message to return to the caller.
            responseCode (int): The HTTP response code to return.
            logEntries (list, optional): Lines to write to the log in one transaction so that they appear in one block as a string list. Defaults to [].
            innerException (Exception, optional): The original exception triggering this one to be registered.. Defaults to None.
        """
        self.responseMessage = responseMessage        
        self.responseCode = responseCode
        self.logEntries = logEntries if logEntries is not None else []
        self.innerException = innerException        
        
    
# Errors related to requests ######################################################################################################
class RequestError(StructuredErrorInfo):
    """Represents an error related to request processing. Subclass of `StructuredErrorInfo`."""
    
    # Instantiate =================================================================================================================
    # Lifecycle management ========================================================================================================
    def __init__(self, responseMessage: str, responseCode: int, logEntries: None, innerException: Exception = None):
        """Register a new error of this kind.

        Args:
            responseMessage (str): The message to return to the caller.
            responseCode (int): The HTTP response code to return.
            logEntries (list, optional): Lines to write to the log in one transaction so that they appear in one block as a string list. Defaults to [].
            innerException (Exception, optional): The original exception triggering this one to be registered.. Defaults to None.
        """
        super().__init__(responseMessage=responseMessage, responseCode=responseCode, logEntries=logEntries, innerException=innerException)
        
# Errors related to update checking ###############################################################################################
class UpdateCheckingError(StructuredErrorInfo):
    """Represents an error related to update checking. Subclass of `StructuredErrorInfo`."""
    
    # Lifecycle management ========================================================================================================
    def __init__(self, responseMessage: str, responseCode: int, logEntries = None, innerException: Exception = None):
        """Register a new error of this kind.

        Args:
            responseMessage (str): The message to return to the caller.
            responseCode (int): The HTTP response code to return.
            logEntries (list, optional): Lines to write to the log in one transaction so that they appear in one block as a string list. Defaults to [].
            innerException (Exception, optional): The original exception triggering this one to be registered.. Defaults to None.
        """
        super().__init__(responseMessage=responseMessage, responseCode=responseCode, logEntries=logEntries, innerException=innerException)
        
# Errors related to environmental issues ##########################################################################################
class EnvironmentError(StructuredErrorInfo):
    """Represents an error related to environment or infrastructure issues. Subclass of `StructuredErrorInfo`."""

    # Lifecycle management ========================================================================================================
    def __init__(self, responseMessage: str, responseCode: int, logEntries: None, innerException: Exception = None):
        """Register a new error of this kind.

        Args:
            responseMessage (str): The message to return to the caller.
            responseCode (int): The HTTP response code to return.
            logEntries (list, optional): Lines to write to the log in one transaction so that they appear in one block as a string list. Defaults to [].
            innerException (Exception, optional): The original exception triggering this one to be registered.. Defaults to None.
        """
        super().__init__(responseMessage=responseMessage, responseCode=responseCode, logEntries=logEntries, innerException=innerException)
