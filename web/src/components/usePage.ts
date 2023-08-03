import { useRouteMatch } from "react-router";

export enum Page {
  Analysis = "analysis",
  Discovery = "discovery",
  GPTSearch = "gpt-search",
  QualityReport = "quality-report",
  SentimentSearch = "sentiment-search",
  Spike = "spike",
  SpikeStats = "spike-stats",
}

interface PageParams {
  page: string;
}

/**
 * Get the "page" part of the current URL
 *
 * @returns the current page enum
 */
const usePage = (): Page | undefined => {
  const match = useRouteMatch<PageParams>({ path: "/:lang/:page" });
  const page = match?.params?.page ?? "";
  return Object.values(Page).find(p => p === page);
};

export default usePage;
