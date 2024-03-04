
# Imports #########################################################################################################################

# Standard libraries --------------------------------------------------------------------------------------------------------------
import json
import time
import pytest

# Standard library elements -------------------------------------------------------------------------------------------------------
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

# Third-party imports -------------------------------------------------------------------------------------------------------------
from requests.models import Response

import flask
#from flask import Flask, current_app

# Own libraries and elements ------------------------------------------------------------------------------------------------------
import gitHubUpdateChecker
from gitHubUpdateChecker import checkUpdates, create_app, _parseRequest, _isUpdateAvailable, _getUpdateInfoFromGitHub
from customExceptions import UpdateCheckingError, EnvironmentError, RequestError, StructuredErrorInfo
from repository import UpdateInfo, Repository, RepositoryAccessManager

# Init stuff ######################################################################################################################

flask.current_app = create_app()

@pytest.fixture()
def app():
    app = gitHubUpdateChecker.app
    app.config.update({
        "TESTING": True,
    })

    # other setup can go here

    yield app

    # clean up / reset resources here


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


# Tests for the getUpdateInfo method ##############################################################################################
class Test_GetUpdateInfo:
    
    #==============================================================================================================================
    # Function receives a valid POST request with JSON body containing forceUpdateCheck, repoSlug, and clientCurrentVersion fields. 
    # The request is logged.
    def test_valid_post_request(self, client):
        """
        Submit a single request with non-forced updates to quickly see if the
        vehicle is moving at all.
        """
        
        mimetype = 'application/json'
        headers = {
            'Content-Type': mimetype,
            'Accept': mimetype
        }
        
        requestBody = {
            'appInfo': {
                'repoSlug': 'T1nkR-Mesh-Name-Synchronizer', 
                'currentVersion': '1.0.0'
            }, 
            'forceUpdateCheck': 'false'
        }
        
        url = '/getUpdateInfo'

        response = client.post(url, json = requestBody, headers=headers)

        assert response.content_type == mimetype
        assert response.status_code == 200
        assert response.json["repository"]["repoSlug"] == requestBody["appInfo"]["repoSlug"]


    #==============================================================================================================================
    # Perform a force-unforced-forced check to see if both work
    def test_forcing_flag(self, client):
        """
        Check if forcing and non-forcing updates behave correctly.
        """
        
        mimetype = 'application/json'
        headers = {
            'Content-Type': mimetype,
            'Accept': mimetype
        }
        
        forcedCheckRequestBody = {
            'appInfo': {
                'repoSlug': 'T1nkR-Mesh-Name-Synchronizer', 
                'currentVersion': '1.0.0'
            }, 
            'forceUpdateCheck': True
        }
        
        unforcedCheckRequestBody = {
            'appInfo': {
                'repoSlug': 'T1nkR-Mesh-Name-Synchronizer', 
                'currentVersion': '1.0.0'
            }, 
            'forceUpdateCheck': False
        }
        
        url = '/getUpdateInfo'

        # First a forced check to get a fresh timestamp

        response = client.post(url, json = forcedCheckRequestBody, headers=headers)

        # Check that the call went as expected
        assert response.content_type == mimetype
        assert response.status_code == 200
        assert response.json["repository"]["repoSlug"] == forcedCheckRequestBody["appInfo"]["repoSlug"]
        
        firstForcedCheckTimestamp = response.json["repository"]["lastCheckedTimestamp"]
                
        # Wait one second to make sure the timestamps differ if the second check would be forced as well
        time.sleep(1)
        
        # A non-forced check to expect the timestamp to not change
        
        response = client.post(url, json = unforcedCheckRequestBody, headers=headers)

        # Check that the call went as expected
        assert response.content_type == mimetype
        assert response.status_code == 200
        assert response.json["repository"]["repoSlug"] == unforcedCheckRequestBody["appInfo"]["repoSlug"]
        
        unForcedCheckTimestamp = response.json["repository"]["lastCheckedTimestamp"]
        
        # Check the timestamps are the same, i.e. no update check was performed the second time
        assert firstForcedCheckTimestamp == unForcedCheckTimestamp
        
        # Wait a second to make sure the new forced check will return a different timestamp
        time.sleep(1)

        # One another forced check to expect a new timestamp    
        response = client.post(url, data=json.dumps(forcedCheckRequestBody), headers=headers)

        # Check expectations
        assert response.content_type == mimetype
        assert response.status_code == 200
        assert response.json["repository"]["repoSlug"] == forcedCheckRequestBody["appInfo"]["repoSlug"]
        
        secondForcedCheckTimestamp = response.json["repository"]["lastCheckedTimestamp"]
        
        # Check the timestamps are NOT the same, i.e. an update check was performed the third time
        assert unForcedCheckTimestamp != secondForcedCheckTimestamp


    #==============================================================================================================================
    # Check if correct exception is raised when function fails to initialize logger.
    def test_failed_logger_initialization_exception(self, mocker):
        """
        Checks if the correct exception is raised when the function fails to initialize 
        the logger.

        Args:
            app: The app instance.
            mocker: The pytest mocker object.

        Returns:
            None

        """
        
        # Set up the mock objects
        request_json = {
            'forceUpdateCheck': True,
            'repoSlug': 'test_repo',
            'clientCurrentVersion': '1.0'
        }
            
        # Mock the necessary dependencies
        with gitHubUpdateChecker.app.test_request_context(json=request_json):
            mocker.patch('flask.request')            
            mocker.patch('flask.make_response')
            mocker.patch('customExceptions.EnvironmentError')
            mocker.patch('customExceptions.StructuredErrorInfo.response')
            logger_mock = mocker.patch('gitHubUpdateChecker.app.logger.info', side_effect=Exception)
            
            # Perform the call
            checkUpdates()
            
            # Check if the exception mocked has been raised
            logger_mock.assert_called()
            
            # Assert that the response is correct and the proper exception has been thrown
            StructuredErrorInfo.response.assert_called_once()
        
        

    #==============================================================================================================================        
    # Perform a force-unforced-forced check to see if both work
    def test_failed_logger_initialization_response(self, client, mocker):
        """
        Check if instead of an exception or other error, a status 500 is returned
        for internal errors, being unable to initialize the log in this case.
        
        Args:
            client: The Flask test client.

        Returns:
            None
        """
        
        mimetype = 'application/json'
        headers = {
            'Content-Type': mimetype,
            'Accept': mimetype
        }

        requestBody = {
            'appInfo': {
                'repoSlug': 'T1nkR-Mesh-Name-Synchronizer', 
                'currentVersion': '(1,0,0)'
            }, 
            'forceUpdateCheck': False
        }

        url = '/getUpdateInfo'

        # Make sure an internal error will occur when trying to log something
        mocker.patch('gitHubUpdateChecker.app.logger.info', side_effect=Exception)

        # Submit post
        response = client.post(url, data=json.dumps(requestBody), headers=headers)

        # Check expectations
        assert response.content_type == mimetype
        assert response.status_code == 500
        assert "error" in response.json.keys()
        assert response.json["error"] == "You did everything right, but an internal error occurred."
        



