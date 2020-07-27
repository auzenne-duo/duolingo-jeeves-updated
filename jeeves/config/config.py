# On the target day, the word has to occur at least this many times to be considered as a spike.
COUNT_THRESHOLD = 3

# We compare word occurrences in the past these days.
HISTORY_WINDOW_SIZE = 60

# For spikes, occurrences should be at least five-sigma away from historical values.
SPIKE_THRESHOLD = 5

# Should be greater than HISTORY_WINDOW_SIZE + SPIKE_THRESHOLD
CRAWL_WINDOW_SIZE = 90

# Version number, useful for controlling memcached storage
VERSION_NUMBER = 7
