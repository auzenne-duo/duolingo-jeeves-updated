import type { UseQueryOptions } from "@tanstack/react-query";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { getTicket } from "api/jeeves";

type Data = JSONAPI.Ticket | undefined;

const useTicketQuery = (
  id: string | undefined,
  options: Omit<UseQueryOptions<Data>, "queryFn" | "queryKey"> = {},
) => {
  const { lang } = useParams<{
    lang: JSONAPI.LanguageId;
  }>();
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
