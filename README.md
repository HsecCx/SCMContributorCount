# GitLab Projects Fetcher and Contributor Count

This Python script automates the process of fetching all GitLab projects accessible by a specified API key, writing them to a CSV file, and then running `cx.exe` to count contributors for the projects using an OAuth token. Additionally, it can fetch recent contributors (within the last 90 days) for each project.

## Features

- **Fetches all groups and projects** that the GitLab API key has access to.
- **Saves the list of projects** (in full path/namespace format) to a CSV file.
- **Executes `cx.exe`** to count unique contributors for the projects using the OAuth token.
- **Optionally fetches recent contributors** (within the last 90 days) for each project and outputs the data to a JSON file.
- **Logs all events, warnings, and errors** to `app.log` for troubleshooting and tracking.

## Prerequisites

Before running the script, ensure you have the following:

1. **Python 3.x**

   - Download Python from [python.org](https://www.python.org/downloads/).

2. **GitLab API Key**

   - You need a **GitLab API key** with appropriate permissions to fetch groups and projects.
   - **Create an API key in GitLab:**
     - Go to **User Settings** > **Access Tokens**.
     - Set the required scopes (e.g., `read_api`, `read_repository`).
     - Copy the token and use it in the `config.ini` file.

3. **GitLab OAuth Token**

   - The script requires a **GitLab OAuth token** to authenticate when running `cx.exe`.
   - **Create an OAuth token in GitLab:**
     - Go to **User Settings** > **Applications**.
     - Register a new OAuth application.
     - Set the necessary scopes (`read_api`, `read_repository`).
     - Generate an OAuth token.
     - Add this OAuth token to the `config.ini` file.

4. **cx.exe**

   - Install `cx.exe` and ensure it's available in the system's PATH or the working directory.
   - This script leverages the Checkmarx CLI (`cx.exe`) to loop through all projects.

5. **Required Python Modules**

   - Install the required Python modules using `pip`:
     ```bash
     pip install requests
     ```
   - Alternatively, create a `requirements.txt` file with the following content and install:
     ```txt
     requests
     ```
     ```bash
     pip install -r requirements.txt
     ```

6. **`config.ini` File**

   - Create a `config.ini` file in the same directory as the script with the following format:
     ```ini
     [api]
     API_KEY = <Your GitLab API Key>

     [oauth]
     oauth_token = <Your GitLab OAuth Token>
     ```

## Setup

1. **Clone or Download the Repository**

   - Clone or download this repository to your local machine.

2. **Create the `config.ini` File**

   - Add your GitLab API key and OAuth token to the `config.ini` file as shown above.

3. **Ensure `cx.exe` is Available**

   - Ensure that `cx.exe` is in your system's PATH or located in the same directory as the script.

4. **Install Required Python Modules**

   - Install the required modules using `pip` as mentioned above.

## Usage

The script supports two main actions:

- **Run `cx.exe` with the list of projects.**
- **Fetch recent contributors (within the last 90 days) from GitLab.**

### Running the Script

The script uses command-line arguments to specify the action to perform. Use the `--action` argument to choose the action.

### Available Actions

- `run_cx`: Runs `cx.exe` with the projects fetched from GitLab.
- `fetch_contributors`: Fetches recent contributors (within the last 90 days) for each project and outputs the data to a JSON file.

### Command-Line Usage

```bash
python main.py --action <action>
 ```

### Output
   - When running with --action run_cx:
      -  The script will output the results of cx.exe to cx_unique_contributors_output.txt.
   
   - When running with --action fetch_contributors:
      - The script will generate projects_active_contributors.json, containing the contributor data for each project.
   
   - Logging
      - All events, warnings, and errors are logged to app.log for troubleshooting and tracking.

   - Notes
      - Permissions:

         - Ensure that you have the necessary permissions in GitLab to access the groups and projects.
         - The API key should have sufficient scopes to fetch group and project data.
         - The OAuth token should have scopes to authenticate with cx.exe.

      - Check app.log for detailed logs if you encounter issues.
      - Ensure that the required modules are installed and up to date.