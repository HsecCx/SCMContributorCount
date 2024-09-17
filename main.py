import os,sys
import configparser
import requests
import subprocess
import csv
import logging
import json
from datetime import datetime, timedelta, timezone
from typing import List, Set, Dict
import argparse
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

CONFIG_FILE_PATH = "config.ini"

# Access levels of users in GitLab
ACCESS_LEVELS = {
    10: "Guest",
    20: "Reporter",
    30: "Developer",
    40: "Maintainer",
    50: "Owner"
}

# Set up logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Read the configuration once at the module level
config = configparser.ConfigParser()
config.read(CONFIG_FILE_PATH)

#Read from the config.ini file
def get_config(section: str, key: str) -> str:
    """
    Retrieve the specified key from a given section in the pre-read config.
    """
    try:
        return config[section][key]
    except KeyError as e:
        logging.error(f"Key error: {e}")
        raise ValueError(f"Key '{key}' not found in section '{section}' of config file.")


class GitLabClient:
    """
    A client to interact with the GitLab API.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"PRIVATE-TOKEN": self.api_key}
        self.base_url = "https://gitlab.com/api/v4"
        # Set up a session with retries
        self.session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount('https://', adapter)

    def get(self, endpoint: str, params: dict = None) -> requests.Response:
        """
        Perform a GET request to the specified GitLab API endpoint.
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logging.error(f"Error making GET request to {url}: {e}")
            return None

    def paginate(self, endpoint: str, params: dict = None) -> List[dict]:
        """
        Handle pagination for API endpoints that return multiple pages.
        """
        results = []
        url = f"{self.base_url}{endpoint}"
        while url:
            response = self.session.get(url, headers=self.headers, params=params)
            if response.status_code != 200:
                logging.error(f"Error fetching data: {response.status_code}, {response.text}")
                break
            results.extend(response.json())
            # Use the 'next' link from the response headers for pagination
            url = response.links.get('next', {}).get('url')
            # Clear params after the first request to avoid duplication
            params = None
        return results

    def get_groups(self) -> List[dict]:
        """
        Fetch all groups accessible by the API key.
        """
        return self.paginate('/groups', params={'per_page': 100})

    def get_group_projects(self, group_id: int) -> List[dict]:
        """
        Fetch all projects for a given group from GitLab.
        """
        return self.paginate(f'/groups/{group_id}/projects', params={'per_page': 100})

    def get_project_members(self, project_id: int) -> List[dict]:
        """
        Fetch all members of a project from GitLab.
        """
        return self.paginate(f'/projects/{project_id}/members/all', params={'per_page': 100})

    def get_recent_committers(self, project_id: int) -> Set[str]:
        """
        Fetch all contributors who have committed to the project in the last 90 days.

        Args:
            project_id (int): The ID of the project.

        Returns:
            Set[str]: A set of emails of users who have committed in the last 90 days.
        """
        recent_committers = set()
        since_date = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        endpoint = f'/projects/{project_id}/repository/commits'
        params = {
            'since': since_date,
            'per_page': 100
        }

        url = f"{self.base_url}{endpoint}"
        while url:
            response = self.session.get(url, headers=self.headers, params=params)
            if response.status_code != 200:
                logging.error(f"Error fetching commits for project {project_id}: {response.status_code}, {response.text}")
                break
            commit_data = response.json()
            if not commit_data:
                break
            for commit in commit_data:
                if commit.get('author_email'):
                    recent_committers.add(commit['author_email'])
            # Use the 'next' link from the response headers for pagination
            url = response.links.get('next', {}).get('url')
            # Clear params after the first request
            params = None
        return recent_committers