# Tests for the isUpdateAvailable method ##########################################################################################
class Test_isUpdateAvailable:

    #==============================================================================================================================
    def test_latest_major_version_greater(self):
        """Expect to return true for a larger major version release."""
        
        # Arrange
        updateInfo = UpdateInfo()
        updateInfo.repository = Repository('repoSlug')
        updateInfo.repository.latestVersion = "v2.0.0"
        currentVersion = "1.0.0"

        # Act
        result = _isUpdateAvailable(updateInfo, currentVersion)

        # Assert
        assert result == True
    
    #==============================================================================================================================        
    def test_latest_minor_version_greater(self):
        """Expect to return true for a larger minor version release."""
        
        # Arrange
        updateInfo = UpdateInfo()
        updateInfo.repository = Repository('repoSlug')
        updateInfo.repository.latestVersion = "v1.1.0"
        currentVersion = "1.0.0"

        # Act
        result = _isUpdateAvailable(updateInfo, currentVersion)

        # Assert
        assert result == True
        
    #==============================================================================================================================
    def test_latest_patch_level_greater(self):
        """Expect to return true for a larger patch level release."""
        
        # Arrange
        updateInfo = UpdateInfo()
        updateInfo.repository = Repository('repoSlug')
        updateInfo.repository.latestVersion = "v1.0.1"
        currentVersion = "1.0.0"

        # Act
        result = _isUpdateAvailable(updateInfo, currentVersion)

        # Assert
        assert result == True
        
    #==============================================================================================================================
    def test_latest_major_version_smaller(self):
        """Expect to return false for a smaller major version release."""
        
        # Arrange
        updateInfo = UpdateInfo()
        updateInfo.repository = Repository('repoSlug')
        updateInfo.repository.latestVersion = "v1.1.9"
        currentVersion = "2.2.2"

        # Act
        result = _isUpdateAvailable(updateInfo, currentVersion)

        # Assert
        assert result == False
        
    #==============================================================================================================================
    def test_latest_minor_version_smaller(self):
        """Expect to return false for a smaller minor version release."""
        
        # Arrange
        updateInfo = UpdateInfo()
        updateInfo.repository = Repository('repoSlug')
        updateInfo.repository.latestVersion = "v2.1.9"
        currentVersion = "2.2.2"

        # Act
        result = _isUpdateAvailable(updateInfo, currentVersion)

        # Assert
        assert result == False
        
    #==============================================================================================================================
    def test_latest_patch_level_smaller(self):
        """Expect to return false for a smaller patch level releases."""
        
        # Arrange
        updateInfo = UpdateInfo()
        updateInfo.repository = Repository('repoSlug')
        updateInfo.repository.latestVersion = "v2.2.1"
        currentVersion = "2.2.2"

        # Act
        result = _isUpdateAvailable(updateInfo, currentVersion)

        # Assert
        assert result == False

    #==============================================================================================================================
    def test_invalid_latest_version_format(self):
        """Expected to raise `UpdateCheckingError` as the latest version number is not in the expected format."""
        # Arrange
        updateInfo = UpdateInfo()
        updateInfo.repository = Repository('dummyRepoSlug')
        updateInfo.repository.latestVersion = "invalid format"
        currentVersion = "1.0.0"

        # Act and Assert
        with pytest.raises(UpdateCheckingError):
            _isUpdateAvailable(updateInfo, currentVersion)
            
    #==============================================================================================================================
    def test_empty_latest_version_format(self):
        """Expected to raise `UpdateCheckingError` as the latest version number is empty."""
        # Arrange
        updateInfo = UpdateInfo()
        updateInfo.repository = Repository('dummyRepoSlug')
        updateInfo.repository.latestVersion = ""
        currentVersion = "1.0.0"

        # Act and Assert
        with pytest.raises(UpdateCheckingError):
            _isUpdateAvailable(updateInfo, currentVersion)
            
    #==============================================================================================================================
    def test_currentVersion_none(self):
        """Expected to raise `UpdateCheckingError` as the `currentVersion` argument is None."""
        # Arrange
        updateInfo = UpdateInfo()
        updateInfo.repository = Repository('dummyRepoSlug')
        updateInfo.repository.latestVersion = "v1.1.1"
        currentVersion = None

        # Act and Assert
        with pytest.raises(RequestError):
            _isUpdateAvailable(updateInfo, currentVersion)
            
    #==============================================================================================================================
    def test_currentVersion_empty(self):        
        """Expected to raise `UpdateCheckingError` as the `currentVersion` argument is empty string."""
        # Arrange
        updateInfo = UpdateInfo()
        updateInfo.repository = Repository('dummyRepoSlug')
        updateInfo.repository.latestVersion = "v1.1.1"
        currentVersion = ""

        # Act and Assert
        with pytest.raises(RequestError):
            _isUpdateAvailable(updateInfo, currentVersion)
            
    #==============================================================================================================================
    def test_currentVersion_invalid(self):
        """Expected to raise UpdateCheckingError as the `currentVersion` argument is invalid."""
        # Arrange
        updateInfo = UpdateInfo()
        updateInfo.repository = Repository('dummyRepoSlug')
        updateInfo.repository.latestVersion = "v1.1.1"
        currentVersion = "invalid"

        # Act and Assert
        with pytest.raises(RequestError):
            _isUpdateAvailable(updateInfo, currentVersion)
            
    #==============================================================================================================================
    def test_updateInfo_none(self):
        """Expected to raise `UpdateCheckingError` as the `updateInfo` argument is None."""
        # Arrange
        updateInfo = None
        currentVersion = "1.0.0"

        # Act and assert the proper exception
        with pytest.raises(UpdateCheckingError) as err:
            _isUpdateAvailable(updateInfo, currentVersion)
            
        # Assert the proper message is logged
        assert "The updateInfo argument was set to None" in err.value.logEntries
        
        # Assert the proper public message is disclosed
        assert "For an internal error, can't tell latest version number." in err.value.responseMessage
            
    #==============================================================================================================================
    def test_updateInfo_repository_none(self):
        """Expected to raise `UpdateCheckingError` as the `repository` property of the `updateInfo` argument is None."""
        # Arrange
        updateInfo = UpdateInfo()
        updateInfo.repository = None
        currentVersion = "1.0.0"

        # Act and assert the proper exception
        with pytest.raises(UpdateCheckingError) as err:
            _isUpdateAvailable(updateInfo, currentVersion)
        
        # Assert the proper message is logged
        assert "The repository property of the object passed in updateInfo is set to None" in err.value.logEntries
        
        # Assert the proper public message is disclosed
        assert "For an internal error, can't tell latest version number." in err.value.responseMessage


