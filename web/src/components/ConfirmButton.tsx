import * as React from "react";
import { Toggle } from "web-ui";

import { setSpikeConfirmed } from "api/jeeves";
import styles from "styles/ConfirmButton.scss";
import { getUser } from "api/user";
import { useQuery } from "react-query";

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

  // const [userName, setUserName] = React.useState("");
  // const handleSetName = async (jwt: number) => {
  //   setUserName((await getUser(jwt)).username ?? "");
  // };

  return (
    <ul>
      <li>
        <Toggle
          checked={isConfirmed}
          onChange={async () => {
            const response = await setSpikeConfirmed(
              spike.spike_id,
              !isConfirmed,
            );
            setIsConfirmed(response.confirmed);
            setUserId(response.user_id);
          }}
        />
      </li>
      <li>
        {isConfirmed && (
          <label className={styles["confirm-username"]}>(by {username})</label>
        )}
      </li>
    </ul>
  );
};

export default ConfirmButton;
