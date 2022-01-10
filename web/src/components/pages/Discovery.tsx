import * as React from "react";

import Tickets from "components/Tickets";
import useDocumentTitle from "components/useDocumentTitle";
import usePageView from "components/usePageView";

const Discovery = () => {
  useDocumentTitle("Issue Discovery");
  usePageView();
  return <Tickets />;
};

export default Discovery;
