# T1nk-R's GitHub Update Checker // test/test_gitHubUpdateChecker.py
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

# Create app instance =============================================================================================================
@pytest.fixture()
def app():
    app = gitHubUpdateChecker.app
    app.config.update({
        "TESTING": True,
    })

    yield app


# Create client instance ==========================================================================================================
@pytest.fixture()
def client(app):
    return app.test_client()


# Create runner instance ==========================================================================================================
@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


# Tests for the getUpdateInfo method ##############################################################################################
class Test_getUpdateInfo:
    """
    Test the behavior of the gitHubUpdateChecker.getUpdateInfo() function.
    """
    
    #==============================================================================================================================
    # Function receives a valid POST request with JSON body containing forceUpdateCheck, repoSlug, and clientCurrentVersion fields. 
    # The request is logged.
    def test_valid_post_request(self, client):
        """
        Submit a single request with non-forced updates to quickly see if the
        vehicle is moving at all.
        """
        
        # Arrange -----------------------------------------------------------------------------------------------------------------
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
        
        # Act ---------------------------------------------------------------------------------------------------------------------
        response = client.post(url, json = requestBody, headers=headers)
        
        
        # Assert ------------------------------------------------------------------------------------------------------------------
        assert response.content_type == mimetype                                                , "Wrong MIME type in response"
        assert response.status_code == 200                                                      , "Unexpected response code"
        assert response.json["repository"]["repoSlug"] == requestBody["appInfo"]["repoSlug"]    , "Unexpected repo's data returned"


    #==============================================================================================================================
    # Perform a force-unforced-forced check to see if both work
    @pytest.mark.parametrize( \
        "test_name,                 forcing_disabled,   check_shall_be_forced",
    [ 
        ("Forcing enabled",         False,              True),   
        ("Forcing disabled",        True,               False),  
    ])
    def test_forcing_flag(self, app, client, test_name, forcing_disabled, check_shall_be_forced, monkeypatch):
        """
        Check if forcing and non-forcing updates behave correctly.
        """
        
        # Utility to shorthand repeated assertions --------------------------------------------------------------------------------
        def assertResponse(response, expected_mimetype, expected_status_code, expected_repo_slug):
            """Check if data in response is okay"""
            
            assert \
                response.content_type == expected_mimetype, \
                "Wrong MIME type in response"
                
            assert \
                response.status_code == expected_status_code, \
                "Unexpected response code"
                
            assert \
                response.json["repository"]["repoSlug"] == expected_repo_slug, \
                "Unexpected repo's data returned"
        
        # Arrange -----------------------------------------------------------------------------------------------------------------
        
        # Set the flag to enable/disable forcing update checks accordingly in app.config
        monkeypatch.setattr(app.config, '__contains__', lambda x: x == "disableForcedChecks")
        monkeypatch.setitem(app.config, "disableForcedChecks", forcing_disabled)
        
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
        
        
        
        # Act and assert ----------------------------------------------------------------------------------------------------------

        # First a forced check to get a fresh timestamp

        response = client.post(url, json = forcedCheckRequestBody, headers=headers)

        # Check that the call went as expected
        assertResponse(response, mimetype, 200, forcedCheckRequestBody["appInfo"]["repoSlug"])
        
        firstForcedCheckTimestamp = response.json["repository"]["lastCheckedTimestamp"]
                
        # Wait one second to make sure the timestamps differ if the second check would be forced as well
        time.sleep(1)
        
        # A non-forced check to expect the timestamp to not change
        
        response = client.post(url, json = unforcedCheckRequestBody, headers=headers)

        # Check that the call went as expected
        assertResponse(response, mimetype, 200, unforcedCheckRequestBody["appInfo"]["repoSlug"])
        
        unForcedCheckTimestamp = response.json["repository"]["lastCheckedTimestamp"]
        
        # Check the timestamps are the same, i.e. no update check was performed the second time
        assert firstForcedCheckTimestamp == unForcedCheckTimestamp
        
        # Wait a second to make sure the new forced check will return a different timestamp
        time.sleep(1)

        # One another forced check to expect a new timestamp    
        response = client.post(url, data=json.dumps(forcedCheckRequestBody), headers=headers)

        # Check expectations
        assertResponse(response, mimetype, 200, forcedCheckRequestBody["appInfo"]["repoSlug"])
        
        secondForcedCheckTimestamp = response.json["repository"]["lastCheckedTimestamp"]
        
        # Check the timestamps ARE the same or ARE NOT the same, i.e. an update check was performed the third time, based on forcing flag
        assert \
            (unForcedCheckTimestamp != secondForcedCheckTimestamp) == check_shall_be_forced, \
            f"{test_name}: Second forced request was not actually forced based on timestamps"


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
        # Arrange -----------------------------------------------------------------------------------------------------------------
        
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
            
            # Act -----------------------------------------------------------------------------------------------------------------
            
            # Perform the call
            checkUpdates()
            
            # Assert --------------------------------------------------------------------------------------------------------------
            
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
        
        # Arrange -----------------------------------------------------------------------------------------------------------------
        
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

        # Act ---------------------------------------------------------------------------------------------------------------------
        
        # Submit post
        response = client.post(url, data=json.dumps(requestBody), headers=headers)

        # Assert ------------------------------------------------------------------------------------------------------------------
        assert \
            response.content_type == mimetype, \
            "Unexpected MIME type in response"
            
        assert \
            response.status_code == 500, \
            "Unexpected response code when server error occurs"
            
        assert \
            "error" in response.json.keys(), \
            "No error key in response JSON"
            
        assert \
            response.json["error"] == "You did everything right, but an internal error occurred.", \
            "Wrong error message returned"
        



