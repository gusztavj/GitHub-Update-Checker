# T1nk-R's GitHub Update Checker // test/test_repository.py
#
# This module contains unit tests for the functions and classes in repository.py.
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

# Standard libraries --------------------------------------------------------------------------------------------------------------
import datetime
import re
import json
import pytest
from unittest.mock import patch, mock_open, MagicMock

# Standard library elements -------------------------------------------------------------------------------------------------------
from datetime import datetime

# Own libraries and elements ------------------------------------------------------------------------------------------------------
import repository
import customExceptions

from repository import *
from gitHubUpdateChecker import *
from customExceptions import *

# Tests for the RepositoryAccessManager class #####################################################################################
class TestRepositoryAccessManager:

    #==============================================================================================================================
    # Can instantiate the RepositoryAccessManager class with a valid repository slug
    def test_instantiate_with_valid_slug(self):
        """Can instantiate the RepositoryAccessManager class with a valid repository slug"""
        
        repo_access_manager = RepositoryAccessManager("T1nkR-Mesh-Name-Synchronizer")
        assert \
            isinstance(repo_access_manager, RepositoryAccessManager), \
            "The access manager is of a wrong type"

    #==============================================================================================================================
    # Can get the URL of the repository
    def test_get_repo_url(self):
        """Can get the URL of the repository"""
        
        repo_access_manager = RepositoryAccessManager("T1nkR-Mesh-Name-Synchronizer")
        assert \
            repo_access_manager.repoUrl() == "https://github.com/gusztavj/T1nkR-Mesh-Name-Synchronizer/", \
            "Wrong repository URL constructed"

    #==============================================================================================================================
    # Can get the API URL to get latest release information
    def test_get_repo_release_api_url(self):
        """Can get the API URL to get latest release information"""
        
        repo_access_manager = RepositoryAccessManager("T1nkR-Mesh-Name-Synchronizer")
        assert \
            repo_access_manager.repoReleaseApiUrl() == "https://api.github.com/repos/gusztavj/T1nkR-Mesh-Name-Synchronizer/releases/latest", \
            "Wrong repository release API URL constructed"

    #==============================================================================================================================
    # Throws EnvironmentError when repo slug is just a dash (during initialization)
    def test_throws_value_error_when_repo_slug_is_just_a_dash(self):
        """Throws EnvironmentError when repo slug is just a dash (during initialization)"""
        
        with pytest.raises(customExceptions.EnvironmentError):
            repo_access_manager = RepositoryAccessManager("-")
            
    #==============================================================================================================================
    # Throws EnvironmentError when repo slug is just a dash
    def test_throws_value_error_when_repo_slug_is_set_to_a_dash(self):
        """Throws EnvironmentError when repo slug is just a dash"""
        
        repo_access_manager = RepositoryAccessManager("Foo")
        with pytest.raises(customExceptions.EnvironmentError):
            repo_access_manager.setRepoSlug("-")
            
    #==============================================================================================================================
    # Throws EnvironmentError when repo slug starts with a dash
    def test_throws_value_error_when_repo_slug_starts_with_a_slash(self):
        """Throws EnvironmentError when repo slug starts with a dash"""
        
        repo_access_manager = RepositoryAccessManager("Foo")
        with pytest.raises(customExceptions.EnvironmentError):
            repo_access_manager.setRepoSlug("-Foo")
            
    #==============================================================================================================================
    # Throws EnvironmentError when repo slug is just a slash
    def test_throws_value_error_when_repo_slug_is_just_a_slash(self):
        """Throws EnvironmentError when repo slug is just a slash""" 
        
        repo_access_manager = RepositoryAccessManager("Foo")
        with pytest.raises(customExceptions.EnvironmentError):
            repo_access_manager.setRepoSlug("/")
            

