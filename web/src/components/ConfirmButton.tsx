import * as React from "react";
import { Toggle } from "web-ui";

import { setSpikeConfirmed } from "api/jeeves";

interface Props {
  spike: JSONAPI.SpikeWord;
}

const ConfirmButton = ({ spike }: Props) => {
  const [isConfirmed, setIsConfirmed] = React.useState(spike.confirmed);
  return (
    <Toggle
      checked={isConfirmed}
      onChange={async () => {
        await setSpikeConfirmed(spike.spike_id, !isConfirmed);
        setIsConfirmed(!isConfirmed);
      }}
    />
  );
};

export default ConfirmButton;
