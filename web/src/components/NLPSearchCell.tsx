import * as React from "react";

import styles from "styles/NLPSearchCell.scss";

interface Props {
  cell: JSONAPI.LanguageContent | undefined;
}

const getHoverText = (cell: JSONAPI.LanguageContent): string | undefined =>
  cell.body_orig
    ? `Original text from OpenSearch:\n${cell.body_orig}`
    : undefined;

const renderBoldTags = (body: string) => {
  const parts = body.split(/(<b>|<\/b>)/);
  return parts.map((part, index) => {
    if (part === "<b>") {
      return <b key={index}>{parts[index + 1]}</b>;
    }
    if (part === "</b>" || parts[index - 1] === "<b>") {
      return null;
    }
    return part;
  });
};

const NLPSearchCell = ({ cell }: Props) =>
  cell ? (
    <td className={styles.cell} title={getHoverText(cell)}>
      {cell.title && (
        <div className={styles.title}>
          Title: {cell.title}
          <br />
        </div>
      )}
      <div className={styles.body}>{renderBoldTags(cell.body)}</div>
    </td>
  ) : (
    <td />
  );

export default NLPSearchCell;