# Tests for the AppInfo class #####################################################################################################
class TestAppInfo:
    """
    Test the creation and modification of attributes for an instance of AppInfo.
    """


    #==============================================================================================================================
    # Creating an instance of AppInfo with valid repoSlug and currentVersion should return an object with the same attributes.
    def test_valid_instance(self):
        """Creating an instance of AppInfo with valid repoSlug and currentVersion should return an object with the same attributes."""
        
        app_info = AppInfo(repoSlug="user/repo", currentVersion="1.0.0")
        assert \
            app_info.repoSlug == "user/repo", \
            "Wrong repo slug found in app_info"
            
        assert \
            app_info.currentVersion == "1.0.0", \
            "Wrong current version found in app_info"

    #==============================================================================================================================
    # Modifying the attributes of an instance of AppInfo should update the values of the attributes accordingly.
    def test_modify_attributes(self):
        """Modifying the attributes of an instance of AppInfo should update the values of the attributes accordingly."""
        
        app_info = AppInfo(repoSlug="user/repo", currentVersion="1.0.0")
        app_info.repoSlug = "new_user/new_repo"
        app_info.currentVersion = "2.0.0"
        
        assert \
            app_info.repoSlug == "new_user/new_repo", \
            "Could not properly change repo slug in app info"
                
        assert \
            app_info.currentVersion == "2.0.0", \
            "Could not properly change current version in app info"
    

# Tests for the Repository class ##################################################################################################
class TestRepository:
    """
    Test the creation and behavior of the Repository class.

    """


    #==============================================================================================================================
    # Creating a new instance of Repository with default values should fail for having no repo slug specified
    def test_default_values(self):
        """Creating a new instance of Repository with default values should fail for having no repo slug specified"""
        
        with pytest.raises(TypeError):
            repo = Repository()
        
    #==============================================================================================================================
    # Creating a new instance of Repository with custom values should set all properties to the custom values.
    def test_custom_values(self):
        """Creating a new instance of Repository with custom values should set all properties to the custom values."""
        
        exceptedTimeStamp = datetime.now()
        
        repo = Repository(
            repoSlug="my-repo",
            checkFrequencyDays=7,
            latestVersion="1.0.0",
            latestVersionName="Release 1.0.0",
            lastCheckedTimestamp=exceptedTimeStamp,
            releaseUrl="https://github.com/my-repo/releases/tag/1.0.0",
            repoUrl="https://github.com/my-repo"
        )
        
        assert repo.getRepoSlug() == "my-repo"                                      , "Wrong repo slug found in created Repository instance"
        assert repo.getCheckFrequencyDays() == 7                                    , "Wrong checking frequency found in created Repository instance"
        assert repo.latestVersion == "1.0.0"                                        , "Wrong latest version found in created Repository instance"
        assert repo.latestVersionName == "Release 1.0.0"                            , "Wrong latest version name found in created Repository instance"
        assert repo.getLastCheckedTimestamp() == exceptedTimeStamp                  , "Wrong timestamp for last check found in created Repository instance"
        assert repo.releaseUrl == "https://github.com/my-repo/releases/tag/1.0.0"   , "Wrong release URL found in created Repository instance"
        assert repo.repoUrl == "https://github.com/my-repo"                         , "Wrong repo URL found in created Repository instance"

    #==============================================================================================================================
    # Updating the lastCheckedTimestamp property of a Repository instance should change its value to the new value.
    def test_update_lastCheckedTimestamp(self):
        """Updating the lastCheckedTimestamp property of a Repository instance should change its value to the new value."""
        
        repo = Repository("Foo")
        new_timestamp = datetime.now()
        repo.setLastCheckedTimestamp(new_timestamp)
        assert repo.getLastCheckedTimestamp() == new_timestamp, "Could not properly change timestamp in a Repository object"

    #==============================================================================================================================
    # Creating a new instance of Repository with a negative checkFrequencyDays value should raise a ValueError.
    def test_negative_checkFrequencyDays(self):
        """Creating a new instance of Repository with a negative checkFrequencyDays value should raise a ValueError."""
        
        with pytest.raises(customExceptions.EnvironmentError):
            Repository(repoSlug="Foo", checkFrequencyDays=-1)

    #==============================================================================================================================
    # Creating a new instance of Repository with a lastCheckedTimestamp value that is not a datetime object should raise a TypeError.
    def test_invalid_lastCheckedTimestamp(self):
        """Creating a new instance of Repository with a lastCheckedTimestamp value that is not a datetime object should raise a TypeError."""
        
        with pytest.raises(customExceptions.EnvironmentError):
            Repository(repoSlug="Foo", lastCheckedTimestamp="2022-01-01")
            
            
