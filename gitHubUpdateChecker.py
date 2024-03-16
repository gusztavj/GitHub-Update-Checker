# T1nk-R's GitHub Update Checker // gitHubUpdateChecker.py
#
# Version: Please appVersion below.
#
# This module is responsible for running the web server app for checking updates.
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
#
# *********************************************************************************************************************************

# Imports #########################################################################################################################

# Future -- must be first ---------------------------------------------------------------------------------------------------------
from __future__ import annotations

# Standard libraries --------------------------------------------------------------------------------------------------------------
import contextlib
import json
import logging
import os
import re
import time
import uuid
import sys

# Standard library elements -------------------------------------------------------------------------------------------------------
from datetime import datetime, timedelta
from typing import List

from dataclasses import dataclass
from json import JSONEncoder, JSONDecoder
from logging.config import dictConfig

# Third-party imports -------------------------------------------------------------------------------------------------------------
import requests

# Flask
from flask import Flask, jsonify, request, make_response, Response, g, has_request_context
from flask.logging import default_handler

# Own libraries and elements ------------------------------------------------------------------------------------------------------
from customExceptions import RequestError, EnvironmentError, UpdateCheckingError

import repository
from repository import RepositoryAccessManager, Repository, RepositoryStoreManager, UpdateInfo



# Init stuff ======================================================================================================================
appVersion = "1.0.2-dev"

sys.path.insert(0, os.path.dirname(__file__))

dateTimeFormat = "%Y-%m-%d %H:%M:%S"
"""Date and time format for business data"""


# Convert timestamps to UTC -------------------------------------------------------------------------------------------------------
class UTCFormatter(logging.Formatter):
    """Formatter class for logging with UTC time.

    This class extends the logging.Formatter class and overrides the converter attribute to use the `gmtime` function for UTC time conversion.

    """
    converter = time.gmtime

# Log configuration ---------------------------------------------------------------------------------------------------------------

class RequestFormatter(logging.Formatter):
    def format(self, record):
        record.url = request.url if has_request_context() and request else 'N/A'
        record.remote_addr = request.remote_addr if has_request_context() and request else 'N/A'
        record.session_id = g.get('session_id', 'unknown') if has_request_context() else 'N/A'
        return super().format(record)


dictConfig(
    {
        "version": 1,
        "formatters": {
            "myFormatter": {
                '()': "gitHubUpdateChecker.RequestFormatter",
                "format": f"[%(asctime)s] %(levelname)-8s\t|%(remote_addr)s\t|session_id=%(session_id)s\t|%(module)s\t >>> %(message)s",
                "datefmt": "%B %d, %Y %H:%M:%S"
            },
            "default": {                
                "format": f"[%(asctime)s] %(levelname)s\t|%(module)s\t >>> %(message)s",
                "datefmt": "%B %d, %Y %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "myFormatter"
            },
            "time-rotate-file-logging": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "filename": "GitHubUpdateChecker.log",
                "when": "W1",
                "interval": 10,
                "backupCount": 5,
                "formatter": "myFormatter"
            },
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["console", "time-rotate-file-logging"]
        },
    }
)
"""Logging settings"""

# App factory =====================================================================================================================
def create_app(test_config=None):
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(SECRET_KEY='dev')

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    with contextlib.suppress(OSError):
        os.makedirs(app.instance_path)
        
    app.logger.removeHandler(default_handler)
    for handler in app.logger.handlers:
        handler.setFormatter(RequestFormatter)
    
    # handler = logging.StreamHandler()
    # formatter = RequestFormatter()
    # handler.setFormatter(formatter)
    # app.logger.addHandler(handler)
    
    app.secret_key = "d8ca62a10b0650feb93429bb9eb17a3c968375d6db418b9e"
    
    makeANoteOnLogging: bool = False
    logWhat: str = ""    
    
    # Try to read configured log level or fall back to a default one
    try:
        requestedLevel = eval(os.environ.get("LOG_LEVEL"))        
        
        if requestedLevel in [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]:
            app.logger.setLevel(requestedLevel)            
        else:
            app.logger.setLevel(logging.INFO)
            makeANoteOnLogging = True
            logWhat = f"LOG_LEVEL set to {os.environ.get('LOG_LEVEL')}, and cannot be interpreted or applied."
        
    except Exception as err:
        app.logger.setLevel(logging.INFO)
        makeANoteOnLogging = True
        logWhat = f"LOG_LEVEL is '{os.environ.get('LOG_LEVEL')}'. Can't eval LOG_LEVEL for {err}"        
    
    app.logger.critical(f"Starting gitHubUpdateChecker at {datetime.now()}")
    app.logger.critical(f"Log level set to {app.logger.getEffectiveLevel()}")

    # If we could not read the log level from the environment variable, log an error about it    
    if makeANoteOnLogging:
        app.logger.critical(logWhat)

    
    app.config["repoRepository"] = {}
    app.config["repoRegistry"] = {}
    app.config["dateTimeFormat"] = dateTimeFormat
        
    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    return app



