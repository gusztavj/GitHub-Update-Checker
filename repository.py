# T1nk-R's GitHub Update Checker // repositry.py
#
# This module is responsible for managing repository information.
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

# Future -- must be first ---------------------------------------------------------------------------------------------------------
from __future__ import annotations

# Standard libraries --------------------------------------------------------------------------------------------------------------
import json
import os
import re
import uuid

# Standard library elements -------------------------------------------------------------------------------------------------------
from dataclasses import dataclass
from datetime import datetime, timedelta
from json import JSONEncoder, JSONDecoder
from typing import List, Optional

# Own libraries and elements ------------------------------------------------------------------------------------------------------
from customExceptions import RequestError, EnvironmentError

# Global stuff ####################################################################################################################
app = None
"""Reference to the Flask app, set from the gitHubUpdateChecker.py module."""


# Classes #########################################################################################################################

# Repository information for help and updates *************************************************************************************
class RepositoryAccessManager:
    """
    Information to access the repository for update checking and help access.
    """
    # Private stuff ===============================================================================================================
    
    _repoBase: str ="https://github.com/gusztavj/"
    """Base address of my repositories"""
    
    _repoApiBase: str = "https://api.github.com/repos/gusztavj/"
    """Base address of my repositories for API calls"""

    
    # Public attributes ===========================================================================================================
    
    _repoSlug: str = ""
    """Slug for the repository"""
    
    # Property management =========================================================================================================
    
    # Set repo slug ---------------------------------------------------------------------------------------------------------------
    def setRepoSlug(self, repoSlugToSet: str) -> None:
        """Property validator for `repoSlug`. Validates proposed value, and correct if necessary and possible.

        Args:
            repoSlugToSet (str): The value to set for the `repoSlug` property.

        Raises:
            EnvironmentError: Proposed value is of wrong type or not a valid URI segment.

        Returns:
            The normalized repo slug, corrected if necessary.

        """
        
        self._repoSlug = Repository.ensureRepoSlug(repoSlugToSet)
        
    # Get repo slug ---------------------------------------------------------------------------------------------------------------
    def getRepoSlug(self) -> str | None:
        """Returns the repo's slug

        Returns:
            str | None: The repo's slug
        """
        return self._repoSlug

    # Public stuff ================================================================================================================
    
    # Get the URL of the repo -----------------------------------------------------------------------------------------------------
    def repoUrl(self) -> str:
        """URL of the repository"""
            
        return self._repoBase + self.getRepoSlug() + "/"
    
    
    # Get Releases API address of the repo ----------------------------------------------------------------------------------------
    def repoReleaseApiUrl(self) -> str:
        """API URL to get latest release information"""
        
        return self._repoApiBase + self.getRepoSlug() + "/releases/latest"
    
    # Get Releases page of the repo -----------------------------------------------------------------------------------------------
    def repoReleasesUrl(self) -> str:
        """URL of the releases page of the repository"""
        
        return self._repoBase + self.getRepoSlug() + "/releases/"    

    # Get username ----------------------------------------------------------------------------------------------------------------
    def username(self):  # sourcery skip: class-extract-method
        """Username for API access"""
        
        username = os.environ.get("GITHUB_UPDATE_CHECKER_GITHUB_USER_NAME")    
        
        if username is None:
            raise ValueError("The GitHub user name is not set.")
        if len(username) == 0:
            raise ValueError("The GitHub user name is set to an empty string.")                
        
        return username
    
    # Get token -------------------------------------------------------------------------------------------------------------------
    def token(self):
        """GitHub token"""
        
        token = os.environ.get('GITHUB_UPDATE_CHECKER_GITHUB_API_TOKEN')
                
        if token is None:
            raise ValueError("The GitHub access token is not set.")
        if len(token) == 0:
            raise ValueError("The GitHub access token is set to an empty string.")
        
        return token
        
    
    # Lifecycle management ========================================================================================================
    
    # Instantiation ---------------------------------------------------------------------------------------------------------------
    def __init__(self, repoSlug: str) -> RepositoryAccessManager:
        """Initialize a RepositoryAccessManager instance.

        Args:
            repoSlug (str): The repository slug.

        Returns:
            RepositoryAccessManager: A new instance of this class.

        """

        self.setRepoSlug(repoSlugToSet=repoSlug)

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
    
    repoSlug: Optional[str] = ""
    """The slug of the repo as in https://github.com/repos/<user>/<reposlug>"""
    
    checkFrequencyDays: Optional[int] = 3
    """Frequency of checking for new updates (days)."""
        
    latestVersion: Optional[str] = ""
    """Version number of the latest release (the release tag from the repo) on GitHub."""
    
    latestVersionName: Optional[str] = ""
    """Name of the latest release on GitHub."""
    
    lastCheckedTimestamp: Optional[datetime] = datetime.now() - timedelta(days=checkFrequencyDays + 1)
    """Date and time of last successful check for updates. Defaults to a value to enforce checking as the default means no checks
    have been made yet."""

    releaseUrl: Optional[str] = ""
    """The URL to get the latest release"""
    
    repoUrl: Optional[str] = ""
    """The URL of the repository"""
    
    # Property management =========================================================================================================
    
    # Set repo slug ---------------------------------------------------------------------------------------------------------------
    def setRepoSlug(self, repoSlugToSet: str) -> None:
        """Property validator for `repoSlug`. Validates proposed value, and correct if necessary and possible.

        Args:
            repoSlugToSet (str): The value to set for the `repoSlug` property.

        Raises:
            EnvironmentError: Proposed value is of wrong type or not a valid URI segment.

        Returns:
            The normalized repo slug, corrected if necessary.
        """
        
        self.repoSlug = Repository.ensureRepoSlug(repoSlugToSet)
        
    # Get repo slug ---------------------------------------------------------------------------------------------------------------
    def getRepoSlug(self) -> str | None:
        """Returns the repo's slug

        Returns:
            str | None: The repo's slug
        """
        return self.repoSlug

    
    
    # Set check frequency ---------------------------------------------------------------------------------------------------------
    def setCheckFrequencyDays(self, frequency: int) -> None:
        """Set the frequency of checking for updates on GitHub, specified in days.

        Args:
            frequency (int): Check for updates with a frequency of this many days.

        Raises:
            EnvironmentError: The argument is not a positive integer.
        """
        
        if not isinstance(frequency, int) or frequency < 1:            
            errorKey = uuid.SafeUUID
            raise EnvironmentError(
                responseMessage=f"An internal error occurred. Mention the following error key when requesting support: {errorKey}",
                responseCode=500,
                logEntries=[f"Error key {errorKey}: Wanted to set check frequency but it's not number or not positive integer, but a {type(frequency).__name__}"]
            )
        
        self.checkFrequencyDays = frequency
        
    # Get check frequency ---------------------------------------------------------------------------------------------------------
    def getCheckFrequencyDays(self) -> int:
        """Return the how often, in days, updates shall be checked.

        Returns:
            int: The frequency of checking for updated on GitHub in days.
        """
        return self.checkFrequencyDays
 
    # Set last check timestamp ----------------------------------------------------------------------------------------------------
    def setLastCheckedTimestamp(self, timestamp: datetime) -> None:
        """Set the timestamp of last checking for updates on GitHub.

        Returns:
            None

        Raises:
            RequestError: If the value is not a `datetime` object.

        """
        
        if timestamp is None: # set default back in time so that update check will happen the next time
            timestamp = datetime.now() - timedelta(days=self.checkFrequencyDays + 1)
        
        if not isinstance(timestamp, datetime):
            errorKey = uuid.uuid4()
            raise EnvironmentError(                
                responseMessage=f"An internal error occurred. Mention the following error key when requesting support: {errorKey}",
                responseCode=500,
                logEntries=[f"Error key {errorKey}: Wanted to set update check timestamp but it's not a datetime object, but a {type(timestamp).__name__}"]
            )
        
        self.lastCheckedTimestamp = timestamp
        
    # Set last check timestamp ----------------------------------------------------------------------------------------------------
    def getLastCheckedTimestamp(self) -> datetime:
        """Get the timestamp of last checking for updates on GitHub.

        Returns:
            datetime: The timestamp of the last check for updates on GitHub
        """
        
        return self.lastCheckedTimestamp
    
    # Public functions ============================================================================================================
    
    # Normalize repo slug ---------------------------------------------------------------------------------------------------------
    @staticmethod
    def ensureRepoSlug(repoSlugToSet: str, fromCustomerRequest: bool = False) -> str:
        # sourcery skip: hoist-similar-statement-from-if, remove-unnecessary-else, swap-nested-ifs
        """Normalize the repository slug.

        This static method takes a repository slug as input and performs normalization checks and modifications to ensure it follows the specified URI format.

        Args:
            repoSlugToSet (str): The repository slug to be normalized.

        Returns:
            str: The normalized repository slug.

        Raises:
            TypeError: If the repo slug is not a string.
            ValueError: If the repo slug is an empty string or does not match the specified URI format.

        """
        
        if not isinstance(repoSlugToSet, str):
            if fromCustomerRequest: # Wrong data in request, return 400 and inform the caller on what's wrong
                raise RequestError(
                    responseMessage="The repo slug shall be a string.",
                    responseCode=400,
                    logEntries=[f"Wanted to set a value of {type(repoSlugToSet).__name__} type as repo slug"]                
                )
            else: # Wrong data in internal processing, such as when deserializing repository store. 
                #   Don't blame the user and don't disclose details of internal operations.
                errorKey = uuid.uuid4()
                raise EnvironmentError(
                    responseMessage=f"An internal error occurred. Mention the following error key when requesting support: {errorKey}",
                    responseCode=500,
                    logEntries=[f"Error key {errorKey}: Wanted to set a value of {type(repoSlugToSet).__name__} type as repo slug."]
                )
        
        if not repoSlugToSet:
            if fromCustomerRequest: # Wrong data in request, return 400 and inform the caller on what's wrong
                raise RequestError(
                    responseMessage="The repo slug shall not be an empty string.",
                    responseCode=400,
                    logEntries=["Wanted to set empty string as repo slug"]                
                )
            else: # Wrong data in internal processing, such as when deserializing repository store. 
                #   Don't blame the user and don't disclose details of internal operations.
                errorKey = uuid.uuid4()
                raise EnvironmentError(
                    responseMessage=f"An internal error occurred. Mention the following error key when requesting support: {errorKey}",
                    responseCode=500,
                    logEntries=[f"Error key {errorKey}: Wanted to set empty string as repo slug."]
                )
        
        # URI (slug) format is: 
        # * shall contain at least one number, letter, dash or slash,
        # * may start with a slash,
        # * shall only contain numbers, letters, dashes and slashes,
        # * may end with a slash, but 
        # * no consecutive slashes are allowed
        if not re.search("^/?[\w\d_][\w\d\-_]*(/[\w\d\-_]+)*/?$", repoSlugToSet):
            if fromCustomerRequest: # Wrong data in request, return 400 and inform the caller on what's wrong
                raise RequestError(
                    responseMessage =
                        "Value specified for repo slug is not a valid URI. Valid URIs " + 
                        "shall contain at least one number, letter, dash or slash, " + 
                        "may start with a slash, " + 
                        "shall only contain numbers, letters, dashes and slashes, " + 
                        "may end with a slash, but " + 
                        "no consecutive slashes are allowed.",
                    responseCode=400,
                    logEntries=[f"Invalid repo slug attempted to be set: {repoSlugToSet}"]
                    )
            else: # Wrong data in internal processing, such as when deserializing repository store. 
                #   Don't blame the user and don't disclose details of internal operations.
                errorKey = uuid.uuid4()
                raise EnvironmentError(
                    responseMessage=f"An internal error occurred. Mention the following error key when requesting support: {errorKey}",
                    responseCode=500,
                    logEntries=[f"Error key {errorKey}: Repo slug '{repoSlugToSet}' doesn't conform pattern."]
                )
        
        # Make sure the property does not begin with a slash
        if repoSlugToSet[0] == "/":
            repoSlugToSet = repoSlugToSet[1:]
            
        # Make sure the property does not end with a slash
        if repoSlugToSet[len(repoSlugToSet)-1] == "/":
            repoSlugToSet = repoSlugToSet[:-1]
        
        return repoSlugToSet
    
    # Lifecycle management ========================================================================================================
    
    # Instantiate object ----------------------------------------------------------------------------------------------------------
    def __init__(self,
        repoSlug: str, 
        checkFrequencyDays: int = 3, 
        latestVersion: str = "", 
        latestVersionName: str = "", 
        lastCheckedTimestamp: datetime = None,
        releaseUrl: str = "", 
        repoUrl: str = ""):
        
        
        self.setRepoSlug(repoSlugToSet=repoSlug)
        self.setCheckFrequencyDays(frequency=checkFrequencyDays)
        self.setLastCheckedTimestamp(timestamp=lastCheckedTimestamp)
        self.latestVersion = latestVersion
        self.latestVersionName = latestVersionName        
        self.releaseUrl = releaseUrl        
        self.repoUrl = repoUrl

    
