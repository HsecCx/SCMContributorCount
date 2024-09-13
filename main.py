import configparser
import requests
import subprocess
import csv
import logging
from typing import List

CONFIG_FILE_PATH = "config.ini"

# Set up logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Create a ConfigParser instance to read the API key and OAuth token
def get_config(section: str, key: str) -> str:
    """
    Read the configuration file to get the specified key from a given section.

    Args:
        section (str): The section in the config file.
        key (str): The key to retrieve the value for.

    Returns:
        str: The value of the specified key in the given section.
    """
    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_FILE_PATH)
        return config[section][key]
    except KeyError as e:
        logging.error(f"Key error: {e}")
        raise ValueError(f"Key '{key}' not found in section '{section}' of config file.")

# Function to fetch all groups the API has access to
def get_groups(api_key: str) -> List[dict]:
    """
    Fetch all groups accessible by the API key.

    Args:
        api_key (str): The GitLab API key for authentication.

    Returns:
        List[dict]: A list of groups with their details.
    """
    GITLAB_GROUPS_URL = "https://gitlab.com/api/v4/groups"
    headers = {"PRIVATE-TOKEN": api_key}
    groups = []
    page = 1

    while True:
        try:
            response = requests.get(GITLAB_GROUPS_URL, headers=headers, params={'page': page, 'per_page': 100})
            if response.status_code != 200:
                logging.error(f"Error fetching groups: {response.status_code}, {response.text}")
                break
            group_data = response.json()
            if not group_data:
                break
            groups.extend(group_data)
            page += 1
        except requests.RequestException as e:
            logging.error(f"Network error occurred while fetching groups: {e}")
            break

    return groups

# Function to fetch projects from the GitLab group
def get_group_projects(api_key: str, group_id: str) -> List[str]:
    """
    Fetch all projects for a given group from GitLab.

    Args:
        api_key (str): The GitLab API key for authentication.
        group_id (str): The group ID.

    Returns:
        List[str]: A list of full path/namespaces of the projects.
    """
    GITLAB_GROUP_URL = f"https://gitlab.com/api/v4/groups/{group_id}/projects"
    headers = {"PRIVATE-TOKEN": api_key}
    projects = []
    page = 1

    while True:
        try:
            response = requests.get(GITLAB_GROUP_URL, headers=headers, params={'page': page, 'per_page': 100})
            if response.status_code != 200:
                logging.error(f"Error fetching projects for group {group_id}: {response.status_code}, {response.text}")
                break
            project_data = response.json()
            if not project_data:
                break
            projects.extend([project['path_with_namespace'] for project in project_data])
            page += 1
        except requests.RequestException as e:
            logging.error(f"Network error occurred while fetching projects for group {group_id}: {e}")
            break

    return projects

# Function to run cx.exe with OAuth token and projects from CSV
def run_cx_exe(oauth_token: str, projects: str):
    """
    Run cx.exe with the provided OAuth token and project list.

    Args:
        oauth_token (str): OAuth token for authentication.
        projects (str): Comma-separated list of projects.
    """
    command = [
        "cx.exe",  # Path to cx.exe
        "utils",
        "contributor-count",
        "gitlab",
        "--projects", projects,
        "--token", oauth_token,
        "--url-gitlab", "https://gitlab.com"
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        if result.returncode == 0:
            logging.info("Contributor count successful.")
            cleaned_output = result.stdout.replace('\xa0', ' ').strip()
            with open('output.txt', 'w+') as f:
                f.write(cleaned_output)
        else:
            logging.error(f"cx.exe returned error: {result.stderr}")
    except Exception as e:
        logging.error(f"Error occurred while running cx.exe: {e}")

if __name__ == "__main__":
    # Pull API key and OAuth token from config.ini
    try:
        api_key = get_config("api", "API_KEY")
        oauth_token = get_config("oauth", "oauth_token")
    except Exception as e:
        logging.critical(f"Critical error in configuration: {e}")
        raise

    logging.info("Fetching Projects from GitLab")
    groups = get_groups(api_key)
    
    if not groups:
        logging.warning("No groups found or unable to access groups.")
    else:
        all_projects = []

        # Fetch all projects from each group
        for group in groups:
            group_name = group['name']
            group_id = group['id']
            logging.info(f"Fetching projects for group: {group_name}")
            projects = get_group_projects(api_key, str(group_id))
            all_projects.extend(projects)

        # Write all project full paths to a CSV file
        csv_file_path = "gitlab_projects.csv"
        try:
            with open(csv_file_path, 'w+', newline='') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(all_projects)  # Write the project full paths separated by commas
            logging.info(f"Project full paths have been written to {csv_file_path}")
        except Exception as e:
            logging.error(f"Error writing to CSV file: {e}")

        # Now that projects are written to CSV, read the CSV and use the projects in cx.exe
        try:
            with open(csv_file_path, 'r') as csvfile:
                reader = csv.reader(csvfile)
                projects_from_csv = next(reader)  # Assuming a single line of projects
                project_list = ','.join(projects_from_csv)

                # Run cx.exe with the projects from CSV
                run_cx_exe(oauth_token, project_list)

        except FileNotFoundError:
            logging.error(f"CSV file '{csv_file_path}' not found.")
        except Exception as e:
            logging.error(f"Error reading CSV file: {e}")