# Tests for the _parseRequest method ##############################################################################################
class Test_parseRequest:

    #==============================================================================================================================
    # Happy path tests with various realistic test values
    @pytest.mark.parametrize("input_data, expected", [
        
        ({"appInfo": {"repoSlug": "validRepo", "currentVersion": "1.0.0"}, "forceUpdateCheck": True}, 
        (True, "validRepo", "1.0.0")),
        
        ({"appInfo": {"repoSlug": "anotherRepo", "currentVersion": "2.1.3"}, "forceUpdateCheck": False}, 
        (False, "anotherRepo", "2.1.3")),
        
        ({"appInfo": {"repoSlug": "repoWithNumbers123", "currentVersion": "0.0.1"}, "forceUpdateCheck": "true"}, 
        (True, "repoWithNumbers123", "0.0.1")),
        
        ({"appInfo": {"repoSlug": "repoWithNumbers123", "currentVersion": "0.0.1"}, "forceUpdateCheck": "false"}, 
        (False, "repoWithNumbers123", "0.0.1"))
    ])
    def test_parse_request_happy_path(self, input_data, expected):
        """
        Test the happy path of the `parse_request` function.

        Args:
            input_data: The input data to be parsed.
            expected: The expected output of the function.

        Returns:
            None
        """
        # Act
        result = _parseRequest(input_data)

        # Assert
        assert result == expected

    #==============================================================================================================================
    # Edge case data        
    @pytest.mark.parametrize("input_data, expected", [        
        ({"appInfo": {"repoSlug": "validRepo", "currentVersion": "1.0.0"}, "forceUpdateCheck": True}, 
        (True, "validRepo", "1.0.0")),
        
        ({"appInfo": {"repoSlug": "anotherRepo", "currentVersion": "2.1.3"}, "forceUpdateCheck": False}, 
        (False, "anotherRepo", "2.1.3")),
        
        ({"appInfo": {"repoSlug": "repoWithNumbers123", "currentVersion": "0.0.1"}, "forceUpdateCheck": "true"}, 
        (True, "repoWithNumbers123", "0.0.1")),
        
        ({"appInfo": {"repoSlug": "repoWithNumbers123", "currentVersion": "0.0.1"}, "forceUpdateCheck": "false"}, 
        (False, "repoWithNumbers123", "0.0.1")),
                
        ({"appInfo": {"repoSlug": "foo", "currentVersion": "1.0.0"}}, 
        (False, "foo", "1.0.0")), # forceUpdateCheck missing
        
        ({"appInfo": {"repoSlug": "validRepo", "currentVersion": "1.0.0"}, "forceUpdateCheck": ""}, 
        (False, "validRepo", "1.0.0")), # forceUpdateCheck empty string
        
        ({"appInfo": {"repoSlug": "validRepo", "currentVersion": "1.0.0"}, "forceUpdateCheck": "yes, please"}, 
        (False, "validRepo", "1.0.0")), # forceUpdateCheck cannot be converted to bool
    ])
    def test_parse_request_edge_cases(self, input_data, expected):
        """
        Test edge cases of the `parse_request` function not yielding errors.

        Args:
            input_data: The input data to be parsed.
            expected: The expected output of the function.

        Returns:
            None
        """
        
        # Act
        result = _parseRequest(input_data)

        # Assert
        assert result == expected

    #==============================================================================================================================
    # Data to produce errors
    @pytest.mark.parametrize("input_data, expected", [
        ({"forceUpdateCheck": True}, 
        (RequestError, 400, "'appInfo' key missing from request")),
        
        ({"appInfo": {"currentVersion": "1.0.0"}, "forceUpdateCheck": True}, 
        (RequestError, 400, "The 'repoSlug' key is missing from the 'appInfo' object, can't find out which repo to check.")),
        
        ({"appInfo": {"repoSlug": "", "currentVersion": "1.0.0"}, "forceUpdateCheck": True}, 
        (RequestError, 400, "The repo slug shall not be an empty string.")),
        
        ({"appInfo": {"repoSlug": "validRepo"}, "forceUpdateCheck": False}, 
        (RequestError, 400, "The 'currentVersion' key missing from the 'appInfo' object, would not be able to determine if there's a newer version.")),
        
        ({"appInfo": {"repoSlug": "validRepo", "currentVersion": ""}, "forceUpdateCheck": False}, 
        (RequestError, 400, "The 'currentVersion' key is set to an empty string. A valid version number is expected.")),

    ])    
    def test_parse_request_error_cases(self, input_data, expected):
        """
        Test the error cases of the `parse_request` function.

        Args:
            input_data: The input data to be parsed.
            expected: The expected output of the function.

        Returns:
            None
        """
        
        with pytest.raises(expected_exception=expected[0]) as err:
            _parseRequest(input_data)

        # Assert the response code and the exception message is expected
        assert err.value.responseCode == expected[1]
        assert expected[2] in err.value.responseMessage
            

