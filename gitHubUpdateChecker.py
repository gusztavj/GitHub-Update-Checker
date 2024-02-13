# T1nk-R's GitHub Update Checker
# - part of T1nk-R Utilities for Blender
#
# Version: Please see the version tag under bl_info in __init__.py.
#
# This module is responsible for checking if updates are available.
#
# Module and add-on authored by T1nk-R (https://github.com/gusztavj/)
#
# PURPOSE & USAGE *****************************************************************************************************************
# You can use this add-on to synchronize the names of meshes with the names of their parent objects.
#
# Help, support, updates and anything else: https://github.com/gusztavj/T1nkR-Mesh-Name-Synchronizer
#
# COPYRIGHT ***********************************************************************************************************************
#
# ** MIT License **
# 
# Copyright (c) 2023-2024, T1nk-R (Gusztáv Jánvári)
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
# This add-on is provided as-is. Use at your own risk. No warranties, no guarantee, no liability,
# no matter what happens. Still I tried to make sure no weird things happen:
#   * This add-on is intended to change the name of the meshes and other data blocks under your Blender objects.
#   * This add-on is not intended to modify your objects and other Blender assets in any other way.
#   * You shall be able to simply undo consequences made by this add-on.
#
# You may learn more about legal matters on page https://github.com/gusztavj/T1nkR-Mesh-Name-Synchronizer
#
# *********************************************************************************************************************************

from __future__ import annotations
import requests
import re
from datetime import datetime, timedelta
import time
from dataclasses import dataclass
import json
from json import JSONEncoder, JSONDecoder
import os
from flask import Flask, jsonify, request, make_response, Response, g
import loghelper
import logging
from logging.config import dictConfig
from typing import List

# App setup #######################################################################################################################

# Properties ======================================================================================================================

# Logging -------------------------------------------------------------------------------------------------------------------------

class UTCFormatter(logging.Formatter):
    converter = time.gmtime
    
dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s | %(module)s >>> %(message)s",
                "datefmt": f"%B %d, %Y %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "default",
            },
            "time-rotate-file-logging": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": "GitHubUpdateChecker.log",
                "when": "W1",
                "interval": 10,
                "backupCount": 5,
                "formatter": "default",
            },
        },
        "root": {"level": "DEBUG", "handlers": ["console", "time-rotate-file-logging"]},
    }
)
"""Logging settings"""

# Create app ======================================================================================================================
app = Flask(__name__)
"""Flask app"""


# Init stuff ======================================================================================================================
from flask.logging import default_handler
app.logger.removeHandler(default_handler)

app.secret_key = "d8ca62a10b0650feb93429bb9eb17a3c968375d6db418b9e"
app.logger.setLevel(logging.DEBUG)
app.config["repoRepository"] = dict()
app.config["dateTimeFormat"] = "%Y-%m-%d %H:%M:%S"

# Classes #########################################################################################################################

# Repository information for help and updates *************************************************************************************
class RepositoryAccessManager:
    """
    Information to access the repository for update checking and help access.
    """
        
    _repoBase = "https://github.com/gusztavj/"
    """Base address of my repositories"""
    
    _repoApiBase = "https://api.github.com/repos/gusztavj/"
    """Base address of my repositories for API calls"""
    
    repoSlug = ""
    """Slug for the repository"""

    def repoUrl(self) -> str:
        return RepositoryAccessManager._repoBase + self.repoSlug
    """URL of the repository"""
        
    def repoReleaseApiUrl(self) -> str:
        """API URL to get latest release information"""
        return RepositoryAccessManager._repoApiBase + self.repoSlug + "releases/latest"
    
    def repoReleasesUrl(self) -> str:
        """URL of the releases page of the repository"""
        return RepositoryAccessManager._repoBase + self.repoSlug + "releases"    
    
    username = "gusztavj"
    """My username for API access"""
    
    def token(self):
        """A token restricted only to read code from Blender add-on repos (public anyway)"""
        os.environ['GITHUB_API_TOKEN'] = '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'
        return os.environ.get('GITHUB_API_TOKEN')
    
    
    def __init__(self, repoSlug: str):
        if repoSlug[len(repoSlug)-1] != "/":
            repoSlug = repoSlug + "/"
        
        self.repoSlug = repoSlug

# Request payload *****************************************************************************************************************
@dataclass 
class AppInfo:
    """
    Data structure parsed from the body of POST requests for checking updates.
    """
    
    repoSlug: str = ""
    """The slug of the repo as in `https://github.com/repos/<user>/<reposlug>`"""
    
    currentVersion: str = ""
    """Version number of the current version running in `x.y.z` format"""
    
