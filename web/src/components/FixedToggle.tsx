import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import { Toggle } from "web-ui";

import { setSpikeFixed } from "api/jeeves";
import { getUser } from "api/user";

interface Props {
  spike: JSONAPI.SpikeWord;
}

const FixedToggle = ({ spike }: Props) => {
  const queryClient = useQueryClient();

  const { data: username } = useQuery(
    ["users", spike.fixed_user_id],
    () => {
      if (spike.fixed_user_id === undefined) {
        throw Error("Query shouldn't be enabled.");
      }
      return getUser(spike.fixed_user_id);
    },
    {
      enabled: !!spike.fixed_user_id,
      select: data => data.username,
    },
  );

  const handleToggle = () => {
    if (!spike.confirmed) {
      alert("You must confirm this spike before you can fix it.");
      return;
    }
    mutation.mutate();
  };

  const mutation = useMutation(
    () => setSpikeFixed(!spike.fixed, spike.spike_id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(["spikes"]);
      },
    },
  );

  return (
    <>
      <Toggle checked={spike.fixed} onChange={handleToggle} />
      {spike.fixed && username && <div>({username})</div>}
    </>
  );
};

export default FixedToggle;
