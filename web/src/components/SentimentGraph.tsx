import Plotly from "plotly.js-basic-dist";
import * as React from "react";
import createPlotlyComponent from "react-plotly.js/factory";

import styles from "styles/SentimentGraph.scss";

interface PlotState {
  config: unknown;
  data: unknown[];
  frames: unknown[];
  layout: unknown;
}

const BLACK_TEXT = "#3c3c3c";
const JUICY_SWAN = "#e5e5e5";
const JUICY_OWL = "#58cc02";
const JUICY_CARDINAL = "#ff4b4b";

const Plot = createPlotlyComponent(Plotly);

interface Props {
  negativeBucket: { date: Date; score: number; count: number }[];
  positiveBucket: { date: Date; score: number; count: number }[];
}

const BUCKET_SIZE = 0.2;
const getColorOpacity = (score: number): string => {
  const lowerBound = Math.floor(score / BUCKET_SIZE) * BUCKET_SIZE;
  const color = score > 0 ? JUICY_OWL : JUICY_CARDINAL;
  const opacityBucket = Math.max(Math.abs(lowerBound), 0.2);
  return `${color}${Math.round(opacityBucket * 255)
    .toString(16)
    .toUpperCase()
    .padStart(2, "0")}`;
};

const SentimentGraph = ({ negativeBucket, positiveBucket }: Props) => {
  const [plotState, setPlotState] = React.useState<PlotState>({
    config: {},
    data: [],
    frames: [],
    layout: {},
  });

  const containerRef = React.useRef<HTMLDivElement>(null);
  const plotRef = React.useRef<typeof Plot>(null);

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
    const positiveX = positiveBucket?.map(({ date }) => date);
    const negativeX = negativeBucket?.map(({ date }) => date);
    const positiveY = positiveBucket?.map(({ count }) =>
      parseFloat(count.toFixed(4)),
    );
    const negativeY = negativeBucket?.map(({ count }) =>
      parseFloat(count.toFixed(4)),
    );
    const positiveColors = positiveBucket?.map(({ score }) =>
      getColorOpacity(score),
    );
    const negativeColors = negativeBucket?.map(({ score }) =>
      getColorOpacity(score),
    );
    const positiveText = positiveBucket?.map(
      bucket =>
        `Count: ${bucket.count}<br>Avg. sentiment: ${bucket.score.toFixed(3)}`,
    );
    const negativeText = negativeBucket?.map(
      bucket =>
        `Count: ${bucket.count}<br>Avg. sentiment: ${bucket.score.toFixed(3)}`,
    );

    const completeX = positiveX.concat(negativeX);
    const range = completeX
      ? [
          new Date(Math.min(...completeX.map(d => d.valueOf()))),
          new Date(Math.max(...completeX.map(d => d.valueOf()))),
        ]
      : undefined;

    setPlotState({
      config: {
        displayModeBar: false,
        showTips: false,
      },
      data: [
        {
          hovertemplate: "%{text}",
          marker: {
            color: positiveColors, // Map higher scores to darker shades of green
          },
          name: "",
          text: positiveText,
          type: "bar",
          x: positiveX,
          y: positiveY,
        },
        {
          hovertemplate: "%{text}",
          marker: {
            color: negativeColors, // Map higher scores to darker shades of red
          },
          name: "",
          text: negativeText,
          type: "bar",
          x: negativeX,
          y: negativeY,
        },
      ],
      frames: [],
      layout: {
        autosize: true,
        barmode: "group",
        font: {
          color: BLACK_TEXT,
          family: "din-round, sans-serif",
        },
        hovermode: "x",
        margin: {
          b: 10,
          l: 50,
          r: 10,
          t: 10,
        },
        showlegend: false,
        xaxis: {
          gridcolor: JUICY_SWAN,
          range,
          rangeslider: {
            visible: true,
          },
        },
        yaxis: {
          gridcolor: JUICY_SWAN,
          rangemode: "tozero",
          title: "# of documents",
        },
      },
    });
  }, [positiveBucket, negativeBucket]);

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
          onUpdate={(figure: Partial<PlotState>) =>
            setPlotState(value => ({ ...value, figure }))
          }
          ref={plotRef}
        />
      </div>
    </div>
  );
};

export default SentimentGraph;
