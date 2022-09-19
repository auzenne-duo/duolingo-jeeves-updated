import datetime
import json
import os
import sys
from calendar import WEDNESDAY
from collections import defaultdict
from typing import Dict, Set, Tuple

import requests
import rollbar
from duolingo_base.config import Config
from duolingo_base.dal import s3
from google.cloud import bigquery

from jeeves.util.error_util import print_request_exception

_config = Config.load_config()
_config.apply_logging()
_config.apply_rollbar()

DUOLINGO_JWT = os.getenv("DUOLINGO_JWT")
GRANT_XP_AMOUNT = 0
DRY_RUN = True


def retrieve_dogfooding_versions() -> Tuple[int, Dict[str, str]]:
    obj = s3.S3Client().download(
        "internal-static.duolingo.com", "release-dashboard/release-dashboard.json"
    )
    dashboard_data = json.loads(obj)

    versions = {}
    for data in dashboard_data["platformData"]:
        platform = data["platform"]["name"]
        dogfooding_version = None
        for release in data["releases"]:
            if release["status"] in ("Dogfooding", "Store Approved"):
                assert (
                    dogfooding_version is None
                ), f"Multiple dogfooding versions found for {platform}"
                dogfooding_version = release["majorMinor"]
        if dogfooding_version is not None:
            assert platform not in versions, f"Multiple dogfooding version found for {platform}"
            versions[platform] = dogfooding_version

    return dashboard_data["now"], versions


def get_last_dogfooding_time_range(current_time: int) -> Tuple[str, str]:
    current_time = datetime.datetime.fromtimestamp(current_time / 1000)
    # release cut
    release_time = datetime.datetime(
        year=current_time.year,
        month=current_time.month,
        day=current_time.day - (current_time.weekday() - WEDNESDAY) % 7,
        hour=15,
        tzinfo=current_time.tzinfo,
    )
    return str(release_time), str(current_time)


def query_dogfooders(
    platform: str, version: str, start_time: str, end_time: str
) -> Dict[int, Set[str]]:
    platform = {
        "Android": "Duodroid",
        "iOS": "iOS",
        "Web": "web",
    }[platform]

    query = f"""SELECT DISTINCT
  user_id, direction
FROM
  `excess-etl.events.app_open`
WHERE
  event_timestamp > '{start_time}'
  AND event_timestamp <= '{end_time}'
  AND user_id IS NOT NULL
  AND app_version LIKE '{version}%'
  AND client = '{platform}'"""

    user_courses = defaultdict(set)
    client = bigquery.Client(project="bq-default")
    for row in client.query(query):
        user_courses[row[0]].add(row[1])
    client.close()

    return user_courses


def query_employees() -> Set[int]:
    obj = s3.S3Client().download("internal-static.duolingo.com", "internal-tools/employees.json")
    employees = json.loads(obj)["employees"]
    ret = set()
    for employee in employees:
        duolingo_id = employee["duolingoId"]
        assert duolingo_id is not None and duolingo_id not in ret
        ret.add(duolingo_id)
    return ret


def grant_xp(user_id: int, directions: Set[str]):
    for direction in directions:
        try:
            to_language, from_language = direction.split("<-")
        except ValueError:
            continue
        if not DRY_RUN:
            # TODO: have a dedicated route for this
            resp = requests.post(
                "https://api.duolingo.com/internal_api/1/audio_lessons/award_skill_points",
                json={
                    "user_id": user_id,
                    "learning_language_id": to_language,
                    "from_language_id": from_language,
                    "skill_points": GRANT_XP_AMOUNT,
                },
                cookies={"jwt_token": DUOLINGO_JWT},
            )
            try:
                resp.raise_for_status()
            except requests.RequestException as e:
                print_request_exception(e, rollbar_level="error")
                continue
            assert (
                resp.headers["Content-Type"] == "application/json; charset=UTF-8"
            ), "Not authenticated"
        print(f"Grant user {user_id} with {GRANT_XP_AMOUNT} XP on {direction}")
        break


def main():
    employees = query_employees()
    current_time, versions = retrieve_dogfooding_versions()
    start_time, end_time = get_last_dogfooding_time_range(current_time)

    dogfooders_tree = defaultdict(set)
    for platform, version in versions.items():
        print(f"Loading dogfooders for {platform} version {version}")
        dogfooders = query_dogfooders(platform, version, start_time, end_time)
        for duolingo_id, direction in dogfooders.items():
            if duolingo_id in employees:
                dogfooders_tree[duolingo_id].update(direction)
    for user_id, directions in dogfooders_tree.items():
        grant_xp(user_id, directions)


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            GRANT_XP_AMOUNT = int(sys.argv[1])
            DRY_RUN = False  # if there's argument, actually run
        else:
            GRANT_XP_AMOUNT = 20
        main()
    except:
        rollbar.report_exc_info()