# Boot up =========================================================================================================================
app = create_app()
repository.app = app

# Event handlers ###################################################################################################################

# Generate session ID at request creation===========================================================================================
@app.before_request
def before_request():
    """Create a session ID.
    
    Returns: A unique session ID.
    """
    g.session_id = uuid.uuid4()


# API Endpoints ###################################################################################################################

# Test service endpoint ===========================================================================================================
@app.get("/info")
def version():
    """
    Returns verion information.
    """
    
    about = {
        "Application Name": "GitHub Update Checker by T1nk-R",
        "Version": appVersion,
        "Author": "T1nk-R (Gusztáv Jánvári)",
        "Author's GitHub": "https://github.com/gusztavj/",
        "Author's Website": "https://gusztav.janvari.name/",
        "Author's Portfolio": "https://gusztav.janvari.name/t1nk-r/",
        "Help and support": "https://github.com/gusztavj/GitHub-Update-Checker",        
        "Updates": "https://github.com/gusztavj/GitHub-Update-Checker/releases"
    }        
    
    return make_response(jsonify(about), 200)


# Get update information ==========================================================================================================
@app.post("/getUpdateInfo")
def checkUpdates():
    """
    Performs update check for the add-on and caches results. The cache expires in some days as specified in
    `Repository.getCheckFrequencyDays()`, and then new check is performed. Until that the
    cached information is served.
    """
    response = None

    try: # a big wrapper to not return implementation details to clients

        # Initialize logging ------------------------------------------------------------------------------------------------------
        try: # to initialize logger
            app.logger.info(f"Request: POST /getUpdateInfo from {request.remote_addr}")
        except Exception as error:
            raise EnvironmentError(
                responseCode=500,
                responseMessage="You did everything right, but an internal error occurred.",
                logEntries=None, # as it's logging what isn't working
                innerException=error) from error

        # Parse request JSON in body ----------------------------------------------------------------------------------------------
        try: # to get and parse request body JSON
            requestJson = request.json            
            app.logger.debug(f"JSON in request body: {json.dumps(requestJson)}")
        except Exception as error:
            whatHappened = f"POST body is not well-formed JSON. Details:\r\n{error}"
            raise RequestError(
                responseCode=400,
                responseMessage=whatHappened,
                logEntries=[f"{whatHappened}"],
                innerException=error) from error

        # Validate request --------------------------------------------------------------------------------------------------------

        forceUpdateCheck, repoSlug, clientCurrentVersion = _parseRequest(requestJson)

        # Load cached repository info if exist in repository store ----------------------------------------------------------------

        # Get stored or brand new updateInfo        
        updateInfo = RepositoryStoreManager.getUpdateInfoFromRepoRepository(repoSlug)

        # See if update check is necessary ----------------------------------------------------------------------------------------

        # Check cache expiry only if update check is not forced
        if not forceUpdateCheck:            
            # Check if update check shall be performed based on frequency and suppress error if it cannot to not bother the user
            with contextlib.suppress(Exception):
                delta = datetime.now() - updateInfo.repository.getLastCheckedTimestamp()
                if delta.days < updateInfo.repository.getCheckFrequencyDays(): # recently checked
                    # Successfully checked for updates in the last checkFrequencyDays number of days
                    # so no need for a repeated check.

                    # See if there is an update and set current version in response
                    updateInfo.updateAvailable = _isUpdateAvailable(updateInfo, clientCurrentVersion)

                    # Do not flood the repo API, use cached info
                    return make_response(jsonify(updateInfo), 200)

        else: # turn forcing check off to prevent accidental flooding                
            forceUpdateCheck = False

        # Submit request ----------------------------------------------------------------------------------------------------------
        repoConn = RepositoryAccessManager(repoSlug=updateInfo.repository.getRepoSlug())
        
        # Submit request to GitHub. If it fails, we'll continue working with cached data
        try:
            response = _getUpdateInfoFromGitHub(repoConn)
        
            # Populate info from response
            _populateUpdateInfoFromGitHubResponse(response, updateInfo, repoConn) 

            app.logger.debug(f"Update info received from GitHub: {updateInfo}")
            
        except UpdateCheckingError as err:
            if hasattr(err, "apiLimitResetsAt"): 
                # Rate limit exceeded, set last check timestamp to the future after ban expiry
                # to make sure to not flood GitHub till that
                updateInfo.repository.lastCheckedTimestamp = err.apiLimitResetsAt - timedelta(days=updateInfo.repository.getCheckFrequencyDays())                
            elif len(updateInfo.repository.latestVersion) == 0:
                # We could not make request and has no cached info on the repo, so let's fail here
                raise err
        
        # See if there is an update and set current version in response
        updateInfo.updateAvailable = _isUpdateAvailable(updateInfo, clientCurrentVersion)        

        # Store info --------------------------------------------------------------------------------------------------------------

        # Check if the repo is registered (even if it was not at the beginning, since a parallel request
        # might have resulted in adding it) and add the repo to the store if it's still not there
        if not [repo for repo in RepositoryStoreManager.repoStore if repo.getRepoSlug() == updateInfo.repository.getRepoSlug()]:
            # Add the repo info created right before
            RepositoryStoreManager.repoStore.append(updateInfo.repository)

        # By reaching this point, at least the last check's timestamp has been updated, so let's save it
        # to the repo store file for later use when the app is restarted for some reason
        RepositoryStoreManager.saveRepoRepository()

        # Pack response with a proper response code
        response = make_response(jsonify(updateInfo), 200)


    except (EnvironmentError, RequestError, UpdateCheckingError) as err:
        # Try to log but don't make more trouble if the root of the problem is a failure in logging
        with contextlib.suppress(Exception):
            app.logger.error(f"{type(err).__name__} occurred")
            
            # Log additional message(s)        
            [app.logger.error(f"\t{line}") for line in err.logEntries]
            if err.innerException is not None:
                app.logger.debug(f"Error details: {'-' * 40}")
                app.logger.debug(f"{err.innerException}")
                app.logger.debug("-" * 50)
            app.logger.info(f"Information returned: HTTP {err.responseCode}: {err.responseMessage}")
            
        response = err.response()

    except Exception as err:
        whatHappened = f"An unexpected exception of {type(err).__name__} occurred."
        
        # Try to log but don't make more trouble if the root of the problem is a failure in logging
        with contextlib.suppress(Exception):
            errorKey = uuid.uuid4()
            
            app.logger.exception(f"Error key {errorKey}: An {type(err).__name__} exception has been thrown.")
            app.logger.debug(f"Details: {err}")
                        
            responseJson = {"error": f"An internal error occurred. Mention the following error key when requesting support: {errorKey}"}
            response = make_response(jsonify(responseJson), 500)
    finally:
        pass

    return response

