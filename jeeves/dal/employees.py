import json
from typing import Any, Dict, List, Optional

import duo_logging.legacy as rollbar
from duolingo_base.dal.s3 import S3Client, S3DownloadException

_EMPLOYEES_JSON_FILE_BUCKET = "internal-static.duolingo.com"
_EMPLOYEES_JSON_FILE_PATH = "internal-tools/employees.json"


class EmployeesDAL:
    def _fetch_json(self) -> Dict[str, Any]:
        """
        Fetch the `employees.json` file from S3 and parse it as a `Dict`.
        """
        client = S3Client()
        return json.loads(client.download(_EMPLOYEES_JSON_FILE_BUCKET, _EMPLOYEES_JSON_FILE_PATH))

    def get_employees(self) -> List[Dict[str, Any]]:
        """
        Returns a list of employees data.
        """
        return self._fetch_json()["employees"]

    def get_teams(self) -> List[Dict[str, Any]]:
        """
        Returns a list of teams data.
        """
        return self._fetch_json()["teams"]

    def get_employee_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            employees = self.get_employees()
            for employee in employees:
                if employee["email"] == email:
                    return employee
        except S3DownloadException:
            rollbar.report_exc_info()
            return None
        except KeyError:
            rollbar.report_message("Could not parse employees.json", "error")
            return None
        return None
