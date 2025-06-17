from duolingo_base.config import Config

# A singleton instance of duolingo_base.config.Config
CONFIG = Config.load_config()

# On the target day, the word has to occur at least this many times to be considered as a spike.
COUNT_THRESHOLD = 3

# Should be greater than HISTORY_WINDOW_SIZE + SPIKE_THRESHOLD
CRAWL_WINDOW_SIZE = 90

# We compare word occurrences in the past these days.
HISTORY_WINDOW_SIZE = 60

# Projects that are used only with video call
VIDEO_CALL_PROJECTS = ["VCCF", "VCBF", "EXAI", "VCS", "VCG"]

# Projects that related to DET
DET_DEBUG_PROJECTS = ["DETBUG", "DETMON"]

# Jira projects that are used for bug reporting
JIRA_PROJECTS = ["DLAA", "DLAI", "DLAW"] + VIDEO_CALL_PROJECTS + DET_DEBUG_PROJECTS

# Localization contractors label
JIRA_LOCALIZATION_CONTRACTORS_LABEL = "localization-contractor"

# Jira issue type label for bugs
JIRA_ISSUE_TYPE_BUG = "Bug"
JIRA_ISSUE_TYPE_EPIC = "Epic"

# For storing stats on words, only consider words that appear more commonly across the corpus
MIN_SAMPLES_THRESHOLD = 10

# Directory for storing quality reports
QUALITY_REPORT_S3_PATH = "quality_report_scores"
QUALITY_REPORT_PLOTS_DIRECTORY = "plots"
QUALITY_REPORT_PLOTS_EXTERNAL_DIRECTORY = (
    "https://public-static.duolingo.com/delight/quality-report/"
)

# For spikes, occurrences should be at least five-sigma away from historical values.
SPIKE_THRESHOLD = 5

SENTENCE_TRANSFORMER_MODEL = "SentenceTransformers"

GPT_EMBEDDING_MODEL = "GPT_text-embedding-ada-002"


def get_config() -> Config:
    """
    Exposes a way to get a singleton instance of duolingo_base.config.Config
    so that we only have to call Config.load_config() once.
    """
    return CONFIG