# Tests for the isUpdateAvailable method ##########################################################################################
class Test_isUpdateAvailable:
    """
    Test the behavior of the gitHubUpdateChecker.isUpdateAvailable() function.
    """
    
    #==============================================================================================================================
    # Check version comparison with valid values
    @pytest.mark.parametrize( \
        "test_name,                 latest_version, current_version,    expected_result,    error_message",
    [ 
        ("New major",               "v2.0.0",       "1.0.0",            True,               "New major version not recognized"),   
        ("New minor",               "v1.1.0",       "1.0.0",            True,               "New minor version not recognized"),  
        ("New patch",               "v1.0.1",       "1.0.0",            True,               "New patch not recognized"), 
        ("Greater current major",   "v1.1.9",       "2.2.2",            False,              "Major version comparison error"),
        ("Greater current minor",   "v2.1.9",       "2.2.2",            False,              "Minor version comparison error"),
        ("Greater current patch",   "v2.2.1",       "2.2.2",            False,              "Patch comparison error"),
    ])
    def test_version_number_comparison(self, test_name, latest_version, current_version, expected_result, error_message):        
        """
        Test the version number comparison logic.

        Args:
            self: The instance of the test case.
            test_name (str): The name of the test case.
            latest_version (str): The latest version number.
            current_version (str): The current version number.
            expected_result (bool): The expected result of the version comparison.
            error_message (str): The error message to display if the test fails.

        Raises:
            AssertionError: If the version comparison does not produce the expected result.
        """
        
        # Arrange -----------------------------------------------------------------------------------------------------------------
        updateInfo = UpdateInfo()
        updateInfo.repository = Repository('repoSlug')
        updateInfo.repository.latestVersion = latest_version
        currentVersion = current_version

        # Act ---------------------------------------------------------------------------------------------------------------------
        result = _isUpdateAvailable(updateInfo, currentVersion)

        # Assert ------------------------------------------------------------------------------------------------------------------
        assert result == expected_result, f"{test_name}: {error_message}"

    #==============================================================================================================================
    # Check version comparison error handling
    @pytest.mark.parametrize( \
        "test_name,                     latest_version, current_version,    expected_exception,     error_message",
    [ 
        ("Latest version in invalid",   "invalid",      "1.0.0",            UpdateCheckingError,    "Wrong error signalled or no error signalled for invalid latest version"),
        ("Latest version is empty",     "",             "1.0.0",            UpdateCheckingError,    "Wrong error signalled or no error signalled for empty latest version"),  
        ("Current version is invalid",  "v1.0.0",       "invalid",          RequestError,           "Wrong error signalled or no error signalled for invalid current version"),
        ("Current version is none",     "v1.0.0",       "None",             RequestError,           "Wrong error signalled or no error signalled when current version is None"),
        ("Current version is empty",    "v1.0.0",       "",                 RequestError,           "Wrong error signalled or no error signalled for empty current version"),
    ])
    def test_version_number_comparison_error_handling(self, test_name, latest_version, current_version, expected_exception, error_message):        
        """
        Test the error handling in the version number comparison logic.

        Args:
            self: The instance of the test case.
            test_name (str): The name of the test case.
            latest_version (str): The latest version number.
            current_version (str): The current version number.
            expected_exception (Exception): The expected exception class.
            error_message (str): The expected error message.

        Raises:
            AssertionError: If the error handling does not produce the expected exception or error message.
        """
        
        # Arrange -----------------------------------------------------------------------------------------------------------------
        updateInfo = UpdateInfo()
        updateInfo.repository = Repository('dummyRepoSlug')
        updateInfo.repository.latestVersion = latest_version
        currentVersion = current_version

        # Act and assert ----------------------------------------------------------------------------------------------------------
        with pytest.raises(expected_exception) as ee:
            _isUpdateAvailable(updateInfo, currentVersion)
            
        if not ee:
            pytest.fail(f"{test_name}: {error_message}")
        
    #==============================================================================================================================
    # See if proper error is raised when UpdateInfo is None
    def test_updateInfo_none(self):
        """Expected to raise `UpdateCheckingError` as the `updateInfo` argument is None."""
        
        # Arrange -----------------------------------------------------------------------------------------------------------------
        
        updateInfo = None
        currentVersion = "1.0.0"

        # Arrange -----------------------------------------------------------------------------------------------------------------
        # Act and assert the proper exception
        with pytest.raises(UpdateCheckingError) as err:
            _isUpdateAvailable(updateInfo, currentVersion)
        
        # Act and assert ----------------------------------------------------------------------------------------------------------            
        
        # Assert the proper message is logged
        assert "The updateInfo argument was set to None" in err.value.logEntries
        
        # Assert the proper public message is disclosed
        assert "For an internal error, can't tell latest version number." in err.value.responseMessage
            
    #==============================================================================================================================
    # See if proper error is raised when the repository attribute of UpdateInfo is None
    def test_updateInfo_repository_none(self):
        """Expected to raise `UpdateCheckingError` as the `repository` property of the `updateInfo` argument is None."""
        
        # Arrange -----------------------------------------------------------------------------------------------------------------
        updateInfo = UpdateInfo()
        updateInfo.repository = None
        currentVersion = "1.0.0"

        # Act and assert ----------------------------------------------------------------------------------------------------------
        
        # Act and assert the proper exception
        with pytest.raises(UpdateCheckingError) as err:
            _isUpdateAvailable(updateInfo, currentVersion)
        
        # Assert the proper message is logged
        assert "The repository property of the object passed in updateInfo is set to None" in err.value.logEntries
        
        # Assert the proper public message is disclosed
        assert "For an internal error, can't tell latest version number." in err.value.responseMessage


