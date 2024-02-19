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
from dataclasses import dataclass
from datetime import datetime, timedelta
from json import JSONEncoder, JSONDecoder
from logging.config import dictConfig
from typing import List
import contextlib
import json
import logging
import os
import re
import requests
import time

from flask import Flask, jsonify, request, make_response, Response, g
from flask.logging import default_handler
from customExceptions import RequestError, EnvironmentError, UpdateCheckingError

import repository
from repository import RepositoryAccessManager, Repository, RepositoryStoreManager, UpdateInfo

import importlib


# Preparatory steps ===============================================================================================================

# Convert timestamps to UTC -------------------------------------------------------------------------------------------------------
class UTCFormatter(logging.Formatter):
    """Formatter class for logging with UTC time.

    This class extends the logging.Formatter class and overrides the converter attribute to use the `gmtime` function for UTC time conversion.

    """
    converter = time.gmtime

# Log configuration ---------------------------------------------------------------------------------------------------------------
dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s | %(module)s >>> %(message)s",
                "datefmt": "%B %d, %Y %H:%M:%S",
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
        "root": {
            "level": "DEBUG",
            "handlers": ["console", "time-rotate-file-logging"],
        },
    }
)
"""Logging settings"""

# Create app ======================================================================================================================
app = Flask(__name__)
"""Flask app"""

repository.app = app

dateTimeFormat = "%Y-%m-%d %H:%M:%S"
"""Date and time format for business data"""

# Init stuff ======================================================================================================================
app.logger.removeHandler(default_handler)
app.secret_key = "d8ca62a10b0650feb93429bb9eb17a3c968375d6db418b9e"
app.logger.setLevel(logging.DEBUG)
app.config["repoRepository"] = {}
app.config["dateTimeFormat"] = dateTimeFormat



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
        response, updateInfo = _getUpdateInfoFromGitHub(repoConn, updateInfo)                

        # Being here means a response has been received successfully

        # Populate info from response
        _populateUpdateInfoFromGitHubResponse(response, updateInfo, repoConn) 

        app.logger.debug(f"Update info received from GitHub: {updateInfo}")

        # See if there is an update and set current version in response
        updateInfo.updateAvailable = _isUpdateAvailable(updateInfo, clientCurrentVersion)

        # Store info --------------------------------------------------------------------------------------------------------------

        # Check if the repo is registered (even if it was not at the beginning, since a parallel request
        # might have resulted in adding it) and add the repo to the store if it's still not there
        if not [repo for repo in RepositoryStoreManager.repos if repo.getRepoSlug() == updateInfo.repository.getRepoSlug()]:
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
            app.logger.debug("-" * 50)
        app.logger.info(f"Information returned: HTTP {err.responseCode}: {err.responseMessage}")

        response = err.response()

    except Exception as err:
        whatHappened = f"An unexpected exception of {type(err).__name__} occurred."
        app.logger.exception(f"{whatHappened}")
        app.logger.debug(f"Details: {err}")
        responseJson = {"error": whatHappened}
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
def _getUpdateInfoFromGitHub(repoConn: RepositoryAccessManager, updateInfo: UpdateInfo) -> tuple[Response, UpdateInfo]:
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
        with requests.get(repoConn.repoReleaseApiUrl(), timeout=timeout, auth=(repoConn.username, repoConn.token())) as response:
            pass  # Process the response here as needed
    except requests.exceptions.Timeout as tex:
        # Timeout when checking GitHub
        app.logger.warning(f"Version checking timed out for {updateInfo.repository.getRepoSlug()}")

            # Don't bother the user, just return that there's no update
        updateInfo.updateAvailable = False

        raise UpdateCheckingError(
                responseMessage = "Request to GitHub timed out.", 
                responseCode = 500,
                logEntries = [f"Request to {repoConn.repoReleaseApiUrl()} timed out after {timeout} seconds"],
                innerException = None
                ) from tex  

    # For errors, enable raising exceptions
    if response.status_code != 200:
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

                updateInfo.repository.setLastCheckedTimestamp(apiLimitResetsAt - timedelta(days=updateInfo.repository.getCheckFrequencyDays()))
                whatHappened = f"API limit exceeded, and will be reset at {apiLimitResetsAt}. Next non-forced check will be made afterwards only."
            case 404:
                whatHappened = "GitHub returned with HTTP 404. The repo URL specified in the request does not exist. Unknown repo specified?"
                responseCode = 404
            case _:
                whatHappened = "An error occurred in GitHub Update Checker or on GitHub while checking for updates."
                responseCode = 500

        raise UpdateCheckingError(
                responseMessage = whatHappened, 
                responseCode = responseCode,
                logEntries = [whatHappened, "Details:", json.dumps(response.json())],
                innerException = None
                )

    return response, updateInfo

