import configparser
import requests
import subprocess
import csv
import logging
import json
from typing import List

CONFIG_FILE_PATH = "config.ini"
#Access levels of users in GitLab
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

# Create a ConfigParser instance to read the API key and OAuth token
def get_config(section: str, key: str) -> str:
    """
    Read the configuration file to get the specified key from a given section.
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
def get_group_projects(api_key: str, group_id: str) -> List[dict]:
    """
    Fetch all projects for a given group from GitLab.
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
            projects.extend([{'id': project['id'], 'name': project['path_with_namespace']} for project in project_data])
            page += 1
        except requests.RequestException as e:
            logging.error(f"Network error occurred while fetching projects for group {group_id}: {e}")
            break

    return projects

# Function to run cx.exe with OAuth token and projects from CSV
def run_cx_exe(oauth_token: str, projects: str):
    """
    Run cx.exe with the provided OAuth token and project list.
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

# Function to fetch detailed information (including email) for a user
def get_user_details(api_key, user_id):
    """
    Fetch user details, including email, from GitLab.
    """
    GITLAB_USER_URL = f"https://gitlab.com/api/v4/users/{user_id}"
    headers = {"PRIVATE-TOKEN": api_key}
    response = requests.get(GITLAB_USER_URL, headers=headers)

    if response.status_code != 200:
        logging.error(f"Error fetching user details: {response.status_code}, {response.text}")
        return None

    return response.json()

# Function to fetch project members and their details
def get_project_members(api_key, project_id):
    """
    Fetch all members of a project from GitLab.
    """
    GITLAB_PROJECT_MEMBERS_URL = f"https://gitlab.com/api/v4/projects/{project_id}/members/all"
    headers = {"PRIVATE-TOKEN": api_key}
    members = []
    page = 1

    while True:
        response = requests.get(GITLAB_PROJECT_MEMBERS_URL, headers=headers, params={'page': page, 'per_page': 100})
        if response.status_code != 200:
            logging.error(f"Error fetching members: {response.status_code}, {response.text}")
            break
        
        member_data = response.json()
        if not member_data:
            break
        
        for member in member_data:
            user_details = get_user_details(api_key, member['id'])
            email = user_details.get('email', 'No Email') if user_details else 'No Email'
            members.append({
                'username': member['username'],
                'name': member['name'],
                'email': email,
                'access_level': ACCESS_LEVELS.get(member['access_level'], 'Unknown')
            })
        page += 1

    return members

# Menu to choose the operation
def menu():
    print("1. Run cx.exe with OAuth token and projects from CSV")
    print("2. Fetch unique contributors from GitLab")
    choice = input("Enter your choice: ")
    return choice

if __name__ == "__main__":
    # Pull API key and OAuth token from config.ini
    choice = menu()
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
                writer.writerow([project['name'] for project in all_projects])  # Write project paths as a single row
            logging.info(f"Project full paths have been written to {csv_file_path}")
        except Exception as e:
            logging.error(f"Error writing to CSV file: {e}")
        
        if choice == "1":
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
        
    if choice == "2":
        project_data = {}
        unique_users = set()  # Set to track unique usernames

        for project in all_projects:
            print(f"\nProject: {project['name']} (ID: {project['id']})")
            members = get_project_members(api_key, project['id'])
            
            if members:
                print("  Contributing Developers:")
                project_contributors = {}  # Dictionary to store users for this project

                for member in members:
                    # Add the member to the project's contributors list
                    if "_bot_" in member['username']:
                        continue  # Skip bot users
                    project_contributors[member['username']] = {
                        "name": member['name'],
                        "role": member['access_level']
                    }
                    # Track unique users by username
                    unique_users.add(member['username'])
                
                # Add the project and its contributors to the project_data dictionary
                project_data[project['name']] = project_contributors
            else:
                print("  No contributing developers found.")

        # After processing all projects, add the unique usernames and total count
        final_output = {
            "projects": project_data,
            "unique_usernames": list(unique_users),
            "total_users": len(unique_users)
        }

        # Write the final output to a JSON file
        output_file = "projects_contributors.json"
        with open(output_file, 'w') as json_file:
            json.dump(final_output, json_file, indent=4)

        print(f"\nContributor data has been written to {output_file}")
        print(f"Total unique users: {len(unique_users)}")
