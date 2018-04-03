import os
import yaml

from jeeves import package_directory

_METADATA_CONFIG_PATH = os.path.join(package_directory, 'config', 'feedback_metadata_grammar.yml')

with open(_METADATA_CONFIG_PATH, 'r') as f:
    Config = yaml.load(f)

STATS_FIELD_TITLES = [f['field'] for f in Config['fields'] if not f['unique']]
UNIQUE_FIELD_TITLES = [f['field'] for f in Config['fields'] if f['unique']]

# It is important that SEMANTIC_FIELD_TITLES is subset(eq) to STATS_FIELD_TITLES
SEMANTIC_FIELD_TITLES = [f['field'] for f in Config['fields'] if f['semantic'] and not f['unique']]

FIELD_TITLES = STATS_FIELD_TITLES + UNIQUE_FIELD_TITLES
