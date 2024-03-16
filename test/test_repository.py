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
        assert isinstance(repo_access_manager, RepositoryAccessManager)

    #==============================================================================================================================
    # Can get the URL of the repository
    def test_get_repo_url(self):
        """Can get the URL of the repository"""
        
        repo_access_manager = RepositoryAccessManager("T1nkR-Mesh-Name-Synchronizer")
        assert repo_access_manager.repoUrl() == "https://github.com/gusztavj/T1nkR-Mesh-Name-Synchronizer/"

    #==============================================================================================================================
    # Can get the API URL to get latest release information
    def test_get_repo_release_api_url(self):
        """Can get the API URL to get latest release information"""
        
        repo_access_manager = RepositoryAccessManager("T1nkR-Mesh-Name-Synchronizer")
        assert repo_access_manager.repoReleaseApiUrl() == "https://api.github.com/repos/gusztavj/T1nkR-Mesh-Name-Synchronizer/releases/latest"

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

    #==============================================================================================================================
    # Creating an instance of AppInfo with valid repoSlug and currentVersion should return an object with the same attributes.
    def test_valid_instance(self):
        """Creating an instance of AppInfo with valid repoSlug and currentVersion should return an object with the same attributes."""
        
        app_info = AppInfo(repoSlug="user/repo", currentVersion="1.0.0")
        assert app_info.repoSlug == "user/repo"
        assert app_info.currentVersion == "1.0.0"

    #==============================================================================================================================
    # Modifying the attributes of an instance of AppInfo should update the values of the attributes accordingly.
    def test_modify_attributes(self):
        """Modifying the attributes of an instance of AppInfo should update the values of the attributes accordingly."""
        
        app_info = AppInfo(repoSlug="user/repo", currentVersion="1.0.0")
        app_info.repoSlug = "new_user/new_repo"
        app_info.currentVersion = "2.0.0"
        assert app_info.repoSlug == "new_user/new_repo"
        assert app_info.currentVersion == "2.0.0"
    

# Tests for the Repository class ##################################################################################################
class TestRepository:

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
        
        assert repo.getRepoSlug() == "my-repo"
        assert repo.getCheckFrequencyDays() == 7
        assert repo.latestVersion == "1.0.0"
        assert repo.latestVersionName == "Release 1.0.0"
        assert repo.getLastCheckedTimestamp() == exceptedTimeStamp
        assert repo.releaseUrl == "https://github.com/my-repo/releases/tag/1.0.0"
        assert repo.repoUrl == "https://github.com/my-repo"

    #==============================================================================================================================
    # Updating the lastCheckedTimestamp property of a Repository instance should change its value to the new value.
    def test_update_lastCheckedTimestamp(self):
        """Updating the lastCheckedTimestamp property of a Repository instance should change its value to the new value."""
        
        repo = Repository("Foo")
        new_timestamp = datetime.now()
        repo.setLastCheckedTimestamp(new_timestamp)
        assert repo.getLastCheckedTimestamp() == new_timestamp

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
        assert re.match(
            '\{"repoSlug": "test_repo", "checkFrequencyDays": \d+, "lastCheckedTimestamp": "[^"]*", "latestVersion": "", "latestVersionName": "", "releaseUrl": "", "repoUrl": ""\}',
            json_data
        )

    #==============================================================================================================================
    # Datetime objects can be serialized to JSON using the custom default method of RepositoryEncoder.
    def test_datetime_serialization(self):  # sourcery skip: class-extract-method
        """Datetime objects can be serialized to JSON using the custom default method of RepositoryEncoder."""
        
        dt = datetime(2022, 1, 1)
        encoder = RepositoryEncoder()
        json_data = encoder.encode(dt)
        assert json_data == '"2022-01-01 00:00:00"'

    #==============================================================================================================================
    # The custom default method returns the __dict__ representation of non-datetime objects.
    def test_dict_representation(self):
        """The custom default method returns the __dict__ representation of non-datetime objects."""
        
        obj = {"key": "value"}
        encoder = RepositoryEncoder()
        json_data = encoder.encode(obj)
        assert json_data == '{"key": "value"}'

    #==============================================================================================================================
    # The object passed to the default method is not a datetime object or a Repository object.
    def test_non_datetime_repository_object(self):
        """The object passed to the default method is not a datetime object or a Repository object."""
        
        obj = {}
        encoder = RepositoryEncoder()
        json_data = encoder.encode(obj)
        assert json_data == '{}'

    #==============================================================================================================================
    # The datetime object passed to the default method is not in the format specified in the app configuration.
    def test_invalid_datetime_format(self):
        """The datetime object passed to the default method is not in the format specified in the app configuration."""
        
        dt = datetime(2022, 1, 1)
        app.config = {"dateTimeFormat": "%Y-%m-%d"}
        encoder = RepositoryEncoder()
        json_data = encoder.encode(dt)
        assert json_data == '"2022-01-01"'

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
            assert json_data == '{"attr": {}}'