# Tests for the _parseRequest method ##############################################################################################
class Test_parseRequest:
    """
    Test the behavior of the gitHubUpdateChecker._parseRequest() function.
    """

    #==============================================================================================================================
    # Happy path tests of parsing requests with various realistic test values
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
        
        # Act ---------------------------------------------------------------------------------------------------------------------
        with patch('repository.RepositoryStoreManager.isRepoRegistered') as mock_is_repo_registered:
            mock_is_repo_registered.return_value = True
            result = _parseRequest(input_data)

        # Assert ------------------------------------------------------------------------------------------------------------------
        assert result == expected

    #==============================================================================================================================
    # Check edge cases when parsing requests
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
        
        # Act ---------------------------------------------------------------------------------------------------------------------
        with patch('repository.RepositoryStoreManager.isRepoRegistered') as mock_is_repo_registered:
            mock_is_repo_registered.return_value = True
            result = _parseRequest(input_data)
        
        # Assert ------------------------------------------------------------------------------------------------------------------
        assert result == expected

    #==============================================================================================================================
    # Check error handling of the request parser
    @pytest.mark.parametrize("input_data, expected, isRepoRegistered", [
        
        ({"forceUpdateCheck": True}, 
        (RequestError, 400, "'appInfo' key missing from request"), 
        True),
        
        ({"appInfo": {"currentVersion": "1.0.0"}, "forceUpdateCheck": True}, 
        (RequestError, 400, "The 'repoSlug' key is missing from the 'appInfo' object, can't find out which repo to check."), 
        True),
        
        ({"appInfo": {"repoSlug": "", "currentVersion": "1.0.0"}, "forceUpdateCheck": True}, 
        (RequestError, 400, "The repo slug shall not be an empty string."), 
        True),
        
        ({"appInfo": {"repoSlug": "validRepo"}, "forceUpdateCheck": False}, 
        (RequestError, 400, "The 'currentVersion' key missing from the 'appInfo' object, would not be able to determine if there's a newer version."), 
        True),
        
        ({"appInfo": {"repoSlug": "validRepo", "currentVersion": ""}, "forceUpdateCheck": False}, 
        (RequestError, 400, "The 'currentVersion' key is set to an empty string. A valid version number is expected."), 
        True),
        
        ({"appInfo": {"repoSlug": "validRepo", "currentVersion": ""}, "forceUpdateCheck": False}, 
        (RequestError, 403, "The 'repoSlug' key specifies an unregistered repository"), 
        False),

    ])    
    def test_parse_request_error_cases(self, input_data, expected, isRepoRegistered):
        """
        Test the error cases of the `parse_request` function.

        Args:
            input_data: The input data to be parsed.
            expected: The expected output of the function.
            isRepoRegistered: Whether the given repository shall be considered (mocked) as registered
        """
        
        # Act and assert ----------------------------------------------------------------------------------------------------------
        
        # Check if the proper exception is raised
        with pytest.raises(expected_exception=expected[0]) as err:
            
            with patch('repository.RepositoryStoreManager.isRepoRegistered') as mock_is_repo_registered:
                mock_is_repo_registered.return_value = isRepoRegistered
                _parseRequest(input_data)

        # Assert the response code and the exception message is expected
        assert err.value.responseCode == expected[1]
        assert expected[2] in err.value.responseMessage
            

