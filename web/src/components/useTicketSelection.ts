import * as React from "react";
import { useHistory, useLocation } from "react-router-dom";

import { encodeURLSearchParams } from "../util";
import useSearchParams from "components/useSearchParams";

export const LIST_ID_PROP = Symbol();

interface Options {
  onNext?: () => void;
  onPrev?: () => void;
}

type SetIdCallback = (newId?: string, listId?: string) => void;

interface TicketInList extends JSONAPI.Ticket {
  [LIST_ID_PROP]?: string;
}

const useTicketSelection = (
  tickets: TicketInList[] | undefined,
  { onNext, onPrev }: Options = {},
): [
  string | undefined,
  SetIdCallback,
  {
    listId: string | undefined;
  },
] => {
  const history = useHistory();
  const location = useLocation();
  const search = useSearchParams();

  const id = search.get("id");
  const listId = search.get("list");

  const setId = React.useCallback<SetIdCallback>(
    (newId, newListId) => {
      const params = new URLSearchParams(location.search);
      if (newId === undefined) {
        params.delete("id");
      } else {
        params.set("id", newId);
      }
      if (newListId === undefined) {
        params.delete("list");
      } else {
        params.set("list", newListId);
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
      const currentIndex = tickets.findIndex(
        t =>
          t.jeeves_uid === id &&
          (t[LIST_ID_PROP] === listId || listId === null),
      );

      const setIdByTicket = (t: TicketInList) =>
        setId(t.jeeves_uid, t[LIST_ID_PROP]);

      const next = () => {
        if (currentIndex < tickets.length - 1) {
          setIdByTicket(tickets[currentIndex + 1]);
        } else {
          onNextRef.current?.();
        }
      };

      const prev = () => {
        if (currentIndex === -1) {
          setIdByTicket(tickets[tickets.length - 1]);
        } else if (currentIndex > 0) {
          setIdByTicket(tickets[currentIndex - 1]);
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
  }, [history, id, listId, setId, tickets]);

  return [id ?? undefined, setId, { listId: listId ?? undefined }];
};

export default useTicketSelection;
