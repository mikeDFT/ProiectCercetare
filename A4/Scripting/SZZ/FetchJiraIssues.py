import requests
import json

def fetch_cli_issues():
	"""
	Fetches all fixed bug reports for the 'CLI' project from the Apache Jira
	"""
	base_url = "https://issues.apache.org/jira"
	api_url = f"{base_url}/rest/api/2/search"
	
	# JQL to find all fixed bugs in the CLI project
	jql = (
		"project = CLI "
		"AND issuetype = Bug "
		"AND status in (Resolved, Closed) "
		"AND resolution = Fixed "
		"ORDER BY created ASC"  # Get oldest first
	)
	
	session = requests.Session()
	start_at = 0
	max_results = 100
	total = 1  # dummy value to start
	
	all_issues = {}
	
	print(f"Starting to fetch issues from {base_url} for project 'CLI'")
	
	while start_at < total:
		params = {
			'jql': jql,
			'startAt': start_at,
			'maxResults': max_results
		}
		
		try:
			response = session.get(api_url, params=params, verify=True, timeout=30)
			response.raise_for_status()  # Raise error for bad responses
			
			data = response.json()
			total = data['total']
			
			for issue in data['issues']:
				key = issue['key']
				created_date = issue['fields']['created']
				all_issues[key] = created_date
			
			start_at += max_results
			print(f" Fetched {len(all_issues)} / {total} issues...")
		
		except requests.exceptions.RequestException as e:
			print(f"\n[ERROR] Failed to fetch issues: {e}")
			return None
	
	output_file = 'cli_issues.json'
	with open(output_file, 'w', encoding='utf-8') as f:
		json.dump(all_issues, f, indent=2)
	
	print(f"\nSaved {len(all_issues)} issues to {output_file}")
	return output_file


if __name__ == "__main__":
	fetch_cli_issues()