# Encode repository info to JSON **************************************************************************************************
class RepositoryEncoder(JSONEncoder):
    """Custom JSON encoder for serializing Repository objects. This class extends the `JSONEncoder` class and overrides the default 
    method to provide custom serialization for datetime objects and other objects by returning their `__dict__` representation.

    """
    
    # Encoder function ------------------------------------------------------------------------------------------------------------
    def default(self, o):            
        # sourcery skip: remove-unnecessary-else, use-fstring-for-concatenation
        """Override the `default` method of `JSONEncoder`.

        Args:
            o: The object to be serialized.

        Returns:
            JSON-serializable representation of the object.

        """
        if type(o) == datetime:
            if app is None:
                errorKey = uuid.uuid4()
                raise EnvironmentError(
                    responseMessage=f"An internal error occurred. Mention the following error key when requesting support: {errorKey}",
                    responseCode=500,
                    logEntries=[f"Error key {errorKey}: Variable 'app' in repository.py is not defined."]
                )
            if app.config is None: 
                errorKey = uuid.uuid4()
                raise EnvironmentError(
                    responseMessage=f"An internal error occurred. Mention the following error key when requesting support: {errorKey}",
                    responseCode=500,
                    logEntries=[f"Error key {errorKey}: The 'app' global variable in repository.py has no 'config' property"]
                )
            if "dateTimeFormat" not in app.config.keys():
                errorKey = uuid.uuid4()
                raise EnvironmentError(
                    responseMessage=f"An internal error occurred. Mention the following error key when requesting support: {errorKey}",
                    responseCode=500,
                    logEntries=[f"Error key {errorKey}: No 'dateTimeFormat' key in 'app.config' in repository.py"]
                )
                
            return datetime.strftime(o, app.config["dateTimeFormat"])
        
        if hasattr(o, "__dict__"):        
            return o.__dict__
        else:
            errorKey = uuid.uuid4()
            raise EnvironmentError(
                    responseMessage=f"An internal error occurred. Mention the following error key when requesting support: {errorKey}",
                    responseCode=500,
                    logEntries=[ f"Error key {errorKey}: An object of the type '{type(o).__name__}' is passed to "  
                                + "RepositoryEncoder, and the encoder cannot encode it."]
                )
    