# Tests for the _getUpdateInfoFromGitHub method ###################################################################################
class Test_getUpdateInfoFromGitHub:
    
    # Mock objects and helper functions ===========================================================================================
    def create_mock_response(self, status_code=200, json_data=None, headers=None):
        mock_resp = Mock(spec=Response)
        mock_resp.status_code = status_code
        mock_resp.json.return_value = json_data or {}
        mock_resp.headers = headers or {}
        return mock_resp

    #==============================================================================================================================
    # Check happy paths, edge cases and errors
    @pytest.mark.parametrize(
        "test_id, repo_api_url, username, token, status_code, json_data, headers, expected_exception, expected_update_available",
        [
            # Happy path tests
            ("HP-1", "https://api.github.com/repos/user/repo/releases/latest", "user", "token", 200, {"tag_name": "v1.0.0"}, None, None, True),
            ("HP-2", "https://api.github.com/repos/user/repo/releases/latest", "user", "token", 200, {"tag_name": "v2.0.0"}, None, None, True),
            
            # Edge cases
            ("EC-1", "https://api.github.com/repos/user/repo/releases/latest", "user", "token", 200, {}, None, None, False),  # No tag_name in response
            
            # Error cases
            ("ERR-1", "https://api.github.com/repos/user/repo/releases/latest", "user", "token", 400, None, None, UpdateCheckingError, False),
            ("ERR-2", "https://api.github.com/repos/user/repo/releases/latest", "user", "token", 401, None, None, UpdateCheckingError, False),
            ("ERR-3", "https://api.github.com/repos/user/repo/releases/latest", "user", "token", 403, None, {"x-ratelimit-reset": str(int(time.time()) + 60 * 60)}, UpdateCheckingError, False),
            ("ERR-4", "https://api.github.com/repos/user/repo/releases/latest", "user", "token", 404, None, None, UpdateCheckingError, False),
            ("ERR-5", "https://api.github.com/repos/user/repo/releases/latest", "user", "token", 429, None, {"x-ratelimit-reset": str(int(time.time()) + 60 * 60)}, UpdateCheckingError, False),
            ("ERR-6", "https://api.github.com/repos/user/repo/releases/latest", "user", "token", 500, None, None, UpdateCheckingError, False),
            ("ERR-7", "https://api.github.com/repos/user/repo/releases/latest", "user", "token", 200, None, None, None, False),
        ],
    )
    def test_getUpdateInfoFromGitHub(self, test_id, repo_api_url, username, token, status_code, json_data, headers, expected_exception, expected_update_available):
        """
        Test the `_getUpdateInfoFromGitHub` function.

        :param test_id: The ID of the test case.
        :param repo_api_url: The API URL of the repository.
        :param username: The username for API access.
        :param token: The GitHub token.
        :param status_code: The HTTP status code of the response.
        :param json_data: The JSON data of the response.
        :param headers: The headers of the response.
        :param expected_exception: The expected exception class.
        :param expected_update_available: The expected value of `updateAvailable` in the response.

        :raises expected_exception: If there is an error while checking for updates.                        
        """
        # Arrange
        repoConn = Mock(spec=RepositoryAccessManager)
        repoConn.repoReleaseApiUrl.return_value = repo_api_url
        repoConn.username.return_value = username
        repoConn.token.return_value = token
        updateInfo = Mock(spec=UpdateInfo)
        updateInfo.updateAvailable = None
        updateInfo.repository = Mock()
        updateInfo.repository.getRepoSlug.return_value = "user/repo"
        updateInfo.repository.getCheckFrequencyDays.return_value = 1
        updateInfo.repository.setLastCheckedTimestamp = Mock()

        # Mock the requests.get call to return a custom response
        mock_response = self.create_mock_response(status_code, json_data, headers)
        with patch('requests.get', return_value=mock_response) as mock_get:
            # Act and Assert
            
            # sourcery skip: no-conditionals-in-tests
            if expected_exception:
                with pytest.raises(expected_exception) as exc_info:
                    _getUpdateInfoFromGitHub(repoConn)
                
                if status_code == 403:
                    assert hasattr(exc_info.value, "apiLimitResetsAt")
                    assert exc_info.value.apiLimitResetsAt == datetime.fromtimestamp(int(headers["x-ratelimit-reset"]))
            else:
                response = _getUpdateInfoFromGitHub(repoConn)            
                assert response == mock_response

