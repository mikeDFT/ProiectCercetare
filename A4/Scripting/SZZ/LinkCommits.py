import json
import re
from pydriller import Repository


ISSUES_FILE = 'cli_issues.json'  # Input from FetchJiraIssues.py
REPO_PATH = 'commons-cli'  # Path to cloned repo
OUTPUT_FILE = 'bug-fixes.json'  # Output for pySZZ
REPO_NAME = 'apache/commons-cli'  # Name pySZZ will use

# Regex to find Jira issue keys (ex: CLI-123)
issue_key_regex = re.compile(r'\b(CLI-\d+)\b', re.IGNORECASE)


def link_commits_to_issues():
	"""
	Scans a git repo, links commits to Jira issues, and
	creates the bug-fixes.json file for pySZZ
	"""
	
	print(f"Loading issues from {ISSUES_FILE}...")
	try:
		with open(ISSUES_FILE, 'r') as f:
			issues = json.load(f)
	except FileNotFoundError:
		print(f"[ERROR] Issues file not found: {ISSUES_FILE}")
		print("Run 'fetch_jira_issues.py' first")
		return
	
	print(f"Found {len(issues)} issues.")
	print(f"Scanning git repo at {REPO_PATH}")
	
	pyszz_data = []
	found_links = 0
	
	# Using PyDriller to scan the repo
	for commit in Repository(REPO_PATH).traverse_commits():
		# Checking the commit message for issue keys
		matches = issue_key_regex.findall(commit.msg)
		
		if matches:
			for key in set(matches):  # Use set to avoid duplicates
				# Check if the found key is a real bug report
				if key.upper() in issues:
					# If it is, create the entry for pySZZ
					pyszz_data.append({
						"repo_name": REPO_NAME,
						"fix_commit_hash": commit.hash,
						"earliest_issue_date": issues[key.upper()]
					})
					found_links += 1
		
		if len(pyszz_data) % 100 == 0 and found_links > 0:
			print(f" Scanning commits: found {found_links} bug-fix links")
	
	print(f"\nFound {len(pyszz_data)} total bug-fix links")
	
	with open(OUTPUT_FILE, 'w') as f:
		json.dump(pyszz_data, f, indent=2)
	
	print(f"Successfully created {OUTPUT_FILE} for pySZZ")


if __name__ == "__main__":
	link_commits_to_issues()
	