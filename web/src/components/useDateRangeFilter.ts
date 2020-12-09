import { endOfToday, startOfDay, subDays } from "date-fns";

import useSearchParams from "components/useSearchParams";

const useDateRangeFilter = ({ daysAgo }: { daysAgo?: number } = {}) => {
  const search = useSearchParams();

  const from = search.get("from")
    ? new Date(search.get("from") as string)
    : daysAgo
    ? startOfDay(subDays(new Date(), daysAgo))
    : undefined;

  const to = search.get("to")
    ? new Date(search.get("to") as string)
    : endOfToday();

  return { from, to };
};

export default useDateRangeFilter;