# Tests for the _checkUpdates method ##############################################################################################
class Test_checkUpdates:

    # Init common stuff ===========================================================================================================
    app = create_app()

    # Constants for test cases
    VALID_REPO_SLUG = "valid/repo"
    INVALID_REPO_SLUG = "invalid/repo"
    CLIENT_SAME_VERSION = "1.0.0"
    CLIENT_NEWER_VERSION = "1.1.0"
    CLIENT_OLDER_VERSION = "0.9.0"
    GITHUB_LATEST_VERSION = "v1.0.0"


    #==============================================================================================================================
    # Data and test for happy path
    @pytest.mark.parametrize("test_id, force_update_check, repo_slug, client_version, latest_version, cache_expired, update_expected", 
    [
        ("HP-01", True, VALID_REPO_SLUG, CLIENT_SAME_VERSION, GITHUB_LATEST_VERSION, False, False),
        ("HP-02", False, VALID_REPO_SLUG, CLIENT_NEWER_VERSION, GITHUB_LATEST_VERSION, True, False),
        ("HP-03", False, VALID_REPO_SLUG, CLIENT_OLDER_VERSION, GITHUB_LATEST_VERSION, True, True)
    ])
    def test_check_updates_happy_path(self, test_id, force_update_check, repo_slug, client_version, latest_version, cache_expired, update_expected):
        # Arrange
        with gitHubUpdateChecker.app.test_request_context(json={'forceUpdateCheck': force_update_check, 'appInfo': {'repoSlug': repo_slug, 'currentVersion': client_version}}):
            with patch('repository.RepositoryStoreManager.getUpdateInfoFromRepoRepository') as mock_get_update_info:
                update_info = UpdateInfo(Repository(repo_slug))
                update_info.repository.latestVersion = latest_version
                mock_get_update_info.return_value = update_info

                with patch('repository.RepositoryAccessManager') as mock_repo_access_manager:
                    mock_repo_access_manager.return_value.getRepoSlug.return_value = repo_slug

                    with patch('repository.RepositoryStoreManager.saveRepoRepository') as mock_save_repo_repository:
                        mock_save_repo_repository.return_value = None

                        with patch('gitHubUpdateChecker._getUpdateInfoFromGitHub') as mock_get_update_info_from_github:
                            mock_get_update_info_from_github.return_value = MagicMock()

                            with patch('gitHubUpdateChecker._populateUpdateInfoFromGitHubResponse') as mock_populate_update_info:
                                mock_populate_update_info.return_value = None

                                # Act
                                response = checkUpdates()

                                # Assert
                                assert response.status_code == 200
                                assert response.json['updateAvailable'] == update_expected

    #==============================================================================================================================                            
    # Data and test for edge cases
    @pytest.mark.parametrize("test_id, force_update_check, repo_slug, client_version, latest_version, cache_expired, update_expected, expected_exception, expected_status_code, expected_message", 
    [
        ("EC-01", True, VALID_REPO_SLUG, CLIENT_SAME_VERSION, "", False, False, UpdateCheckingError, 500, "For an internal error, can't tell latest version number."),  # No version info available
        ("EC-02", False, VALID_REPO_SLUG, CLIENT_SAME_VERSION, GITHUB_LATEST_VERSION, True, False, None, 200, ""),   # Cache expired
        ("EC-03", False, VALID_REPO_SLUG, CLIENT_SAME_VERSION, GITHUB_LATEST_VERSION, False, False, None, 200, ""),  # Cache not expired
        ("EC-04", False, VALID_REPO_SLUG, CLIENT_OLDER_VERSION, GITHUB_LATEST_VERSION, True, True, None, 200, ""),   # Cache expired
        ("EC-05", False, VALID_REPO_SLUG, CLIENT_OLDER_VERSION, GITHUB_LATEST_VERSION, False, True, None, 200, ""),  # Cache not expired
        ("EC-06", False, VALID_REPO_SLUG, CLIENT_NEWER_VERSION, GITHUB_LATEST_VERSION, True, False, None, 200, ""),  # Cache expired
        ("EC-07", False, VALID_REPO_SLUG, CLIENT_NEWER_VERSION, GITHUB_LATEST_VERSION, False, False, None, 200, ""), # Cache not expired
    ])
    def test_check_updates_edge_cases(self, test_id, force_update_check, repo_slug, client_version, latest_version, cache_expired, update_expected, expected_exception, expected_status_code, expected_message):
        # Arrange
        with gitHubUpdateChecker.app.test_request_context(json={'forceUpdateCheck': force_update_check, 'appInfo': {'repoSlug': repo_slug, 'currentVersion': client_version}}):
            with patch('repository.RepositoryStoreManager.getUpdateInfoFromRepoRepository') as mock_get_update_info:
                update_info = UpdateInfo(Repository(repo_slug))
                update_info.repository.latestVersion = latest_version
                mock_get_update_info.return_value = update_info

                with patch('repository.RepositoryAccessManager') as mock_repo_access_manager:
                    mock_repo_access_manager.return_value.getRepoSlug.return_value = repo_slug

                    with patch('repository.RepositoryStoreManager.saveRepoRepository') as mock_save_repo_repository:
                        mock_save_repo_repository.return_value = None

                        with patch('gitHubUpdateChecker._getUpdateInfoFromGitHub') as mock_get_update_info_from_github:
                            mock_get_update_info_from_github.return_value = MagicMock()

                            with patch('gitHubUpdateChecker._populateUpdateInfoFromGitHubResponse') as mock_populate_update_info:                            
                                mock_populate_update_info.return_value = None
                                
                                with patch('repository.Repository.getLastCheckedTimestamp') as mock_getLastCheckedTimestamp:
                                    mock_getLastCheckedTimestamp.return_value = datetime(1980, 1, 1) if cache_expired else datetime.now()                                

                                    # Act
                                    response = checkUpdates()
                                    
                                    # Assert
                                    if expected_exception is None:                            
                                        assert response.status_code == 200
                                        assert response.json['updateAvailable'] == update_expected
                                    else:
                                        assert response.status_code == expected_status_code
                                        assert expected_message in response.get_json()["error"]


    #==============================================================================================================================
    # Data and tests for error cases
    @pytest.mark.parametrize("test_id, force_update_check, repo_slug, client_version, latest_version, raised_exception, expected_status_code, exception_message", 
    [
        ("ERR-01", False, INVALID_REPO_SLUG, CLIENT_SAME_VERSION, GITHUB_LATEST_VERSION, RequestError, 400, "Request error"),
        ("ERR-02", False, VALID_REPO_SLUG, CLIENT_SAME_VERSION, GITHUB_LATEST_VERSION, EnvironmentError, 500, "Environment error"),
        ("ERR-03", False, VALID_REPO_SLUG, CLIENT_SAME_VERSION, GITHUB_LATEST_VERSION, UpdateCheckingError, 500, "Update checking error"),
        ("ERR-04", False, VALID_REPO_SLUG, CLIENT_SAME_VERSION, GITHUB_LATEST_VERSION, Exception, 500, "An internal error occurred. Mention the following error key when requesting support"),
    ])
    def test_check_updates_error_cases(self, test_id, force_update_check, repo_slug, client_version, latest_version, raised_exception, expected_status_code, exception_message):
        """Expect the method to never fail but instead return a response referring to the nature of the error.
        """
        # Arrange
        with gitHubUpdateChecker.app.test_request_context(json={'forceUpdateCheck': force_update_check, 'appInfo': {'repoSlug': repo_slug, 'currentVersion': client_version}}):
            with patch('repository.RepositoryStoreManager.getUpdateInfoFromRepoRepository') as mock_get_update_info:
                update_info = UpdateInfo(Repository(repo_slug))
                update_info.repository.latestVersion = latest_version
                mock_get_update_info.return_value = update_info

                with patch('gitHubUpdateChecker._parseRequest') as mock_parse_request:

                    mock_parse_request.side_effect = raised_exception(exception_message, expected_status_code, [], None)

                    # Act
                    
                    response = checkUpdates()

                    # Assert
                    assert response.status_code == expected_status_code
                    assert exception_message in response.get_json()["error"]