# GitHub access data **************************************************************************************************************
class GitHubAccess:
    """
    Credentials to access GitHub.
    """
    pass

# Structured repository info ******************************************************************************************************
@dataclass
class Repository:
    """Release information associated with a GitHub repository"""
    
    # Properties ==================================================================================================================
    
    repoSlug: str = ""
    """The slug of the repo as in https://github.com/repos/<user>/<reposlug>"""
    
    checkFrequencyDays: int = 3
    """
    Frequency of checking for new updates (days).
    """
    
    latestVersion: str = ""
    """
    Version number of the latest release (the release tag from the repo) on GitHub.
    """
    
    latestVersionName: str = ""
    """
    Name of the latest release on GitHub.
    """
    
    lastCheckedTimestamp: datetime = datetime.now() - timedelta(days=checkFrequencyDays + 1)
    """
    Date and time of last successful check for updates. Defaults to a value to enforce checking as the default means no checks
    have been made yet.
    """
    
    releaseUrl: str = ""
    """
    The URL to get the latest release
    """
    
    repoUrl: str = ""
    """
    The URL of the repository
    """
    
    def __init__(self,
        repoSlug: str = "", 
        checkFrequencyDays: int = 3, 
        latestVersion: str = "", 
        latestVersionName: str = "", 
        lastCheckedTimestamp: datetime = None,
        releaseUrl: str = "", 
        repoUrl: str = ""):
        
        self.repoSlug = repoSlug
        self.checkFrequencyDays = checkFrequencyDays
        self.latestVersion = latestVersion
        self.latestVersionName = latestVersionName
        self.lastCheckedTimestamp = lastCheckedTimestamp if lastCheckedTimestamp is not None else datetime.now() - timedelta(days=checkFrequencyDays + 1)
        self.releaseUrl = releaseUrl
        self.repoUrl = repoUrl

class RepositoryEncoder(JSONEncoder):
        def default(self, o):
            if type(o) == datetime:
                return datetime.strftime(o, app.config["dateTimeFormat"])
            else:
                return o.__dict__

class RepositoryDecoder():
    
    @staticmethod    
    def decode(dct):
        try:
            repo = Repository(
                repoSlug = dct["repoSlug"],
                checkFrequencyDays = dct["checkFrequencyDays"],
                latestVersion = dct["latestVersion"],
                latestVersionName = dct["latestVersionName"],
                lastCheckedTimestamp = datetime.strptime(dct["lastCheckedTimestamp"], app.config["dateTimeFormat"]),
                releaseUrl = dct["releaseUrl"],
                repoUrl = dct["repoUrl"]
            )
            return repo
        except Exception as err:
            app.logger.exception(f"Could not decode repo store file for an error of {type(err).__name__}. Details: {err}")

class RepositoryStore(List[Repository]):
    pass
        
class RepositoryStoreManager:
    repos: RepositoryStore = RepositoryStore()
    _repoStore: str = "repo-repo.json"
    _repoRepositoryKey: str = "repoRepository"
    
    # Public functions ============================================================================================================

    @staticmethod
    def _populateRepositories():
        RepositoryStoreManager.repos = RepositoryStore()
        repoDict = app.config[RepositoryStoreManager._repoRepositoryKey]

        for repo in repoDict:
            RepositoryStoreManager.repos.append(RepositoryDecoder.decode(repo))

    # Load repository of known GitHub repositories --------------------------------------------------------------------------------
    @staticmethod
    def loadRepoRepository() -> RepositoryStore:
        """Load repository of known GitHub repositories and populate into app.config["repoRepository"]"""
        
        if RepositoryStoreManager.repos is not None and len(RepositoryStoreManager.repos) > 0:
            # Already loaded
            return
        
        if RepositoryStoreManager._repoRepositoryKey not in app.config.keys() or len(app.config[RepositoryStoreManager._repoRepositoryKey].keys()) == 0: 
            # No repository loaded or it's empty
        
            # Try to open repo repository file ----------------------------------------------------------------------------------------
            repoRepository = dict()
            
            if os.path.exists(RepositoryStoreManager._repoStore) and os.path.isfile(RepositoryStoreManager._repoStore):    
                try:
                    with open(RepositoryStoreManager._repoStore) as f:
                        repoRepository = json.load(f)
                        
                    app.config[RepositoryStoreManager._repoRepositoryKey] = repoRepository
                    
                    RepositoryStoreManager._populateRepositories()
                    
                except Exception as ex:
                    app.logger.error(f"Could not open repo repository '{RepositoryStoreManager._repoStore}' for an error of {type(ex).__name__}: {ex}")            
                    # Do not reset app.config["repoRepository"], it may contain some not too old information, better than nothing
                    
                    # Fail silently
                    return None
        
        RepositoryStoreManager._populateRepositories()
        
        return RepositoryStoreManager.repos
    
    # Save repository of known GitHub repositories ------------------------------------------------------------------------------------
    @staticmethod
    def saveRepoRepository() -> None:
        """Save repository of known GitHub repositories"""
        
        try:
            with open(RepositoryStoreManager._repoStore, "w") as f:
                f.write(json.dumps(RepositoryStoreManager.repos, cls=RepositoryEncoder, indent=4))
        except Exception as ex:
            app.logger.error(f"Could not save repo repository '{RepositoryStoreManager._repoStore}' for an error of {type(ex).__name__}: {ex}")
            


