import { parseISO } from "date-fns";
import * as React from "react";

import cn from "classnames";
import ResizableGraph, { usePlotState } from "components/ResizableGraph";
import styles from "components/quality-report/QualityGraph.scss";

const BLACK_TEXT = "#3c3c3c";
const JUICY_BEETLE = "#ce82ff";
const JUICY_FOX = "#ff9600";
const JUICY_OWL = "#58cc02";
const JUICY_MACAW = "#1cb0f6";
const JUICY_SWAN = "#e5e5e5";

type Project = typeof PROJECTS[number];

const COLOR_MAP: Record<Project, string> = {
  DLAA: JUICY_FOX,
  DLAI: JUICY_MACAW,
  DLAW: JUICY_BEETLE,
  Overall: JUICY_OWL,
};

const LEGEND_MAP: Record<Project, string> = {
  DLAA: "Android",
  DLAI: "iOS",
  DLAW: "Web",
  Overall: "Overall",
};

const PROJECTS = ["DLAA", "DLAI", "DLAW", "Overall"] as const;

interface Props {
  className?: string;
  disableHover?: boolean;
  overallOnly?: boolean;
  scores: JSONAPI.QualityReport["areas"][number]["scores"];
  title: string;
}

const QualityGraph = ({
  className,
  disableHover,
  overallOnly,
  scores,
  title,
}: Props) => {
  const [plotState, setPlotState] = usePlotState();

  const data = React.useMemo(
    () =>
      PROJECTS.filter(p => !overallOnly || p === "Overall").map(p => ({
        line: {
          color: COLOR_MAP[p],
          dash: p === "Overall" ? "solid" : "dashdot",
        },
        mode: p === "Overall" ? "lines+markers" : "lines",
        name: LEGEND_MAP[p],
        type: "scatter",
        // Scores are actually computed on EST date grouping, but
        // for simplicity we pretend that they are local date groups
        // in the UI.
        x: scores[p].map(([date]) => parseISO(`${date}T00:00:00`)),
        y: scores[p].map(([, value]) => value),
      })),
    [overallOnly, scores],
  );

  React.useEffect(() => {
    setPlotState({
      config: {
        displayModeBar: false,
        showTips: false,
      },
      data,
      frames: [],
      layout: {
        autosize: true,
        font: {
          color: BLACK_TEXT,
          family: "din-round, sans-serif",
        },
        hovermode: disableHover ? false : undefined,
        legend: {
          orientation: "h",
        },
        margin: {
          b: overallOnly ? 20 : 0,
          l: 25,
          r: 0,
          t: 40,
        },
        showlegend: !overallOnly,
        title: {
          font: {
            // Matches the <h2> element style.
            size: 19,
          },
          text: `<b>${title}</b>`,
        },
        xaxis: {
          fixedrange: true,
          gridcolor: JUICY_SWAN,
        },
        yaxis: {
          fixedrange: true,
          gridcolor: JUICY_SWAN,
          range: [0, 100],
          rangemode: "tozero",
        },
      },
    });
  }, [data, disableHover, overallOnly, setPlotState, title]);

  return (
    <ResizableGraph
      className={cn(styles.graph, className)}
      onChange={setPlotState}
      state={plotState}
    />
  );
};

export default QualityGraph;