# Tests for the RepositoryEncoder class ###########################################################################################
class TestRepositoryEncoder:

    #==============================================================================================================================
    # Repository object can be serialized to JSON using the default method of JSONEncoder.
    def test_repository_serialization(self):
        """Repository object can be serialized to JSON using the default method of JSONEncoder."""
        
        repo = Repository(repoSlug="test_repo")
        encoder = RepositoryEncoder()
        json_data = encoder.encode(repo)
        assert \
            re.match(
                '\{"repoSlug": "test_repo", "checkFrequencyDays": \d+, "lastCheckedTimestamp": "[^"]*", "latestVersion": "", "latestVersionName": "", "releaseUrl": "", "repoUrl": ""\}',
                json_data
            ), \
            "Error in serializing a Repository object"

    #==============================================================================================================================
    # Datetime objects can be serialized to JSON using the custom default method of RepositoryEncoder.
    def test_datetime_serialization(self):  # sourcery skip: class-extract-method
        """Datetime objects can be serialized to JSON using the custom default method of RepositoryEncoder."""
        
        dt = datetime(2022, 1, 1)
        encoder = RepositoryEncoder()
        json_data = encoder.encode(dt)
        assert json_data == '"2022-01-01 00:00:00"', "Error in encoding datetime value"

    #==============================================================================================================================
    # The custom default method returns the __dict__ representation of non-datetime objects.
    def test_dict_representation(self):
        """The custom default method returns the __dict__ representation of non-datetime objects."""
        
        obj = {"key": "value"}
        encoder = RepositoryEncoder()
        json_data = encoder.encode(obj)
        assert json_data == '{"key": "value"}', "Error in encoding a key-value pair"

    #==============================================================================================================================
    # The object passed to the default method is not a datetime object or a Repository object.
    def test_non_datetime_repository_object(self):
        """The object passed to the default method is not a datetime object or a Repository object."""
        
        obj = {}
        encoder = RepositoryEncoder()
        json_data = encoder.encode(obj)
        assert json_data == '{}', "Error encoding empty object"

    #==============================================================================================================================
    # The datetime object passed to the default method is not in the format specified in the app configuration.
    def test_invalid_datetime_format(self):
        """The datetime object passed to the default method is not in the format specified in the app configuration."""
        
        dt = datetime(2022, 1, 1)
        app.config = {"dateTimeFormat": "%Y-%m-%d"}
        encoder = RepositoryEncoder()
        json_data = encoder.encode(dt)
        assert json_data == '"2022-01-01"', "Error encoding unexpectedly formatted datetime"

    #==============================================================================================================================
    # Repository object contains non-serializable attributes.
    def test_non_serializable_attributes(self):
        """Repository object contains non-serializable attributes."""
        
        @dataclass
        class CustomObject:
            def __init__(self):
                self.attr = object()
    
        obj = CustomObject()
        encoder = RepositoryEncoder()
        with pytest.raises(EnvironmentError):        
            json_data = encoder.encode(obj)
            assert json_data == '{"attr": {}}', "Non-serializable attributes serialized"


# Tests for the RepositoryDecoder class ###########################################################################################
class TestRepositoryDecoder:
    """
    Test the decoding of dictionaries into Repository objects using the RepositoryDecoder class.
    """
    
    #==============================================================================================================================
    # Decodes a valid dictionary into a Repository object with a mocked 'app' object.
    def test_valid_dictionary_decoding_with_mocked_app(self):
        """Decodes a valid dictionary into a Repository object with a mocked 'app' object."""
        
        repo_dict = {
            "repoSlug": "my-repo",
            "checkFrequencyDays": 7,
            "latestVersion": "1.0.0",
            "latestVersionName": "First Release",
            "lastCheckedTimestamp": "2022-01-01 00:00:00",
            "releaseUrl": "https://github.com/my-repo/releases/latest",
            "repoUrl": "https://github.com/my-repo"
        }

        # Mock the 'app' object and its attributes
        repository.app = Flask(__name__)
        repository.app.config = {"dateTimeFormat": "%Y-%m-%d %H:%M:%S"}
        

        repo = RepositoryDecoder.decode(repo_dict)

        assert isinstance(repo, Repository)                                     , "The 'repo' object is of a wrong type after decoding"
        assert repo.repoSlug == "my-repo"                                       , "Decoding resulted in unexpected value for the repo slug"
        assert repo.checkFrequencyDays == 7                                     , "Decoding resulted in unexpected value for the update checking frequency"
        assert repo.latestVersion == "1.0.0"                                    , "Decoding resulted in unexpected value for the latest version's number"
        assert repo.latestVersionName == "First Release"                        , "Decoding resulted in unexpected value for the latest version name"
        assert repo.lastCheckedTimestamp == datetime.strptime(repo_dict["lastCheckedTimestamp"], repository.app.config["dateTimeFormat"]) \
                                                                                , "Decoding resulted in unexpected value for the timestamp of the last update check"
        assert repo.releaseUrl == "https://github.com/my-repo/releases/latest"  , "Decoding resulted in unexpected value for the release URL"
        assert repo.repoUrl == "https://github.com/my-repo"                     , "Decoding resulted in unexpected value for the repo URL"
    
    
    #==============================================================================================================================
    # Decoding a dictionary with a missing required field raises an EnvironmentError.
    def test_missing_required_field(self):
        """Decoding a dictionary with a missing required field raises an EnvironmentError."""
        
        # Create a sample dictionary representing a serialized Repository object with a missing required field
        repo_dict = {
            "checkFrequencyDays": 7,
            "latestVersion": "1.0.0",
            "latestVersionName": "Release 1.0.0",
            "lastCheckedTimestamp": "2022-01-01 00:00:00",
            "releaseUrl": "https://github.com/my-repo/releases/tag/1.0.0",
            "repoUrl": "https://github.com/my-repo"
        }

        # Assert that an EnvironmentError is raised when trying to decode the dictionary
        with pytest.raises(EnvironmentError):
            RepositoryDecoder.decode(repo_dict)
                
                
