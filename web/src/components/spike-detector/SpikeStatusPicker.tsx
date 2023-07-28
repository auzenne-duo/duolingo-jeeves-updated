import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { Select } from "web-ui";

import { setSpikeStatus } from "api/jeeves";
import { getUser } from "api/user";
import styles from "components/spike-detector/SpikeStatusPicker.scss";

const STATUSES: Record<JSONAPI.SpikeStatus, string> = {
  CONFIRMED: "Confirmed",
  FIXED: "Fixed",
  UNCONFIRMED: "Unconfirmed",
};

interface Props {
  className?: string;
  spike: JSONAPI.SpikeWord;
}

const SpikeStatusPicker = ({ className, spike }: Props) => {
  const queryClient = useQueryClient();

  const { data: username } = useQuery(
    ["users", spike.status_user_id],
    () => {
      if (spike.status_user_id === undefined) {
        throw Error("Query shouldn't be enabled.");
      }
      return getUser(spike.status_user_id);
    },
    {
      enabled: !!spike.status_user_id,
      select: data => data.username,
    },
  );

  const mutation = useMutation(
    (status: JSONAPI.SpikeStatus) => setSpikeStatus(status, spike.spike_id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(["spikes"]);
      },
    },
  );

  return (
    <>
      <Select
        className={className}
        onChange={e => mutation.mutate(e.target.value as JSONAPI.SpikeStatus)}
        options={Object.entries(STATUSES).map(([k, v]) => ({
          text: v,
          value: k,
        }))}
        text={`${STATUSES[spike.status]}`}
        value={spike.status}
      />
      {spike.status_user_id && username && (
        <div className={styles.username}>({username})</div>
      )}
    </>
  );
};

export default SpikeStatusPicker;