# Tests for the _getUpdateInfoFromGitHub method ###################################################################################
class Test_getUpdateInfoFromGitHub:
    """
    Test the behavior of the gitHubUpdateChecker.getUpdateInfoFromGitHub() function.
    """
    
    # Mock objects and helper functions ===========================================================================================
    def create_mock_response(self, status_code=200, json_data=None, headers=None):
        """
        Create a mock response object for testing purposes.

        Args:
            self: The instance of the test case.
            status_code (int): The HTTP status code of the response. Default is 200.
            json_data (dict): The JSON data of the response. Default is an empty dictionary.
            headers (dict): The headers of the response. Default is an empty dictionary.

        Returns:
            Mock: The mock response object.
        """
        
        mock_resp = Mock(spec=Response)
        mock_resp.status_code = status_code
        mock_resp.json.return_value = json_data or {}
        mock_resp.headers = headers or {}
        
        return mock_resp

    #==============================================================================================================================
    # Check happy paths, edge cases and errors
    @pytest.mark.parametrize(
        "   test_id,    json_data,              expected_update_available",
        [
            # Happy path tests
            ("HP-1",    {"tag_name": "v1.0.0"}, True),
            ("HP-2",    {"tag_name": "v2.0.0"}, True),
            
            # Edge cases
            ("EC-1",    {},                     False),  # No tag_name in response             
        ],
    )
    def test_getUpdateInfoFromGitHub(self, test_id, json_data, expected_update_available):
        """
        Test the `_getUpdateInfoFromGitHub` function.

        :param test_id: The ID of the test case.               
        :param json_data: The JSON data of the response.
        :param expected_update_available: The expected value of `updateAvailable` in the response.
        """
        
        # Arrange -----------------------------------------------------------------------------------------------------------------
        repoConn = Mock(spec=RepositoryAccessManager)
        repoConn.repoReleaseApiUrl.return_value = "https://api.github.com/repos/user/repo/releases/latest"
        repoConn.username.return_value = "user"
        repoConn.token.return_value = "token"
        
        updateInfo = Mock(spec=UpdateInfo)
        updateInfo.updateAvailable = expected_update_available
        updateInfo.repository = Mock()
        updateInfo.repository.getRepoSlug.return_value = "user/repo"
        updateInfo.repository.getCheckFrequencyDays.return_value = 1
        updateInfo.repository.setLastCheckedTimestamp = Mock()

        # Mock the requests.get call to return a custom response
        mock_response = self.create_mock_response(200, json_data, None)
        
        # Act and assert ----------------------------------------------------------------------------------------------------------
        with patch('requests.get', return_value=mock_response) as mock_get:            
            response = _getUpdateInfoFromGitHub(repoConn)            
            
            assert response == mock_response, "Unexpected response received"
                
    #==============================================================================================================================
    # Check happy paths, edge cases and errors
    @pytest.mark.parametrize(
        "   test_id,    status_code,    headers",
        [
            ("ERR-1",   400,            None),
            ("ERR-2",   401,            None),
            ("ERR-3",   403,            {"x-ratelimit-reset": str(int(time.time()) + 60 * 60)}),
            ("ERR-4",   404,            None),
            ("ERR-5",   429,            {"x-ratelimit-reset": str(int(time.time()) + 60 * 60)}),
            ("ERR-6",   500,            None),
        ],
    )
    def test_getUpdateInfoFromGitHub(self, test_id, status_code, headers):
        """
        Test the `_getUpdateInfoFromGitHub` function.

        :param test_id: The ID of the test case.       
        :param status_code: The HTTP status code of the response.
        :param headers: The headers of the response.
        """
        
        # Arrange -----------------------------------------------------------------------------------------------------------------
        
        repoConn = Mock(spec=RepositoryAccessManager)
        repoConn.repoReleaseApiUrl.return_value = "https://api.github.com/repos/user/repo/releases/latest"
        repoConn.username.return_value = "user"
        repoConn.token.return_value = "token"
        updateInfo = Mock(spec=UpdateInfo)
        updateInfo.updateAvailable = None
        updateInfo.repository = Mock()
        updateInfo.repository.getRepoSlug.return_value = "user/repo"
        updateInfo.repository.getCheckFrequencyDays.return_value = 1
        updateInfo.repository.setLastCheckedTimestamp = Mock()
        
        # Mock the requests.get call to return a custom response
        mock_response = self.create_mock_response(status_code, None, headers)
        
        # Act and assert ----------------------------------------------------------------------------------------------------------
        with patch('requests.get', return_value=mock_response) as mock_get:
            # Act and Assert

            with pytest.raises(UpdateCheckingError) as exc_info:
                _getUpdateInfoFromGitHub(repoConn)
            
            if status_code == 403:
                assert \
                    hasattr(exc_info.value, "apiLimitResetsAt"), \
                    f"{test_id}: API limit reset value expected"
                    
                assert \
                    exc_info.value.apiLimitResetsAt == datetime.fromtimestamp(int(headers["x-ratelimit-reset"])), \
                    f"{test_id}: Unexpected API limit value received"


