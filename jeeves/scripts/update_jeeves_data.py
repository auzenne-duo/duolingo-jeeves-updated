import time

from jeeves.lib.ticket_crawler import crawl_tickets

if __name__ == "__main__":
    start = time.time()

    crawl_tickets()

    print("=" * 100)
    print(f"Batch done in {(time.time() - start):.3f} sec.")
    print("=" * 100)
