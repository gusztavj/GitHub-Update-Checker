from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from json import JSONEncoder, JSONDecoder
from logging.config import dictConfig
from typing import List, Optional
import json
import os
import re


import customExceptions
from customExceptions import RequestError, EnvironmentError, UpdateCheckingError

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
            TypeError: Proposed value is of wrong type.
            ValueError: Proposed value is not a valid URI segment.

        Returns:
            None
        """
        
        self._repoSlug = Repository.normalizeRepoSlug(repoSlugToSet)
        
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
            
        self._performRepoSlugValidations("repo URL")
        return self._repoBase + self.getRepoSlug() + "/"
    
    
    # Get Releases API address of the repo ----------------------------------------------------------------------------------------
    def repoReleaseApiUrl(self) -> str:
        """API URL to get latest release information"""
        
        self._performRepoSlugValidations("repo release API URL")
        return self._repoApiBase + self.getRepoSlug() + "/releases/latest"
    
    # Get Releases page of the repo -----------------------------------------------------------------------------------------------
    def repoReleasesUrl(self) -> str:
        """URL of the releases page of the repository"""
        
        self._performRepoSlugValidations("repo release URL")
        return self._repoBase + self.getRepoSlug() + "/releases/"    

    # Check when repo slug is invalid ---------------------------------------------------------------------------------------------
    def _performRepoSlugValidations(self, propertyServed: str):
        """Check conditions preventing computation of a property.

        Args:
            propertyServed (str): The human readable name of what is being served

        Raises:
            ValueError: If the repo slug is None, empty string or a single dash
        """
        
        if self.getRepoSlug() is None:
            raise ValueError(f"Cannot get ${propertyServed} since the repository slug is None")
        if len(self.getRepoSlug()) == 0:
            raise ValueError(f"Cannot get ${propertyServed} since the repository slug is empty string")
        if self.getRepoSlug() == "/":
            raise ValueError(f"Cannot get ${propertyServed} URL since the repository slug is just a dash")    
    
    # Get username ----------------------------------------------------------------------------------------------------------------
    def username(self):
        """Username for API access"""
        # TODO: Get username from environment variable
        os.environ['GITHUB_USER_NAME'] = "gusztavj"
        return os.environ.get("GITHUB_USER_NAME")    
    
    # Get token -------------------------------------------------------------------------------------------------------------------
    def token(self):
        """GitHub token"""
        # TODO: Get token from environment variable
        os.environ['GITHUB_API_TOKEN'] = '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'
        return os.environ.get('GITHUB_API_TOKEN')
        
    
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
            TypeError: Proposed value is of wrong type.
            ValueError: Proposed value is not a valid URI segment.

        Returns:
            None
        """
        
        self.repoSlug = Repository.normalizeRepoSlug(repoSlugToSet)
        
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
            customExceptions.RequestError: The argument is not a positive integer.
        """
        if not isinstance(frequency, int) or frequency < 1:
            raise RequestError(
                responseMessage="Check frequency days shall be a natural number greater than zero.",
                responseCode=400,
                logEntries=[f"Wanted to set check frequency but it's not number or not positive integer, but a {type(frequency).__name__}"]
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
            customExceptions.RequestError: If the value is not a `datetime` object.

        """
        
        if timestamp is None: # set default back in time so that update check will happen the next time
            timestamp = datetime.now() - timedelta(days=self.checkFrequencyDays + 1)
        
        if not isinstance(timestamp, datetime):
            raise RequestError(
                responseMessage="The timestamp of the last check shall be a datetime object.",
                responseCode=400,
                logEntries=[f"Wanted to set update check timestamp but it's not a datetime object, but a {type(timestamp).__name__}"]
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
    def normalizeRepoSlug(repoSlugToSet):
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
            raise RequestError(
                responseMessage="The repo slug shall be a string.",
                responseCode=400,
                logEntries=[f"Wanted to set a value of {type(repoSlugToSet).__name__} type as repo slug"]                
            )
        
        if len(repoSlugToSet) == 0:
            raise RequestError(
                responseMessage="The repo slug shall not be an empty string.",
                responseCode=400,
                logEntries=["Wanted to set empty string as repo slug"]                
            )
        
        
        # URI (slug) format is: 
        # * shall contain at least one number, letter, dash or slash,
        # * may start with a slash,
        # * shall only contain numbers, letters, dashes and slashes,
        # * may end with a slash, but 
        # * no consecutive slashes are allowed
        if not re.search("^/?[\w\d\-_]+(/[\w\d\-_]+)*/?$", repoSlugToSet):
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
        """Override the `default` method of `JSONEncoder`.

        Args:
            o: The object to be serialized.

        Returns:
            JSON-serializable representation of the object.

        """
        if type(o) == datetime:
            return datetime.strftime(o, app.config["dateTimeFormat"])
        else:
            return o.__dict__

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
            app.logger.exception(f"Could not decode repo store file for an error of {type(err).__name__}. Details: {err}")

# Repository store ****************************************************************************************************************
class RepositoryStore(List[Repository]):
    """RepositoryStore class for storing a list of `Repository` objects. This class extends the built-in `List` class."""
    pass
        
# Repository store manager ********************************************************************************************************
class RepositoryStoreManager:
    """Manager class for handling the repository store.

    This class provides functions for populating and saving the repository store, as well as retrieving update information from the repository repository.

    """
    
    # Private properties ==========================================================================================================
    _repoStore: str = "repo-repo.json"
    """File name of the repository store repository"""
    
    _repoRepositoryKey: str = "repoRepository"
    """The key in the JSON file containing repositories"""
    
    
    # Public properties ===========================================================================================================
    repos: RepositoryStore = RepositoryStore()
        
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
        RepositoryStoreManager.repos = RepositoryStore()
        repoDict = app.config[RepositoryStoreManager._repoRepositoryKey]

        for encodedRepo in repoDict:            
            repo = RepositoryDecoder.decode(encodedRepo)
            if repo is not None:
                RepositoryStoreManager.repos.append(repo)
            
    # Load repository of known GitHub repositories --------------------------------------------------------------------------------
    @staticmethod
    def _loadRepoRepository() -> RepositoryStore:
        """Load repository of known GitHub repositories and populate into app.config["repoRepository"]"""
        
        if RepositoryStoreManager.repos is not None and len(RepositoryStoreManager.repos) > 0:
            # Already loaded
            return
        
        if RepositoryStoreManager._repoRepositoryKey not in app.config.keys() or len(app.config[RepositoryStoreManager._repoRepositoryKey].keys()) == 0: 
            # No repository loaded or it's empty
        
            # Try to open repo repository file ----------------------------------------------------------------------------------------
            repoRepository = {}
            
            if os.path.exists(RepositoryStoreManager._repoStore) and os.path.isfile(RepositoryStoreManager._repoStore):    
                try:
                    with open(RepositoryStoreManager._repoStore) as f:
                        repoRepository = json.load(f)
                        
                    app.config[RepositoryStoreManager._repoRepositoryKey] = repoRepository
                    
                    RepositoryStoreManager._populateRepositoryStore()
                    
                except Exception as ex:
                    app.logger.error(f"Could not open repo repository '{RepositoryStoreManager._repoStore}' for an error of {type(ex).__name__}: {ex}")            
                    # Do not reset app.config["repoRepository"], it may contain some not too old information, better than nothing
                    
                    # Fail silently
                    return None
        
        RepositoryStoreManager._populateRepositoryStore()
        
        return RepositoryStoreManager.repos
    
    
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
        repoSlug = Repository.normalizeRepoSlug(repoSlug)
        
        # Load repos from store on demand        
        RepositoryStoreManager._loadRepoRepository()

        updateInfo: UpdateInfo = UpdateInfo()

        if RepositoryStoreManager.repos is not None and len(RepositoryStoreManager.repos) > 0: # the store is not empty
            # Load cached info
            for repo in RepositoryStoreManager.repos:
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
            with open(RepositoryStoreManager._repoStore, "w") as f:
                f.write(json.dumps(RepositoryStoreManager.repos, cls=RepositoryEncoder, indent=4))
        except Exception as ex:
            app.logger.error(f"Could not save repo repository '{RepositoryStoreManager._repoStore}' for an error of {type(ex).__name__}: {ex}")
            


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
