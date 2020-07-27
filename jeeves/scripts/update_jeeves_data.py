import requests
import time

from duolingo_base.config import Config
from jeeves.lib.spike_detector import run_spike_detector
from jeeves.lib.ticket_crawler import crawl_tickets
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES

if __name__ == "__main__":
    start = time.time()
    num_tickets_added = crawl_tickets()
    config = Config.load_config()
    is_production_env = config.get_nested(["environment"]) == "prod"
    for lang in SUPPORTED_LANGUAGES:
        if num_tickets_added[lang.name] > 0:
            run_spike_detector(lang)

        # Reset cache on web server
        if is_production_env:
            print(requests.get(f"https://jeeves.duolingo.com/api/1/{lang.name}/init").content)
        else:
            print(
                requests.get(
                    f"https://duolingo-jeeves-dev.duolingo.com/api/1/{lang.name}/init"
                ).content
            )

    print("=" * 100)
    print(f"Batch done in {(time.time() - start):.3f} sec.")
    print("=" * 100)

    # Put in a sleep so that we don't exceed our daily limit of 1000
    # requests to AppFigures. The sleep happens in 15-second chunks
    # so that we don't die to failed health checks, etc
    print("Starting 15 minute sleep cycle to mitigate rate limiting")
    for i in range(60):
        time.sleep(15)