# Tests for the RepositoryDecoder class ###########################################################################################
class TestRepositoryDecoder:
    
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

        assert isinstance(repo, Repository)
        assert repo.repoSlug == "my-repo"
        assert repo.checkFrequencyDays == 7
        assert repo.latestVersion == "1.0.0"
        assert repo.latestVersionName == "First Release"
        assert repo.lastCheckedTimestamp == datetime.strptime(repo_dict["lastCheckedTimestamp"], repository.app.config["dateTimeFormat"])
        assert repo.releaseUrl == "https://github.com/my-repo/releases/latest"
        assert repo.repoUrl == "https://github.com/my-repo"
    
    
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
    
    #==============================================================================================================================
    # Cannot add an object that is not a Repository to the RepositoryStore
    def test_cannot_add_non_repository_object(self):
        """Cannot add an object that is not a Repository to the RepositoryStore"""
        
        repoStore = RepositoryStore()
        with pytest.raises(EnvironmentError):
            repoStore.append("not a repository")
        assert len(repoStore) == 0
        
        
# Tests for the RepositoryStoreManager class ####################################################################################==
class TestRepositoryStoreManager:

    #==============================================================================================================================
    # Populating the repository store from the repository store file with valid data should result in the 'RepositoryStoreManager.repos' property being populated with 'Repository' objects.
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
        assert isinstance(RepositoryStoreManager.repoStore, RepositoryStore)
        assert all(isinstance(repo, Repository) for repo in RepositoryStoreManager.repoStore)
        
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
        assert isinstance(RepositoryStoreManager.repoStore, RepositoryStore)
        assert all(isinstance(repo, Repository) for repo in RepositoryStoreManager.repoStore)
        
        # Assert that the non-registered repo is not loaded
        assert len(RepositoryStoreManager.repoStore) == 1
        assert RepositoryStoreManager.repoStore[0].repoSlug == app.config["repoRepository"][0]["repoSlug"]
        
    
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
        assert len(RepositoryStoreManager.repoStore) == 0


    def test_loadRepositoryRegistry_happy_path(self):
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
                    assert len(app.config[RepositoryStoreManager._repoRegistryKey]) == len(SUPPORTED_REPOSITORIES)
                    
                    with patch("builtins.open", mock_open(read_data=json.dumps({"supported-repositories": EXTRA_REPOSITORY}))):
                        RepositoryStoreManager._loadRepositoryRegistry()

                        # Assert the length is the same, no new item was loaded
                        assert len(app.config[RepositoryStoreManager._repoRegistryKey]) == len(SUPPORTED_REPOSITORIES)

        loadRepoRepo_edge_case_data = [
        # Add edge case scenarios here
    ]

    
    @pytest.mark.parametrize("test_id, exception, error_message", 
    [
        ("EC001", OSError, "Could not load repository registry"),  # OSError when opening file
        ("EC002", json.JSONDecodeError, "JSONDecodeError"),  # JSON decode error
    ])
    def test_loadRepositoryRegistry_error_cases(self, test_id, exception, error_message):
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
                        assert exc_info.value.responseCode == 500
                        assert "An internal error occurred. Mention the following error key when requesting support:" in exc_info.value.responseMessage
                        assert error_message in str(exc_info.value.logEntries)


# Assuming RepositoryStoreManager and RepositoryEncoder are defined in repository.py

    @pytest.mark.parametrize("test_id, repo_store, repo_registry, expected_output, expected_exception, expected_message", [
        # Happy path tests
        ("happy-1", ["repo1", "repo2"], ["repo1", "repo2"], '[\n    "repo1",\n    "repo2"\n]', None, ""),
        ("happy-2", ["repo1", "repo2"], ["repo1"], '[\n    "repo1"\n]', None, ""),
        ("happy-3", [], [], '[]', None, ""),
        
        # Edge cases
        ("edge-1", ["repo1"], ["repo1"], '[\n    "repo1"\n]', None, ""),
        
        # Error cases
        ("error-1", ["repo1"], ["repo1"], None, IOError, "Failed to open file for writing"),
    ])
    def test_saveRepoRepository(self, test_id, repo_store, repo_registry, expected_output, expected_exception, expected_message):
        
        def mock_isRepoRegistered(*args, **kwargs):
            return args[0] in repo_registry
            
        # Arrange
        RepositoryStoreManager.repoStore = repo_store
        RepositoryStoreManager._repoStoreFile = "repo_store.json"
        m_open = mock_open()

        # Act        
        with patch("builtins.open", m_open):
            if expected_exception:
                # Mock app.logger.error
                logger_mock = MagicMock()
                with patch("repository.app.logger.error", logger_mock):
                    with patch.object(RepositoryStoreManager, "isRepoRegistered", side_effect=mock_isRepoRegistered):
                        m_open.side_effect = OSError("Failed to open file for writing")                        
                        RepositoryStoreManager.saveRepoRepository()
                    
                    logMessageFound = any("Could not save repository store to 'repo_store.json' for an error of OSError: Failed to open file for writing" in call_args[0] for call_args in logger_mock.call_args_list)
                    assert logMessageFound, "The heading of the log entry about the exception during repository store saving is missing"
                    
            else:
                with patch.object(RepositoryStoreManager, "isRepoRegistered", side_effect=mock_isRepoRegistered):
                    RepositoryStoreManager.saveRepoRepository()
                    
                m_open.assert_called_once_with("repo_store.json", "w")
                m_open().write.assert_called_once_with(expected_output)



# Tests for the UpdateInfo class ##################################################################################################
class TestUpdateInfo:
    
    #==============================================================================================================================
    # Create an instance of UpdateInfo with default values.
    def test_default_values(self):
        """Create an instance of UpdateInfo with default values."""
        
        update_info = UpdateInfo()
        assert update_info.repository is None
        assert update_info.updateAvailable is False