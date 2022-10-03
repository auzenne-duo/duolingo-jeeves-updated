# On the target day, the word has to occur at least this many times to be considered as a spike.
COUNT_THRESHOLD = 3

# We compare word occurrences in the past these days.
HISTORY_WINDOW_SIZE = 60

# For spikes, occurrences should be at least five-sigma away from historical values.
SPIKE_THRESHOLD = 5

# Should be greater than HISTORY_WINDOW_SIZE + SPIKE_THRESHOLD
CRAWL_WINDOW_SIZE = 90

# Version number, useful for controlling data storage
DATA_VERSION_IDENTIFIER = "5.1.3"

# For storing stats on words, only consider words that appear more commonly across the corpus
MIN_SAMPLES_THRESHOLD = 10

# If the count of tickets increase by more than x times the average daily count, treat as a
# cold start for spike detection
ROLLOUT_RESET_THRESHOLD = 4

# Path name for where to upload the priority estimator model in aws s3
PRIORITY_ESTIMATOR_S3_PATH = "priority_estimator_model/"
