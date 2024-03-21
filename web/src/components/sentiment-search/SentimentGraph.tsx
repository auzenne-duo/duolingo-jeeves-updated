import * as React from "react";

import ResizableGraph, { usePlotState } from "components/ResizableGraph";
import styles from "components/sentiment-search/SentimentGraph.module.scss";

const BUCKET_SIZE = 0.2;

// Colors
const BLACK_TEXT = "#3c3c3c";
const JUICY_SWAN = "#e5e5e5";
const JUICY_OWL = "#58cc02";
const JUICY_CARDINAL = "#ff4b4b";

interface Props {
  negativeBucket: { date: Date; score: number; count: number }[];
  positiveBucket: { date: Date; score: number; count: number }[];
}

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
  const [plotState, setPlotState] = usePlotState();

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

    const range = [
      new Date(Math.min(...completeX.map(d => d.valueOf()))),
      new Date(Math.max(...completeX.map(d => d.valueOf()))),
    ];

    setPlotState({
      config: {
        displayModeBar: false,
        showTips: false,
      },
      data: [
        {
          customdata: positiveText,
          hovertemplate: "%{customdata}",
          marker: {
            color: positiveColors, // Map higher scores to darker shades of green
          },
          name: "",
          type: "bar",
          x: positiveX,
          y: positiveY,
        },
        {
          customdata: negativeText,
          hovertemplate: "%{customdata}",
          marker: {
            color: negativeColors, // Map higher scores to darker shades of red
          },
          name: "",
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
  }, [negativeBucket, positiveBucket, setPlotState]);

  return (
    <ResizableGraph
      className={styles.graph}
      onChange={setPlotState}
      state={plotState}
    />
  );
};

export default SentimentGraph;
