import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { Toggle } from "web-ui";

import { setSpikeConfirmed } from "api/jeeves";
import { getUser } from "api/user";
import styles from "styles/ConfirmButton.scss";

interface Props {
  spike: JSONAPI.SpikeWord;
}

const ConfirmButton = ({ spike }: Props) => {
  const queryClient = useQueryClient();

  const { data: username } = useQuery(
    ["users", spike.user_id],
    () => {
      if (spike.user_id === undefined) {
        throw Error("Query shouldn't be enabled.");
      }
      return getUser(spike.user_id);
    },
    {
      enabled: !!spike.user_id,
      select: data => data.username,
    },
  );

  const mutation = useMutation(
    () => setSpikeConfirmed(spike.spike_id, !spike.confirmed),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("spikes");
      },
    },
  );

  return (
    <>
      <Toggle
        checked={spike.confirmed}
        className={styles.toggle}
        onChange={async () => {
          mutation.mutate();
        }}
      />
      {spike.confirmed && username && (
        <span className={styles["confirm-username"]}>(by {username})</span>
      )}
    </>
  );
};

export default ConfirmButton;
