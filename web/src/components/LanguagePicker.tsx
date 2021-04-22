import * as React from "react";
import { Select } from "web-ui";

const LANGUAGES: Record<JSONAPI.LanguageId, string> = {
  fr: "French",
  de: "German",
  en: "English",
  es: "Spanish",
  it: "Italian",
  ja: "Japanese",
  ru: "Russian",
  xx: "Other",
  zh: "Chinese",
};

interface Props {
  className?: string;
  onChange: (value: JSONAPI.LanguageId) => void;
  value: JSONAPI.LanguageId;
}

const LanguagePicker: React.FC<Props> = ({ className, onChange, value }) => (
  <Select
    className={className}
    onChange={e => onChange(e.target.value as JSONAPI.LanguageId)}
    options={Object.entries(LANGUAGES)
      .map(([key, value]) => ({ text: value, value: key }))
      .sort((a, b) => a.text.localeCompare(b.text))}
    text={`${LANGUAGES[value]} tickets`}
    type="secondary"
    value={value}
  />
);

export default LanguagePicker;
