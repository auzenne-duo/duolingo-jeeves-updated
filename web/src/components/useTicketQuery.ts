import type { UseQueryOptions } from "@tanstack/react-query";
import { useQuery } from "@tanstack/react-query";

import { getTicket } from "api/jeeves";
import usePageLanguage from "components/usePageLanguage";

type Data = JSONAPI.Ticket | undefined;

const useTicketQuery = (
  id: string | undefined,
  options: Omit<UseQueryOptions<Data>, "queryFn" | "queryKey"> = {},
) => {
  const lang = usePageLanguage();
  return useQuery<Data>(
    ["tickets", id, { lang }],
    () => getTicket(lang, id as string),
    {
      enabled: !!id,
      ...options,
    },
  );
};

export default useTicketQuery;