# Populate update info object from GitHub response ================================================================================
def _populateUpdateInfoFromGitHubResponse(response: Response, updateInfo: UpdateInfo, repoConn: RepositoryAccessManager):
    """Populate the update information from the GitHub response.

    Args:
        response (Response): The response object from the GitHub API.
        updateInfo (UpdateInfo): The update information object to populate.
        repoConn (RepositoryAccessManager): The repository connection object.

    Returns:
        None. Expect the variable passed in the `updateInfo` argument to be updated.

    """
    # Save timestamp
    updateInfo.repository.setLastCheckedTimestamp(datetime.now())

    updateInfo.repository.latestVersionName = response.json()["name"]
    updateInfo.repository.latestVersion = response.json()["tag_name"]
    updateInfo.repository.repoUrl = repoConn.repoUrl()
    updateInfo.repository.releaseUrl = repoConn.repoReleaseApiUrl()


# Submit request to GitHub ========================================================================================================
def _getUpdateInfoFromGitHub(repoConn: RepositoryAccessManager) -> Response:
    # sourcery skip: extract-method
    """Get update information from GitHub.

    Args:
        repoConn (repository.RepositoryAccessManager): A repository connection object.
        updateInfo (repository.UpdateInfo): The update information object.

    Returns:
        tuple[Response, repository.UpdateInfo]: A tuple containing the response object and the updated updateInfo object.

    Raises:
        customExceptions.UpdateCheckingError: If there is an error while checking for updates.

    """
    
    timeout = 5
    try:                
        response = requests.get(repoConn.repoReleaseApiUrl(), timeout=timeout, auth=(repoConn.username(), repoConn.token()))
        
    except requests.exceptions.Timeout as tex:
        whatHappened = f"Request to {repoConn.repoReleaseApiUrl()} timed out after {timeout} seconds"

        raise UpdateCheckingError(
            responseMessage = "", 
            responseCode = 200,
            logEntries = [whatHappened],
            innerException = None
            ) from tex
        
    except Exception as ex: 
        whatHappened = f"Unexpected error of {type(ex).__name__} occurred. Details: {ex}"

        raise UpdateCheckingError(
            responseMessage = "", 
            responseCode = 200,
            logEntries = [whatHappened],
            innerException = None
            ) from ex

    # For errors, enable raising exceptions
    if response.status_code != 200:
        
        err = UpdateCheckingError(responseMessage="", responseCode="", logEntries=[], innerException=None)
        
        responseCode = 500
        whatHappened = ""
        match response.status_code:
            case 400:
                whatHappened = (
                    "GitHub returned with HTTP 400. Something bad happened."
                )
            case 401:
                whatHappened = "Can't reach GitHub for invalid credentials."
            case 403 | 429:  # API rate is exceeded
                # Find when API rate is reset
                apiLimitResetsAt = datetime.fromtimestamp(
                    int(response.headers["x-ratelimit-reset"])
                )
                err.apiLimitResetsAt = apiLimitResetsAt
                whatHappened = f"API limit exceeded, and will be reset at {apiLimitResetsAt}. Next non-forced check will be made afterwards only."
            case 404:
                whatHappened = "GitHub returned with HTTP 404. The repo URL specified in the request does not exist. Unknown repo specified?"
                responseCode = 404
            case _:
                whatHappened = "An error occurred in GitHub Update Checker or on GitHub while checking for updates."
                responseCode = 500

        
        err.responseMessage = whatHappened
        err.responseCode = responseCode
        err.logEntries = [whatHappened, "Details:", json.dumps(response.json())]
        err.innerException = None
        raise err

    return response

