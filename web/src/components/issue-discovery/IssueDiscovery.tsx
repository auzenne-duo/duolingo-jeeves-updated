import * as React from "react";

import Tickets from "components/Tickets";
import useDocumentTitle from "components/useDocumentTitle";

const IssueDiscovery = () => {
  useDocumentTitle("Issue Discovery");
  return <Tickets />;
};

export default IssueDiscovery;
