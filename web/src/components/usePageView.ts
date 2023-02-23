import * as React from "react";
import { useLocation } from "react-router";

const usePageView = () => {
  const location = useLocation();

  React.useEffect(() => {
    ga("send", "pageview", location.pathname);
  }, [location.pathname]);
};

export default usePageView;