# Decode repository info from JSON ************************************************************************************************
class RepositoryDecoder(JSONDecoder):
    """Decoder class for deserializing Repository objects from JSON. This class extends the `JSONDecoder` class and provides 
    a static method `decode` that takes a dictionary as input and returns a deserialized `Repository` object.
    """
    
    # Decoder function ------------------------------------------------------------------------------------------------------------
    @staticmethod
    def decode(dct) -> Repository:
        """Decode a dictionary into a `Repository` object.

        Args:
            dct (dict): The dictionary to be deserialized.

        Returns:
            Repository: The deserialized `Repository` object.

        Raises:
            Exception: If there is an error during decoding.

        """
        try:            
            return Repository(
                repoSlug=dct["repoSlug"],
                checkFrequencyDays=dct["checkFrequencyDays"],
                latestVersion=dct["latestVersion"],
                latestVersionName=dct["latestVersionName"],
                lastCheckedTimestamp=datetime.strptime(dct["lastCheckedTimestamp"], app.config["dateTimeFormat"]),
                releaseUrl=dct["releaseUrl"],
                repoUrl=dct["repoUrl"]
            )
        except Exception as err:            
            errorKey = uuid.uuid4()
            raise EnvironmentError(
                responseMessage=f"An internal error occurred. Mention the following error key when requesting support: {errorKey}",
                responseCode=500,
                logEntries=[f"Error key {errorKey}: Could not decode repo store file for an error of {type(err).__name__}. Details: {err}"]
            ) from err
            

