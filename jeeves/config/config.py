# On the target day, the word has to occur at least this many times to be considered as a spike.
COUNT_THRESHOLD = 3

# Should be greater than HISTORY_WINDOW_SIZE + SPIKE_THRESHOLD
CRAWL_WINDOW_SIZE = 90

# Version number, useful for controlling data storage
DATA_VERSION_IDENTIFIER = "5.1.4"

# We compare word occurrences in the past these days.
HISTORY_WINDOW_SIZE = 60

# Jira projects that are used for bug reporting
JIRA_PROJECTS = ["DLAA", "DLAI", "DLAW"]

# Jira issue type label for bugs
JIRA_ISSUE_TYPE_BUG = "Bug"

# For storing stats on words, only consider words that appear more commonly across the corpus
MIN_SAMPLES_THRESHOLD = 10

# Path name for where to upload the priority estimator model in aws s3
PRIORITY_ESTIMATOR_S3_PATH = "priority_estimator_model/"

# Mapping of Jira priorities to int classifications used by priority estimator
JIRA_PRIORITY_STR_TO_INT = {"Low": 0, "Lowest": 0, "Medium": 1, "High": 2, "Highest": 2}

# Directory for storing quality reports
QUALITY_REPORT_PLOTS_DIRECTORY = "plots"
QUALITY_REPORT_PLOTS_EXTERNAL_DIRECTORY = "delight/quality-report/"

# For spikes, occurrences should be at least five-sigma away from historical values.
SPIKE_THRESHOLD = 5