def run_cx_exe(oauth_token: str, projects: List[str]):
    """
    Run cx.exe with the provided OAuth token and project list.

    Args:
        oauth_token (str): The OAuth token for authentication.
        projects (List[str]): A list of project paths.
    """
    command = [
        "cx.exe",
        "utils",
        "contributor-count",
        "gitlab",
        "--projects", ','.join(projects),
        "--token", oauth_token,
        "--url-gitlab", "https://gitlab.com"
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        if result.returncode == 0:
            logging.info("Contributor count successful.")
            cleaned_output = result.stdout.replace('\xa0', ' ').strip()
            with open('cx_unique_contributors_output.txt', 'w', encoding='utf-8') as f:
                f.write(cleaned_output)
        else:
            logging.error(f"cx.exe returned error: {result.stderr}")
    except Exception as e:
        logging.error(f"Error occurred while running cx.exe: {e}")


def parse_arguments():
    """
    Parse command-line arguments and check if they exceed the system's command-line length limit.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(description='Process GitLab projects.')
    parser.add_argument(
        '--action',
        choices=['run_cx', 'fetch_contributors'],
        required=True,
        help='Action to perform.'
    )

    # Parse the arguments
    args = parser.parse_args()

    # Check the length of the entire command
    command_length = len(' '.join(sys.argv))
    
    # Retrieve the system's maximum command length
    max_command_length = os.sysconf('SC_ARG_MAX') if hasattr(os, 'sysconf') else 32768  # Fallback to 32K if not available

    if command_length > max_command_length:
        parser.error(f"Command length exceeds the system limit of {max_command_length} characters.")
    
    return args


def main():
    """
    The main function to execute script logic.
    """
    # Parse command-line arguments
    args = parse_arguments()
    action = args.action

    # Pull API key and OAuth token from environment variables or config.ini
    try:
        api_key = os.environ.get('GITLAB_API_KEY') or get_config("api", "API_KEY")
    except Exception as e:
        logging.critical(f"Critical error in configuration: {e}")
        raise

    gitlab_client = GitLabClient(api_key)
    logging.info("Fetching Projects from GitLab")
    groups = gitlab_client.get_groups()

    if not groups:
        logging.warning("No groups found or unable to access groups.")
        return

    all_projects = []

    # Fetch all projects from each group
    for group in groups:
        group_name = group.get('name')
        group_id = group.get('id')
        logging.info(f"Fetching projects for group: {group_name}")
        projects = gitlab_client.get_group_projects(group_id)
        # Extract necessary project info
        for project in projects:
            all_projects.append({
                'id': project['id'],
                'name': project['path_with_namespace']
            })

    # Write all project full paths to a CSV file
    csv_file_path = "gitlab_projects.csv"
    try:
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for project in all_projects:
                writer.writerow([project['name']])
        logging.info(f"Project full paths have been written to {csv_file_path}")
    except Exception as e:
        logging.error(f"Error writing to CSV file: {e}")

    if action == 'run_cx':
        oauth_token = os.environ.get('GITLAB_OAUTH_TOKEN') or get_config("oauth", "oauth_token")
        # Now that projects are written to CSV, read the CSV and use the projects in cx.exe
        try:
            projects_from_csv = []
            with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    projects_from_csv.extend(row)
            # Run cx.exe with the projects from CSV
            run_cx_exe(oauth_token, projects_from_csv)
        except FileNotFoundError:
            logging.error(f"CSV file '{csv_file_path}' not found.")
        except Exception as e:
            logging.error(f"Error reading CSV file: {e}")

    elif action == 'fetch_contributors':
        project_data = {}
        unique_users = set()  # Set to track unique user emails

        for project in all_projects:
            project_name = project['name']
            project_id = project['id']
            logging.info(f"Processing project: {project_name} (ID: {project_id})")

            # Get recent committers for the project (last 90 days)
            recent_committers = gitlab_client.get_recent_committers(project_id)

            if recent_committers:
                logging.info(f"Found active contributors in the last 90 days for project: {project_name}")
                project_contributors = {}  # Dictionary to store users for this project
                unique_proj_contributors = 0
                for email in recent_committers:
                    project_contributors[email] = {
                        "role": "Active Contributor (last 90 days)"
                    }
                    # Track unique users by email
                    unique_users.add(email)
                    unique_proj_contributors += 1
                    project_contributors["unique_contributors"] = unique_proj_contributors
                # Add the project and its contributors to the project_data dictionary
                project_data[project_name] = project_contributors
            else:
                logging.info(f"No active contributors in the last 90 days for project: {project_name}")

        # After processing all projects, add the unique emails and total count
        final_output = {
            "projects": project_data,
            "unique_user_emails": list(unique_users),
            "total_users": len(unique_users)
        }

        # Write the final output to a JSON file
        output_file = "projects_active_contributors.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as json_file:
                json.dump(final_output, json_file, indent=4)
            logging.info(f"Contributor data (last 90 days) has been written to {output_file}")
            logging.info(f"Total unique users (last 90 days): {len(unique_users)}")
        except Exception as e:
            logging.error(f"Error writing to JSON file: {e}")
    else:
        logging.error(f"Invalid action specified: {action}")


if __name__ == "__main__":
    main()
