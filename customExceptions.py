
from flask import jsonify, make_response, Response, g
import flask


# Base custom exception to support debugging **************************************************************************************
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
        
    
# Errors related to requests ******************************************************************************************************
class RequestError(StructuredErrorInfo):
    """Represents an error related to request processing. Subclass of `StructuredErrorInfo`."""
    
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
        
# Errors related to update checking ***********************************************************************************************
class UpdateCheckingError(StructuredErrorInfo):
    """Represents an error related to update checking. Subclass of `StructuredErrorInfo`."""
    
    def __init__(self, responseMessage: str, responseCode: int, logEntries = None, innerException: Exception = None):
        """Register a new error of this kind.

        Args:
            responseMessage (str): The message to return to the caller.
            responseCode (int): The HTTP response code to return.
            logEntries (list, optional): Lines to write to the log in one transaction so that they appear in one block as a string list. Defaults to [].
            innerException (Exception, optional): The original exception triggering this one to be registered.. Defaults to None.
        """
        super().__init__(responseMessage=responseMessage, responseCode=responseCode, logEntries=logEntries, innerException=innerException)
        
# Errors related to environmental issues ******************************************************************************************
class EnvironmentError(StructuredErrorInfo):
    """Represents an error related to enrivonment or infrastructure issues. Subclass of `StructuredErrorInfo`."""

    def __init__(self, responseMessage: str, responseCode: int, logEntries: None, innerException: Exception = None):
        """Register a new error of this kind.

        Args:
            responseMessage (str): The message to return to the caller.
            responseCode (int): The HTTP response code to return.
            logEntries (list, optional): Lines to write to the log in one transaction so that they appear in one block as a string list. Defaults to [].
            innerException (Exception, optional): The original exception triggering this one to be registered.. Defaults to None.
        """
        super().__init__(responseMessage=responseMessage, responseCode=responseCode, logEntries=logEntries, innerException=innerException)