# Repository store ****************************************************************************************************************
class RepositoryStore(List[Repository]):    
    """RepositoryStore class for storing a list of `Repository` objects. This class extends the built-in `List` class."""
    
    def append(self, item: Repository) -> None:
        if not isinstance(item, Repository):
            errorKey = uuid.uuid4()
            raise EnvironmentError(
                responseMessage=f"An internal error occurred. Mention the following error key when requesting support: {errorKey}",
                responseCode=500,
                logEntries=[f"Only instances of the 'Repository' class can be added to the store, but an item of {type(item).__name__} was attempted to be added."]
            )
        super().append(item)
    pass
        
# Repository store manager ********************************************************************************************************
class RepositoryStoreManager:
    """Manager class for handling the repository store.

    This class provides functions for populating and saving the repository store, as well as retrieving update information from the repository repository.

    """
    
    # Private properties ==========================================================================================================
    _repoStoreFile: str = "repository-store.json"
    """File name of the repository store repository"""
    
    _repoRegistryFile: str = "repository-registry.json"
    """File name of the repository registry listing repo slugs to support/recognize."""
    
    _repoRepositoryKey: str = "repoRepository"
    """The key in the app config JSON and the repo store JSON file containing repositories"""
    
    _repoRegistryKey: str = "repoRegistry"
    """The key in the app config JSON containing the list of supported repositories"""

    _supportedRepositories: List[str] = []
    """This list of supported repositories as read from the file referenced in `_repoRegistry`"""        
    
    # Public properties ===========================================================================================================
    
    repoStore: RepositoryStore = RepositoryStore()
    """The managed repository store."""        
        
    # Private functions ===========================================================================================================

    # Populate repository store ---------------------------------------------------------------------------------------------------
    @staticmethod
    def _populateRepositoryStore() -> None:
        """Populate the repositories from the repository repository. This static method retrieves the repository dictionary from 
        the app configuration and populates the `RepositoryStore` with `Repository` objects created from the dictionary entries.

        Args:
            None

        Returns:
            None

        """
        RepositoryStoreManager.repoStore = RepositoryStore()
        registeredRepoDict = app.config[RepositoryStoreManager._repoRegistryKey]
        cachedRepoDict = app.config[RepositoryStoreManager._repoRepositoryKey]
        

        stagingRepoStore: RepositoryStore = RepositoryStore()

        for encodedRepo in cachedRepoDict:            
            repo = RepositoryDecoder.decode(encodedRepo)            
            if repo is not None and repo.repoSlug in registeredRepoDict: # the repo is valid and supported                
                stagingRepoStore.append(repo)
            
        # Getting here means no exception has been thrown, so it's safe to finalize the staging container
        RepositoryStoreManager.repoStore = stagingRepoStore
            
    # Load repository of known GitHub repositories --------------------------------------------------------------------------------
    @staticmethod
    def _loadRepoRepository() -> RepositoryStore:
        """Load repository of known GitHub repositories and populate into `app.config["repoRepository"]`"""
        
        if RepositoryStoreManager.repoStore is not None and len(RepositoryStoreManager.repoStore) > 0:
            # Already loaded
            return
        
        RepositoryStoreManager._loadRepositoryRegistry()
        
        if RepositoryStoreManager._repoRepositoryKey not in app.config.keys() or len(app.config[RepositoryStoreManager._repoRepositoryKey].keys()) == 0: 
            # No repository loaded or it's empty
        
            # Try to open repository store file ----------------------------------------------------------------------------------------
            repoRepository = {}
            
            if os.path.exists(RepositoryStoreManager._repoStoreFile) and os.path.isfile(RepositoryStoreManager._repoStoreFile):    
                try:
                    with open(RepositoryStoreManager._repoStoreFile) as f:
                        repoRepository = json.load(f)
                        
                    app.config[RepositoryStoreManager._repoRepositoryKey] = repoRepository
                    
                except Exception as ex:
                    app.logger.error(f"Could not open repository store '{RepositoryStoreManager._repoStoreFile}' for an error of {type(ex).__name__}: {ex}")            
                    # Do not reset app.config["repoRepository"], it may contain some not too old information, better than nothing
                    
                    # Fail silently
                    return None
        
        RepositoryStoreManager._populateRepositoryStore()
        
        return RepositoryStoreManager.repoStore
    
    # Load list of registered and hence supported repositories --------------------------------------------------------------------
    def _loadRepositoryRegistry() -> None:
        """Load list of registered and hence supported repositories.

        Raises:
            EnvironmentError: If the registry cannot be loaded.
        """
        
        if RepositoryStoreManager._repoRegistryKey in app.config and len(app.config[RepositoryStoreManager._repoRegistryKey]) > 0:
            # Repository registry already loaded, return
            return
        
        # Load list of supported repositories
        if os.path.exists(RepositoryStoreManager._repoRegistryFile) and os.path.isfile(RepositoryStoreManager._repoRegistryFile):
            try:
                repoList = {}
                
                with open (RepositoryStoreManager._repoRegistryFile) as f:
                    repoList = json.load(f)
                
                app.config[RepositoryStoreManager._repoRegistryKey] = repoList['supported-repositories']
            except Exception as ex:
                whatHappened: str = f"Could not load repository registry '{RepositoryStoreManager._repoStoreFile}' for an error of {type(ex).__name__}: {ex}"
                errorKey = uuid.SafeUUID
                raise EnvironmentError(
                    responseMessage=f"An internal error occurred. Mention the following error key when requesting support: {errorKey}",
                    responseCode=500,
                    logEntries=[f"Error key {errorKey}: {whatHappened}"]
                ) from ex
                        
    
    # Public functions ============================================================================================================
    
    # Return update info for a repository -----------------------------------------------------------------------------------------
    @staticmethod
    def getUpdateInfoFromRepoRepository(repoSlug) -> UpdateInfo:
        """Get the update information from the repository repository.

        Args:
            repoSlug (str): The repository slug.

        Returns:
            UpdateInfo: The update information object. If the repo data is not there, it returns a new object.

        """
        
        # Fix repo slug if necessary
        repoSlug = Repository.ensureRepoSlug(repoSlug)
        
        # Deny requests for non-registered repositories
        if repoSlug not in app.config[RepositoryStoreManager._repoRegistryKey]:
            whatHappened: str = f"Unregistered repository '{repoSlug}' in request."
            raise RequestError(
                responseMessage=whatHappened,
                responseCode=400,
                logEntries=[whatHappened]
            )
        
        # Load repos from store on demand        
        RepositoryStoreManager._loadRepoRepository()

        updateInfo: UpdateInfo = UpdateInfo()

        if RepositoryStoreManager.repoStore is not None and len(RepositoryStoreManager.repoStore) > 0: # the store is not empty
            # Load cached info
            for repo in RepositoryStoreManager.repoStore:
                if repo.getRepoSlug() == repoSlug: # this is it
                    updateInfo.repository = repo
                    break # found it, need no more loops

        # Create new repo info if no stored info is available    
        if updateInfo.repository is None or updateInfo.repository.getRepoSlug() is None or len(updateInfo.repository.getRepoSlug()) == 0:
            updateInfo.repository = Repository(repoSlug=repoSlug)
            updateInfo.updateAvailable = False
            
            
        return updateInfo
    
    # Save repository of known GitHub repositories ------------------------------------------------------------------------------------
    @staticmethod
    def saveRepoRepository() -> None:
        """Save repository of known GitHub repositories"""
        
        try:
            # Filter for supported repositories to make sure no unsupported repository is saved
            supportedRepositories = [repo for repo in RepositoryStoreManager.repoStore if RepositoryStoreManager.isRepoRegistered(repo.repoSlug)]

            with open(RepositoryStoreManager._repoStoreFile, "w") as f:
                f.write(json.dumps(supportedRepositories, cls=RepositoryEncoder, indent=4))
        except Exception as ex:
            app.logger.error(f"Could not save repository store to '{RepositoryStoreManager._repoStoreFile}' for an error of {type(ex).__name__}: {ex}")
            
    # Tell if a given repository is registered (supported) ------------------------------------------------------------------------
    @staticmethod
    def isRepoRegistered(repoSlug: str) -> bool:
        """Tell if a given repository is registered (supported).

        Args:
            repoSlug (str): The repository to check if it is supported and hence registered.

        Returns:
            bool: True if the repository can be checked (is supported), False otherwise.
        """
        
        # Make sure the format is correct
        repoSlugToCheck = Repository.ensureRepoSlug(repoSlug)
        
        # Load the registry        
        RepositoryStoreManager._loadRepositoryRegistry()
            
        return RepositoryStoreManager._repoRegistryKey in app.config and repoSlugToCheck in app.config[RepositoryStoreManager._repoRegistryKey]

# Structured update info **********************************************************************************************************
@dataclass
class UpdateInfo:
    """
    A pair of a repository information block (`RepoInfo` class) and the information whether an update is available for the client.
    """
    
    # Public properties ===========================================================================================================
    repository: Optional[Repository] = None
    """The repository about which this object collects update information"""

            
    updateAvailable: Optional[bool] = False
    """Tells whether an update is available (`True`) for the repository in `repository`"""
    
    # Lifecycle management ========================================================================================================
    
    # Instantiate object ----------------------------------------------------------------------------------------------------------
    def __init__(self, repository: Repository = None, updateAvailable: bool = False):
        """Create a new instance

        Args:
            repository (Repository, optional): The repository object to which the update info belongs. Defaults to None.
            updateAvailable (bool, optional): Whether update is available. Defaults to False.
        """
        self.repository = repository
        self.updateAvailable = updateAvailable

