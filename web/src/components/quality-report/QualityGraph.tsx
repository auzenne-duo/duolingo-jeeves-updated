import cn from "classnames";
import { parseISO } from "date-fns";
import * as React from "react";
import { Checkbox } from "web-ui/juicy";

import DateRangeInput, {
  type DateRangeChangeEvent,
} from "components/DateRangeInput";
import ResizableGraph, { usePlotState } from "components/ResizableGraph";
import styles from "components/quality-report/QualityGraph.module.scss";

const BLACK_TEXT = "#3c3c3c";
const JUICY_BEETLE = "#ce82ff";
const JUICY_FOX = "#ff9600";
const JUICY_OWL = "#58cc02";
const JUICY_MACAW = "#1cb0f6";
const JUICY_SWAN = "#e5e5e5";

type Project = (typeof PROJECTS)[number];

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
  Overall: "Overall: All platforms",
};

const PROJECTS = ["DLAA", "DLAI", "DLAW", "Overall"] as const;

interface Props {
  className?: string;
  disableHover?: boolean;
  from?: Date;
  isErrorLoading?: boolean;
  isLoading?: boolean;
  onChangeDateRange?: (e: DateRangeChangeEvent) => void;
  onLegendClick?: (trace: string) => void;
  scores: JSONAPI.QualityReport["areas"][number]["scores"];
  title?: string;
  to?: Date;
  visibleTraces: string[];
}

const QualityGraph = ({
  className,
  disableHover,
  from,
  isErrorLoading,
  isLoading,
  onChangeDateRange,
  onLegendClick,
  scores,
  title,
  to,
  visibleTraces,
}: Props) => {
  const [plotState, setPlotState] = usePlotState();

  const data = React.useMemo(
    () =>
      PROJECTS.map(p => ({
        line: {
          color: COLOR_MAP[p],
          dash: p === "Overall" ? "solid" : "dashdot",
        },
        mode: p === "Overall" ? "lines+markers" : "lines",
        name: LEGEND_MAP[p],
        type: "scatter",
        visible: visibleTraces.includes(p),
        // Scores are actually computed on EST date grouping, but
        // for simplicity we pretend that they are local date groups
        // in the UI.
        x: scores[p].map(([date]) => parseISO(`${date}T00:00:00`)),
        y: scores[p].map(([, value]) => value),
      })),
    [scores, visibleTraces],
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
          b: 0,
          l: 25,
          r: 0,
          t: title === undefined ? 0 : 40,
        },
        showlegend: false,
        title:
          title === undefined
            ? undefined
            : {
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
  }, [data, disableHover, setPlotState, title]);

  return (
    <div className={cn(styles.container, className)}>
      <ResizableGraph
        className={styles.graph}
        isLoading={isLoading}
        onChange={setPlotState}
        state={plotState}
      />
      {onLegendClick ? (
        <div className={styles["legend-container"]}>
          <div className={styles.legend}>
            {PROJECTS.map(p => (
              <label
                className={
                  visibleTraces.includes(p)
                    ? styles["label-checked"]
                    : styles.label
                }
                key={p}
                style={{
                  ["--checkbox-color-override" as string]: COLOR_MAP[p],
                }}
              >
                <Checkbox
                  checked={visibleTraces.includes(p)}
                  onClick={() => onLegendClick(p)}
                />
                <span>{LEGEND_MAP[p]}</span>
              </label>
            ))}
          </div>
          <div className={styles["date-range-container"]}>
            {isErrorLoading && (
              <div className={styles["error-message"]}>
                Error fetching new dates
              </div>
            )}
            <DateRangeInput
              alignPopover="end"
              from={from}
              onChange={onChangeDateRange}
              to={to}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default QualityGraph;