# Parse request body received from user ===========================================================================================
def _parseRequest(requestJson: dict) -> tuple[bool, str, str]:
    """Parse the request JSON and extract relevant information.

    Args:
        requestJson (dict): The request JSON object.

    Returns:
        tuple: A tuple containing the forceUpdateCheck (bool) telling if update shall be forced, repoSlug (str) specifying the repo
        to provide information about, and clientCurrentVersion (str) specifying the current version of the app running on the client.

    Raises:
        customExceptions.RequestError: If there is an error parsing the request JSON.

    """
    
    if requestJson is None:
        whatHappened = "No payload found in request. Don't know what to check."
        raise RequestError(
                responseCode=400,
                responseMessage=whatHappened,
                logEntries=[whatHappened],
                innerException=None)

    if not isinstance(requestJson, dict):
        whatHappened = "Invalid payload found in request. Don't know what to check. Payload shall be a JSON compliant to the gitHubUpdateCheckerRequest.json schema"
        raise RequestError(
                responseCode=400,
                responseMessage=whatHappened,
                logEntries=[whatHappened],
                innerException=None)

    if "appInfo" in requestJson:
        appInfoJson = requestJson["appInfo"]
        if "repoSlug" in appInfoJson.keys():                                    
            repoSlug = Repository.ensureRepoSlug(repoSlugToSet=appInfoJson['repoSlug'], fromCustomerRequest=True)
            
            if RepositoryStoreManager.isRepoRegistered(repoSlug):            
                app.logger.info(f"Update check requested for repo: {repoSlug}")
            else:
                whatHappened = f"The 'repoSlug' key specifies an unregistered repository '{repoSlug}'."
                raise RequestError(
                        responseCode=403,
                        responseMessage=whatHappened,
                        logEntries=[whatHappened],
                        innerException=None)
        else:
            whatHappened = "The 'repoSlug' key is missing from the 'appInfo' object, can't find out which repo to check."
            raise RequestError(
                    responseCode=400,
                    responseMessage=whatHappened,
                    logEntries=[whatHappened],
                    innerException=None)
        if "currentVersion" in appInfoJson.keys():   
            clientCurrentVersion = appInfoJson["currentVersion"]

            if len(clientCurrentVersion) == 0:
                whatHappened = "The 'currentVersion' key is set to an empty string. A valid version number is expected."
                raise RequestError(
                    responseCode=400,
                    responseMessage=whatHappened,
                    logEntries=[whatHappened],
                    innerException=None)

            try: # to parse to validate
                cvTags = [int(t) for t in str.split(clientCurrentVersion, ".")]
                
                # Check how many segments it has                
                if len(cvTags) != 3:
                    whatHappened = f"Invalid version in 'currentVersion' of 'appInfo'. Version shall be specified as 'x.y.z' or 'x.y.z-foo'. Received '{clientCurrentVersion}'."
                    raise RequestError(
                        responseMessage=whatHappened,
                        responseCode=400,
                        logEntries=[whatHappened],
                        innerException=err                
                    )

            except Exception as err:
                if isinstance(err, RequestError):
                    # It's us who raised and initialized it, let's just pass it on
                    raise

                whatHappened = f"Invalid version number in request: {clientCurrentVersion}"
                raise RequestError(
                    responseMessage="Invalid version in 'currentVersion' of 'appInfo'. Version shall be specified as 'x.y.z' or 'x.y.z-foo'.",
                    responseCode=400,
                    logEntries=[whatHappened],
                    innerException=err                
                ) from err
                
            app.logger.info(f"Current version in request: {clientCurrentVersion}")
        else:
            whatHappened = "The 'currentVersion' key missing from the 'appInfo' object, would not be able to determine if there's a newer version."
            raise RequestError(
                    responseCode=400,
                    responseMessage=whatHappened,
                    logEntries=[whatHappened],
                    innerException=None)
    else:
        whatHappened = "'appInfo' key missing from request"
        raise RequestError(
                responseCode=400,
                responseMessage=whatHappened,
                logEntries=[whatHappened],
                innerException=None)

        # Check force update setting
    if "forceUpdateCheck" in requestJson:
        try:
            if isinstance(requestJson['forceUpdateCheck'], bool):
                # Only process if it's bool
                forceUpdateCheck = bool(requestJson['forceUpdateCheck'])
            else:
                # Try to parse string value, or fall back to false to stay on the safe side
                forceUpdateCheck = str.lower(requestJson['forceUpdateCheck']) == 'true'
            app.logger.info(f"Update check forced in request: {forceUpdateCheck}")
        except ValueError as ve:
            whatHappened = f"Could not convert the value of forceUpdateCheck to bool. Details: {ve}"
            raise RequestError(
                    responseCode=400,
                    responseMessage=whatHappened,
                    logEntries=[whatHappened],
                    innerException=None) from ve
    else:
        forceUpdateCheck = False            
        app.logger.debug(f"Force update check set to the default of {forceUpdateCheck}")
    return forceUpdateCheck, repoSlug, clientCurrentVersion