# Parse request body received from user ===========================================================================================
def _parseRequest(requestJson) -> tuple[bool, str, str]:
    """Parse the request JSON and extract relevant information.

    Args:
        requestJson (dict): The request JSON object.

    Returns:
        tuple: A tuple containing the forceUpdateCheck (bool) telling if update shall be forced, repoSlug (str) specifying the repo
        to provide information about, and clientCurrentVersion (str) specifying the current version of the app running on the client.

    Raises:
        customExceptions.RequestError: If there is an error parsing the request JSON.

    """
    if "AppInfo" in requestJson.keys():
        appInfoJson = requestJson["AppInfo"]
        if "repoSlug" in appInfoJson.keys():
            repoSlug = Repository.ensureRepoSlug(repoSlugToSet=appInfoJson['repoSlug'], fromCustomerRequest=True)
            app.logger.info(f"Update check requested for repo: {repoSlug}")
        else:
            whatHappened = "The 'repoSlug' key is missing from the 'AppInfo' object, can't find out which repo to check."
            raise RequestError(
                    responseCode=400,
                    responseMessage=whatHappened,
                    logEntries=[whatHappened],
                    innerException=None)
        if "currentVersion" in appInfoJson.keys():
            clientCurrentVersion = appInfoJson["currentVersion"]

            app.logger.info(f"Current version in request: {clientCurrentVersion}")
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
            if isinstance(requestJson['forceUpdateCheck'], bool):
                    # Only process if it's bool
                forceUpdateCheck = bool(requestJson['forceUpdateCheck'])
            else:
                    # For all other values make it false to stay on the safe side
                forceUpdateCheck = False

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
        latestVersionCleaned = re.match("[v]((\d+\.)*(\d+)).*", updateInfo.repository.latestVersion)[1]

        # Parse into a list
        latestVersionTags = [int(t) for t in latestVersionCleaned.split(".")]
    except Exception as err:
        raise UpdateCheckingError(
            responseMessage="Invalid response received from GitHub. Can't tell latest version number.",
            responseCode=500,
            logEntries=[f"Invalid version number in GitHub's response: {updateInfo.repository.latestVersion}"],
            innerException=err                
        ) from err

    updateAvailable = False

    # Get installed version (already stored as a list by Blender)
    try:
        currentVersionTags = [int(t) for t in str.split(currentVersion[1:-1], ",")]

        currentVersion = ".".join([str(i) for i in currentVersionTags])

        if latestVersionTags[0] > currentVersionTags[0]:
            updateAvailable = True
        elif latestVersionTags[1] > currentVersionTags[1]:
            updateAvailable = True
        elif len(currentVersionTags) > 2 and latestVersionTags[2] > currentVersionTags[2]:
            updateAvailable = True

        app.logger.debug(f"New version available: {updateInfo.updateAvailable}")

    except Exception as err:
        raise RequestError(
            responseMessage="Invalid version in 'currentVersion' of 'AppInfo'. Version shall be specified as (x, y, z).",
            responseCode=400,
            logEntries=[f"Invalid version number in request: {currentVersion}"],
            innerException=err                
        ) from err

    return updateAvailable