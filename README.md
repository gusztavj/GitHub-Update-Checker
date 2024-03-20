# T1nk-R's GitHub Update Checker

Authored by T1nk-R ([https://github.com/gusztavj/](https://github.com/gusztavj/))

This Flask-based web server application works as a middleware or proxy between a Python module/application and GitHub and can be used to perform checking for updates using your personal GitHub API key without disclosing it to the public and without flooding GitHub. For the latter, this proxy stores fresh release (version) information in its cache and serves requests from the cache until it expires or direct checking is forced.

Help, support, updates and anything else: [https://github.com/gusztavj/GitHub-Update-Checker/](https://github.com/gusztavj/GitHub-Update-Checker/)

## Legal Matters

### Copyright

### MIT License

Copyright (c) 2024, T1nk-R (Gusztáv Jánvári)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify,  merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is  furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

### Commercial Use

I would highly appreciate to get notified via [janvari.gusztav@imprestige.biz](mailto:janvari.gusztav@imprestige.biz) about any such usage. I would be happy to learn this work is of your interest, and to discuss options for commercial support and other services you may need.

### DISCLAIMER

This application is provided as-is. Use at your own risk. No warranties, no guarantee, no liability,
no matter what happens.

You may learn more about legal matters on page [https://github.com/gusztavj/GitHub-Update-Checker/](https://github.com/gusztavj/GitHub-Update-Checker/)

## Requirements

* This application can be deployed on a web server running [Flask](https://flask.palletsprojects.com/). You need Flask 3.0+.
* You need Python 3.10.11+.
* Required Python modules are listed in [requirements.txt](./requirements.txt).
* You also need access to a web server (where Flask is deployed) and you may need certain rights, such as being able to write log files. More on such requirements can be found in [Flask's documentation](https://flask.palletsprojects.com/). You web hosting service provider may help you in deploying Flash. For example, cPanel makes it very easy.

## Introduction

This application operates as a proxy or middleware between your Python app and GitHub to check for updates. While you could check for updates from your Python app directly, too, to make sure you don't exceed GitHub's API Rate Limit, you need to use some kind of tokens, such as a [PAT (Personal Access Token)](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens). When doing so, you need to make sure you don't disclose this token, even if it only enables accessing information that is public otherwise. If you include your token in your code, GitHub will disable the token.

On the other hand if you have your application deployed by many users, there may be many requests for the same information, making your rate limit closer to reach.

To avoid such situations, this application can be deployed to your web server and your Python apps can use it to check for updates. This proxy does not store your credentials (user name and PAT), but you supply them as environment variables, meaning that only you and those you authorize shall be able to access your PAT or other token.

Information about a GitHub repository (represented by the `Repository` class implemented in [repository.py](./repository.py)) includes some details of the repository, including the URL to its Releases page as well as the version number of the latest release. For a detailed list of information, check the `Repository` class implemented in [repository.py](./repository.py).

To avoid superfluous calls to GitHub, this proxy caches results of update checks by saving these repository information to a cache called the **Repository Store**, contained in [repository-store.json](./repository-store.json). (Note that this file is a data file and is therefore added to gitignore, so you'll only find it in your local folders once running the application successfully and performing the first successful check of updates).

An item in the cache expires after some time. This time is 3 days by default, and it can be specified at repository level either when creating the repository programmatically or in the Repository Store.

When a client submits a request for checking if new version is available, it must send its app identifier called the **repo slug** or **repository slug**, the `<repo>` part of the URL pattern `https://github.com/<user>/<repo>/`, as well as its current version number in the form of `x.y.z`. The client may also try to force update checking to invalidate the cache.

When a request is found and update is not forced, this proxy checks its Repository Store. If it finds repository information for the named application, and founds that it's still up-to-date (meaning that the last request to GitHub for version information happened within the update checking frequency specified for that repo), it will use the cached information to tell the client if there is a newer version, and will return the cached information to the client.

If the cached information is expired, or the client forced the update, or no information is available in the repository store for that repository yet, the proxy performs update check against the corresponding GitHub repository, and in addition to telling the client if a new version is available and providing other information, it also stores the information in the Repository Store so that subsequent non-forced requests can be served from the cache within the time specified by the update checking frequency.

The application is intended to always return a proper HTTP response and let the user know what happened, while trying to not disclose any sensitive information to the client, not even about the internal structures of the application. To be able to find causes of issues, however, error responses always contain an error key, a GUID, which is unique for each session and is included in server log entries. This way, given an error key, you can check the relevant log entries and you can try reproducing what happened. Server logs, when set to more verbose level, contain detailed error messages and exception traces as well.

### Restrictions to Prevent Your Peace of Mind

#### Repository Registry

To limit who can use your application, it only processes a request if it refers to a repository registered in your application instance's **Repository Registry**, namely in [repository-registry.json](./repository-registry.json). To serve requests for a repository, include its repo slug here and restart the application. When the application loads the Repository Store, it only loads items for registered repositories. When it saves the store, it only saves registered repositories. That is, if you want to terminate support for a repository, you can simply delete it from the repository registry and restart the application: it's repository store entry won't be loaded, and the next save operation will clean it up completely from the repository store file.

#### Disabling Forced Checks

You can use the **GITHUB_UPDATE_CHECKER_DISABLE_FORCED_CHECKS** [environment variable](#environment-variables) to disable forced checks. If this variable is set and it is True, even if the client asks for a forced check, the application will disregard it, and will only perform a check against GitHub if the corresponding cache entry is expired, or there's no information about that repository in the cache at all. This is the same as if the request were not forced.

You can use this option to decrease the number of calls to GitHub to control your API Rate Limit.

Once you change this setting, don't forget to restart the application.

## Environment Variables

You can configure the following environment variables for **GitHub Update Checker**:

* **GITHUB_UPDATE_CHECKER_GITHUB_USER_NAME** contains your username for which the token is issued.
* **GITHUB_UPDATE_CHECKER_GITHUB_API_TOKEN** contains your PAT or other API token.
* **GITHUB_UPDATE_CHECKER_LOG_LEVEL** can be one of the Python logging constants, `logging.ERROR`, `logging.WARNING`, `logging.INFO` or `logging.DEBUG`. Other values or absence of this property trigger INFO level logging.
* **GITHUB_UPDATE_CHECKER_DISABLE_FORCED_CHECKS**, if set to a value of `True` (case doesn't matter), prevents forced checks requested by clients. You can use this to temporarily decrease traffic against GitHub if you find clients force too many checks without a good reason. When true, the application will only make a request against GitHub after the requested repository's cached information expire.

When setting or changing an environment variable, don't forget to restart Python and the app.

## Logging and Debugging

Log entries are stored in `GitHubUpdateChecker.log` in the application's folder. The log is rotated weekly, with up to 5 weeks of files kept. You can change logging settings in the `dictConfig` dictionary in [gitHubUpdateChecker](./gitHubUpdateChecker.py).

## Installing the Application

To install the application in **cPanel**:

1. Open cPanel and find **Setup Python App**.
1. Click **Create Application**.
1. For **Python Version**, select **3.10.11** or newer.
1. For the **Application root** and **Application URL**, enter a folder and a URL as required by your hosting provider.
1. For **Application Startup File**, enter **gitHubUpdateChecker.py**.
1. For **Application Entry Point**, enter **app**.
1. For **Passenger Log File**, enter a file name if you want to have a copy of log entries there. You may then be able to disable creating the above-mentioned log file in the application folder.
1. Create the aforementioned environment variables.
1. Create the virtual environment by following the instructions on the top of the page. You'll need SSH access to your server. Use [requirements.txt](./requirements.txt) to deploy required Python modules.
1. Copy the .py files from this repo's root to the directory specified for **Application root**.
1. Start the application.

If the application starts properly on your domain `app.foo.com`, and the application URL is `gitHubUpdateChecker`, open `app.foo.com/gitHubUpdateChecker/info` in a web browser. If everything works fine, you'll see a JSON response like this:

```json
{
    "Application Name": "GitHub Update Checker by T1nk-R",
    "Author": "T1nk-R (Gusztáv Jánvári)",
    "Author's GitHub": "https://github.com/gusztavj/",
    "Author's Portfolio": "https://gusztav.janvari.name/t1nk-r/",
    "Author's Website": "https://gusztav.janvari.name/",
    "Help and support": "https://github.com/gusztavj/GitHub-Update-Checker",
    "Updates": "https://github.com/gusztavj/GitHub-Update-Checker/releases",
    "Version": "1.0.0"
}
```

## API Endpoints

### GET /info

You can use this endpoint to get the version number of the proxy, as well as some other about-like information.

#### Response

The response is a JSON object of the following structure:

```json
{
    "Application Name": "GitHub Update Checker by T1nk-R",
    "Author": "T1nk-R (Gusztáv Jánvári)",
    "Author's GitHub": "https://github.com/gusztavj/",
    "Author's Portfolio": "https://gusztav.janvari.name/t1nk-r/",
    "Author's Website": "https://gusztav.janvari.name/",
    "Help and support": "https://github.com/gusztavj/GitHub-Update-Checker",
    "Updates": "https://github.com/gusztavj/GitHub-Update-Checker/releases",
    "Version": "1.0.0"
}
```

Note that the version number may be different, and will likely slightly increase over time. :)

### POST /getUpdateInfo

This endpoint performs an update check for the add-on and caches results. The cache expires in some days as specified in `Repository.getCheckFrequencyDays()`, and then a new check is performed. Until that, the cached information is served.

#### Request

The request should be a JSON object conforming to the [gitHubUpdateCheckerRequest.schema.json](./gitHubUpdateCheckerRequest.schema.json) schema. Such JSON objects look like this:

```json
{
    "appInfo": {
        "repoSlug": "repo-slug",
        "clientCurrentVersion": "x.y.z"
    },
    "forceUpdateCheck": true
}
```

|Key|Required?|Description|
|---|---------|-----------|
| **repoSlug** | Yes | A string representing the repository slug, the `<repo>` part of the URL pattern `https://github.com/<user>/<repo>/`.
| **clientCurrentVersion** | Yes | Contains the current version number in the form of `x.y.z` or `x.y.z-foo`, according to the rules of [semantic versioning](https://semver.org/) recommended by GitHub. |
| **forceUpdateCheck** | No | A boolean value indicating whether to force an update check. |

#### Response

The response is a JSON object with the update information or error.

The normal response conforms to the following JSON object:

```json
{
    "repository": {
        "checkFrequencyDays": <check-frequency>,
        "lastCheckedTimestamp": "<timestamp>",
        "latestVersion": "<version>",
        "latestVersionName": "<release-title>",
        "releaseUrl": "<release-url>",
        "repoSlug": "<repo-slug>",
        "repoUrl": "<repo-url>"
    },
    "updateAvailable": true
}
```

| Key | Type | Description |
|-----|------|-------------|
|`<check-frequency>` | Number | Cache expiry in days. |
|`<timestamp>` | Datetime string | The timestamp of the last update against GitHub. The value is in the format specified by the `dateTimeFormat` constant in [gitHubUpdateChecker.py](./gitHubUpdateChecker.py). |
|`<version>` | String | The version number received from GitHub in the form of `vx.y.z` or `vx.y.z-foo`, following the rules of semantic versioning, where `v` is simply `v`, `x` is the major version number, `x` is the minor version number, `z` is the build number or patch level, and `foo` is the version tag, such as `alpha` or `beta`. |
|`<release-title>` | String | The title of the release as specified in GitHub. |
|`<release-url>` | String (URL) | The URL of the GitHub repo's **Releases** page. If your username is `john-doe`and the repo slug is `foo-bar`, this is going to be `https://api.github.com/repos/john-doe/foo-bar/releases/latest`. |
|`<repo-slug>` | String | This is the repository slug submitted in the request. You can use this to make sure you received the response for the proper repo. |
|`<repo-url>` | String (URL) | The URL of the GitHub repo. If your username is `john-doe`and the repo slug is `foo-bar`, this is going to be `https://github.com/john-doe/foo-bar/`. |

#### Error Handling

If an error occurs, the response will be a JSON object with an `error` property containing a description of the error.

#### Status Codes

The API can return the following status codes:

* 200: The request was successful.
* 400: The request was malformed. The `error` key in the response contains the description of the error.
* 500: An internal server error occurred. The response contains an error key. If you are the operator of **GitHub Update Checker**, you can use this to find the relevant log entries on the server. If you are not an operator of **GitHub Update Checker**, you can include this information in your support request so that the operator can find more detailed error information.

## Help for Developers and Tests

The code is heavily documented and commented. The `test` folder contains a bunch of unit tests. If that's not enough and you need more help, head to the Discussions page of this repo. In addition, you can import [GitHub-Update-Checker.postman_collection.json](./test/GitHub-Update-Checker.postman_collection.json) from the **test** folder to **PostMan** to perform API tests. In **PostMan**, two environments and some collection variables are defined. Take a look at them and change them accordingly so that they point to your server's URL.
