import csv
import re
import sys
from pydriller import Repository

# Defining the repository to analyze
# A large repo like log4j2 will take many hours to process and a lot of RAM with panda
# (for analysis and validation)
# REPO_PATH = 'https://github.com/apache/logging-log4j2.git'
# so I'll be using a smaller repo because of limited resources
REPO_PATH = 'https://github.com/apache/commons-cli'

# Defining the output file for the Cause Data
OUTPUT_CSV = 'metrics_data.csv'

LANGUAGE = 'java' # 'python', 'java'

# Defining the regex for Self Admitted Technical Debt (SATD)
# this pattern looks for common SATD keywords in comments
if LANGUAGE == 'java':
	SATD_PATTERN = re.compile(r'//\s*(TODO|HACK|FIXME|XXX)|technical debt', re.IGNORECASE)
elif LANGUAGE == 'python':
	SATD_PATTERN = re.compile(r'#\s*(TODO|HACK|FIXME|XXX)|technical debt', re.IGNORECASE)

# Defining file extensions to analyze (ex: .java for log4j)
if LANGUAGE == 'java':
	TARGET_EXTENSIONS = '.java'
elif LANGUAGE == 'python':
	TARGET_EXTENSIONS = '.py'


def analyze_repository():
	"""
	Implements the MSR pipeline
	- Iterates through commits with PyDriller
	- Gets metrics (CCN, LOC) via integrated Lizard
	- Identifies comment-based SATD
	- Saves results to a CSV file
	"""
	
	print(f"Starting analysis of {REPO_PATH}...")
	
	# Using 'w' (write) mode to create a new file
	with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
		writer = csv.writer(f)
		
		# Writing the header row for our structured dataset
		writer.writerow([
			"commit_hash",
			"author_date",
			"file_path",
			"cyclomatic_complexity",
			"nloc", # nr lines of code
			"has_comment_SATD"
		])
		
		try:
			# Using PyDriller's Repository.traverse_commits()
			for i, commit in enumerate(Repository(REPO_PATH).traverse_commits()):
				commit_hash = commit.hash
				author_date = commit.author_date
				
				if i % 100 == 0:
					print(f" Processed {i} commits (current: {commit_hash} on {author_date})...")
				
				# Accessing file-level data for this commit
				for file in commit.modified_files:
					# Filter for relevant file types
					if not file.filename.endswith(TARGET_EXTENSIONS):
						continue

					try:
						# Get metrics (PyDriller calls Lizard automatically)
						ccn = file.complexity
						loc = file.nloc
						
						# Check for SATD in source code
						has_satd = False
						source_code = file.source_code
						
						if source_code:
							if SATD_PATTERN.search(source_code):
								has_satd = True
						
						# Write the aggregated data row
						writer.writerow([
							commit_hash,
							author_date,
							file.filename,
							ccn,
							loc,
							has_satd
						])
					
					except Exception as e:
						# Log errors for specific files (ex: encoding issues, parse errors)
						print(
							f"[Warning] Could not process file {file.filename} in commit {commit_hash}. Error: {e}",
							file=sys.stderr)
		
		except Exception as e:
			print(f"\n[FATAL ERROR] Analysis failed: {e}", file=sys.stderr)
			return
	
	print(f"\nAnalysis complete. Data saved to {OUTPUT_CSV}")


if __name__ == "__main__":
	analyze_repository()
