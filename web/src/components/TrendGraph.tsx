import { useQuery } from "@tanstack/react-query";
import Plotly from "plotly.js-basic-dist";
import * as React from "react";
import createPlotlyComponent from "react-plotly.js/factory";

import { getTimeSeries } from "api/jeeves";
import useFeaturesByTeamAndArea from "components/useFeaturesByTeamAndArea";
import styles from "styles/TrendGraph.scss";

interface PlotState {
  config: unknown;
  data: unknown[];
  frames: unknown[];
  layout: unknown;
}

export interface RangeChangeEvent {
  from?: Date;
  to?: Date;
}

/* eslint-disable @typescript-eslint/naming-convention */
interface RelayoutEvent {
  /** Set when double clicking the plot to reset the range. */
  "xaxis.autorange"?: boolean;
  /** Set when using the range slider. */
  "xaxis.range"?: [string, string];
  /** Set when selecting an area directly on the plot. */
  "xaxis.range[0]"?: string;
  /** Set when selecting an area directly on the plot. */
  "xaxis.range[1]"?: string;
}
/* eslint-enable @typescript-eslint/naming-convention */

const BLACK_TEXT = "#3c3c3c";
const JUICY_MACAW = "#1cb0f6";
const JUICY_SWAN = "#e5e5e5";

const Plot = createPlotlyComponent(Plotly);

interface Props {
  filter?: JSONAPI.ShakeToReportCategory;
  language: JSONAPI.LanguageId;
  onRangeChange?: (e: RangeChangeEvent) => void;
  query: string;
  spikeCategory: string;
  useLemmas: boolean;
  zoomFrom?: Date;
  zoomTo?: Date;
}

const TrendGraph = ({
  filter,
  language: lang,
  onRangeChange,
  query,
  spikeCategory,
  useLemmas,
  zoomFrom,
  zoomTo,
}: Props) => {
  const { data: areas = [], isSuccess: areasLoaded } =
    useFeaturesByTeamAndArea();

  const { data } = useQuery(
    ["time-series", { areas, filter, lang, query, spikeCategory, useLemmas }],
    () =>
      getTimeSeries(lang, {
        areas,
        beta_filter: filter,
        spike_category: spikeCategory,
        use_lemmas: useLemmas,
        word: query,
      }),
    {
      enabled: areasLoaded && !!query,
    },
  );

  const [plotState, setPlotState] = React.useState<PlotState>({
    config: {},
    data: [],
    frames: [],
    layout: {},
  });

  const containerRef = React.useRef<HTMLDivElement>(null);
  const plotRef = React.useRef<typeof Plot>(null);

  const handleRelayout = (e: RelayoutEvent) => {
    if (!data) {
      return;
    }
    let from = e["xaxis.range"]?.[0] ?? e["xaxis.range[0]"];
    let to = e["xaxis.range"]?.[1] ?? e["xaxis.range[1]"];
    if (from !== undefined || to !== undefined) {
      // Plotly doesn't really document this event and doesn't
      // supply the data in a consistent format. Just in case
      // they would provide a date-only string, pad it with
      // zeroes to force the Date constructor to treat it as
      // a date in the local timezone.
      if (from?.length === 10) {
        from += " 00:00:00";
      }
      if (to?.length === 10) {
        to += " 00:00:00";
      }
      onRangeChange?.({
        from: from ? new Date(from) : undefined,
        to: to ? new Date(to) : undefined,
      });
    } else if (e["xaxis.autorange"]) {
      // User double clicked the plot to reset the range.
      onRangeChange?.({ from: undefined, to: undefined });
    }
  };

  React.useEffect(() => {
    if (containerRef.current && plotRef.current) {
      const observer = new ResizeObserver(() =>
        Plotly.Plots.resize(plotRef.current.el),
      );
      observer.observe(containerRef.current);
      return () => observer.disconnect();
    }
    return undefined;
  }, []);

  React.useEffect(() => {
    const x = data?.map(({ date }) => date);
    const y = data?.map(({ value }) => value);

    const range = x
      ? [
          zoomFrom ?? new Date(Math.min(...x.map(d => d.valueOf()))),
          zoomTo ?? new Date(Math.max(...x.map(d => d.valueOf()))),
        ]
      : undefined;

    setPlotState({
      config: {
        displayModeBar: false,
        showTips: false,
      },
      data: [
        {
          line: {
            color: JUICY_MACAW,
          },
          mode: "lines",
          type: "scatter",
          x,
          y,
        },
      ],
      frames: [],
      layout: {
        autosize: true,
        font: {
          color: BLACK_TEXT,
          family: "din-round, sans-serif",
        },
        margin: {
          b: 10,
          l: 50,
          r: 10,
          t: 10,
        },
        xaxis: {
          gridcolor: JUICY_SWAN,
          range,
          rangeslider: {
            visible: true,
          },
        },
        yaxis: {
          fixedrange: true,
          gridcolor: JUICY_SWAN,
          rangemode: "tozero",
          title: "# of tickets",
        },
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, zoomFrom?.valueOf(), zoomTo?.valueOf()]);

  return (
    <div className={styles.container} ref={containerRef}>
      <div className={styles.inner}>
        <Plot
          className={styles.plot}
          config={plotState.config}
          data={plotState.data}
          frames={plotState.frames}
          layout={plotState.layout}
          onInitialized={(figure: Partial<PlotState>) =>
            setPlotState(value => ({ ...value, figure }))
          }
          onRelayout={handleRelayout}
          onUpdate={(figure: Partial<PlotState>) =>
            setPlotState(value => ({ ...value, figure }))
          }
          ref={plotRef}
        />
      </div>
    </div>
  );
};

export default TrendGraph;
