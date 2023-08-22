import * as React from "react";
import { alignNearest } from "web-ui/util/scroll";

import styles from "components/TicketList.scss";
import TicketListItem from "components/TicketListItem";
import type { RenderableTag } from "components/TicketListItem";

interface Props {
  bordered?: boolean;
  onClick?: (ticket: JSONAPI.Ticket) => void;
  selectedId?: string;
  showTags?: RenderableTag[];
  supportsTicketQuery?: boolean;
  tickets: JSONAPI.Ticket[];
}

const TicketList = ({
  bordered = true,
  onClick,
  selectedId: id,
  showTags,
  supportsTicketQuery = false,
  tickets,
}: Props) => {
  const currentRowRef = React.useRef<HTMLLIElement>(null);

  React.useEffect(() => {
    if (currentRowRef.current) {
      const bodyStyle = getComputedStyle(document.body);
      const topbarHeight = parseFloat(
        bodyStyle.getPropertyValue("--height-topbar"),
      );
      const margin = parseFloat(bodyStyle.getPropertyValue("--margin"));
      const target = currentRowRef.current.getBoundingClientRect();
      document.documentElement.scrollTop += alignNearest(
        topbarHeight + margin,
        window.innerHeight - margin,
        window.innerHeight - topbarHeight - 2 * margin,
        0,
        0,
        target.top,
        target.bottom,
        target.height,
      );
    }
  }, [id, tickets]);

  return (
    <ul className={bordered ? styles["list-bordered"] : styles.list}>
      {tickets.length ? null : (
        <li className={styles.empty}>No issues have been found.</li>
      )}
      {tickets.map((t, i) => (
        <TicketListItem
          key={i}
          onClick={() => onClick?.(t)}
          ref={t.jeeves_uid === id ? currentRowRef : undefined}
          selected={t.jeeves_uid === id}
          showTags={showTags}
          supportsTicketQuery={supportsTicketQuery}
          ticket={t}
        />
      ))}
    </ul>
  );
};

export default TicketList;