# Tests for the RepositoryStore class #############################################################################################
class TestRepositoryStore:
    """
    Test the behavior of the RepositoryStore class.

    """
    
    #==============================================================================================================================
    # Cannot add an object that is not a Repository to the RepositoryStore
    def test_cannot_add_non_repository_object(self):
        """Cannot add an object that is not a Repository to the RepositoryStore"""
        
        repoStore = RepositoryStore()
        with pytest.raises(EnvironmentError):
            repoStore.append("not a repository")
        
        assert len(repoStore) == 0, "Objects of a type other than Repository could be added to the Repository Store"
        
        
# Tests for the RepositoryStoreManager class ####################################################################################==
class TestRepositoryStoreManager:
    """
    Test the behavior of the RepositoryStoreManager class.
    """

    #==============================================================================================================================
    # Populating the repository store from the repository store file with valid data should result in the 
    # 'RepositoryStoreManager.repos' property being populated with 'Repository' objects.
    def test_populate_repository_store_with_valid_data(self):
        """Populating the repository store from the repository store file with valid data should result in the 'RepositoryStoreManager.repos' property being populated with 'Repository' objects."""
        
        # Initialize Flask app
        app = Flask(__name__)

        # Set app configuration
        app.config["dateTimeFormat"] = "%Y-%m-%d %H:%M:%S"
        app.config["repoRepository"] = [
                {
                    "repoSlug": "user/repo1",
                    "checkFrequencyDays": 7,
                    "latestVersion": "1.0.0",
                    "latestVersionName": "Release 1.0.0",
                    "lastCheckedTimestamp": "2022-01-01 12:00:00",
                    "releaseUrl": "https://github.com/user/repo1/releases/latest",
                    "repoUrl": "https://github.com/user/repo1"
                },
                {
                    "repoSlug": "user/repo2",
                    "checkFrequencyDays": 3,
                    "latestVersion": "2.0.0",
                    "latestVersionName": "Release 2.0.0",
                    "lastCheckedTimestamp": "2022-01-01 12:00:00",
                    "releaseUrl": "https://github.com/user/repo2/releases/latest",
                    "repoUrl": "https://github.com/user/repo2"
                }
        ]
        
        app.config[RepositoryStoreManager._repoRegistryKey] = ["user/repo1", "user/repo2"]
            

        # Set app reference in Repository class
        repository.app = app

        with patch('repository.RepositoryStoreManager.isRepoRegistered') as mock_is_repo_registered:
            mock_is_repo_registered.return_value = True
        
            # Load serialized repo store
            RepositoryStoreManager._populateRepositoryStore()

        # Assert that the repository store is populated with Repository objects
        assert \
            isinstance(RepositoryStoreManager.repoStore, RepositoryStore), \
            "The repoStore property of the RepositoryStoreManager is of a wrong type (other than RepositoryStore)"
            
        assert \
            all(isinstance(repo, Repository) for repo in RepositoryStoreManager.repoStore), \
            "Some elements of the repoStore property of the RepositoryStoreManager are of a wrong type (other than Repository)"
        
    #==============================================================================================================================
    # Populating the repository store from the repository store file with valid data should result in the 
    # 'RepositoryStoreManager.repos' property being populated with 'Repository' objects.
    def test_populate_repository_store_with_no_more_supported_repo(self):
        """Populating the repository store from the repository store file with valid data should result in the 
        'RepositoryStoreManager.repos' property being populated with 'Repository' objects."""
        
        # Initialize Flask app
        app = Flask(__name__)

        # Set app configuration
        app.config["dateTimeFormat"] = "%Y-%m-%d %H:%M:%S"
        app.config["repoRepository"] = [
                {
                    "repoSlug": "user/repo1",
                    "checkFrequencyDays": 7,
                    "latestVersion": "1.0.0",
                    "latestVersionName": "Release 1.0.0",
                    "lastCheckedTimestamp": "2022-01-01 12:00:00",
                    "releaseUrl": "https://github.com/user/repo1/releases/latest",
                    "repoUrl": "https://github.com/user/repo1"
                },
                {
                    "repoSlug": "user/repo2",
                    "checkFrequencyDays": 3,
                    "latestVersion": "2.0.0",
                    "latestVersionName": "Release 2.0.0",
                    "lastCheckedTimestamp": "2022-01-01 12:00:00",
                    "releaseUrl": "https://github.com/user/repo2/releases/latest",
                    "repoUrl": "https://github.com/user/repo2"
                }
        ]
        
        app.config[RepositoryStoreManager._repoRegistryKey] = ["user/repo1"]

        # Set app reference in Repository class
        repository.app = app
        
        # Load serialized repo store
        RepositoryStoreManager._populateRepositoryStore()

        # Assert that the repository store is of the proper type and is populated with Repository objects
        assert \
            isinstance(RepositoryStoreManager.repoStore, RepositoryStore), \
            "The repoStore property of the RepositoryStoreManager is of a wrong type (other than RepositoryStore)"
            
        assert \
            all(isinstance(repo, Repository) for repo in RepositoryStoreManager.repoStore), \
            "Some elements of the repoStore property of the RepositoryStoreManager are of a wrong type (other than Repository)"
        
        # Assert that the non-registered repo is not loaded
        assert \
            len(RepositoryStoreManager.repoStore) == 1, \
            "The repoStore property of RepositoryStoreManager should contain exactly 1 item"
            
        assert \
            RepositoryStoreManager.repoStore[0].repoSlug == app.config["repoRepository"][0]["repoSlug"], \
            "The value of the repoSlug attribute of the first item of the repoStore attribute of the RepositoryStoreManager class is unexpected"
        
    
    #==============================================================================================================================
    # Populating the repository store from the repository store file with invalid data should result in the 'RepositoryStoreManager.repos' property being empty.
    def test_populate_repository_store_with_invalid_data(self):
        """Populating the repository store from the repository store file with invalid data should result in the 'RepositoryStoreManager.repos' property being empty."""
        
        # Initialize Flask app
        app = Flask(__name__)

        # Set app configuration with invalid data
        app.config["dateTimeFormat"] = "%Y-%m-%d %H:%M:%S"
        app.config["repoRepository"] = [
                {
                    "repoSlug": "user/repo1",
                    "checkFrequencyDays": 7,
                    "latestVersion": "1.0.0",
                    "latestVersionName": "Release 1.0.0",
                    "lastCheckedTimestamp": "2022-01-01 12:00:00",
                    "releaseUrl": "https://github.com/user/repo1/releases/latest",
                    "repoUrl": "https://github.com/user/repo1"
                },
                {
                    "repoSlug": "user/repo2",
                    "checkFrequencyDays": 3,
                    "latestVersion": "2.0.0",
                    "latestVersionName": "Release 2.0.0",
                    "lastCheckedTimestamp": "2022-01-01 12:00:00",
                    "releaseUrl": "https://github.com/user/repo2/releases/latest",
                    "repoUrl": "https://github.com/user/repo2"
                },
                {
                    "repoSlug": "user/repo3",
                    "checkFrequencyDays": "invalid",
                    "latestVersion": "3.0.0",
                    "latestVersionName": "Release 3.0.0",
                    "lastCheckedTimestamp": "2022-01-01 12:00:00",
                    "releaseUrl": "https://github.com/user/repo3/releases/latest",
                    "repoUrl": "https://github.com/user/repo3"
                }
        ]

        app.config[RepositoryStoreManager._repoRegistryKey] = ["user/repo1", "user/repo2", "user/repo3"]
        
        # Set app reference in Repository class
        repository.app = app
        with patch('repository.RepositoryStoreManager.isRepoRegistered') as mock_is_repo_registered:
            mock_is_repo_registered.return_value = True
            
            with pytest.raises(EnvironmentError) as err:
                # Load serialized repo store
                RepositoryStoreManager._populateRepositoryStore()

                # Assert the proper exception is thrown
                assert any(
                    True
                    for tb in err._traceback
                    if "Could not decode repo store file for an error of" in str(tb)
                )
                

        # Assert that the repository store is empty
        assert len(RepositoryStoreManager.repoStore) == 0, "The repoStore property of RepositoryStoreManager should be an empty list"

    #==============================================================================================================================
    # Check if only registered repositories are deserialized from the repository store file
    def test_loadRepositoryRegistry_happy_path(self):
        """
        Test the happy path for loading the repository registry.
        """

        # Constants for tests
        SUPPORTED_REPOSITORIES = ["repo1", "repo2", "repo3"]
        EXTRA_REPOSITORY = ["repo4"]

        # Arrange    
        app.config[RepositoryStoreManager._repoRegistryKey] = []
        repository.app = app
        with patch("repository.os.path.exists", return_value=True):
            with patch("repository.os.path.isfile", return_value=True):
                with patch("builtins.open", mock_open(read_data=json.dumps({"supported-repositories": SUPPORTED_REPOSITORIES}))):

                    RepositoryStoreManager._loadRepositoryRegistry()

                    # Assert items are loaded as the list was empty
                    assert \
                        len(app.config[RepositoryStoreManager._repoRegistryKey]) == len(SUPPORTED_REPOSITORIES), \
                        "The repo registry in app config has unexpected number of items after loading the repo registry"
                    
                    with patch("builtins.open", mock_open(read_data=json.dumps({"supported-repositories": EXTRA_REPOSITORY}))):
                        RepositoryStoreManager._loadRepositoryRegistry()

                        # Assert the length is the same, no new item was loaded
                        assert \
                            len(app.config[RepositoryStoreManager._repoRegistryKey]) == len(SUPPORTED_REPOSITORIES), \
                            "While the app.config contained the repo registry, another attempt to load the registry file again \
                            resulted in new items being added to the registry in app.config"

    #==============================================================================================================================
    # Check error handling for loading registered repositories
    @pytest.mark.parametrize(
        "test_id, exception,            error_message", [
        ("EC001", OSError,              "Could not load repository registry"),  # OSError when opening file
        ("EC002", json.JSONDecodeError, "JSONDecodeError"),                     # JSON decode error
    ])
    def test_loadRepositoryRegistry_error_cases(self, test_id, exception, error_message):
        """
        Test the error cases for loading the repository registry.

        Args:
            self: The instance of the test case.
            test_id (str): The identifier for the test case.
            exception (Exception): The expected exception class.
            error_message (str): The expected error message.

        Raises:
            AssertionError: If the response code, response message, or log entries do not match the expected values.
        """
        
        SUPPORTED_REPOSITORIES = ["repo1", "repo2", "repo3"]
        
        # Arrange
        with patch("repository.app") as mock_app:
            mock_app.config = {}
            with patch("repository.os.path.exists", return_value=True):
                with patch("repository.os.path.isfile", return_value=True):
                    with patch("builtins.open", mock_open(read_data=json.dumps({"supported-repositories": SUPPORTED_REPOSITORIES}))) as mock_file:
                        mock_file.side_effect = exception

                        # Act & Assert
                        with pytest.raises(EnvironmentError) as exc_info:
                            RepositoryStoreManager._loadRepositoryRegistry()
                        
                        assert \
                            exc_info.value.responseCode == 500, \
                            "Unexpected response code for repo registry loading error"
                            
                        assert \
                            "An internal error occurred. Mention the following error key when requesting support:" in exc_info.value.responseMessage, \
                            "Unexpected error message provided to client upon repo registry loading error"
                                
                        assert \
                            error_message in str(exc_info.value.logEntries), \
                            "Detailed error message not found in application log about repo registry loading error"


    #==============================================================================================================================
    # Check saving repositories when everything is okay
    @pytest.mark.parametrize(
        "test_id,       repo_store,         repo_registry", [
        # Happy path tests
        ("happy-1",     ["repo1", "repo2"], ["repo1", "repo2"]),
        ("happy-2",     ["repo1", "repo2"], ["repo1"]),
        ("happy-3",     ["repo1"],          ["repo1"]),
        # Edge cases
        ("edge-1",      ["repo1"],          []),
        ("edge-2",      [],                 ["repo1"]),
        ("edge-3",      [],                 []),
    ])
    def test_saveRepoRepositoryHappyCases(self, test_id, repo_store, repo_registry):
        """
        Test the happy path and edge cases for saving the repository store.

        Args:
            test_id (str): The identifier for the test case.
            repo_store (list): The list of repository slugs.
            repo_registry (list): The list of registered repository slugs.

        Raises:
            AssertionError: If the file 'repo_store.json' was not opened for saving the repository store as expected, 
            or if not exactly the registered repositories were saved to the repository store.
        """

        
        def mock_isRepoRegistered(*args, **kwargs):
            """Mock the result as requested by test data"""
            return args[0] in repo_registry
            
        # Arrange
        
        # Create repository objects from slugs        
        [RepositoryStoreManager.repoStore.append(Repository(repoSlug)) for repoSlug in repo_store]
        
        RepositoryStoreManager._repoStoreFile = "repo_store.json"
        m_open = mock_open()

        # Act        
        with patch("builtins.open", m_open):
            with patch.object(RepositoryStoreManager, "isRepoRegistered", side_effect=mock_isRepoRegistered):
                RepositoryStoreManager.saveRepoRepository()
                
            assert \
                any(("repo_store.json", "w") in call for call in m_open.mock_calls), \
                f"{test_id}: The file 'repo_store.json' was not opened for saving the repository store as expected."
            
            mockedOutput = m_open().write.call_args.args[0]
            
            assert \
                all(repoSlug in mockedOutput for repoSlug in repo_store if repoSlug in repo_registry), \
                f"{test_id}: Not exactly the registered repositories were saved to the repository store"
                
                
    #==============================================================================================================================
    # Check error handling when saving repositories
    @pytest.mark.parametrize(
        "test_id,   repo_store, repo_registry,  expected_exception, expected_message", [
        ("error-1", ["repo1"],  ["repo1"],      OSError,            "Failed to open file for writing"),
    ])
    def test_saveRepoRepositoryErrorCases(self, test_id, repo_store, repo_registry, expected_exception, expected_message):
        """
        Test the error cases for saving the repository store.

        Args:
            test_id (str): The identifier for the test case.
            repo_store (list): The list of repository slugs.
            repo_registry (list): The list of registered repository slugs.
            expected_exception (Exception): The expected exception class.
            expected_message (str): The expected error message.

        Raises:
            AssertionError: If the heading of the log entry about the exception during repository store saving is missing.
        """

        def mock_isRepoRegistered(*args, **kwargs):
            """Mock the result as requested by test data"""
            return args[0] in repo_registry
            
        # Arrange
        
        # Create repository objects from slugs        
        [RepositoryStoreManager.repoStore.append(Repository(repoSlug)) for repoSlug in repo_store]
        
        RepositoryStoreManager._repoStoreFile = "repo_store.json"
        m_open = mock_open()

        # Act        
        with patch("builtins.open", m_open):
            logger_mock = MagicMock()
            with patch("repository.app.logger.error", logger_mock):
                with patch.object(RepositoryStoreManager, "isRepoRegistered", side_effect=mock_isRepoRegistered):
                    m_open.side_effect = expected_exception(expected_message)                        
                    RepositoryStoreManager.saveRepoRepository()
                
                logMessageFound = \
                    any(f"Could not save repository store to 'repo_store.json' for an error of {expected_exception.__name__}: {expected_message}" \
                        in call_args[0] for call_args \
                            in logger_mock.call_args_list)
                
                assert \
                    logMessageFound, \
                    f"{test_id}: The heading of the log entry about the exception during repository store saving is missing"                               


# Tests for the UpdateInfo class ##################################################################################################
class TestUpdateInfo:
    """
    Test the creation of an instance of UpdateInfo with default values.
    """
    
    #==============================================================================================================================
    # Create an instance of UpdateInfo with default values.
    def test_default_values(self):
        """Create an instance of UpdateInfo with default values."""
        
        update_info = UpdateInfo()
        assert update_info.repository is None
        assert update_info.updateAvailable is False