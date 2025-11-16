import lizard
import os
import re
from pydriller import Repository
from datetime import datetime, timedelta
from collections import defaultdict

# path to local repo
# REPO_PATH = './commons-cli'
# REPO_PATH = './airflow' # couldn't run yet, has way too many commits and takes too much time
# REPO_PATH = './commons-lang'
# REPO_PATH = './requests'
# REPO_PATH = './zxing'
# REPO_PATH = './flask'
# REPO_PATH = './react'
REPO_PATH = './Chart.js'

# time window for recent activity
SINCE_DAYS = 180  # 6 months

# effort proxy (LEP) "k-factor"
# to decide how much to penalize complex code
# Effort = NLOC + (k * CCN)
K_PENALTY = 5

# TDR-W Weights
# wc = 0.5, wb = 1.0 (a bug is twice as painful as a commit)
W_COMMIT = 0.5
W_BUG = 1.0

# HBFM Bug-Finding Regex
# Looks for "CLI-" (Apache JIRA key) or common fix keywords.
BUG_REGEX = re.compile(  # for commons-lang
	# r'\b(CLI-\d+)\b|fix(es|ed)?\b|bug\b|patch\b', # for commons-cli
	# r'\b(AIRFLOW-\d+)\b|fix(es|ed)?\b|bug\b|patch\b', # for airflow
	# r'\b(LANG-\d+)\b|fix(es|ed)?\b|bug\b|patch\b',  # for commons-lang
	r'\b(fix(es|ed)?\s*#\d+)\b|bug\b|patch\b',  # for requests, zxing, flask, react, chart.js (github issues)
	
	re.IGNORECASE
)

EXCLUDE_PATTERNS = [
	"*/test/*",  # Exclude all test directories
	"*/tests/*",  # Exclude all test directories
	"*/docs/*",  # Exclude documentation
	"*/.tox/*",  # Exclude tox virtualenvs
	"*/venv/*",  # Exclude virtualenvs
	"*/node_modules/*",  # Exclude node modules
	"*/helm-chart/*",  # Exclude helm chart (specific to airflow)
	"*/.git/*",  # Exclude git directory
	"*.md",  # Exclude markdown
	"*.xml",  # Exclude XML config files
	"*.yml",  # Exclude YAML config files
	"*.json",  # Exclude JSON files
]


def get_effort_scores(repo_path):
	"""
	proxy model for Effort to Fix using Lizard
	Calculates the Lizard Effort Proxy score for each module
	Effort_Proxy = (Sum of NLOC) + (k * Sum of CCN)
	"""
	print("1/2: analyzing code effort with Lizard")
	module_metrics = defaultdict(lambda: {'nloc': 0, 'ccn': 0})  # nloc = nr lines of code
	
	# normalize the repo_path to ensure correct prefix removing
	normalized_repo_path = os.path.normpath(os.path.abspath(repo_path))
	
	# lizard.analyze recursively analyzes paths
	analysis = lizard.analyze(
		[repo_path],  # pass the repo_path as a list of paths
		exclude_pattern=EXCLUDE_PATTERNS  # to make it a bit faster
	)
	
	# convert generator to list to check if it's empty
	analysis_list = list(analysis)
	
	if not analysis_list:
		print(f"lizard found no source files to analyze in {repo_path}")
		return {}
	
	for file_info in analysis_list:
		# get the full absolute path of the file
		full_path = os.path.normpath(os.path.abspath(file_info.filename))
		
		# create the relative path (key) by removing the repo path
		if full_path.startswith(normalized_repo_path):
			relative_path = full_path[len(normalized_repo_path):]
			# strip leading path separator (/ or \)
			relative_path = relative_path.lstrip(os.path.sep)
		else:
			# fallback, though this shouldn't happen
			relative_path = file_info.filename
		
		# The module is defined as the directory
		module_path = os.path.dirname(relative_path)
		
		for func in file_info.function_list:
			module_metrics[module_path]['nloc'] += func.nloc
			module_metrics[module_path]['ccn'] += func.cyclomatic_complexity
	
	effort_scores = {}
	for module, metrics in module_metrics.items():
		effort = metrics['nloc'] + (K_PENALTY * metrics['ccn'])
		effort_scores[module] = effort
	
	print(f"found {len(effort_scores)} modules.")
	return effort_scores