def _isUpdateAvailable(updateInfo: UpdateInfo, currentVersion: str) -> bool:
    
    try:        
        # Trim leading v and eventual trailing qualifiers such as -alpha
        latestVersionCleaned = re.match("v?((\d+\.)*(\d+)).*", updateInfo.repository.latestVersion)[1]

        # Parse into a list
        latestVersionTags = [int(t) for t in latestVersionCleaned.split(".")]
    except Exception as err:
        whatHappened: str
        
        if updateInfo is None:
            whatHappened = "The updateInfo argument was set to None"
        elif not hasattr(updateInfo, "repository"):
            whatHappened = "The object passed in updateInfo has no repository property"
        elif updateInfo.repository is None:
            whatHappened = "The repository property of the object passed in updateInfo is set to None"
        elif not hasattr(updateInfo.repository, "latestVersion"):
            whatHappened = "The repository property of the object passed in updateInfo has no latestVersion property"
        elif len(updateInfo.repository.latestVersion) == 0:
            whatHappened = "The latestVersion property in updateInfo is an empty string"
        else:
            whatHappened = f"Invalid version number in GitHub's response: {updateInfo.repository.latestVersion}"
            
        raise UpdateCheckingError(
            responseMessage="For an internal error, can't tell latest version number.",
            responseCode=500,
            logEntries=[whatHappened],
            innerException=err                
        ) from err

    updateAvailable = False

    # Get installed version (already stored as a list by Blender)
    try:
        currentVersionTags = [int(t) for t in str.split(currentVersion, ".")]

        currentVersion = ".".join([str(i) for i in currentVersionTags])

        if latestVersionTags[0] > currentVersionTags[0]:
            updateAvailable = True

        # Minor comparison only applies if majors are the same            
        elif latestVersionTags[0] == currentVersionTags[0] \
            and latestVersionTags[1] > currentVersionTags[1]:
                
            updateAvailable = True
        
        # Patch comparison only applies if majors and minors are the same
        elif latestVersionTags[0] == currentVersionTags[0] \
            and latestVersionTags[1] == currentVersionTags[1] \
            and len(currentVersionTags) > 2 \
            and latestVersionTags[2] > currentVersionTags[2]:
            
            updateAvailable = True

        app.logger.debug(f"New version available: {updateInfo.updateAvailable}")

    except Exception as err:
        whatHappened = f"Invalid version number in request: {currentVersion}" if currentVersion else "None was passed in the currentVersion argument of _isUpdateAvailable"
        raise RequestError(
            responseMessage="Invalid version in 'currentVersion' of 'appInfo'. Version shall be specified as 'x.y.z'.",
            responseCode=400,
            logEntries=[whatHappened],
            innerException=err                
        ) from err

    return updateAvailable