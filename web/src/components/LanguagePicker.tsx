import * as React from "react";
import { Select } from "web-ui";

const LANGUAGES = {
  en: "English",
  es: "Spanish",
  ja: "Japanese",
  zh: "Chinese",
};

export type LanguageId = keyof typeof LANGUAGES;

interface Props {
  className?: string;
  onChange: (value: LanguageId) => void;
  value: LanguageId;
}

const LanguagePicker: React.FC<Props> = ({ className, onChange, value }) => (
  <Select
    className={className}
    onChange={e => onChange(e.target.value as LanguageId)}
    options={Object.entries(LANGUAGES)
      .map(([key, value]) => ({ text: value, value: key }))
      .sort((a, b) => a.text.localeCompare(b.text))}
    text={`${LANGUAGES[value]} tickets`}
    type="secondary"
    value={value}
  />
);

export default LanguagePicker;
