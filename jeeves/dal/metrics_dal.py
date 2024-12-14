from typing import Dict, List, Tuple

import requests
from duolingo_base.dal.duoapi import DuolingoApiClient
from duolingo_base.util import registry

from jeeves.dal.auth_dal import AuthDAL
from jeeves.util.error_util import print_request_exception

EXPERIMENTS_ROUTE = "api/1/experiments"
TOP_SHARED_CONDITIONS = 5
SHARED_CONDITIONS_ROUTE = "api/1/find_shared_conditions"
STANDARD_DEVIATION_THRESHOLD = 3
MIN_SHARED_USERS = 3
TIMEOUT = 30  # in seconds


@registry.bind(auth_dal=registry.reference(AuthDAL))
class MetricsDAL:
    def __init__(self, auth_dal: AuthDAL):
        self.client = DuolingoApiClient(
            url="https://metrics.duolingo.com/",
            auth_api=auth_dal.auth_api,
        )
        self._headers = {
            "Accept": "application/json",
            "User-Agent": "product-quality (DuolingoService)",
        }
        experiments = self._get_experiments()
        self.experiments_metadata = {experiment["name"]: experiment for experiment in experiments}

    def get_shared_conditions(
        self, user_ids: List[int], use_rollout=True
    ) -> Dict[Tuple[str, str], float]:
        """
        Get the shared experiment conditions for a list of users. We have a binomial distribution of whether users are in a specific
        condition or not. We can use this to determine if the number of users in a condition is significantly significant.


        Arguments:
            user_ids (List[str]): List of user IDs
            use_rollout (bool): Whether to use the rollout percentage in the calculation - should be off for admin/beta users
        Returns:
            Dict[Tuple(str, str), float]: Dictionary of experiment and condition to the percentage of users that share that condition
        """
        # if we couldn't get the experiments, return an empty dict
        if not self.experiments_metadata:
            return {}

        user_ids = {id for id in user_ids if id not in [None, ""]}
        if len(user_ids) < MIN_SHARED_USERS:
            return {}

        # Search for user
        params = {"user_ids": ",".join(str(id) for id in user_ids)}
        total_users = len(user_ids)
        try:
            response = self.client.get(SHARED_CONDITIONS_ROUTE, params=params, timeout=TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Request to /{SHARED_CONDITIONS_ROUTE} failed with exception: {e}", flush=True)
            print_request_exception(e, log_level="warning")
            return {}

        # Return top X shared conditions that are not in the control condition
        shared_conditions = {}
        for experiment in response.json()["conditions"]:
            if experiment["condition"] == "control":
                continue
            if experiment["num_shared"] < MIN_SHARED_USERS:
                continue
            if experiment["experiment"] not in self.experiments_metadata:
                continue

            # Calculate the standard deviation of the binomial distribution
            condition_index = self.experiments_metadata[experiment["experiment"]][
                "conditions"
            ].index(experiment["condition"])
            weights = self.experiments_metadata[experiment["experiment"]]["selector"]["weights"]
            p = weights[condition_index] / sum(weights)

            if use_rollout:
                p *= experiment["rollout"]
            if p == 0 or p == 1:
                continue
            std = (p * (1 - p) * total_users) ** 0.5
            mean = p * total_users
            spikiness = (experiment["num_shared"] - mean) / std
            if spikiness > STANDARD_DEVIATION_THRESHOLD:
                shared_conditions[(experiment["experiment"])] = spikiness
                if len(shared_conditions) >= TOP_SHARED_CONDITIONS:
                    break
        return shared_conditions

    def _get_experiments(self) -> List[Dict]:
        """
        Get the list of experiments.
        Returns:
            List[Dict]: List of experiments
        """
        try:
            response = self.client.get(EXPERIMENTS_ROUTE, timeout=TIMEOUT)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Request to /{EXPERIMENTS_ROUTE} failed with exception: {e}", flush=True)
            print_request_exception(e, log_level="warning")
            return []
        return response.json()
