
# Imports #########################################################################################################################

# Standard libraries --------------------------------------------------------------------------------------------------------------
import datetime
import re
import pytest

# Standard library elements -------------------------------------------------------------------------------------------------------
from datetime import datetime

# Own libraries and elements ------------------------------------------------------------------------------------------------------
import repository
import customExceptions

from repository import *
from gitHubUpdateChecker import *

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
    # Populating the repository store from the repository repository with valid data should result in the 'RepositoryStoreManager.repos' property being populated with 'Repository' objects.
    def test_populate_repository_store_with_valid_data(self):
        """Populating the repository store from the repository repository with valid data should result in the 'RepositoryStoreManager.repos' property being populated with 'Repository' objects."""
        
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
            

        # Set app reference in Repository class
        repository.app = app

        # Load serialized repo store
        RepositoryStoreManager._populateRepositoryStore()

        # Assert that the repository store is populated with Repository objects
        assert isinstance(RepositoryStoreManager.repoStore, RepositoryStore)
        assert all(isinstance(repo, Repository) for repo in RepositoryStoreManager.repoStore)
    
    #==============================================================================================================================
    # Populating the repository store from the repository repository with invalid data should result in the 'RepositoryStoreManager.repos' property being empty.
    def test_populate_repository_store_with_invalid_data(self):
        """Populating the repository store from the repository repository with invalid data should result in the 'RepositoryStoreManager.repos' property being empty."""
        
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


        # Set app reference in Repository class
        repository.app = app

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

# Tests for the UpdateInfo class ##################################################################################################
class TestUpdateInfo:
    
    #==============================================================================================================================
    # Create an instance of UpdateInfo with default values.
    def test_default_values(self):
        """Create an instance of UpdateInfo with default values."""
        
        update_info = UpdateInfo()
        assert update_info.repository is None
        assert update_info.updateAvailable is False