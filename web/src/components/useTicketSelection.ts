import * as React from "react";
import { useHistory, useLocation } from "react-router-dom";

import { encodeURLSearchParams } from "../util";
import useSearchParams from "components/useSearchParams";

interface Options {
  onNext?: () => void;
  onPrev?: () => void;
}

type SetIdCallback = (newId: string | undefined) => void;

const useTicketSelection = (
  tickets: JSONAPI.Ticket[] | undefined,
  { onNext, onPrev }: Options = {},
): [string | undefined, SetIdCallback] => {
  const history = useHistory();
  const location = useLocation();
  const search = useSearchParams();

  const id = search.get("id");

  const setId = React.useCallback<SetIdCallback>(
    newId => {
      const params = new URLSearchParams(location.search);
      if (newId === undefined) {
        params.delete("id");
      } else {
        params.set("id", newId);
      }
      history.push({
        ...location,
        search: encodeURLSearchParams(params),
      });
    },
    [history, location],
  );

  const onNextRef = React.useRef(onNext);
  onNextRef.current = onNext;

  const onPrevRef = React.useRef(onPrev);
  onPrevRef.current = onPrev;

  React.useEffect(() => {
    if (tickets?.length) {
      const currentIndex = tickets.findIndex(t => t.jeeves_uid === id);

      const next = () => {
        if (currentIndex < tickets.length - 1) {
          setId(tickets[currentIndex + 1].jeeves_uid);
        } else {
          onNextRef.current?.();
        }
      };

      const prev = () => {
        if (currentIndex === -1) {
          setId(tickets[tickets.length - 1].jeeves_uid);
        } else if (currentIndex > 0) {
          setId(tickets[currentIndex - 1].jeeves_uid);
        } else {
          onPrevRef.current?.();
        }
      };

      const handleKeydown = (e: KeyboardEvent) => {
        if (e.key === "j") {
          next();
          e.preventDefault();
        } else if (e.key === "k") {
          prev();
          e.preventDefault();
        }
      };
      document.addEventListener("keydown", handleKeydown);
      return () => document.removeEventListener("keydown", handleKeydown);
    }
    return undefined;
  }, [history, id, setId, tickets]);

  return [id ?? undefined, setId];
};

export default useTicketSelection;
