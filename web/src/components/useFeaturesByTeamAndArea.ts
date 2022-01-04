import { useQuery } from "react-query";

import { getFeaturesByTeamAndArea } from "api";

const useFeaturesByTeamAndArea = () =>
  useQuery("areas", () => getFeaturesByTeamAndArea(), {
    // Cache data until the page is refreshed.
    cacheTime: Infinity,
    staleTime: Infinity,
  });

export default useFeaturesByTeamAndArea;
