import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { Button } from "web-ui";

import { getUser } from "api/user";
import FixedModal from "components/EmailBetaModal";

interface Props {
  spike: JSONAPI.SpikeWord;
}

const EmailBetaButton = ({ spike }: Props) => {
  const [modalIsOpen, setIsOpen] = React.useState<boolean>(false);
  const fixedStatus = "FIXED";

  const closeModal = () => setIsOpen(false);

  const { data: username } = useQuery(
    ["users", spike.email_user_id],
    () => {
      if (spike.email_user_id === undefined) {
        throw Error("Query shouldn't be enabled.");
      }
      return getUser(spike.email_user_id);
    },
    {
      enabled: !!spike.email_user_id,
      select: data => data.username,
    },
  );

  return (
    <>
      {spike.email_sent_date ? (
        <div>
          Email sent on {spike.email_sent_date} by {username}
        </div>
      ) : (
        <Button
          color="owl"
          disabled={!(spike.status === fixedStatus)}
          onClick={() => setIsOpen(true)}
          variant="solid"
        >
          Send email
        </Button>
      )}
      <FixedModal closeModal={closeModal} isOpen={modalIsOpen} spike={spike} />
    </>
  );
};

export default EmailBetaButton;
