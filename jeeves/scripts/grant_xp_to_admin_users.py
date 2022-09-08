import datetime
import json
import os
from calendar import WEDNESDAY
from collections import defaultdict
from typing import Dict, Set, Tuple

import google
import requests
import rollbar
from duolingo_base.config import Config
from duolingo_base.dal import s3
from google.cloud import bigquery

# pylint: disable=unused-import
from google.oauth2 import credentials, service_account

from jeeves.util.date_util import date_to_str
from jeeves.util.error_util import print_request_exception

_config = Config.load_config()
_config.apply_logging()
_config.apply_rollbar()

DUOLINGO_JWT = os.getenv("DUOLINGO_JWT")
GRANT_XP_AMOUNT = 20


def authenticate_bq() -> google.oauth2.credentials.Credentials:
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(os.environ.get("GOOGLE_CREDENTIALS_INFO"))
    )
    return credentials


_CREDENTIALS = authenticate_bq()
_CLIENT = bigquery.Client(project="excess-etl", credentials=_CREDENTIALS)


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
    """
    Returns the release datetime, which is currently the previous wednesday at 3pm
    """
    current_time = datetime.datetime.fromtimestamp(current_time / 1000)
    # release cut
    offset = (current_time.weekday() - WEDNESDAY) % 7
    release_time = current_time - datetime.timedelta(days=offset)
    release_time = release_time.replace(hour=15)
    return release_time, current_time


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
    for row in _CLIENT.query(query):
        user_courses[row[0]].add(row[1])
    _CLIENT.close()

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
            print_request_exception(e)
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
    dogfooders_platforms = defaultdict(set)
    for platform, version in versions.items():
        print(f"Loading dogfooders for {platform} version {version}")
        dogfooders = query_dogfooders(platform, version, str(start_time), str(end_time))
        for duolingo_id, direction in dogfooders.items():
            if duolingo_id in employees:
                dogfooders_tree[duolingo_id].update(direction)
                dogfooders_platforms[duolingo_id].add(platform)
    dogfooders_tree = {23133309: "es<-en"}
    dogfooders_platforms = {23133309: "web"}
    for user_id, directions in dogfooders_tree.items():
        grant_xp(user_id, directions)

    s3_client = None
    if _config.get_nested(["s3_document_cache", "endpoint_url"]):
        s3_client = s3.S3Client(_config.get_nested(["s3_document_cache", "endpoint_url"]))
    else:
        s3_client = s3.S3Client()
    s3_bucket_name = _config.get_nested(["s3_document_cache", "bucket_name"])
    dogfooder_data = [
        {
            "user_id": user_id,
            "platforms": list(dogfooders_platforms[user_id]),
            "directions": list(directions),
            "xp": GRANT_XP_AMOUNT,
        }
        for user_id, directions in dogfooders_tree.items()
    ]
    s3_client.upload(
        s3_bucket_name, f"dogfooders_granted_xp_{date_to_str(end_time)}", json.dumps(dogfooder_data)
    )


if __name__ == "__main__":
    try:
        main()
    except:
        rollbar.report_exc_info()
