import { useQuery } from "@tanstack/react-query";

import { getFeaturesByTeamAndArea } from "api/shakira";

const useFeaturesByTeamAndArea = () =>
  useQuery(["areas"], () => getFeaturesByTeamAndArea(), {
    // Cache data until the page is refreshed.
    cacheTime: Infinity,
    select: data => {
      data.sort((a, b) => a.area_name.localeCompare(b.area_name));
      data.forEach(area =>
        area.teams.sort((a, b) => a.team_name.localeCompare(b.team_name)),
      );
      return data;
    },
    staleTime: Infinity,
  });

export default useFeaturesByTeamAndArea;
