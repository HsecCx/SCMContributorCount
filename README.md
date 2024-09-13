# GitLab Projects Fetcher and Contributor Count

This Python script automates the process of fetching all GitLab projects accessible by a specified API key, writing them to a CSV file, and then running `cx.exe` to count contributors for the projects using an OAuth token.

## Features
- Fetches all groups and projects that the GitLab API key has access to.
- Saves the list of projects (in full path/namespace format) to a CSV file.
- Executes `cx.exe` to count unique contributors for the projects using the OAuth token.
- Logs all events, warnings, and errors to `app.log` for troubleshooting and tracking.

## Prerequisites

Before running the script, ensure you have the following:

1. **Python 3.x**: Download Python from [python.org](https://www.python.org/downloads/).

2. **GitLab API Key**: You need a **GitLab API key** with appropriate permissions to fetch groups and projects. You can create an API key from GitLab:
   - Go to **User Settings** > **Access Tokens**.
   - Set the required scopes (`api`).
   - Copy the token and use it in the `config.ini` file.

3. **GitLab OAuth Token**: The script also requires a **GitLab OAuth token** to authenticate when running `cx.exe`.
   - Go to **User Settings** > **Applications** in GitLab.
   - Register a new OAuth application, set the necessary scopes (`read_api`, `api`, `read_repository`), and generate an OAuth token.
   - Add this OAuth token to the `config.ini` file.

4. **cx.exe**: Install `cx.exe` and ensure it's available in the system's PATH or the working directory. This script runs by leveraging the checkmarx cli and uses it to loop through all projects.

5. **Requests Module**: The script uses the `requests` module to make HTTP calls. Install it with:
   ```bash
   pip install requests

6. **INI Format**:
   ```ini
   [api]
   API_KEY = <Your GitLab API Key>

   [oauth]
   oauth_token = <Your GitLab OAuth Token>

7. **Setup**:
- Clone or Download the Repository: Clone or download this repository to your local machine.

- Create the config.ini File: Add your GitLab API key and OAuth token to a config.ini file as shown above.

- Ensure cx.exe is Available: Ensure that cx.exe is in your system's PATH or located in the same directory as the script.

8. **Run**
 ``` python main.py

9. **Output**
- This will output the results to output.txt 
 