# Tests for the _checkUpdates method ##############################################################################################
class Test_checkUpdates:
    """
    Test the behavior of the gitHubUpdateChecker._checkUpdates() function.
    """

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
    @pytest.mark.parametrize(
        "test_id, force_update_check,   client_version,         update_expected", 
    [
        ("HP-01", True,                 CLIENT_SAME_VERSION,    False),
        ("HP-02", False,                CLIENT_NEWER_VERSION,   False),
        ("HP-03", False,                CLIENT_OLDER_VERSION,   True)
    ])
    def test_check_updates_happy_path(self, test_id, force_update_check, client_version, update_expected):
        """
        Test the happy path of the checkUpdates function.
        
        Args:
            self: The instance of the test case.
            test_id (str): The ID of the test case.
            force_update_check (bool): The value of the forceUpdateCheck field.
            client_version (str): The version of the client.
            update_expected (bool): The expected value of the updateAvailable field in the response.
        """
        
        # Arrange -----------------------------------------------------------------------------------------------------------------
        repo_slug = Test_checkUpdates.VALID_REPO_SLUG
        latest_version = Test_checkUpdates.GITHUB_LATEST_VERSION
                
        with gitHubUpdateChecker.app.test_request_context(json={'forceUpdateCheck': force_update_check,
                                                                'appInfo': {'repoSlug': repo_slug, 'currentVersion': client_version}}):
            
            with patch('repository.RepositoryStoreManager.getUpdateInfoFromRepoRepository') as mock_get_update_info:
                update_info = UpdateInfo(Repository(repo_slug))
                update_info.repository.latestVersion = latest_version
                mock_get_update_info.return_value = update_info


                with    patch('repository.RepositoryAccessManager.getRepoSlug',             MagicMock(return_value=repo_slug)), \
                        patch('repository.RepositoryStoreManager.saveRepoRepository',       MagicMock(return_value=None)), \
                        patch('repository.RepositoryStoreManager.isRepoRegistered',         MagicMock(return_value=True)), \
                        patch('gitHubUpdateChecker._getUpdateInfoFromGitHub',               MagicMock()), \
                        patch('gitHubUpdateChecker._populateUpdateInfoFromGitHubResponse',  MagicMock(return_value=None)):
                            
                    # Act -----------------------------------------------------------------------------------------------------
                    response = checkUpdates()

                    # Assert --------------------------------------------------------------------------------------------------
                    assert response.status_code == 200                          , f"{test_id}: Unexpected status code in response"
                    assert response.json['updateAvailable'] == update_expected  , f"{test_id}: Unexpected value for updateAvailable"


    #==============================================================================================================================                            
    # Data and test for edge cases
    @pytest.mark.parametrize(
        "test_id, force_update_check,   client_version,         cache_expired,  update_expected",   # Scenario
    [
        ("EC-02", False,                CLIENT_SAME_VERSION,    True,           False),             # Cache expired
        ("EC-03", False,                CLIENT_SAME_VERSION,    False,          False),             # Cache not expired
        ("EC-04", False,                CLIENT_OLDER_VERSION,   True,           True),              # Cache expired
        ("EC-05", False,                CLIENT_OLDER_VERSION,   False,          True),              # Cache not expired
        ("EC-06", False,                CLIENT_NEWER_VERSION,   True,           False),             # Cache expired
        ("EC-07", False,                CLIENT_NEWER_VERSION,   False,          False),             # Cache not expired
    ])

    def test_check_updates_edge_cases(self, test_id, force_update_check, client_version, cache_expired, update_expected):
        """
        Test edge cases of the checkUpdates function.

        Args:
            self: The instance of the test case.
            test_id (str): The ID of the test case.
            force_update_check (bool): The value of the forceUpdateCheck field.
            client_version (str): The version of the client.
            latest_version (str): The latest version of the repository.
            cache_expired (bool): Indicates whether the cache is expired or not.
            update_expected (bool): The expected value of the updateAvailable field in the response.
        """
        
        # Arrange -----------------------------------------------------------------------------------------------------------------
        repo_slug = Test_checkUpdates.VALID_REPO_SLUG
        latest_version = Test_checkUpdates.GITHUB_LATEST_VERSION
        
        with gitHubUpdateChecker.app.test_request_context(json={'forceUpdateCheck': force_update_check, 
                                                                'appInfo': {'repoSlug': repo_slug, 'currentVersion': client_version}}):
            
            with patch('repository.RepositoryStoreManager.getUpdateInfoFromRepoRepository') as mock_get_update_info:
                update_info = UpdateInfo(Repository(repo_slug))
                update_info.repository.latestVersion = latest_version
                mock_get_update_info.return_value = update_info

                with    patch('repository.RepositoryAccessManager.getRepoSlug',             MagicMock(return_value=repo_slug)), \
                        patch('repository.RepositoryStoreManager.saveRepoRepository',       MagicMock(return_value=None)), \
                        patch('repository.RepositoryStoreManager.isRepoRegistered',         MagicMock(return_value=True)), \
                        patch('repository.Repository.getLastCheckedTimestamp',              MagicMock(return_value=datetime(1980, 1, 1) if cache_expired else datetime.now())), \
                        patch('gitHubUpdateChecker._getUpdateInfoFromGitHub',               MagicMock(return_value=MagicMock())), \
                        patch('gitHubUpdateChecker._populateUpdateInfoFromGitHubResponse',  MagicMock(return_value=None)):

                    # Act ---------------------------------------------------------------------------------------------------------
                    response = checkUpdates()
                    
                    # Assert --------------------------------------------------------------------------------------------------
                    assert response.status_code == 200                          , f"{test_id}: Unexpected status code in response"
                    assert response.json['updateAvailable'] == update_expected  , f"{test_id}: Unexpected value for updateAvailable"

    #==============================================================================================================================                            
    # Data and test for edge cases
    @pytest.mark.parametrize(
        "test_id, force_update_check,   client_version,         latest_version, cache_expired, update_expected, expected_exception,     expected_status_code, expected_message", 
    [
        ("EC-01", True,                 CLIENT_SAME_VERSION,    "",             False,          False,          UpdateCheckingError,    500, "For an internal error, can't tell latest version number."),  # No version info available
    ])

    def test_check_updates_error_cases_1(self, test_id, force_update_check, client_version, latest_version, cache_expired, update_expected, expected_exception, expected_status_code, expected_message):
        
        # Arrange -----------------------------------------------------------------------------------------------------------------
        repo_slug = Test_checkUpdates.VALID_REPO_SLUG
        
        with gitHubUpdateChecker.app.test_request_context(json={'forceUpdateCheck': force_update_check, 'appInfo': {'repoSlug': repo_slug, 'currentVersion': client_version}}):
            with patch('repository.RepositoryStoreManager.getUpdateInfoFromRepoRepository') as mock_get_update_info:
                update_info = UpdateInfo(Repository(repo_slug))
                update_info.repository.latestVersion = latest_version
                mock_get_update_info.return_value = update_info

                with    patch('repository.RepositoryAccessManager.getRepoSlug',             MagicMock(return_value=repo_slug)), \
                        patch('repository.RepositoryStoreManager.saveRepoRepository',       MagicMock(return_value=None)), \
                        patch('repository.RepositoryStoreManager.isRepoRegistered',         MagicMock(return_value=True)), \
                        patch('repository.Repository.getLastCheckedTimestamp',              MagicMock(return_value=datetime(1980, 1, 1) if cache_expired else datetime.now())), \
                        patch('gitHubUpdateChecker._getUpdateInfoFromGitHub',               MagicMock(return_value=MagicMock())), \
                        patch('gitHubUpdateChecker._populateUpdateInfoFromGitHubResponse',  MagicMock(return_value=None)):

                    # Act ---------------------------------------------------------------------------------------------------------
                    response = checkUpdates()
                    
                    # Assert ------------------------------------------------------------------------------------------------------
                    assert response.status_code == expected_status_code     , f"{test_id}: Unexpected status code in response"
                    assert expected_message in response.get_json()["error"] , f"{test_id}: Wrong error message in response"

    #==============================================================================================================================
    # Data and tests for error cases
    @pytest.mark.parametrize(
        "test_id,   force_update_check, repo_slug,          raised_exception,       expected_status_code,   exception_message", 
    [
        ("ERR-01",  False,              INVALID_REPO_SLUG,  RequestError,           400,                    "Request error"),
        ("ERR-02",  False,              VALID_REPO_SLUG,    EnvironmentError,       500,                    "Environment error"),
        ("ERR-03",  False,              VALID_REPO_SLUG,    UpdateCheckingError,    500,                    "Update checking error"),
        ("ERR-04",  False,              VALID_REPO_SLUG,    Exception,              500,                    "An internal error occurred. Mention the following error key when requesting support"),
    ])
    def test_check_updates_error_cases_2(self, test_id, force_update_check, repo_slug, raised_exception, expected_status_code, exception_message):
        """
        Test error cases of the checkUpdates function.

        Args:
            self: The instance of the test case.
            test_id (str): The ID of the test case.
            force_update_check (bool): The value of the forceUpdateCheck field.
            repo_slug (str): The repository slug.
            raised_exception (Exception): The expected exception class.
            expected_status_code (int): The expected status code in the response.
            exception_message (str): The expected error message in the response.
        """
        
        # Arrange -----------------------------------------------------------------------------------------------------------------        
        client_version = Test_checkUpdates.CLIENT_SAME_VERSION
        latest_version = Test_checkUpdates.GITHUB_LATEST_VERSION        
        
        with gitHubUpdateChecker.app.test_request_context(json={'forceUpdateCheck': force_update_check, 'appInfo': {'repoSlug': repo_slug, 'currentVersion': client_version}}):
            with patch('repository.RepositoryStoreManager.getUpdateInfoFromRepoRepository') as mock_get_update_info:
                update_info = UpdateInfo(Repository(repo_slug))
                update_info.repository.latestVersion = latest_version
                mock_get_update_info.return_value = update_info

                with patch('gitHubUpdateChecker._parseRequest') as mock_parse_request:

                    mock_parse_request.side_effect = raised_exception(exception_message, expected_status_code, [], None)

                    # Act ---------------------------------------------------------------------------------------------------------
                    
                    response = checkUpdates()

                    # Assert ------------------------------------------------------------------------------------------------------
                    assert response.status_code == expected_status_code         , f"{test_id}: Unexpected status code in response"
                    assert exception_message in response.get_json()["error"]    , f"{test_id}: Wrong error message in response"



