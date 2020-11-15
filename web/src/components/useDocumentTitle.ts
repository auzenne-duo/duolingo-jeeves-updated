import * as React from "react";

const useDocumentTitle = (page: string) =>
  React.useEffect(() => {
    document.title = `${page} | Duolingo Jeeves`;
    return () => {
      document.title = "Duolingo Jeeves";
    };
  }, [page]);

export default useDocumentTitle;