# Structured update info **********************************************************************************************************
@dataclass
class UpdateInfo():
    """
    A RepoInfo class extended with information whether an update is available for the client
    """
    
    repository: Repository
    """
    The repository about which this object collects update information
    """

            
    updateAvailable: bool = False
    """
    Tells whether an update is available (`True`) for the repository in `repository`.
    """
    
    
    def __init__(self):
        self.repository = Repository()
        self.updateAvailable = False
        pass


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
        responseJson = dict()
        responseJson["error"] = self.responseMessage
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






# API Endpoints ###################################################################################################################

# Test service endpoint ===========================================================================================================
@app.get("/foo")
def get_foo():
    """
    Test request

    Returns: Something in a response, depending on its ever changing code :)
    """
    app.config["x"] = app.config["x"] + 1
    return jsonify(app.config["x"])


# Get update information ==========================================================================================================
@app.post("/getUpdateInfo")
def checkUpdates(forceUpdateCheck: bool = False):
    """
    Performs update check for the add-on and caches results. The cache expires in some days as specified in
    `Repository.checkFrequencyDays`, and then new check is performed. Until that the
    cached information is served.
    """
    response = None
    
    try: # a big wrapper to not return implementation details to clients
    
        # Initialize logging ------------------------------------------------------------------------------------------------------
        try: # to initialize logger
            app.logger.info(f"Request: POST /getUpdateInfo from {request.remote_addr}")
        except Exception as ex:
            raise EnvironmentError(
                responseCode=500,
                responseMessage="You did everything right, but an internal error occurred.",
                logEntries=None, # as it's logging what isn't working
                innerException=ex)
                    
        # Parse request JSON in body ----------------------------------------------------------------------------------------------
        try: # to get and parse request body JSON
            requestJson = request.json            
            app.logger.debug(f"JSON in request body: {json.dumps(requestJson)}")
        except Exception as ex:
            whatHappened = f"POST body is not well-formed JSON. Details:\r\n{ex}"
            raise RequestError(
                responseCode=400,
                responseMessage=whatHappened,
                logEntries=[f"{whatHappened}"],
                innerException=ex)
                    
        # Validate request --------------------------------------------------------------------------------------------------------
        if "AppInfo" in requestJson.keys():
            appInfoJson = requestJson["AppInfo"]
            if "repoSlug" in appInfoJson.keys():
                repoSlug = appInfoJson["repoSlug"]
                if len(repoSlug) == 0:
                    whatHappened = "The value of the 'appSlug' key in the 'AppInfo' object is empty, can't find out which repo to check."
                    raise RequestError(
                        responseCode=400,
                        responseMessage=whatHappened,
                        logEntries=[whatHappened],
                        innerException=None)
                if repoSlug == "/":
                    whatHappened = "The value of the 'appSlug' key in the 'AppInfo' object is just a slash, can't find out which repo to check."
                    raise RequestError(
                        responseCode=400,
                        responseMessage=whatHappened,
                        logEntries=[whatHappened],
                        innerException=None)
                
                # Remove trailing slash to make neutral against slashing favors
                if repoSlug[-1] == "/": repoSlug = repoSlug[0:-1]
                    
                app.logger.info(f"Update check requested for repo: {repoSlug}")
            else:
                whatHappened = "The 'appSlug' key is missing from the 'AppInfo' object, can't find out which repo to check."
                raise RequestError(
                    responseCode=400,
                    responseMessage=whatHappened,
                    logEntries=[whatHappened],
                    innerException=None)
            if "currentVersion" in appInfoJson.keys():
                currentVersion = appInfoJson["currentVersion"]
                
                app.logger.info(f"Current version in request: {currentVersion}")
            else:
                whatHappened = "The 'currentVersion' key missing from the 'AppInfo' object, would not be able to determine if there's a newer version."
                raise RequestError(
                    responseCode=400,
                    responseMessage=whatHappened,
                    logEntries=[whatHappened],
                    innerException=None)                
        else:
            whatHappened = "'AppInfo' key missing from request"
            raise RequestError(
                responseCode=400,
                responseMessage=whatHappened,
                logEntries=[whatHappened],
                innerException=None)
        
        # Check force update setting
        if "forceUpdateCheck" in requestJson.keys():
            try:
                forceUpdateCheck = bool(requestJson['forceUpdateCheck'])
                
                app.logger.info(f"Update check forced in request: {forceUpdateCheck}")
            except ValueError as ve:
                whatHappened = f"Could not convert the value of forceUpdateCheck to bool. Details: {ve}"
                raise RequestError(
                    responseCode=400,
                    responseMessage=whatHappened,
                    logEntries=[whatHappened],
                    innerException=None)
        else:
            forceUpdateCheck = False            
            app.logger.debug(f"Force update check set to the default of {forceUpdateCheck}")

        # Load cached repository info if exist in repository store ----------------------------------------------------------------

        # Load repos from store on demand        
        repos = RepositoryStoreManager.loadRepoRepository()
        
        updateInfo: UpdateInfo = UpdateInfo()
        
        if RepositoryStoreManager.repos is not None and len(RepositoryStoreManager.repos) > 0: # the store is not empty
            # Load cached info
            for repo in RepositoryStoreManager.repos:
                if repo.repoSlug == repoSlug: # this is it
                    updateInfo.repository = repo
                    break # found it, need no more loops
        
        # Create new repo info if no stored info is available    
        if updateInfo.repository is None or updateInfo.repository.repoSlug is None or len(updateInfo.repository.repoSlug) == 0:
            updateInfo.repository = Repository()
            updateInfo.repository.repoSlug = repoSlug
        
        # See if update check is necessary ----------------------------------------------------------------------------------------
        
        # Check cache expiry only if update check is not forced
        if not forceUpdateCheck:                    
            # Check if update check shall be performed based on frequency
            try:                        
                delta = datetime.now() - updateInfo.repository.lastCheckedTimestamp
                if delta.days < updateInfo.repository.checkFrequencyDays: # Successfully checked for updates in the last checkFrequencyDays number of days
                    # Do not flood the repo API, use cached info
                    return make_response(jsonify(updateInfo), 200)
            except: # For example, lastCheck is None as no update check was ever performed yet
                # Could not determine when last update check was performed, do nothing (check it now)
                pass
        else: # turn forcing check off to prevent accidental flooding                
            forceUpdateCheck = False
            
        
        repoConn = RepositoryAccessManager(repoSlug=updateInfo.repository.repoSlug)
        timeout = 5
        try:                
            response = requests.get(repoConn.repoReleaseApiUrl(), timeout=timeout, auth=(repoConn.username, repoConn.token()))
        except requests.exceptions.Timeout as tex:
            # Timeout when checking GitHub
            app.logger.warning(f"Version checking timed out for {repoSlug}")
            
            # Don't bother the user, just return that there's no update
            updateInfo.updateAvailable = False
            
            raise UpdateCheckingError(
                responseMessage = "Request to GitHub timed out.", 
                responseCode = 500,
                logEntries = [f"Request to {repoConn.repoReleaseApiUrl()} timed out after {timeout} seconds"],
                innerException = None
                )    
        
        # For errors, enable raising exceptions
        if response.status_code != 200:
            whatHappened = ""
            match response.status_code:
                case 400:
                    whatHappened = "GitHub returned with HTTP 400. Something bad happened."
                case 401:
                    whatHappened = "Can't reach GitHub for invalid credentials."
                case 403 | 429: # API rate is exceeded
                    # Find when API rate is reset
                    apiLimitResetsAt = datetime.fromtimestamp(int(response.headers["x-ratelimit-reset"]))
                    
                    # Change last check date so that no new check is made before that time
                    updateInfo.repository.lastCheckedTimestamp = apiLimitResetsAt - timedelta(days=updateInfo.repository.checkFrequencyDays)
                    whatHappened = f"API limit exceeded, and will be reset at {apiLimitResetsAt}. " + \
                                    "Next non-forced check will be made afterwards only."
                case 404:
                    whatHappened = "GitHub returned with HTTP 404. The repo URL specified in the request does not exist. Probably it's just a typo."
                case _:
                    whatHappened = "An error occurred in GitHub Update Checker or on GitHub while checking for updates."
                    
            raise UpdateCheckingError(
                responseMessage = whatHappened, 
                responseCode = 500,
                logEntries = [whatHappened, "Details:", json.dumps(response.json())],
                innerException = None
                )                
    
        # Being here means a response has been received successfully
        
        # Save timestamp
        updateInfo.repository.lastCheckedTimestamp = datetime.now()        
    
        updateInfo.repository.latestVersionName = response.json()["name"]
        updateInfo.repository.latestVersion = response.json()["tag_name"]
        updateInfo.repository.repoUrl = repoConn.repoUrl()
        updateInfo.repository.releaseUrl = repoConn.repoReleaseApiUrl() 
        
        app.logger.debug(f"Update info received from GitHub: {updateInfo}")
        
        try:        
            # Trim leading v and eventual trailing qualifiers such as -alpha
            latestVersionCleaned = re.match("[v]((\d+\.)*(\d+)).*", updateInfo.repository.latestVersion)[1]
            
            # Parse into a list
            latestVersionTags = [int(t) for t in latestVersionCleaned.split(".")]
        except Exception as err:
            raise UpdateCheckingError(
                responseMessage="Invalid response received from GitHub. Can't tell latest version number.",
                responseCode=500,
                logEntries=[f"Invalid version number in GitHub's response: {updateInfo.repository.latestVersion}"],
                innerException=err                
            )
        
        updateInfo.updateAvailable = False
        
        # Get installed version (already stored as a list by Blender)
        try:
            currentVersionTags = [int(t) for t in str.split(currentVersion[1:-1], ",")]
            
            updateInfo.repository.currentVersion = ".".join([str(i) for i in currentVersionTags])
        
            if latestVersionTags[0] > currentVersionTags[0]:
                updateInfo.updateAvailable = True
            else:
                if latestVersionTags[1] > currentVersionTags[1]:
                    updateInfo.updateAvailable = True
                else:
                    if len(currentVersionTags) > 2 and latestVersionTags[2] > currentVersionTags[2]:
                        updateInfo.updateAvailable = True

            app.logger.debug(f"New version available: {updateInfo.updateAvailable}")
        except Exception as err:
            raise RequestError(
                responseMessage="Invalid version in 'currentVersion' of 'AppInfo'. Version shall be specified as (x, y, z).",
                responseCode=400,
                logEntries=[f"Invalid version number in request: {currentVersion}"],
                innerException=err                
            )
            
                    
        # Store info --------------------------------------------------------------------------------------------------------------
        
        # Check if the repo is registered (even if it was not at the beginning, since a parallel request
        # might have resulted in adding it) and add the repo to the store if it's still not there
        if len([repo for repo in RepositoryStoreManager.repos if repo.repoSlug == repoSlug]) == 0:            
            # Add the repo info created right before
            RepositoryStoreManager.repos.append(updateInfo.repository)

        # By reaching this point, at least the last check's timestamp has been updated, so let's save it
        # to the repo store file for later use when the app is restarted for some reason
        RepositoryStoreManager.saveRepoRepository()
        
        # Pack response with a proper response code
        response = make_response(jsonify(updateInfo), 200)
                
        
    
    except (EnvironmentError, RequestError, UpdateCheckingError) as err:
        app.logger.error(f"{type(err).__name__} occurred")        
        # Log additional message(s)        
        [app.logger.error(f"\t{line}") for line in err.logEntries]
        if err.innerException is not None:
            app.logger.debug(f"Error details: {'-' * 40}")
            app.logger.debug(f"{err.innerException}")
            app.logger.debug(f"-" * 50)
        app.logger.info(f"Information returned: HTTP {err.responseCode}: {err.responseMessage}")
        
        response = err.response()
        
    except Exception as err:
        whatHappened = f"An unexpected exception of {type(err).__name__} occurred."
        app.logger.exception(f"{whatHappened}")
        app.logger.debug(f"Details: {err}")
        responseJson = dict()
        responseJson["error"] = whatHappened
        response = make_response(jsonify(responseJson), 500)
    finally:
        pass
        
    return response