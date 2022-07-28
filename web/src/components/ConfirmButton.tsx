import * as React from "react";
import { useQuery } from "react-query";
import { Toggle } from "web-ui";

import { setSpikeConfirmed } from "api/jeeves";
import { getUser } from "api/user";
import styles from "styles/ConfirmButton.scss";

interface Props {
  spike: JSONAPI.SpikeWord;
}

const ConfirmButton = ({ spike }: Props) => {
  const [isConfirmed, setIsConfirmed] = React.useState(spike.confirmed);
  const [userId, setUserId] = React.useState(spike.user_id);

  const { data: username } = useQuery(
    ["users", userId],
    () => {
      if (userId === undefined) {
        throw Error("Query shouldn't be enabled.");
      }
      return getUser(userId);
    },
    {
      enabled: !!userId,
      select: data => data.username,
    },
  );

  return (
    <>
      <Toggle
        checked={isConfirmed}
        className={styles.toggle}
        onChange={async () => {
          const response = await setSpikeConfirmed(
            spike.spike_id,
            !isConfirmed,
          );
          setIsConfirmed(response.confirmed);
          setUserId(response.user_id);
        }}
      />
      {isConfirmed && username && (
        <span className={styles["confirm-username"]}>(by {username})</span>
      )}
    </>
  );
};

export default ConfirmButton;
