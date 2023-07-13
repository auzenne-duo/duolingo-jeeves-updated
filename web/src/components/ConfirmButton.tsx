import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
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
    ["users", spike.confirmed_user_id],
    () => {
      if (spike.confirmed_user_id === undefined) {
        throw Error("Query shouldn't be enabled.");
      }
      return getUser(spike.confirmed_user_id);
    },
    {
      enabled: !!spike.confirmed_user_id,
      select: data => data.username,
    },
  );

  const mutation = useMutation(
    () => setSpikeConfirmed(!spike.confirmed, spike.spike_id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(["spikes"]);
      },
    },
  );

  return (
    <>
      <Toggle
        checked={spike.confirmed}
        className={styles.toggle}
        onChange={() => mutation.mutate()}
      />
      {spike.confirmed && username && <div>({username})</div>}
    </>
  );
};

export default ConfirmButton;
