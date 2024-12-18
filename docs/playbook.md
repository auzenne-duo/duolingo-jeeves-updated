# Playbook

## Monitoring

### Prod environment

- [Grafana](https://grafana.duolingo.com/d/jiS6nriZz/duolingo-jeeves-prod-api?orgId=1&refresh=1m)
- [Sentry](https://duolingo-sentry.sentry.io/projects/duolingo-jeeves/?issuesType=all&project=4506582948184064)

### Sentry - Encountered X errors when bulk indexing tickets ...

'reason': 'Indexing knn vector fields is rejected as circuit breaker triggered. Check \_opendistro/\_knn/stats for detailed state'

The KNN chache for opensearch has filled and tripped a circuit breaker (why doesn't it remove things from the cache? IDK couldn't find an answer when asking for help)
To double check the state of the cache, you can run these curl requests:

```
# Gets info about the knn cache and memory usage
curl -X GET "https://vpc-duolingo-jeeves-es-prod-eg2rc47wen2dsgmzunu4whvfju.us-east-1.es.amazonaws.com/_opendistro/_knn/stats"

# Info about opnesearch cluster settings such as the cache expiry time
curl -X GET "https://vpc-duolingo-jeeves-es-prod-eg2rc47wen2dsgmzunu4whvfju.us-east-1.es.amazonaws.com/_cluster/settings?include_defaults=true"
```

To reset the circuit breaker, you can clear the cache by setting “knn.memory.circuit_breaker.limit” to null and then return it to its previous value.([reference](https://forum.opensearch.org/t/how-to-deal-with-knn-circuit-breaker-triggered-stays-set-nodes-at-max-cache-capacity/4733))
You can do so using these requests:

```
curl -X PUT "https://vpc-duolingo-jeeves-es-prod-eg2rc47wen2dsgmzunu4whvfju.us-east-1.es.amazonaws.com/_cluster/settings" -H 'Content-Type: application/json' -d'
{
  "persistent": {
    "knn.memory.circuit_breaker.limit": 0
  }
}
'

curl -X PUT "https://vpc-duolingo-jeeves-es-prod-eg2rc47wen2dsgmzunu4whvfju.us-east-1.es.amazonaws.com/_cluster/settings" -H 'Content-Type: application/json' -d'
{
  "persistent": {
    "knn.memory.circuit_breaker.limit":"50%"
  }
}
'
```

## Secrets Management

[duolingo-jeeves Doppler project](https://dashboard.doppler.com/workplace/043ab88427eb7d8c605b/projects/duolingo-jeeves)

For more information on how secrets are managed at Duolingo, please refer to the following documentation: [Doppler](https://duolingo.atlassian.net/wiki/x/MQD9w)

<div align="right"><a href="#table-of-contents">back to top ⬆</a></div>