def analyze_commit_history(repo_path, since_date):
	"""
	Measuring Recent Commits (C) and Bugs (B) using PyDriller
	"""
	print("2/2: Analyzing commit history with PyDriller")
	module_commit_counts = defaultdict(int)
	module_bug_counts = defaultdict(int)
	commit_count = 0
	bug_commit_count = 0
	
	try:
		for commit in Repository(repo_path, since=since_date, ).traverse_commits():
			commit_count += 1
			
			# check if the commit message matches the bug heuristics
			is_bug_commit = BUG_REGEX.search(commit.msg)
			if is_bug_commit:
				bug_commit_count += 1
			
			# loop through modified files
			for mod in commit.modified_files:
				filepath = mod.new_path or mod.old_path
				if filepath:
					module_path = os.path.dirname(filepath)
					
					# always increment the total commit count for the module
					module_commit_counts[module_path] += 1
					
					# if it's a bug, also increment the bug count
					if is_bug_commit:
						module_bug_counts[module_path] += 1
		
		print(f"analyzed {commit_count} commits.")
		print(f"found {bug_commit_count} potential bug-fix commits.")
		
		# return both dictionaries
		return module_commit_counts, module_bug_counts
	
	except Exception as e:
		print(f"Error running PyDriller analysis: {e}")
		print(f"make sure '{repo_path}' is a valid Git repository.")
		return {}, {}


def main():
	"""
	Main function to run the TDR-W analysis and print the report.
	"""
	print(f"Running TDR-W analysis on {REPO_PATH}")
	
	if not os.path.isdir(REPO_PATH):
		print(f"error: Repository path not found: {REPO_PATH}")
		return
	
	# set the time window
	since_date_obj = datetime.now() - timedelta(days=SINCE_DAYS)
	
	# gather all data
	effort_data = get_effort_scores(REPO_PATH)
	commit_data, bug_data = analyze_commit_history(REPO_PATH, since_date_obj)
	
	if not effort_data and not commit_data and not bug_data:
		print("\nAnalysis failed. No data gathered")
		return
	
	# combine and calculate TDR scores
	all_modules = set(effort_data.keys()) | set(commit_data.keys()) | set(bug_data.keys())
	results = []
	
	for module in all_modules:
		# filter out empty/root paths or non-source directories
		if not module or module == '.' or 'test' in module.lower():
			continue
		
		e = effort_data.get(module, 0)
		c = commit_data.get(module, 0)
		b = bug_data.get(module, 0)
		
		pain_score = (W_COMMIT * c) + (W_BUG * b)
		tdr_score = e * pain_score
		
		# only report on modules that have some TDR score
		if tdr_score > 0:
			results.append({
				'module': module,
				'effort': e,
				'commits': c,
				'bugs': b,
				'pain': round(pain_score, 2),
				'tdr_score': round(tdr_score, 2)
			})
	
	# sort by TDR score (highest risk first)
	results.sort(key=lambda x: x['tdr_score'], reverse=True)
	
	# print the final report (python string format has this cool table-like format)
	print("\n\nTDR-W Hotspot Report (Top 20)")
	print("=" * 120)
	print(f"{'Module':<70} {'TDR Score':>12} {'Effort':>10} {'Pain':>8} {'Commits':>8} {'Bugs':>6}")
	print("-" * 120)
	
	if not results:
		print("No hotspots found with a TDR score > 0.")
	else:
		for row in results[:20]:
			print(
				f"{row['module']:<70} {row['tdr_score']:>12} {row['effort']:>10} {row['pain']:>8} {row['commits']:>8} {row['bugs']:>6}")
	
	print("-" * 120)


if __name__ == "__main__":
	main()
