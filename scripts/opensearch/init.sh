#!/bin/sh
set -eu -o pipefail

echo
echo "Initializing index templates..."

h1="Content-Type: application/json"
h2="Accept: application/json"

curl --fail -H "$h1" -H "$h2" -X PUT "http://opensearch:9200/_template/no_replicas" -d '{"index_patterns": ["*"], "template": {"settings": {"auto_expand_replicas": false, "number_of_replicas": 0}}}'
curl --fail -H "$h1" -H "$h2" -X PUT "http://opensearch:9200/*/_settings" -d '{"index": {"auto_expand_replicas": false, "number_of_replicas": 0}}'
echo
echo
echo "Finished initializing index templates."

while true; do sleep 5; done # Infinite loop to keep service running