# Tests for the _checkUpdates method ##############################################################################################
class Test_isForcedCheckDisabled:
    """
    Test the _isForcedCheckDisabled() function of gitHubUpdateCheker.py
    """

    #==============================================================================================================================
    # Data and tests for the function
    @pytest.mark.parametrize(
        "test_id,                   config_value,   expected_result", [
        ("HP1 - Force disabled",    True,           True),
        ("HP2 - Force enabled",     False,          False),
        ("EC1 - Force None",        None,           False),
        ("EC2 - Force empty",       "",             False),
        ("EC3 - Force #1",          1,              True),
        ("EC4 - Force #0",          0,              False),
        ("ERR1 - Force is dict",    {},             False),
        ("ERR2 - Force is list",    [],             False),
    ])
    def test_isForcedCheckDisabled(self, app, test_id, config_value, expected_result, monkeypatch):
        """
        Test the _isForcedCheckDisabled function.

        Args:
            app: The Flask application object.
            test_id: The unique identifier for the test case.
            config_value: The value to be set in the app.config["disableForcedChecks"].
            expected_result: The expected result of the function.
        """
        
        # Arrange -----------------------------------------------------------------------------------------------------------------
        monkeypatch.setattr(app.config, '__contains__', lambda x: x == "disableForcedChecks")
        monkeypatch.setitem(app.config, "disableForcedChecks", config_value)
        
        # Act ---------------------------------------------------------------------------------------------------------------------
        result = gitHubUpdateChecker._isForcedCheckDisabled()

        # Assert ------------------------------------------------------------------------------------------------------------------
        assert result == expected_result, f"Test failed for test_id: {test_id}"
